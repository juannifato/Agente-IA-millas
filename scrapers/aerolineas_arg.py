"""Extractor de Aerolineas Argentinas (Aerolineas Plus).

Estado: esqueleto. El endpoint real de la API se completa en el proximo paso
de la Fase 3, una vez identificada la llamada que hace su propia web.
"""
import requests

from config import TIMEOUT, USER_AGENT
from scrapers.base import ErrorScraper, Scraper


class AerolineasArgentinas(Scraper):
    clave = "aerolineas_arg"
    nombre = "Aerolineas Argentinas (Aerolineas Plus)"

    # Se completa al identificar la llamada real de su web.
    URL_BUSQUEDA = ""

    def __init__(self):
        # Una sola sesion por busqueda: reutiliza la conexion TCP y conserva
        # las cookies que el sitio entrega en la primera respuesta.
        self.sesion = requests.Session()
        self.sesion.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "es-AR,es;q=0.9",
        })

    def buscar(self, origen: str, destino: str, fecha_iso: str) -> dict:
        if not self.URL_BUSQUEDA:
            raise ErrorScraper(
                "El extractor de Aerolineas Argentinas todavia no esta conectado "
                "a la API real (paso pendiente de la Fase 3).",
                motivo="scraper_sin_implementar",
            )

        try:
            r = self.sesion.get(
                self.URL_BUSQUEDA,
                params={"origen": origen, "destino": destino, "fecha": fecha_iso},
                timeout=TIMEOUT,
            )
        except requests.Timeout as e:
            raise ErrorScraper(
                "Aerolineas Argentinas tardo demasiado en responder.",
                motivo="timeout",
            ) from e
        except requests.RequestException as e:
            raise ErrorScraper(
                f"No se pudo conectar con Aerolineas Argentinas: {e}",
                motivo="sin_conexion",
            ) from e

        # 403 y 429 no son errores a reintentar a lo loco: significan que hay
        # que bajar la frecuencia de consultas, no insistir mas fuerte.
        if r.status_code in (401, 403):
            raise ErrorScraper(
                "Aerolineas Argentinas rechazo la consulta (sesion vencida o acceso bloqueado).",
                motivo="acceso_denegado",
            )
        if r.status_code == 429:
            raise ErrorScraper(
                "Se hicieron demasiadas consultas seguidas. Esperar unos minutos.",
                motivo="limite_de_consultas",
            )
        if r.status_code != 200:
            raise ErrorScraper(
                f"Aerolineas Argentinas respondio con codigo {r.status_code}.",
                motivo="respuesta_inesperada",
            )

        try:
            return r.json()
        except ValueError as e:
            raise ErrorScraper(
                "La respuesta de Aerolineas Argentinas no era JSON.",
                motivo="respuesta_no_json",
            ) from e
