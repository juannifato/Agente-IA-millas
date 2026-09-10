"""Renueva a mano el token de Aerolineas usando el client_secret.

Correr una vez que AEROLINEAS_CLIENT_SECRET este cargado en el .env:

    .\\.venv\\Scripts\\python.exe renovar_token.py

Imprime la respuesta cruda del endpoint (para ajustar el formato si hiciera
falta) y, si consigue el token, la linea lista para pegar en el .env. No
escribe el .env solo: ese archivo lo maneja Juan.
"""
import sys
from pathlib import Path

# Asegura que se pueda importar config/scrapers al correr el script suelto.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrapers.token_aerolineas import (
    CLIENT_ID,
    ErrorToken,
    expira_en_seg,
    obtener_token,
)


def main() -> int:
    print(f"client_id (publico): {CLIENT_ID}")
    print("Pidiendo token nuevo a Aerolineas...\n")
    try:
        token = obtener_token()
    except ErrorToken as e:
        print(f"NO SE PUDO: [{e.motivo}] {e}")
        if e.motivo == "falta_client_secret":
            print("\nCargá AEROLINEAS_CLIENT_SECRET en el .env y volvé a correr esto.")
        elif e.motivo == "token_no_obtenido":
            print("\nEl secret llegó pero el endpoint no dio token. El detalle de")
            print("arriba dice que respondio cada variante: con eso ajustamos el")
            print("formato del cuerpo o el nombre del campo en token_aerolineas.py.")
        return 1

    seg = expira_en_seg(token)
    horas = f"~{seg // 3600} h" if seg else "desconocido"
    print("TOKEN OBTENIDO. Vence en:", horas)
    print(f"Longitud: {len(token)} caracteres\n")
    print("Pegá esta línea en el .env (reemplazando la que está):\n")
    print(f"AEROLINEAS_TOKEN={token}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
