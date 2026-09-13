# Agente Millas IA — contexto para Claude Code

Buscador de pasajes en millas: consulta la API de las aerolíneas, le pasa los
datos a un modelo en Groq para que compare y elija el más conveniente, y expone
el resultado como JSON para una app de escritorio en Visual Basic.

**Restricción del proyecto: costo cero.** Toda la infraestructura tiene que ser
de tier gratuito y sin tarjeta de crédito. Ante dos opciones, va la gratuita.

- Repo: https://github.com/juannifato/Agente-IA-millas
- Arrancó el 2026-09-09. Última sesión: 2026-09-12.

---

## Estado

| Fase | Estado |
|---|---|
| 1 — Entorno, repo y auto-bitácora | ✅ probada |
| 2 — Cuentas Groq + Render | ✅ Groq verificado. **Render sin verificar** (se prueba en la Fase 6) |
| 3 — Motor de extracción | ✅ **búsqueda real funcionando** |
| 4 — Cerebro analítico (IA) | ✅ **validada con datos reales** (recorte + filtro de dominadas + franja horaria + IA eligiendo bien) |
| 5 — Interfaz Visual Basic | ✅ app WPF: buscador + **chat con IA** + calendario + **token editable desde la app**. Compila. Falta la verificación visual final de Juan |
| 6 — Deploy en Render | ⬅️ **preparada** (`render.yaml`, `.python-version`, guía en docs). Falta que Juan la ejecute |
| 7 — Más aerolíneas | la estructura ya está lista |

El plan original completo de las 7 fases está transcripto en
`docs/plan_original.md`, junto con la lista de desvíos que se le hicieron.
El README tiene el resumen y la arquitectura.

---

## Cómo trabajar en este proyecto

Juan pidió explícitamente ir **de a poco, fase por fase**: *"me parece
importante ir de a poco así no cometemos errores"*. En la práctica:

1. Se completa **una** cosa, no cinco.
2. Se **prueba de verdad** — correr el código, no asumir que anda. Este
   proyecto encontró varios errores justamente por probar en vez de suponer.
3. Se le muestra el resultado real.
4. Recién ahí se propone el paso siguiente.

Otras cosas acordadas:

- **Responder en español rioplatense.** El código, los comentarios y los
  mensajes de commit también van en español.
- Juan autoriza instalar herramientas necesarias sin preguntar cada vez.
- Los comentarios del código explican **por qué**, no qué. Ver los que están
  escritos: marcan las trampas encontradas, no narran el código.
- Mensajes de commit: prosa en español explicando qué se construyó y por qué,
  sin viñetas, terminando con `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

### Límite acordado sobre el scraping

El plan original pedía `playwright-stealth` y técnicas para saltear el CAPTCHA.
**Eso quedó fuera de alcance**, acordado con Juan el 2026-09-09. Se consume la
API JSON pública con User-Agent propio, sin reintentos agresivos ante 403 o 429.

Si aparece un bloqueo, la respuesta es **bajar la frecuencia de consultas**, no
falsificar el rastro del navegador. En la práctica no costó nada: el "Plan A"
del propio documento (la API oculta) resultó ser el mejor camino igual.

### Secretos

Las claves viven en `.env`, que está en `.gitignore`. **Juan las carga él
mismo; nunca se le piden por chat.** Todas las verificaciones se hacen
enmascarando los valores (ej. `gsk_Dqn...lMvp`).

> El 2026-09-09 Juan mandó una captura del `.env` con la clave de Groq visible
> y hubo que rotarla. Si vuelve a pasar: revocar en console.groq.com/keys,
> generar otra, y actualizarla **en los dos lados** — el `.env` local y el
> secret `GROQ_API_KEY` del repo en GitHub.

---

## Entorno (Windows 11)

**Trampa importante:** el comando `python` está tomado por el alias de Microsoft
Store y no ejecuta nada. Python 3.14.0 sí está instalado. Usar siempre:

```powershell
py                              # el launcher, para crear el venv
.\.venv\Scripts\python.exe      # el intérprete del proyecto, para todo lo demás
```

Disponible: Git, Node.js v24, Python 3.14, GitHub CLI (`gh`, sin autenticar), y
**.NET SDK 10** (se instaló el 2026-09-12 con `winget install Microsoft.DotNet.SDK.10`,
para la app WPF). No hay Visual Studio, pero con la CLI `dotnet` alcanza.
Ojo en Git Bash: `dotnet` puede no estar en el PATH; usar
`export PATH="$PATH:/c/Program Files/dotnet"`. En una PowerShell nueva ya está.

### Comandos

```powershell
# Levantar el backend (queda escuchando en http://127.0.0.1:3000)
.\.venv\Scripts\python.exe app.py

# Chequear que el entorno está sano (valida .env y pega contra Groq de verdad)
.\.venv\Scripts\python.exe verificar_setup.py

# Instalar dependencias
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Correr todos los tests de una (test_endpoint y test_chat necesitan GROQ_API_KEY)
.\.venv\Scripts\python.exe tests\correr_todo.py

# Levantar la app de escritorio (necesita el backend corriendo)
cd MillasApp; dotnet run
```

Flask corre sin recarga automática: **después de editar código hay que
reiniciar el servidor**, si no se prueba la versión vieja (ya pasó).

---

## Mapa del repositorio

```
app.py                        Flask. /salud /aerolineas /aeropuertos /buscar /chat /token
config.py                     Lee el .env una sola vez y expone las constantes
busqueda.py                   Orquesta scraper→recorte→IA (lo usan /buscar y el chat). Cachea el crudo
aeropuertos.py                Lista curada de aeropuertos (para el autocompletado)
token_estado.py               Token vigente, actualizable en caliente (archivo .token)
verificar_setup.py            Chequeo de entorno: .env + conexión real con Groq
requirements.txt              Dependencias con versión fijada
render.yaml / .python-version Config para el deploy en Render (Fase 6)
ia/
  recorte.py                  Achica el crudo + filtro de dominadas + filtro por franja horaria
  analisis_ia.py              Le pide a Groq que elija la mejor tarifa por tramo
  conversacion.py             Cerebro del chat: entiende el pedido, guardrails, dispara la búsqueda
  groq_cliente.py             Llamada común a Groq (la comparten analisis y conversacion)
  __init__.py                 Expone recortar() y ErrorRecorte
scrapers/
  base.py                     Contrato común (clase Scraper) + ErrorScraper
  __init__.py                 Registro y ruteo dinámico por clave (Fase 7)
  aerolineas_arg.py           Extractor de Aerolíneas Argentinas (usa token_estado)
  token_aerolineas.py         Código muerto: renovación por client_secret que no se pudo conseguir
MillasApp/                    App de escritorio WPF en VB.NET (Fase 5)
  MainWindow.xaml(.vb)        Ventana: buscador (izq) + chat con IA (der)
  VentanaToken.xaml(.vb)      Ventanita para pegar el token nuevo
  ClienteApi.vb               Cliente HTTP + modelos que consumen el backend
tests/
  correr_todo.py              Corre toda la suite y da un único resultado
  test_recorte.py             Recorte + filtro dominadas + franja (sin red)
  test_analisis.py            Reconstrucción y red de seguridad (sin red)
  test_contrato.py            Validaciones y contrato de la API, incl. token (sin red)
  test_endpoint.py            /buscar de punta a punta con Groq real
  test_chat.py                El chat: guardrails, faltan datos, ambigüedad (Groq real)
  datos_muestra.py            Crudos de ejemplo con la forma real de Aerolíneas
docs/plan_original.md          El plan de las 7 fases, con sus desvíos
docs/fase5_visual_basic.md     Guía de integración de la app de escritorio
docs/fase6_render.md           Guía de deploy en Render
.github/workflows/autodoc.yml La auto-bitácora
Bitacora_Construccion.txt     Se escribe sola, no editar a mano
```

**Para sumar una aerolínea (Fase 7):** crear el módulo en `scrapers/`, heredar
de `Scraper`, e importarlo en `DISPONIBLES` dentro de `scrapers/__init__.py`.
No hace falta tocar nada más del backend.

### Contrato de la API

`POST /buscar` recibe:

```json
{"origen":"AEP", "destino":"BRC", "fecha":"15/09/2026",
 "fecha_vuelta":"22/09/2026", "adultos":1, "aerolinea":"aerolineas_arg"}
```

`fecha_vuelta`, `adultos` y `aerolinea` son opcionales. La fecha se acepta en
`DD/MM/AAAA` (lo que manda Visual Basic) o ISO.

Toda respuesta es JSON, **incluso los errores 404 y 500** — si no, al cliente de
Visual Basic le explota al intentar parsear HTML. Cada error trae un `motivo`
corto (`falta_token`, `token_vencido`, `limite_de_consultas`, ...) además del
texto, para que el frontend reaccione sin leer strings.

Los códigos HTTP dicen **de quién es el problema**: `400` datos mal enviados,
`503` falta configuración del backend, `502` falló la aerolínea.

Otros endpoints:

- `GET /aeropuertos` — lista para el autocompletado de la app (iata, ciudad, país, nombre).
- `POST /chat` — el agente conversacional. Recibe `{mensaje, estado}` (el cliente
  reenvía el `estado` en cada mensaje: memoria multi-turno sin sesión en el server).
  Devuelve `{accion, respuesta, estado, mejor, ...}`. Entiende horario ("a la mañana")
  y refina filtrando por franja. Tiene guardrails: solo responde sobre vuelos.
- `GET /token/estado` y `POST /token` — la app consulta y actualiza el token en
  caliente (ver token_estado.py). `POST` valida que sea un JWT no vencido.

---

## Cosas que ya costaron tiempo (no repetirlas)

1. **Groq está detrás de Cloudflare.** Pegarle con `urllib` da
   `403 error code: 1010`. Usar `requests` para todo.

2. **`gpt-oss` es un modelo de razonamiento**: gasta tokens pensando antes de
   responder. Con `max_tokens` bajo se queda sin presupuesto y devuelve
   `json_validate_failed` con `failed_generation` vacío. Usar `max_tokens`
   holgado y `reasoning_effort: "low"`.

3. **Groq ya no tiene modelos Llama** en el tier gratuito (pasaron a
   Enterprise). El modelo es `openai/gpt-oss-120b`. Se puede cambiar sin tocar
   código con la variable de repo `GROQ_MODEL`.

4. **`load_dotenv()` sin argumentos no mira el directorio actual**, sino la
   carpeta del `.py` que lo llama. Siempre pasarle la ruta explícita.

5. **La respuesta de Aerolíneas no tiene la forma esperable.** `brandedOffers`
   es un diccionario con claves `"0"` (ida) y `"1"` (vuelta), no una lista. Las
   millas están en `offers[].fare.baseFare`. El README lo documenta entero.

6. **El `shoppingId` de la URL del navegador no hay que mandarlo**: lo genera la
   API y vuelve en `searchMetadata`.

---

## La auto-bitácora

Cada push a `main` dispara la Action, que le pide a Groq un resumen técnico del
commit y lo agrega a `Bitacora_Construccion.txt` con un commit propio.

- **Después de cada push hay que hacer `git pull`**, porque el bot commitea. El
  repo ya tiene `pull.rebase true` configurado para que sea limpio.
- Para saltearla en un commit: incluir `[skip bitacora]` en el mensaje.
- Si empieza a escribir "la IA no pudo redactar el resumen", el secret
  `GROQ_API_KEY` del repo está vencido o mal cargado.

---

## Pendientes concretos

Fases 4 y 5 hechas; Fase 6 preparada. Lo que queda es de Juan (verificar en
pantalla, deployar) o menor.

### Para cuando Juan pruebe la app (verificacion visual pendiente)

La app WPF (`MillasApp/`) compila y cada pieza se probo por separado, pero falta
que Juan confirme en pantalla, con un token vigente cargado desde el boton
"token":

- Que el **calendario** resalte el rango en **violeta** (se corrigio moviendo el
  estilo a `Application.Resources`; es el segundo intento).
- Que el **refinamiento por horario** del chat filtre de verdad ("a la manana"
  trae vuelos de la manana). El filtro y la interpretacion estan probados por
  separado; falta la corrida real de punta a punta.
- Que la **ventanita del token** guarde bien un token real.

### Fase 6 - deploy en Render (lista para ejecutar)

Todo preparado: `render.yaml` (gunicorn, 1 worker, secretos con `sync:false`),
`.python-version` (3.12, porque Render no tiene la 3.14 local) y la guia paso a
paso en `docs/fase6_render.md`. Falta que Juan lo ejecute: conectar el repo como
Blueprint, cargar `GROQ_API_KEY` y `AEROLINEAS_TOKEN`, y apuntar la app a la URL
(cambiar `BaseUrl` en `ClienteApi.vb`).

### Bugs y dudas abiertas

- **El token no se pudo automatizar** (investigado a fondo el 2026-09-12): no hay
  `client_secret` accesible en el cliente ni una llamada que entregue el token; lo
  arma el JS de la web. La unica via seria un navegador headless, descartado por
  el acuerdo de no usar navegador y porque no entra en Render free. **Decision:
  queda manual pero comodo** (boton token en la app). `scrapers/token_aerolineas.py`
  y `renovar_token.py` quedan como codigo muerto.
- **En Render el token en caliente es efimero**: al dormir/reiniciar el servicio
  se pierde y vuelve al `AEROLINEAS_TOKEN` de las env vars. Para uso personal
  alcanza (se recarga desde la app). Documentado en la guia de Fase 6.

### Ya resueltos

- OK **Fase 4** validada con datos reales (recorte + filtro de dominadas + franja
  horaria). `taxes`: pesos argentinos enteros, por tramo (sumar ida+vuelta esta bien).
- OK **Fase 5**: app WPF con buscador, autocompletado de aeropuertos, calendario de
  rango, chat con IA (entiende, repregunta, refina por horario, guardrails) y token
  editable desde la app. Compila con `dotnet` (se instalo .NET SDK 10).
- OK **La bitacora truncaba los resumenes.** `max_tokens: 400` -> 1200 +
  `reasoning_effort: "low"` en autodoc.yml. Y el prompt decia "Node.js" siendo Python.
