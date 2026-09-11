"""Cliente de bajo nivel para Groq: una llamada, devuelve el JSON parseado.

Lo comparten los modulos de ia/ que le piden algo a Groq (elegir la mejor
tarifa, entender el pedido del chat). Centraliza las trampas ya conocidas:
Cloudflare rechaza los User-Agent genericos, y gpt-oss razona antes de responder
(por eso `max_tokens` holgado y `reasoning_effort` bajo, si no se queda sin
presupuesto y devuelve vacio).
"""
import json

import requests

from config import GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL, TIMEOUT, USER_AGENT


class ErrorGroq(Exception):
    """Falla al hablar con Groq. `motivo` es el codigo corto para el frontend."""

    def __init__(self, mensaje: str, motivo: str = "error_ia"):
        super().__init__(mensaje)
        self.motivo = motivo


def pedir_json(mensajes: list, max_tokens: int = 1024) -> dict:
    """Manda `mensajes` a Groq y devuelve el JSON de la respuesta ya parseado.

    Raises:
        ErrorGroq: si falta la clave, Groq no responde, o no devuelve JSON valido.
    """
    if not GROQ_API_KEY or "pegar_aca" in GROQ_API_KEY:
        raise ErrorGroq("Falta la clave de Groq (GROQ_API_KEY en el .env).",
                        "falta_clave_groq")

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
                "max_tokens": max_tokens,
                "reasoning_effort": "low",
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": mensajes,
            },
        )
    except requests.Timeout as e:
        raise ErrorGroq("Groq tardo demasiado en responder.", "ia_timeout") from e
    except requests.RequestException as e:
        raise ErrorGroq(f"No se pudo conectar con Groq: {e}", "ia_sin_conexion") from e

    if r.status_code == 401:
        raise ErrorGroq("Groq rechazo la clave (GROQ_API_KEY).", "ia_clave_invalida")
    if r.status_code == 429:
        raise ErrorGroq("Groq: demasiadas consultas seguidas, esperar un momento.",
                        "ia_limite")
    if r.status_code != 200:
        raise ErrorGroq(f"Groq respondio con codigo {r.status_code}: {r.text[:200]}",
                        "ia_error")

    try:
        cuerpo = r.json()
        contenido = cuerpo["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError) as e:
        raise ErrorGroq("Groq devolvio una respuesta con forma inesperada.",
                        "ia_sin_respuesta") from e

    if not contenido or not contenido.strip():
        # Sintoma clasico de gpt-oss sin presupuesto: gasto todo razonando.
        raise ErrorGroq("Groq devolvio una respuesta vacia (posible falta de tokens).",
                        "ia_sin_respuesta")

    try:
        return json.loads(contenido)
    except json.JSONDecodeError as e:
        raise ErrorGroq("Groq no devolvio un JSON valido.", "ia_json_invalido") from e
