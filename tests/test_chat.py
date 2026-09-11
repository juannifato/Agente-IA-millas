r"""Tests del cerebro conversacional (ia/conversacion.py).

Pegan contra Groq de verdad (necesitan GROQ_API_KEY), pero NO tocan la API de la
aerolinea: los casos elegidos se resuelven antes de buscar (guardrail, faltan
datos, ambiguedad), asi que no dependen del token de Aerolineas.

    .\.venv\Scripts\python.exe tests\test_chat.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ia.conversacion import conversar


def main() -> int:
    chequeos = []

    # 1) Guardrail: un pedido ajeno a vuelos no se responde.
    r = conversar("como se hace un flan casero paso a paso?")
    chequeos.append(("guardrail: pedido fuera de tema no se contesta",
                     r["accion"] == "fuera_de_tema" and r["mejor"] is None))

    # 2) Faltan datos: dice el destino pero no el origen ni la fecha.
    r = conversar("quiero ir a Bariloche")
    chequeos.append(("faltan datos: entiende el destino y pide el resto",
                     r["accion"] in ("faltan_datos", "aclarar")
                     and r["estado"]["destino"] == "BRC" and r["mejor"] is None))

    # 3) Ambiguedad: "Buenos Aires" son dos aeropuertos, tiene que repreguntar.
    r = conversar("de Buenos Aires a Cordoba el 20/12/2026")
    chequeos.append(("ambiguedad: repregunta cual aeropuerto de Buenos Aires",
                     r["accion"] in ("aclarar", "faltan_datos")
                     and r["estado"]["destino"] == "COR" and r["mejor"] is None))

    for txt, ok in chequeos:
        print(f"  [{'OK ' if ok else 'MAL'}] {txt}")
    ok = all(o for _, o in chequeos)
    print("\nRESULTADO:", "todo bien" if ok else "REVISAR")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
