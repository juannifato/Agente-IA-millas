"""Token vigente de Aerolineas, actualizable en caliente desde la app.

El token dura 24 h y se renueva a mano (no se pudo automatizar; ver la memoria
del proyecto). Para no tener que editar archivos ni reiniciar el backend, la app
manda el token nuevo a POST /token y se guarda aca.

Se guarda en un archivo `.token` aparte (no en el .env) para no arriesgar las
otras claves. En local eso persiste entre reinicios; en Render el disco es
efimero, pero al menos dura mientras el servicio este vivo. Si no hay `.token`,
se usa el AEROLINEAS_TOKEN del .env como valor inicial.
"""
import base64
import json
import time

from config import AEROLINEAS_TOKEN, RAIZ

_ARCHIVO = RAIZ / ".token"
_token_memoria: str | None = None


def token_vigente() -> str:
    """El token que hay que usar ahora: el cargado en caliente, el de `.token`,
    o el del .env, en ese orden."""
    global _token_memoria
    if _token_memoria:
        return _token_memoria
    if _ARCHIVO.exists():
        try:
            guardado = _ARCHIVO.read_text(encoding="utf-8").strip()
            if guardado:
                _token_memoria = guardado
                return guardado
        except OSError:
            pass
    return AEROLINEAS_TOKEN


def actualizar_token(nuevo: str) -> None:
    """Guarda un token nuevo (en memoria y en `.token`)."""
    global _token_memoria
    _token_memoria = nuevo.strip()
    try:
        _ARCHIVO.write_text(_token_memoria, encoding="utf-8")
    except OSError:
        pass  # si no se puede escribir (Render), al menos queda en memoria


def info(token: str) -> dict:
    """Lee el JWT y dice si es valido, cuando vence y cuanto le queda.

    No verifica la firma (no tenemos la clave ni hace falta): solo mira que tenga
    forma de JWT y lee su campo `exp`.
    """
    vacio = {"valido": False, "vence": None, "vencido": None, "minutos": None}
    if not isinstance(token, str) or token.count(".") != 2:
        return vacio
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        exp = json.loads(base64.urlsafe_b64decode(payload)).get("exp")
    except (ValueError, KeyError):
        return vacio

    if not exp:
        return {"valido": True, "vence": None, "vencido": False, "minutos": None}
    ahora = int(time.time())
    return {
        "valido": True,
        "vence": time.strftime("%d/%m/%Y %H:%M", time.localtime(exp)),
        "vencido": exp <= ahora,
        "minutos": max(0, (exp - ahora) // 60),
    }
