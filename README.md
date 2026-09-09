# Agente Millas IA

Agente que busca pasajes en millas, los analiza con IA (Groq) y
devuelve el vuelo más conveniente. Infraestructura 100% gratuita.

## Arquitectura

```
Windows Forms (Visual Basic)             <-- Fase 5
        |  POST /buscar  (JSON)
        v
Backend Python (Flask) en Render         <-- Fases 3 y 6
        |
        +--> /scrapers/  consulta la API de la aerolínea  --> JSON crudo
        |
        +--> /ia/        Groq analiza y compara           --> JSON limpio
```

## Estado de las fases

- [x] **Fase 1** — Entorno, repositorio y auto-bitácora con GitHub Actions
- [ ] **Fase 2** — Cuentas: Render + Groq, variables de entorno
- [ ] **Fase 3** — Motor de extracción (API de Aerolíneas Argentinas)
- [ ] **Fase 4** — Cerebro analítico (Groq)
- [ ] **Fase 5** — Interfaz de escritorio en Visual Basic
- [ ] **Fase 6** — Despliegue en Render con auto-deploy
- [ ] **Fase 7** — Escalabilidad: más aerolíneas (Smiles, AA, ...)

## Stack

| Capa | Herramienta | Por qué |
|---|---|---|
| Backend | Python 3.14 + Flask | El endpoint es un solo POST, Flask no arrastra dependencias compiladas |
| HTTP | requests | Consulta la API de las aerolíneas y la de Groq |
| IA | Groq · `openai/gpt-oss-120b` | Gratis y muy rápido. Los modelos Llama pasaron a tier Enterprise |
| Producción | gunicorn en Render | Plan gratuito, sin tarjeta de crédito |
| Frontend | Visual Basic (WinForms) | Pedido del proyecto |

## Auto-bitácora

Cada `git push` a `main` dispara `.github/workflows/autodoc.yml`: toma el mensaje
del commit y la lista de archivos tocados, se los pasa al modelo de Groq y agrega
un resumen técnico a `Bitacora_Construccion.txt`. Requiere el secret
`GROQ_API_KEY` cargado en el repositorio.

Para saltear la bitácora en un commit puntual, incluí `[skip bitacora]` en el mensaje.
Para cambiar de modelo sin tocar el workflow, creá la variable de repositorio
`GROQ_MODEL` en `Settings > Secrets and variables > Actions > Variables`.

## Configuración local (Windows)

En este equipo el comando `python` está tomado por el alias de Microsoft Store,
así que se usa `py` para crear el entorno y después el python del propio `.venv`.

```powershell
# 1. Crear el entorno virtual (una sola vez)
py -m venv .venv

# 2. Activarlo (cada vez que abrís una terminal nueva)
.\.venv\Scripts\Activate.ps1

# 3. Instalar las dependencias
pip install -r requirements.txt

# 4. Cargar las claves: copiar .env.example a .env y completar GROQ_API_KEY
copy .env.example .env

# 5. Levantar el backend
python app.py
```

El archivo `.env` está en `.gitignore` y nunca se sube al repositorio.
