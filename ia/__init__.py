"""Cerebro analitico del agente (Fase 4).

Dos piezas separadas a proposito:

    recorte.py      achica el JSON de la aerolinea a lo que se puede comparar
    analisis_ia.py  le pide a Groq que elija la mejor opcion de ese recorte

Estan separadas porque el recorte se puede probar sin gastar una llamada al
modelo, y porque cada aerolinea nueva (Fase 7) va a necesitar su propio
recorte pero comparte el mismo analisis.
"""
from ia.recorte import ErrorRecorte, recortar

__all__ = ["ErrorRecorte", "recortar"]
