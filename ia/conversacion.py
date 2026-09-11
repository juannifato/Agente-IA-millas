"""Cerebro conversacional del chat: entiende el pedido y dispara la busqueda.

A diferencia de `analisis_ia` (que elige la mejor tarifa de una lista), aca la IA
hace de recepcionista: lee lo que el usuario escribe en criollo, saca origen,
destino, fechas y pasajeros, y decide si ya puede buscar o si tiene que
repreguntar. Cuando tiene lo minimo, llama al mismo motor de busqueda que usa el
formulario (`busqueda.buscar_vuelos`).

Guardrails: la IA tiene instruccion estricta de responder SOLO sobre busqueda de
vuelos en millas. Si le preguntan otra cosa (una receta, codigo, lo que sea), no
contesta el tema: redirige. Ademas `conversar` nunca revienta: cualquier falla se
traduce a un mensaje amable, asi el chat siempre responde algo.
"""
from datetime import date, datetime

import aeropuertos
import busqueda
from ia.analisis_ia import ErrorIA
from ia.groq_cliente import ErrorGroq, pedir_json
from scrapers.base import ErrorScraper

# Errores de la aerolinea/IA traducidos a un mensaje que entiende cualquiera.
_DISCULPAS = {
    "token_vencido": "Ahora mismo no puedo consultar los vuelos (se venció el acceso a la aerolínea). Probá de nuevo en un rato.",
    "falta_token": "Todavía no está configurado el acceso a la aerolínea. Avisale al administrador.",
    "falta_clave_groq": "Me falta la configuración de la IA para poder pensar. Avisale al administrador.",
    "limite_de_consultas": "Hicimos muchas búsquedas seguidas y la aerolínea nos frenó. Esperá unos minutos.",
}


def _lista_aeropuertos() -> str:
    """'AEP: Buenos Aires\\nEZE: Buenos Aires\\n...' para que la IA mapee ciudades."""
    return "\n".join(f"{a['iata']}: {a['ciudad']}, {a['pais']}"
                     for a in aeropuertos.catalogo())


def _instrucciones(hoy: date) -> str:
    return (
        "Sos el asistente de 'Agente Millas IA', un buscador de pasajes en millas "
        "de aerolineas. Tu UNICA funcion es ayudar a buscar vuelos en millas: "
        "entender origen, destino, fechas y cantidad de pasajeros de lo que "
        "escribe el usuario.\n\n"
        "GUARDRAILS (obligatorio):\n"
        "- Si el usuario pide cualquier cosa que NO sea buscar vuelos (recetas, "
        "programacion, cuentas, consejos, charla general, etc.), NO respondas ese "
        "tema: poné accion 'fuera_de_tema' y en 'mensaje' decile con amabilidad, en "
        "espanol rioplatense, que solo podés ayudarlo a buscar vuelos en millas.\n"
        "- No inventes vuelos, precios ni disponibilidad. Vos solo entendes el "
        "pedido; la busqueda la hace el sistema.\n\n"
        f"Hoy es {hoy.strftime('%d/%m/%Y')}. Convertí las fechas relativas ('el "
        "finde que viene', 'en diciembre', 'manana') a fechas concretas DD/MM/AAAA. "
        "Nunca uses fechas pasadas.\n\n"
        "Aeropuertos disponibles (codigo: ciudad, pais):\n"
        f"{_lista_aeropuertos()}\n"
        "Convertí las ciudades al codigo IATA. Si una ciudad tiene varios "
        "aeropuertos (ej. Buenos Aires: AEP y EZE) y el usuario no aclaro cual, "
        "poné accion 'aclarar' y preguntá cual.\n\n"
        "Respondé SOLO con un objeto JSON con esta forma exacta:\n"
        '{"accion": "buscar|faltan_datos|aclarar|fuera_de_tema", '
        '"origen": "<IATA o null>", "destino": "<IATA o null>", '
        '"fecha": "<DD/MM/AAAA o null>", "fecha_vuelta": "<DD/MM/AAAA o null>", '
        '"adultos": <numero>, "mensaje": "<lo que le decis, en rioplatense>"}\n'
        "Reglas de accion:\n"
        "- 'buscar': ya tenés origen, destino y fecha. En 'mensaje' confirmá corto "
        "que estas buscando.\n"
        "- 'faltan_datos': falta origen, destino o fecha de ida. Pedila.\n"
        "- 'aclarar': hay ambiguedad (varios aeropuertos para una ciudad). Preguntá.\n"
        "- 'fuera_de_tema': el pedido no es sobre buscar vuelos.\n"
        "Si el estado previo ya trae datos, combinálos con el mensaje nuevo."
    )


def _a_iso(fecha_texto) -> str | None:
    """DD/MM/AAAA -> AAAA-MM-DD. None si no es una fecha valida y futura."""
    if not isinstance(fecha_texto, str):
        return None
    try:
        d = datetime.strptime(fecha_texto.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None
    return d.isoformat() if d >= date.today() else None


def _estado_desde(data: dict) -> dict:
    """Toma del JSON de la IA los datos de la busqueda (el estado acumulado)."""
    adultos = data.get("adultos")
    return {
        "origen": data.get("origen") or None,
        "destino": data.get("destino") or None,
        "fecha": data.get("fecha") or None,
        "fecha_vuelta": data.get("fecha_vuelta") or None,
        "adultos": adultos if isinstance(adultos, int) and adultos >= 1 else 1,
    }


def _vacia(mejor=None, **extra) -> dict:
    base = {"accion": None, "respuesta": "", "estado": {}, "mejor": mejor,
            "eleccion_por_ia": None, "opciones_evaluadas": None,
            "consulta": None, "motivo": None}
    base.update(extra)
    return base


def conversar(mensaje: str, estado: dict | None = None, hoy: date | None = None) -> dict:
    """Procesa un mensaje del chat. Nunca levanta: siempre devuelve una respuesta.

    Args:
        mensaje: lo que escribio el usuario.
        estado: lo que se sabe de la busqueda hasta ahora (para varios turnos).
        hoy: la fecha de referencia (para tests); por defecto, hoy.

    Returns:
        dict con `accion`, `respuesta` (texto para el usuario), `estado`
        actualizado, y si hubo busqueda `mejor` + `consulta` + metricas.
    """
    hoy = hoy or date.today()
    estado = estado or {}
    if not isinstance(mensaje, str) or not mensaje.strip():
        return _vacia(accion="faltan_datos",
                      respuesta="Contame a dónde querés viajar y desde dónde.",
                      estado=estado)

    mensajes = [
        {"role": "system", "content": _instrucciones(hoy)},
        {"role": "user", "content": (
            f"Estado actual de la busqueda: {estado}. "
            f"Mensaje del usuario: {mensaje.strip()}"
        )},
    ]

    try:
        data = pedir_json(mensajes)
    except ErrorGroq as e:
        return _vacia(accion="error", estado=estado, motivo=e.motivo,
                      respuesta=_DISCULPAS.get(e.motivo,
                                "Tuve un problema para entenderte. Probá de nuevo."))

    accion = data.get("accion")
    mensaje_ia = (data.get("mensaje") or "").strip()
    nuevo_estado = _estado_desde(data)

    # Fuera de tema o repregunta: solo se devuelve el texto de la IA, sin buscar.
    if accion in ("fuera_de_tema", "aclarar", "faltan_datos"):
        return _vacia(accion=accion, estado=nuevo_estado,
                      respuesta=mensaje_ia or "¿A dónde querés viajar?")

    # Buscar: hace falta origen, destino y una fecha valida.
    fecha_iso = _a_iso(nuevo_estado["fecha"])
    if not (nuevo_estado["origen"] and nuevo_estado["destino"] and fecha_iso):
        return _vacia(accion="faltan_datos", estado=nuevo_estado,
                      respuesta=mensaje_ia or "Me falta el origen, el destino o la fecha.")

    fecha_vuelta_iso = _a_iso(nuevo_estado["fecha_vuelta"])
    consulta = {
        "origen": nuevo_estado["origen"], "destino": nuevo_estado["destino"],
        "fecha": fecha_iso, "fecha_vuelta": fecha_vuelta_iso,
        "adultos": nuevo_estado["adultos"], "aerolinea": None,
    }

    try:
        resultado = busqueda.buscar_vuelos(
            nuevo_estado["origen"], nuevo_estado["destino"], fecha_iso,
            fecha_vuelta_iso, nuevo_estado["adultos"])
    except (ErrorScraper, ErrorIA) as e:
        return _vacia(accion="error", estado=nuevo_estado, motivo=e.motivo,
                      consulta=consulta,
                      respuesta=_DISCULPAS.get(e.motivo,
                                f"No pude completar la búsqueda: {e}"))
    except Exception as e:  # ErrorRecorte u otro imprevisto: no romper el chat
        return _vacia(accion="error", estado=nuevo_estado, motivo="error_busqueda",
                      consulta=consulta,
                      respuesta=f"No pude completar la búsqueda ({e}).")

    if resultado["vacio"]:
        return _vacia(accion="sin_resultados", estado=nuevo_estado, consulta=consulta,
                      respuesta="No encontré vuelos en millas para esas fechas. "
                                "¿Probás con otra fecha?")

    # Con resultado: se combina la confirmacion de la IA con el analisis.
    texto = (f"{mensaje_ia}\n" if mensaje_ia else "")
    texto += (f"Lo más conveniente: {resultado['mejor']['millas']:,} millas "
              f"+ ${resultado['mejor']['impuestos']:,} de impuestos. "
              f"{resultado['analisis']}").replace(",", ".")
    return _vacia(accion="resultado", estado=nuevo_estado, consulta=consulta,
                  respuesta=texto.strip(), mejor=resultado["mejor"],
                  eleccion_por_ia=resultado["eleccion_por_ia"],
                  opciones_evaluadas=resultado["opciones_evaluadas"])
