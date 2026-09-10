"""Achica la respuesta de la aerolinea a lo unico que se puede comparar.

Medicion real de una busqueda AEP-BRC ida y vuelta (19 vuelos, 137
combinaciones de vuelo y tarifa): la respuesta completa pesa 243.664 bytes,
de los cuales 76.985 son `fareRules` (la letra chica de cada tarifa) y 103.578
son `combinableOffers` (IDs internos para armar combinaciones). El 74% es
ruido que no ayuda a decidir nada.

Mandarle eso crudo al modelo seria lento, caro y menos preciso, asi que el
recorte se hace aca en Python y a la IA le llega solo la tabla comparable.

El otro motivo de este modulo: cada combinacion queda con un `id` estable. La
IA elige un id y despues Python reconstruye la respuesta final desde estos
datos, en vez de confiar en que el modelo copie bien un numero de millas.
"""
import json
from datetime import datetime

# `brandedOffers` no es una lista: es un diccionario con las claves "0" y "1".
# Es la trampa mas cara de esta API, porque un `for` sobre el da los strings
# "0" y "1" en lugar de los vuelos.
NOMBRE_TRAMO = {"0": "ida", "1": "vuelta"}


class ErrorRecorte(Exception):
    """La respuesta de la aerolinea no tiene la forma esperada."""

    def __init__(self, mensaje: str, motivo: str = "respuesta_inesperada"):
        super().__init__(mensaje)
        self.motivo = motivo


def _sin_segundos(marca) -> str | None:
    """Deja '2026-09-15T08:10' y descarta segundos y zona horaria.

    Todos los vuelos de una busqueda estan en la misma zona, asi que esos
    caracteres no aportan nada para comparar y se repiten en cada fila.
    """
    if not isinstance(marca, str) or len(marca) < 16:
        return marca or None
    return marca[:16]


def _minutos(valor) -> int | None:
    """Duracion en minutos.

    Se acepta entero o el formato ISO 'PT2H20M' porque no todas las rutas de
    esta API contestan igual, y una duracion mal leida cambia cual es el mejor
    vuelo.
    """
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return int(valor)
    if isinstance(valor, str):
        texto = valor.strip().upper()
        if texto.isdigit():
            return int(texto)
        if texto.startswith("PT"):
            total, numero = 0, ""
            for c in texto[2:]:
                if c.isdigit():
                    numero += c
                elif numero:
                    total += int(numero) * (60 if c == "H" else 1)
                    numero = ""
            return total or None
    return None


def _duracion_entre(sale, llega) -> int | None:
    """Minutos entre dos marcas de tiempo.

    Solo se usa cuando la aerolinea no manda `totalDuration`: asume que las
    dos horas estan en la misma zona, lo que vale para un vuelo de cabotaje
    pero no para uno internacional. Por eso es el ultimo recurso y no la
    fuente principal.
    """
    if not (isinstance(sale, str) and isinstance(llega, str)):
        return None
    try:
        a = datetime.fromisoformat(sale)
        b = datetime.fromisoformat(llega)
    except ValueError:
        return None
    minutos = int((b - a).total_seconds() // 60)
    return minutos if minutos > 0 else None


def _primero(dic: dict, *claves):
    """Primer valor no vacio entre varias claves posibles."""
    for clave in claves:
        valor = dic.get(clave)
        if valor not in (None, "", [], {}):
            return valor
    return None


def _recortar_vuelo(oferta: dict, id_base: str) -> dict | None:
    """Convierte una oferta de la aerolinea en una fila comparable."""
    legs = oferta.get("legs") or []
    if not legs:
        return None
    leg = legs[0]
    segmentos = leg.get("segments") or []
    if not segmentos:
        return None

    primero, ultimo = segmentos[0], segmentos[-1]
    numeros = [
        f"{s.get('airline', '')}{s.get('flightNumber', '')}".strip()
        for s in segmentos
    ]

    vuelo = {
        "numeros": [n for n in numeros if n],
        "origen": _primero(primero, "origin", "departureAirport"),
        "destino": _primero(ultimo, "destination", "arrivalAirport"),
        "sale": _sin_segundos(_primero(primero, "departure", "departureDate")),
        "llega": _sin_segundos(_primero(ultimo, "arrival", "arrivalDate")),
        # `stops` es la cantidad que declara la aerolinea; si no viene, la
        # cantidad de segmentos menos uno dice lo mismo.
        "escalas": _primero(leg, "stops") or len(segmentos) - 1,
        "duracion_min": _minutos(_primero(leg, "totalDuration", "duration")),
    }
    if vuelo["duracion_min"] is None:
        vuelo["duracion_min"] = _duracion_entre(vuelo["sale"], vuelo["llega"])
    if vuelo["escalas"]:
        vuelo["escalas_en"] = [s.get("destination") for s in segmentos[:-1]]

    tarifas = []
    for i, tarifa in enumerate(oferta.get("offers") or [], start=1):
        fare = tarifa.get("fare") or {}
        millas = _primero(fare, "baseFare")
        if millas is None:
            # Sin millas no hay nada que comparar: esa fila solo gastaria
            # tokens del modelo.
            continue
        asientos = (tarifa.get("seatAvailability") or {}).get("seats")
        tarifas.append({
            "id": f"{id_base}.{i}",
            "tarifa": (tarifa.get("brand") or {}).get("name"),
            "millas": millas,
            # `taxes` viene como entero (ej. 64022) y falta confirmar si son
            # centavos o pesos enteros, asi que se pasa tal cual y no se
            # convierte a nada que despues haya que desandar.
            "impuestos": _primero(fare, "taxes"),
            "asientos": asientos,
        })

    if not tarifas:
        return None
    vuelo["tarifas"] = tarifas
    return vuelo


def recortar(crudo: dict) -> dict:
    """Deja solo los datos con los que se elige un vuelo.

    Args:
        crudo: la respuesta tal cual la devolvio el scraper.

    Returns:
        Un dict con un tramo por cada pata del viaje, cada vuelo con sus
        tarifas, y `total_opciones` con la cantidad de combinaciones. Si es 0
        no hay nada que analizar y no tiene sentido llamar a la IA.

    Raises:
        ErrorRecorte: si la respuesta no trae `brandedOffers`.
    """
    if not isinstance(crudo, dict):
        raise ErrorRecorte("La aerolinea no devolvio un objeto JSON.")

    ofertas = crudo.get("brandedOffers")
    if ofertas is None:
        raise ErrorRecorte(
            "La respuesta de la aerolinea no trae 'brandedOffers'. "
            "Puede que haya cambiado su API.",
            motivo="formato_desconocido",
        )
    if not isinstance(ofertas, dict):
        raise ErrorRecorte(
            f"Se esperaba que 'brandedOffers' fuera un diccionario y llego "
            f"{type(ofertas).__name__}.",
            motivo="formato_desconocido",
        )

    tramos, total = [], 0
    # Ordenado por la clave numerica: el diccionario podria llegar con "1"
    # antes que "0" y mostrarle la vuelta como si fuera la ida.
    for clave in sorted(ofertas, key=lambda k: int(k) if str(k).isdigit() else 99):
        nombre = NOMBRE_TRAMO.get(str(clave), f"tramo_{clave}")
        vuelos = []
        for i, oferta in enumerate(ofertas[clave] or [], start=1):
            vuelo = _recortar_vuelo(oferta, f"{nombre}-{i}")
            if vuelo:
                vuelos.append(vuelo)
                total += len(vuelo["tarifas"])
        if not vuelos:
            continue
        tramos.append({
            "tramo": nombre,
            "origen": vuelos[0]["origen"],
            "destino": vuelos[0]["destino"],
            "vuelos": vuelos,
        })

    return {"tramos": tramos, "total_opciones": total}


def medir(crudo: dict, recortado: dict) -> dict:
    """Cuanto se achico el JSON. Sirve para verlo, no para decidir nada."""
    def bytes_de(dato):
        return len(json.dumps(dato, ensure_ascii=False).encode("utf-8"))

    antes, despues = bytes_de(crudo), bytes_de(recortado)
    return {
        "bytes_antes": antes,
        "bytes_despues": despues,
        "reduccion_pct": round((1 - despues / antes) * 100, 1) if antes else 0,
    }
