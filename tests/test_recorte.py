r"""Tests del recorte (ia/recorte.py). No usan red: se corren siempre.

    .\.venv\Scripts\python.exe tests\test_recorte.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ia.recorte import filtrar_por_franja, medir, recortar
from tests.datos_muestra import CRUDO


def main() -> int:
    r = recortar(CRUDO)
    ida = r["tramos"][0]
    directo, escala = ida["vuelos"][0], ida["vuelos"][1]

    chequeos = [
        ("los tramos salen ordenados ida->vuelta",
         [t["tramo"] for t in r["tramos"]] == ["ida", "vuelta"]),
        ("total_opciones = 4 (la tarifa sin millas no cuenta)",
         r["total_opciones"] == 4),
        ("las fechas con zona horaria se recortan a minutos",
         directo["sale"] == "2026-09-15T08:10"),
        ("el directo no tiene escalas", directo["escalas"] == 0),
        ("la escala se detecta y dice donde",
         escala["escalas"] == 1 and escala["escalas_en"] == ["MDZ"]),
        ("sin totalDuration, la duracion se calcula de los horarios",
         escala["duracion_min"] == 260),
        ("el vuelo con escala arma la ruta completa AEP->BRC",
         escala["origen"] == "AEP" and escala["destino"] == "BRC"),
        ("se descarto la tarifa sin millas", len(directo["tarifas"]) == 1),
        ("los ids son unicos y estables",
         [t["id"] for v in ida["vuelos"] for t in v["tarifas"]] == ["ida-1.1", "ida-2.1"]),
        ("el recorte achica al menos 85%", medir(CRUDO, r)["reduccion_pct"] >= 85),
    ]

    # --- filtro de tarifas dominadas (Pareto) ---
    # Un vuelo con: A barata en todo, B dominada por A, C con trade-off (mas
    # millas pero menos plata), y D empate exacto con A.
    crudo_dom = {"brandedOffers": {"0": [{"legs": [{"totalDuration": 100, "segments": [
        {"airline": "AR", "flightNumber": "1", "origin": "AEP", "destination": "BRC",
         "departure": "2026-09-15T08:00:00.000", "arrival": "2026-09-15T09:40:00.000"}]}],
        "offers": [
            {"brand": {"name": "A"}, "fare": {"baseFare": 5000, "taxes": 64000}, "seatAvailability": {"seats": 5}},
            {"brand": {"name": "B"}, "fare": {"baseFare": 5200, "taxes": 221000}, "seatAvailability": {"seats": 5}},
            {"brand": {"name": "C"}, "fare": {"baseFare": 8000, "taxes": 40000}, "seatAvailability": {"seats": 5}},
            {"brand": {"name": "D"}, "fare": {"baseFare": 5000, "taxes": 64000}, "seatAvailability": {"seats": 5}},
        ]}]}}
    tarifas_dom = recortar(crudo_dom)["tramos"][0]["vuelos"][0]["tarifas"]
    millas_imp = sorted((t["millas"], t["impuestos"]) for t in tarifas_dom)
    chequeos += [
        ("Pareto: quedan solo 2 tarifas (A y C)", len(tarifas_dom) == 2),
        ("Pareto: sobreviven la barata y la de trade-off",
         millas_imp == [(5000, 64000), (8000, 40000)]),
        ("Pareto: se descarto la dominada (B) y el empate exacto (D)",
         all(t["impuestos"] != 221000 for t in tarifas_dom)),
    ]

    # --- filtro por franja horaria (para el refinamiento del chat) ---
    rec_horas = {"tramos": [
        {"tramo": "ida", "origen": "AEP", "destino": "BRC", "vuelos": [
            {"numeros": ["AR1"], "sale": "2026-09-24T08:10", "tarifas": [{"id": "ida-1.1", "millas": 5000}]},
            {"numeros": ["AR2"], "sale": "2026-09-24T15:30", "tarifas": [{"id": "ida-2.1", "millas": 6000}]}]},
    ], "total_opciones": 2}
    manana = filtrar_por_franja(rec_horas, "manana")
    tarde = filtrar_por_franja(rec_horas, "tarde")
    noche = filtrar_por_franja(rec_horas, "noche")
    chequeos += [
        ("franja manana: deja el vuelo de las 08 y descarta el de las 15",
         [v["numeros"] for v in manana["tramos"][0]["vuelos"]] == [["AR1"]]),
        ("franja tarde: deja el de las 15 y descarta el de las 08",
         [v["numeros"] for v in tarde["tramos"][0]["vuelos"]] == [["AR2"]]),
        ("franja sin vuelos avisa con 'sin_franja'",
         noche["total_opciones"] == 0 and noche.get("sin_franja") == "noche"),
        ("franja con tilde tambien se entiende ('mañana')",
         filtrar_por_franja(rec_horas, "mañana")["total_opciones"] == 1),
    ]

    for txt, ok in chequeos:
        print(f"  [{'OK ' if ok else 'MAL'}] {txt}")
    ok = all(o for _, o in chequeos)
    print("\nRESULTADO:", "todo bien" if ok else "HAY FALLAS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
