"""Chequeo de entorno del Agente Millas IA.

Valida que el .env este bien cargado y que la conexion con Groq funcione de
verdad, listando los modelos que habilita la cuenta y haciendo una generacion
real. Nunca imprime la clave completa.

Uso:
    .venv\\Scripts\\python.exe verificar_setup.py
"""
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# Ruta explicita al .env: llamado sin argumentos, dotenv lo busca al lado del
# archivo .py y no en el directorio de trabajo, lo que da falsos negativos.
load_dotenv(Path(__file__).resolve().parent / ".env")

CLAVE = os.getenv("GROQ_API_KEY", "")
MODELO = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
BASE = "https://api.groq.com/openai/v1"
CABECERAS = {"Authorization": f"Bearer {CLAVE}", "Content-Type": "application/json"}

# Modelos que no sirven para analizar vuelos (audio, moderacion, embeddings).
NO_CHAT = ("whisper", "tts", "guard", "embed", "moderation", "orpheus")


def titulo(texto: str) -> None:
    print()
    print("=" * 62)
    print(texto)
    print("=" * 62)


def main() -> int:
    titulo("1) ARCHIVO .env")
    if not CLAVE or "pegar_aca" in CLAVE:
        print("  ERROR: GROQ_API_KEY no esta cargada o sigue con el texto de ejemplo.")
        print("  Editá el archivo .env y pegá tu clave de https://console.groq.com/keys")
        return 1
    print(f"  GROQ_API_KEY  OK  -> {CLAVE[:7]}...{CLAVE[-4:]}  ({len(CLAVE)} caracteres)")
    print(f"  GROQ_MODEL    -> {MODELO}")
    print(f"  PORT          -> {os.getenv('PORT', '(vacio)')}")

    titulo("2) MODELOS QUE HABILITA TU CUENTA")
    # Se usa requests y no urllib: el Cloudflare de Groq rechaza el
    # User-Agent por defecto de urllib con un 403 "error code: 1010".
    try:
        r = requests.get(f"{BASE}/models", headers=CABECERAS, timeout=45)
    except requests.RequestException as e:
        print(f"  ERROR de red: {e}")
        return 1
    if r.status_code != 200:
        print(f"  ERROR {r.status_code}: {r.text[:300]}")
        return 1

    ids = sorted(m["id"] for m in r.json().get("data", []))
    for i in (x for x in ids if not any(n in x.lower() for n in NO_CHAT)):
        print(f"  {i}{'   <-- el configurado' if i == MODELO else ''}")
    if MODELO not in ids:
        print(f"  AVISO: '{MODELO}' no figura entre los modelos de tu cuenta.")

    titulo("3) PRUEBA REAL DE GENERACION")
    r = requests.post(
        f"{BASE}/chat/completions",
        headers=CABECERAS,
        timeout=45,
        json={
            "model": MODELO,
            # gpt-oss razona antes de responder: con un tope bajo se queda sin
            # tokens en esa etapa y devuelve json_validate_failed con texto vacio.
            "max_tokens": 512,
            "reasoning_effort": "low",
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [{
                "role": "user",
                "content": 'Responde solo con este JSON: {"estado":"ok","proyecto":"agente millas"}',
            }],
        },
    )
    if r.status_code != 200:
        print(f"  ERROR {r.status_code}: {r.text[:400]}")
        return 1

    data = r.json()
    contenido = data["choices"][0]["message"]["content"].strip()
    uso = data.get("usage", {})
    print(f"  Modelo usado : {data.get('model')}")
    print(f"  Respuesta    : {contenido}")
    print(f"  Tokens       : {uso.get('total_tokens')} en {uso.get('total_time', 0):.2f}s")
    try:
        json.loads(contenido)
        print("  JSON valido  : SI")
    except json.JSONDecodeError:
        print("  JSON valido  : NO -> revisar el prompt")
        return 1

    print()
    print("TODO OK: el entorno esta operativo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
