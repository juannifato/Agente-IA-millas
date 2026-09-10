"""Muestra con la forma REAL de la respuesta de Aerolineas, para los tests.

Reproduce las trampas documentadas: brandedOffers como dict "0"/"1" (con la
vuelta antes que la ida a proposito), millas en offers[].fare.baseFare, fechas
con zona horaria, un vuelo con escala, una tarifa sin millas, y el ruido
(fareRules, combinableOffers) que el recorte tiene que descartar.
"""
CRUDO = {
    "searchMetadata": {"shoppingId": "SHOP-XYZ"},
    "brandedOffers": {
        "1": [  # la VUELTA viene primero: el recorte tiene que reordenar
            {"legs": [{"totalDuration": 145, "segments": [
                {"airline": "AR", "flightNumber": "1685", "origin": "BRC",
                 "destination": "AEP", "departure": "2026-09-22T18:00:00.000-03:00",
                 "arrival": "2026-09-22T20:25:00.000-03:00"}]}],
             "offers": [{"brand": {"name": "Economy Promo"},
                         "fare": {"baseFare": 32000, "taxes": 64022},
                         "seatAvailability": {"seats": 2}}]},
            {"legs": [{"totalDuration": 145, "segments": [
                {"airline": "AR", "flightNumber": "1687", "origin": "BRC",
                 "destination": "AEP", "departure": "2026-09-22T21:00:00.000-03:00",
                 "arrival": "2026-09-22T23:25:00.000-03:00"}]}],
             "offers": [{"brand": {"name": "Economy Promo"},
                         "fare": {"baseFare": 28000, "taxes": 64022},
                         "seatAvailability": {"seats": 6}}]},
        ],
        "0": [  # la IDA
            {"legs": [{"totalDuration": 140, "segments": [
                {"airline": "AR", "flightNumber": "1684", "origin": "AEP",
                 "destination": "BRC", "departure": "2026-09-15T08:10:00.000-03:00",
                 "arrival": "2026-09-15T10:30:00.000-03:00"}]}],
             "offers": [
                {"brand": {"name": "Economy Promo"}, "fare": {"baseFare": 30000, "taxes": 64022},
                 "seatAvailability": {"seats": 4}},
                {"brand": {"name": "Economy Flex"}, "fare": {"taxes": 64022}}]},  # sin millas
            {"legs": [{"segments": [  # con escala en MDZ, sin totalDuration
                {"airline": "AR", "flightNumber": "1200", "origin": "AEP",
                 "destination": "MDZ", "departure": "2026-09-15T06:00:00.000-03:00",
                 "arrival": "2026-09-15T07:40:00.000-03:00"},
                {"airline": "AR", "flightNumber": "1502", "origin": "MDZ",
                 "destination": "BRC", "departure": "2026-09-15T09:00:00.000-03:00",
                 "arrival": "2026-09-15T10:20:00.000-03:00"}]}],
             "offers": [{"brand": {"name": "Economy Promo"}, "fare": {"baseFare": 25000, "taxes": 64022},
                         "seatAvailability": {"seats": 9}}]},
        ],
    },
    "fareRules": {"basura": "z" * 3000},
    "combinableOffers": {"basura": "z" * 5000},
}

# Solo ida: brandedOffers con la clave "0" nada mas. La mas barata es la 2da.
CRUDO_SOLO_IDA = {
    "searchMetadata": {"shoppingId": "S1"},
    "brandedOffers": {"0": [
        {"legs": [{"totalDuration": 140, "segments": [
            {"airline": "AR", "flightNumber": "1684", "origin": "AEP", "destination": "BRC",
             "departure": "2026-09-15T08:10:00.000-03:00", "arrival": "2026-09-15T10:30:00.000-03:00"}]}],
         "offers": [{"brand": {"name": "Economy Promo"}, "fare": {"baseFare": 30000, "taxes": 64022},
                     "seatAvailability": {"seats": 4}}]},
        {"legs": [{"totalDuration": 150, "segments": [
            {"airline": "AR", "flightNumber": "1686", "origin": "AEP", "destination": "BRC",
             "departure": "2026-09-15T14:00:00.000-03:00", "arrival": "2026-09-15T16:30:00.000-03:00"}]}],
         "offers": [{"brand": {"name": "Economy Promo"}, "fare": {"baseFare": 22000, "taxes": 64022},
                     "seatAvailability": {"seats": 7}}]},
    ]},
}

# Sin resultados: la busqueda salio bien pero no hay vuelos en millas.
CRUDO_VACIO = {"searchMetadata": {"shoppingId": "S2"}, "brandedOffers": {}}

# API cambiada: ya no viene brandedOffers. El recorte tiene que avisar, no romper.
CRUDO_ROTO = {"searchMetadata": {"shoppingId": "S3"}, "otraCosa": 1}
