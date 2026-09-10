"""Configuracion central del proyecto.

Carga el .env una sola vez y expone las constantes que usa el resto del codigo.
Cualquier modulo hace `from config import GROQ_API_KEY` y no vuelve a tocar
variables de entorno por su cuenta.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent

# Ruta explicita al .env: llamado sin argumentos, load_dotenv lo busca al lado
# del .py que lo invoca, asi que los modulos de /scrapers/ e /ia/ no lo
# encontrarian. En Render no existe el archivo y las variables ya vienen
# cargadas en el entorno, por eso no es un error que falte.
load_dotenv(RAIZ / ".env")

# --- IA (Groq) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# --- Aerolineas Argentinas ---
# Token Bearer que exige su API. Se renueva a mano desde el .env cuando vence.
AEROLINEAS_TOKEN = os.getenv("AEROLINEAS_TOKEN", "")

# --- Servidor ---
PORT = int(os.getenv("PORT", "3000"))
DEBUG = os.getenv("DEBUG", "").lower() in ("1", "true", "si")

# --- HTTP ---
# Segundos de espera antes de dar por perdida una peticion. El plan gratuito de
# Render corta a los 30s, asi que conviene fallar antes y devolver un error claro.
TIMEOUT = 25

# User-Agent propio: identifica al agente en lugar de disfrazarlo. Ademas el
# Cloudflare de Groq rechaza los User-Agent genericos de las librerias HTTP.
USER_AGENT = "AgenteMillasIA/0.1 (+https://github.com/juannifato/Agente-IA-millas)"
