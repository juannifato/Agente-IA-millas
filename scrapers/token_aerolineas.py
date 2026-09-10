"""Renovacion automatica del token de Aerolineas Argentinas.

CONTEXTO (2026-09-10): el token de la API es un JWT anonimo que dura 24 h
exactas. Hasta ahora se pega a mano en AEROLINEAS_TOKEN. Para dejar el sistema
desatendido en Render (Fase 6) hay que renovarlo solo.

Se averiguo de donde sale: `POST https://api.aerolineas.com.ar/v1/auth/token`,
que pide un `client_id` y un `client_secret`. El `client_id` es publico y viaja
dentro del propio JWT (por eso el default de abajo). El `client_secret` lo tiene
que cargar Juan en AEROLINEAS_CLIENT_SECRET: es una credencial de la web, no se
pide por chat ni se commitea.

Lo que NO esta confirmado todavia (falta el secret para probar de verdad):
    - el nombre exacto de los campos del cuerpo (camelCase vs snake_case),
    - la forma de la respuesta (donde viene el token).
Por eso `obtener_token` prueba las variantes razonables y `renovar_token.py`
imprime la respuesta cruda, para ajustar en cuanto haya un secret y veamos el
200 real. Mientras tanto este modulo no esta enganchado al flujo de /buscar:
se activa recien cuando la renovacion este probada.
"""
import base64
import json
import os
import time

import requests

from config import TIMEOUT, USER_AGENT

URL_TOKEN = "https://api.aerolineas.com.ar/v1/auth/token"

# client_id publico, extraido del campo `azp`/`sub` del JWT que venia a mano.
# Se puede pisar por entorno si algun dia cambia.
CLIENT_ID = os.getenv("AEROLINEAS_CLIENT_ID", "oy81ZUn6IX1gv4eGceSFIyaFfhH6a66G")


class ErrorToken(Exception):
    """No se pudo obtener un token nuevo."""

    def __init__(self, mensaje: str, motivo: str = "error_token"):
        super().__init__(mensaje)
        self.motivo = motivo


def _cuerpos_candidatos(client_id: str, client_secret: str) -> list[tuple]:
    """Las formas de cuerpo mas probables, en orden.

    No sabemos cual acepta el endpoint hasta probar con un secret real, asi que
    se intentan de la mas probable (camelCase, como el resto de su API) a la
    menos. Cada tupla es (tipo, payload).
    """
    return [
        ("json", {"clientId": client_id, "clientSecret": client_secret}),
        ("json", {"client_id": client_id, "client_secret": client_secret}),
        ("form", {"grant_type": "client_credentials",
                  "client_id": client_id, "client_secret": client_secret}),
    ]


def _extraer_token(cuerpo: dict) -> str | None:
    """Busca el token en la respuesta sin saber su nombre exacto de campo."""
    if not isinstance(cuerpo, dict):
        return None
    for clave in ("access_token", "accessToken", "token", "id_token", "idToken"):
        valor = cuerpo.get(clave)
        if isinstance(valor, str) and valor.count(".") == 2:  # tiene pinta de JWT
            return valor
    return None


def expira_en_seg(token: str) -> int | None:
    """Segundos que le quedan al JWT, leyendo su campo `exp`. None si no se puede."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        exp = json.loads(base64.urlsafe_b64decode(payload)).get("exp")
        return int(exp - time.time()) if exp else None
    except (IndexError, ValueError, KeyError):
        return None


def obtener_token(client_secret: str | None = None,
                  client_id: str = CLIENT_ID) -> str:
    """Pide un token nuevo a la API de Aerolineas.

    Args:
        client_secret: el secreto. Si es None se lee de AEROLINEAS_CLIENT_SECRET.
        client_id: por defecto el publico embebido en el JWT.

    Returns:
        El token Bearer (un JWT).

    Raises:
        ErrorToken: si falta el secret o el endpoint no devuelve un token.
    """
    secret = client_secret or os.getenv("AEROLINEAS_CLIENT_SECRET", "")
    if not secret:
        raise ErrorToken(
            "Falta AEROLINEAS_CLIENT_SECRET. Cargalo en el .env para renovar el "
            "token solo.",
            motivo="falta_client_secret",
        )

    cabeceras = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    fallas = []
    for tipo, payload in _cuerpos_candidatos(client_id, secret):
        try:
            if tipo == "json":
                r = requests.post(URL_TOKEN, json=payload, headers=cabeceras, timeout=TIMEOUT)
            else:
                r = requests.post(URL_TOKEN, data=payload, headers=cabeceras, timeout=TIMEOUT)
        except requests.RequestException as e:
            raise ErrorToken(f"No se pudo conectar con Aerolineas: {e}",
                             "sin_conexion") from e

        if r.status_code == 200:
            try:
                token = _extraer_token(r.json())
            except ValueError:
                token = None
            if token:
                return token
            fallas.append(f"[{tipo}] 200 pero sin token reconocible: {r.text[:150]}")
            continue
        # 401/403 con secret cargado = secret mal; 400 = forma de cuerpo mal.
        fallas.append(f"[{tipo}] HTTP {r.status_code}: {r.text[:150]}")

    raise ErrorToken(
        "Ninguna variante de la peticion devolvio un token. Detalle: "
        + " | ".join(fallas),
        motivo="token_no_obtenido",
    )
