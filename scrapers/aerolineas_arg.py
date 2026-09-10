"""Extractor de Aerolineas Argentinas (Aerolineas Plus).

Consulta la misma API JSON que usa la web de Aerolineas para mostrar los
vuelos en millas, en lugar de abrir un navegador y leer la pantalla. Se le
pide exactamente lo que pide el sitio y se respetan sus limites: una consulta
por busqueda y nada de reintentos automaticos ante un 403 o un 429.

La API exige un token Bearer. Se lee de AEROLINEAS_TOKEN en el .env.
"""
import requests

from config import AEROLINEAS_TOKEN, TIMEOUT, USER_AGENT
from scrapers.base import ErrorScraper, Scraper


class AerolineasArgentinas(Scraper):
    clave = "aerolineas_arg"
    nombre = "Aerolineas Argentinas (Aerolineas Plus)"

    URL_BUSQUEDA = "https://api.aerolineas.com.ar/v1/flights/offers"

    def __init__(self):
        # Una sesion por busqueda: reutiliza la conexion TCP y conserva las
        # cookies que el sitio entrega en la primera respuesta.
        self.sesion = requests.Session()
        self.sesion.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "es-AR,es;q=0.9",
        })
        if AEROLINEAS_TOKEN:
            self.sesion.headers["Authorization"] = f"Bearer {AEROLINEAS_TOKEN}"

    @staticmethod
    def _tramo(origen: str, destino: str, fecha_iso: str) -> str:
        """Arma un tramo con el formato que espera la API: AEP-BRC-20260915."""
        return f"{origen}-{destino}-{fecha_iso.replace('-', '')}"

    def buscar(
        self,
        origen: str,
        destino: str,
        fecha_iso: str,
        fecha_vuelta_iso: str | None = None,
        adultos: int = 1,
    ) -> dict:
        if not AEROLINEAS_TOKEN:
            raise ErrorScraper(
                "Falta el token de Aerolineas Argentinas. Cargalo como "
                "AEROLINEAS_TOKEN en el archivo .env.",
                motivo="falta_token",
            )

        # La ida y la vuelta se mandan repitiendo el parametro 'leg'.
        tramos = [self._tramo(origen, destino, fecha_iso)]
        if fecha_vuelta_iso:
            tramos.append(self._tramo(destino, origen, fecha_vuelta_iso))

        parametros = [
            ("adt", adultos),
            ("inf", 0),
            ("chd", 0),
            ("flexDates", "false"),
            ("cabinClass", "Economy"),
            ("flightType", "ROUND_TRIP" if fecha_vuelta_iso else "ONE_WAY"),
            # Lo que convierte la busqueda en una busqueda por millas.
            ("awardBooking", "true"),
            *[("leg", t) for t in tramos],
        ]

        try:
            r = self.sesion.get(self.URL_BUSQUEDA, params=parametros, timeout=TIMEOUT)
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

        # 401 aca casi siempre es el token vencido, no un error de programacion.
        if r.status_code == 401:
            raise ErrorScraper(
                "Aerolineas Argentinas rechazo el token (probablemente venció). "
                "Hay que renovar AEROLINEAS_TOKEN en el .env.",
                motivo="token_vencido",
            )
        if r.status_code == 403:
            raise ErrorScraper(
                "Aerolineas Argentinas denegó el acceso a esta consulta.",
                motivo="acceso_denegado",
            )
        # 429 no se reintenta: significa bajar la frecuencia, no insistir mas fuerte.
        if r.status_code == 429:
            raise ErrorScraper(
                "Se hicieron demasiadas consultas seguidas. Esperar unos minutos "
                "antes de volver a buscar.",
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
