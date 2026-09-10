"""Cerebro analitico: le pide a Groq que elija la tarifa mas conveniente.

Recibe el JSON ya recortado por `ia/recorte.py` (no el crudo de la aerolinea) y
le pide al modelo que, por cada tramo, elija un `id` de tarifa. La IA devuelve
solo ids; despues Python reconstruye la respuesta final desde el recorte. Se
hace asi por dos motivos:

- El modelo no tiene que copiar numeros de millas (que es donde se equivocaria),
  solo elegir entre opciones que ya existen.
- Si la IA falla o elige un id que no existe, Python cae a una regla simple
  (la tarifa con menos millas), asi el endpoint nunca se queda sin responder.

gpt-oss razona antes de escribir: por eso `max_tokens` holgado y
`reasoning_effort: "low"`, si no se queda sin presupuesto y devuelve vacio.
"""
import json

import requests

from config import GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL, TIMEOUT, USER_AGENT


class ErrorIA(Exception):
    """Falla al analizar con la IA. `motivo` es el codigo corto para el frontend."""

    def __init__(self, mensaje: str, motivo: str = "error_ia"):
        super().__init__(mensaje)
        self.motivo = motivo


# El modelo elige ids; el criterio de "conveniente" lo define este prompt para
# que la decision sea explicable y no dependa del humor del modelo.
INSTRUCCIONES = (
    "Sos un comparador de pasajes en millas. Te paso un JSON con los vuelos "
    "disponibles agrupados por tramo ('ida' y, si hay, 'vuelta'). Cada vuelo "
    "tiene una o mas tarifas, y cada tarifa trae un 'id', el costo en 'millas', "
    "los 'impuestos' y los 'asientos' disponibles.\n\n"
    "Tu tarea: por cada tramo, elegir la tarifa MAS CONVENIENTE. Conveniencia, "
    "en orden de prioridad:\n"
    "1. Menos millas.\n"
    "2. Si dos opciones tienen millas parecidas (diferencia menor al 10%), "
    "preferir menos impuestos, menos escalas y menor duracion.\n"
    "3. Evita las tarifas con 'asientos' en 0.\n\n"
    "Responde SOLO con un objeto JSON, sin texto afuera, con esta forma exacta:\n"
    '{"tramos": [{"tramo": "<nombre>", "id": "<id elegido>"}], '
    '"analisis": "<una o dos frases en espanol rioplatense explicando por que>"}\n'
    "Usa unicamente ids que aparezcan en el tramo correspondiente y devolve "
    "exactamente un id por cada tramo que te paso."
)


def _indice_ids(recortado: dict) -> dict:
    """id de tarifa -> (nombre del tramo, vuelo, tarifa). Para reconstruir."""
    indice = {}
    for tramo in recortado.get("tramos", []):
        for vuelo in tramo.get("vuelos", []):
            for tarifa in vuelo.get("tarifas", []):
                indice[tarifa["id"]] = (tramo["tramo"], vuelo, tarifa)
    return indice


def _mejor_por_regla(vuelos: list) -> tuple | None:
    """Red de seguridad si la IA no sirve: la tarifa con menos millas.

    Desempata igual que el prompt: a igualdad de millas, menos impuestos, menos
    escalas y menor duracion. Devuelve (vuelo, tarifa) o None si no hay nada.
    """
    mejor = None
    for vuelo in vuelos:
        for tarifa in vuelo.get("tarifas", []):
            orden = (
                tarifa.get("millas", float("inf")),
                tarifa.get("impuestos") or 0,
                vuelo.get("escalas") or 0,
                vuelo.get("duracion_min") or 10 ** 9,
            )
            if mejor is None or orden < mejor[0]:
                mejor = (orden, vuelo, tarifa)
    return (mejor[1], mejor[2]) if mejor else None


def _fila(nombre: str, vuelo: dict, tarifa: dict) -> dict:
    """Arma la fila final que ve Visual Basic: vuelo + la tarifa elegida."""
    return {
        "tramo": nombre,
        "numeros": vuelo.get("numeros"),
        "origen": vuelo.get("origen"),
        "destino": vuelo.get("destino"),
        "sale": vuelo.get("sale"),
        "llega": vuelo.get("llega"),
        "escalas": vuelo.get("escalas"),
        "duracion_min": vuelo.get("duracion_min"),
        "tarifa": tarifa.get("tarifa"),
        "millas": tarifa.get("millas"),
        "impuestos": tarifa.get("impuestos"),
        "asientos": tarifa.get("asientos"),
    }


def _construir_mejor(recortado: dict, elecciones: dict) -> tuple[dict, bool]:
    """Reconstruye la recomendacion desde el recorte y las elecciones de la IA.

    `elecciones` es {nombre_tramo: id}. Por cada tramo usa el id de la IA si es
    valido y pertenece a ese tramo; si no, cae a la regla. Devuelve la
    recomendacion y un bool que dice si hubo que usar la red de seguridad.
    """
    indice = _indice_ids(recortado)
    filas, uso_regla = [], False
    for tramo in recortado.get("tramos", []):
        nombre = tramo["tramo"]
        elegido = elecciones.get(nombre)
        par = None
        if elegido in indice and indice[elegido][0] == nombre:
            _, vuelo, tarifa = indice[elegido]
            par = (vuelo, tarifa)
        else:
            # La IA no eligio, eligio un id inexistente, o de otro tramo.
            uso_regla = True
            par = _mejor_por_regla(tramo.get("vuelos", []))
        if par:
            filas.append(_fila(nombre, par[0], par[1]))

    mejor = {
        "millas": sum(f["millas"] for f in filas),
        "impuestos": sum((f["impuestos"] or 0) for f in filas),
        "tramos": filas,
    }
    return mejor, uso_regla


def _pedir_a_groq(mensajes: list) -> dict:
    """Una llamada a Groq. Devuelve el JSON parseado o levanta ErrorIA."""
    try:
        r = requests.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
                # El Cloudflare de Groq rechaza User-Agent genericos de librerias.
                "User-Agent": USER_AGENT,
            },
            timeout=TIMEOUT,
            json={
                "model": GROQ_MODEL,
                "max_tokens": 1024,
                "reasoning_effort": "low",
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": mensajes,
            },
        )
    except requests.Timeout as e:
        raise ErrorIA("Groq tardo demasiado en responder.", "ia_timeout") from e
    except requests.RequestException as e:
        raise ErrorIA(f"No se pudo conectar con Groq: {e}", "ia_sin_conexion") from e

    if r.status_code == 401:
        raise ErrorIA("Groq rechazo la clave (GROQ_API_KEY).", "ia_clave_invalida")
    if r.status_code == 429:
        raise ErrorIA("Groq: demasiadas consultas seguidas, esperar un momento.",
                      "ia_limite")
    if r.status_code != 200:
        raise ErrorIA(f"Groq respondio con codigo {r.status_code}: {r.text[:200]}",
                      "ia_error")

    try:
        cuerpo = r.json()
        contenido = cuerpo["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError) as e:
        raise ErrorIA("Groq devolvio una respuesta con forma inesperada.",
                      "ia_sin_respuesta") from e

    if not contenido or not contenido.strip():
        # Sintoma clasico de gpt-oss sin presupuesto: gasto todo razonando.
        raise ErrorIA("Groq devolvio una respuesta vacia (posible falta de tokens).",
                      "ia_sin_respuesta")

    try:
        return json.loads(contenido)
    except json.JSONDecodeError as e:
        raise ErrorIA("Groq no devolvio un JSON valido.", "ia_json_invalido") from e


def analizar(recortado: dict) -> dict:
    """Elige la tarifa mas conveniente por tramo.

    Args:
        recortado: la salida de `ia.recorte.recortar`.

    Returns:
        dict con `mejor` (la recomendacion armada), `analisis` (texto de la IA)
        y `eleccion_por_ia` (False si hubo que caer a la regla en algun tramo).

    Raises:
        ErrorIA: si falta la clave o Groq no responde utilmente.
    """
    if not GROQ_API_KEY or "pegar_aca" in GROQ_API_KEY:
        raise ErrorIA("Falta la clave de Groq (GROQ_API_KEY en el .env).",
                      "falta_clave_groq")

    nombres = [t["tramo"] for t in recortado.get("tramos", [])]
    mensajes = [
        {"role": "system", "content": INSTRUCCIONES},
        {"role": "user", "content": (
            f"Tramos a resolver: {nombres}. Vuelos disponibles (JSON):\n"
            f"{json.dumps(recortado, ensure_ascii=False)}"
        )},
    ]

    data = _pedir_a_groq(mensajes)

    elecciones = {}
    for item in data.get("tramos", []):
        if isinstance(item, dict) and item.get("tramo") and item.get("id"):
            elecciones[item["tramo"]] = item["id"]

    mejor, uso_regla = _construir_mejor(recortado, elecciones)
    return {
        "mejor": mejor,
        "analisis": (data.get("analisis") or "").strip(),
        "eleccion_por_ia": not uso_regla,
    }
