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
- [x] **Fase 2** — Cuentas: Render + Groq, variables de entorno
- [x] **Fase 3** — Motor de extracción (API de Aerolíneas Argentinas)
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

## Chequeo del entorno

```powershell
.\.venv\Scripts\python.exe verificar_setup.py
```

Valida el `.env`, lista los modelos que habilita la cuenta de Groq y hace una
generación real. Si algo del entorno se rompe, correr esto primero.

## Notas técnicas (aprendidas a los golpes)

Tres cosas que costaron un rato y conviene no volver a tropezar:

1. **Groq está detrás de Cloudflare.** Pegarle con `urllib` devuelve
   `403 error code: 1010` porque bloquea el User-Agent `Python-urllib/x.y`.
   Por eso el proyecto usa `requests` para todas las llamadas HTTP.

2. **`gpt-oss` es un modelo de razonamiento.** Consume tokens "pensando" antes
   de escribir la respuesta. Con un `max_tokens` bajo se queda sin presupuesto
   en esa etapa y la API devuelve `json_validate_failed` con `failed_generation`
   vacío. Se usa `max_tokens` holgado (512+) y `reasoning_effort: "low"`, que
   para extraer datos de un JSON es suficiente.

3. **`load_dotenv()` sin argumentos no mira el directorio actual**, sino la
   carpeta del `.py` que lo llama. En un proyecto con módulos en subcarpetas
   (`/scrapers/`, `/ia/`) eso da falsos negativos: siempre pasarle la ruta
   explícita del `.env`.

Modelos disponibles en la cuenta gratuita al 09/09/2026: `openai/gpt-oss-120b`,
`openai/gpt-oss-20b`, `qwen/qwen3.6-27b`, `qwen/qwen3.8-27b`, `groq/compound`,
`groq/compound-mini`, `allam-2-7b`. Ningún Llama.

## La API de Aerolíneas Argentinas

Endpoint que usa su propia web para mostrar vuelos en millas:

```
GET https://api.aerolineas.com.ar/v1/flights/offers
    ?adt=1&inf=0&chd=0            cantidad de adultos, bebés y menores
    &cabinClass=Economy
    &flightType=ONE_WAY           o ROUND_TRIP
    &awardBooking=true            <-- esto es lo que la vuelve búsqueda en millas
    &flexDates=false
    &leg=AEP-BRC-20260915         ORIGEN-DESTINO-AAAAMMDD, se repite para la vuelta
```

Requiere un header `Authorization: Bearer <token>`. El token es **anónimo**: la web
muestra los precios en millas sin iniciar sesión, así que no está atado a ninguna
cuenta. No sale de `/v1/token` (responde 404) y por ahora se carga a mano en
`AEROLINEAS_TOKEN`. Queda pendiente automatizar de dónde lo obtiene la web.

El `shoppingId` que aparece en la URL del navegador **no hace falta mandarlo**: lo
genera la API y vuelve dentro de `searchMetadata`.

### Forma de la respuesta

```
brandedOffers
  ├── "0"  -> lista de vuelos de IDA
  └── "1"  -> lista de vuelos de VUELTA
        └── cada elemento:
              legs[0].segments[]  -> flightNumber, airline, origin, destination,
                                     departure, arrival, duration, stops
              offers[]            -> brand.name, seatAvailability.seats,
                                     fare.baseFare  <-- MILLAS
                                     fare.taxes     <-- impuestos aparte
```

Medición de una búsqueda real (AEP-BRC ida y vuelta, 19 vuelos, 137 combinaciones
de vuelo y tarifa):

| Parte | Tamaño | |
|---|---:|---|
| Respuesta completa | 243.664 b | |
| `fareRules` | 76.985 b | letra chica de las tarifas: ruido |
| `combinableOffers` | 103.578 b | IDs de combinaciones: ruido |
| **Solo lo necesario** | **34.131 b** | **86% menos** |

Por eso la Fase 4 **no le puede mandar el JSON crudo a la IA**: hay que recortarlo
antes. Es más rápido, más barato y con menos ruido el modelo acierta más.

Detalle a confirmar: `taxes` viene como entero (ej. `64022`) y falta determinar si
son centavos o pesos enteros.
