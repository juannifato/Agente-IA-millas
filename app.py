"""Backend del Agente Millas IA.

Expone la API que consume la aplicacion de Visual Basic (Fase 5):

    GET  /salud       -> chequeo de que el servidor esta vivo
    GET  /aerolineas  -> lista de aerolineas soportadas
    POST /buscar      -> busca vuelos y devuelve el mas conveniente

Todas las respuestas son JSON, incluso los errores, para que el cliente de
Visual Basic nunca tenga que parsear HTML.
"""
import re
from datetime import date, datetime

from flask import Flask, jsonify, request

import aeropuertos
import busqueda
import scrapers
import token_estado
from config import DEBUG, PORT
from ia import ErrorRecorte, conversacion
from ia.analisis_ia import ErrorIA
from scrapers.base import ErrorScraper

app = Flask(__name__)
# Sin esto Flask ordena las claves alfabeticamente y el JSON queda ilegible.
app.json.sort_keys = False

IATA = re.compile(r"^[A-Z]{3}$")
FORMATOS_FECHA = ("%d/%m/%Y", "%Y-%m-%d")


class ErrorDeDatos(Exception):
    """Los datos que mando el cliente no sirven."""


def _leer_iata(valor, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ErrorDeDatos(f"Falta el campo '{campo}'.")
    codigo = valor.strip().upper()
    if not IATA.match(codigo):
        raise ErrorDeDatos(
            f"El campo '{campo}' debe ser un codigo IATA de 3 letras (ej. BUE), "
            f"y llego '{valor}'."
        )
    return codigo


def _leer_fecha(valor) -> str:
    """Acepta DD/MM/AAAA (lo que manda Visual Basic) o AAAA-MM-DD."""
    if not isinstance(valor, str) or not valor.strip():
        raise ErrorDeDatos("Falta el campo 'fecha'.")
    texto = valor.strip()
    for formato in FORMATOS_FECHA:
        try:
            fecha = datetime.strptime(texto, formato).date()
            break
        except ValueError:
            continue
    else:
        # No se distingue "mal formato" de "fecha inexistente" a proposito:
        # strptime rechaza 31/02/2026 con el mismo ValueError, y para el
        # usuario el consejo util es el mismo en los dos casos.
        raise ErrorDeDatos(
            f"La fecha '{texto}' no es valida. Se espera DD/MM/AAAA (ej. 25/12/2026)."
        )

    if fecha < date.today():
        raise ErrorDeDatos(f"La fecha {texto} ya paso.")
    return fecha.isoformat()


def _leer_adultos(valor) -> int:
    """Cantidad de adultos. Ausente vale 1; la API acepta hasta 9."""
    if valor is None or valor == "":
        return 1
    try:
        cantidad = int(valor)
    except (TypeError, ValueError):
        raise ErrorDeDatos(f"El campo 'adultos' debe ser un numero, y llego '{valor}'.")
    if not 1 <= cantidad <= 9:
        raise ErrorDeDatos("El campo 'adultos' debe estar entre 1 y 9.")
    return cantidad


@app.get("/salud")
def salud():
    return jsonify({
        "ok": True,
        "servicio": "Agente Millas IA",
        "version": "0.1",
        "aerolineas": len(scrapers.DISPONIBLES),
    })


@app.get("/aerolineas")
def aerolineas():
    return jsonify({"ok": True, "aerolineas": scrapers.catalogo()})


@app.get("/aeropuertos")
def listar_aeropuertos():
    # La app de escritorio lo pide al arrancar para el autocompletado de origen
    # y destino (escribir "bariloche" y que sugiera BRC).
    return jsonify({"ok": True, "aeropuertos": aeropuertos.catalogo()})


@app.get("/token/estado")
def estado_token():
    # La app lo consulta para mostrar si el token esta vigente o vencido.
    datos = token_estado.info(token_estado.token_vigente())
    return jsonify({"ok": True, "hay_token": bool(token_estado.token_vigente()), **datos})


@app.post("/token")
def cambiar_token():
    # La app manda el token nuevo (que Juan copia del navegador) y se actualiza
    # en caliente, sin reiniciar ni editar archivos.
    cuerpo = request.get_json(silent=True)
    if not isinstance(cuerpo, dict) or not isinstance(cuerpo.get("token"), str):
        return jsonify({"ok": False, "motivo": "cuerpo_invalido",
                        "error": "Se esperaba un JSON con 'token'."}), 400

    token = cuerpo["token"].strip()
    datos = token_estado.info(token)
    if not datos["valido"]:
        return jsonify({"ok": False, "motivo": "token_invalido",
                        "error": "Eso no parece un token valido (tiene que ser un JWT)."}), 400
    if datos["vencido"]:
        return jsonify({"ok": False, "motivo": "token_vencido",
                        "error": "Ese token ya esta vencido. Copiá uno nuevo del navegador."}), 400

    token_estado.actualizar_token(token)
    return jsonify({"ok": True, "vence": datos["vence"], "minutos": datos["minutos"]})


@app.post("/buscar")
def buscar():
    cuerpo = request.get_json(silent=True)
    if not isinstance(cuerpo, dict):
        return jsonify({
            "ok": False,
            "motivo": "cuerpo_invalido",
            "error": "Se esperaba un cuerpo JSON con origen, destino y fecha.",
        }), 400

    try:
        origen = _leer_iata(cuerpo.get("origen"), "origen")
        destino = _leer_iata(cuerpo.get("destino"), "destino")
        fecha_iso = _leer_fecha(cuerpo.get("fecha"))
        if origen == destino:
            raise ErrorDeDatos("El origen y el destino no pueden ser iguales.")

        # La vuelta es opcional: sin ella se busca solo ida.
        vuelta = cuerpo.get("fecha_vuelta")
        fecha_vuelta_iso = _leer_fecha(vuelta) if vuelta else None
        if fecha_vuelta_iso and fecha_vuelta_iso < fecha_iso:
            raise ErrorDeDatos("La fecha de vuelta es anterior a la de ida.")

        adultos = _leer_adultos(cuerpo.get("adultos"))
        clave = (cuerpo.get("aerolinea") or scrapers.CLAVE_POR_DEFECTO).strip()
    except ErrorDeDatos as e:
        return jsonify({"ok": False, "motivo": "datos_invalidos", "error": str(e)}), 400

    consulta = {
        "origen": origen,
        "destino": destino,
        "fecha": fecha_iso,
        "fecha_vuelta": fecha_vuelta_iso,
        "adultos": adultos,
        "aerolinea": clave,
    }

    try:
        resultado = busqueda.buscar_vuelos(
            origen, destino, fecha_iso, fecha_vuelta_iso, adultos, clave)
    except ErrorScraper as e:
        # Cada motivo dice de quien es el problema, y el codigo HTTP debe
        # coincidir: 400 si los datos que llegaron estan mal, 503 si al backend
        # le falta configuracion, y 502 si fallo la aerolinea de la que dependemos.
        codigo = {
            "aerolinea_desconocida": 400,
            "falta_token": 503,
            "token_vencido": 503,
        }.get(e.motivo, 502)
        return jsonify({"ok": False, "motivo": e.motivo, "error": str(e),
                        "consulta": consulta}), codigo
    except ErrorRecorte as e:
        # Si el recorte falla es porque la aerolinea cambio la forma de su
        # respuesta: el problema es de ellos, no de los datos del cliente.
        return jsonify({"ok": False, "motivo": e.motivo, "error": str(e),
                        "consulta": consulta}), 502
    except ErrorIA as e:
        # 503 si al backend le falta la clave de Groq; 502 si Groq fallo.
        codigo = 503 if e.motivo == "falta_clave_groq" else 502
        return jsonify({"ok": False, "motivo": e.motivo, "error": str(e),
                        "consulta": consulta}), codigo

    if resultado["vacio"]:
        # La busqueda salio bien pero vino vacia: 200 con mejor null.
        return jsonify({
            "ok": True, "consulta": consulta, "mejor": None,
            "mensaje": "No se encontraron vuelos en millas para esas fechas.",
        })

    return jsonify({
        "ok": True,
        "consulta": consulta,
        "mejor": resultado["mejor"],
        "analisis": resultado["analisis"],
        "eleccion_por_ia": resultado["eleccion_por_ia"],
        "opciones_evaluadas": resultado["opciones_evaluadas"],
    })


@app.post("/chat")
def chat():
    # El agente conversacional: el usuario escribe en criollo y aca se entiende
    # el pedido y, si alcanza, se busca. El estado de la charla lo manda el
    # cliente en cada mensaje (Flask no guarda sesion).
    cuerpo = request.get_json(silent=True)
    if not isinstance(cuerpo, dict):
        return jsonify({"ok": False, "motivo": "cuerpo_invalido",
                        "error": "Se esperaba un cuerpo JSON con 'mensaje'."}), 400
    estado = cuerpo.get("estado")
    resultado = conversacion.conversar(
        cuerpo.get("mensaje", ""),
        estado if isinstance(estado, dict) else None,
    )
    # Siempre 200: el chat responde con texto aunque algo haya fallado (el
    # motivo va igual dentro, por si el frontend quiere reaccionar).
    return jsonify({"ok": True, **resultado})


@app.errorhandler(404)
def no_encontrado(_e):
    return jsonify({"ok": False, "motivo": "ruta_inexistente",
                    "error": "Esa ruta no existe. Ver /salud."}), 404


@app.errorhandler(405)
def metodo_incorrecto(_e):
    return jsonify({"ok": False, "motivo": "metodo_incorrecto",
                    "error": "Metodo HTTP no permitido en esa ruta."}), 405


@app.errorhandler(500)
def error_interno(_e):
    return jsonify({"ok": False, "motivo": "error_interno",
                    "error": "Error inesperado en el servidor."}), 500


if __name__ == "__main__":
    # Solo para desarrollo local. En Render arranca gunicorn (Fase 6).
    print(f"Agente Millas IA escuchando en http://127.0.0.1:{PORT}")
    app.run(host="127.0.0.1", port=PORT, debug=DEBUG)
