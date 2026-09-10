# Agente Millas IA — contexto para Claude Code

Buscador de pasajes en millas: consulta la API de las aerolíneas, le pasa los
datos a un modelo en Groq para que compare y elija el más conveniente, y expone
el resultado como JSON para una app de escritorio en Visual Basic.

**Restricción del proyecto: costo cero.** Toda la infraestructura tiene que ser
de tier gratuito y sin tarjeta de crédito. Ante dos opciones, va la gratuita.

- Repo: https://github.com/juannifato/Agente-IA-millas
- Arrancó el 2026-09-09. Última sesión: 2026-09-09.

---

## Estado

| Fase | Estado |
|---|---|
| 1 — Entorno, repo y auto-bitácora | ✅ probada |
| 2 — Cuentas Groq + Render | ✅ Groq verificado. **Render sin verificar** (se prueba en la Fase 6) |
| 3 — Motor de extracción | ✅ **búsqueda real funcionando** |
| 4 — Cerebro analítico (IA) | ⬅️ **acá vamos** |
| 5 — Interfaz Visual Basic | pendiente |
| 6 — Deploy en Render | pendiente |
| 7 — Más aerolíneas | la estructura ya está lista |

El plan original completo de las 7 fases está en el documento que trajo Juan;
el README tiene el resumen y la arquitectura.

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

Disponible: Git, Node.js v24, Python 3.14, GitHub CLI (`gh`, sin autenticar).
**No hay .NET SDK ni Visual Studio** — hay que resolverlo en la Fase 5.

### Comandos

```powershell
# Levantar el backend (queda escuchando en http://127.0.0.1:3000)
.\.venv\Scripts\python.exe app.py

# Chequear que el entorno está sano (valida .env y pega contra Groq de verdad)
.\.venv\Scripts\python.exe verificar_setup.py

# Instalar dependencias
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Flask corre sin recarga automática: **después de editar código hay que
reiniciar el servidor**, si no se prueba la versión vieja (ya pasó).

---

## Mapa del repositorio

```
app.py                        Flask. GET /salud, GET /aerolineas, POST /buscar
config.py                     Lee el .env una sola vez y expone las constantes
verificar_setup.py            Chequeo de entorno: .env + conexión real con Groq
requirements.txt              Dependencias con versión fijada
scrapers/
  base.py                     Contrato común (clase Scraper) + ErrorScraper
  __init__.py                 Registro y ruteo dinámico por clave (Fase 7)
  aerolineas_arg.py           Extractor de Aerolíneas Argentinas
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

### Fase 4 — el cerebro analítico (lo que sigue)

**Antes de escribir el prompt hay que recortar el JSON.** Medición real de una
búsqueda AEP-BRC ida y vuelta (19 vuelos, 137 combinaciones de vuelo y tarifa):

| Parte | Tamaño |
|---|---:|
| Respuesta completa | 243.664 b |
| `fareRules` (letra chica) | 76.985 b |
| `combinableOffers` (IDs internos) | 103.578 b |
| **Solo lo necesario** | **34.131 b — 86% menos** |

O sea que el **74% es ruido**. Mandarle el crudo al modelo sería lento, caro y
menos preciso. El plan es: recortar en Python → pasar eso a la IA → devolver el
JSON del vuelo más conveniente.

Los campos que importan de cada vuelo: `flightNumber`, `airline`, `origin`,
`destination`, `departure`, `arrival`, `stops`, `totalDuration`, `brand.name`,
`fare.baseFare` (millas), `fare.taxes`, `seatAvailability.seats`.

Según el plan original, el módulo va en `ia/analisis_ia.py`.

### Bugs y dudas abiertas

- **La bitácora trunca los resúmenes largos.** El workflow tiene
  `max_tokens: 400` y gpt-oss gasta parte razonando (mismo problema del punto 2
  de arriba). El último resumen quedó cortado a mitad de frase. Subir ese
  límite en `.github/workflows/autodoc.yml`.
- **`taxes` viene como entero** (ej. `64022`) y falta determinar si son centavos
  o pesos enteros. Importa para no mostrarle un número equivocado al usuario.
- **El token de Aerolíneas se carga a mano** en `AEROLINEAS_TOKEN`. Se confirmó
  que es **anónimo** (la web muestra millas sin iniciar sesión), así que se
  puede automatizar y dejar el sistema desatendido en Render. Falta encontrar de
  dónde lo saca la web: `/v1/token` responde 404. Cuando vence, el backend
  avisa con `motivo: "token_vencido"`.
- **Render puede no soportar Python 3.14.** Mantener el código compatible con
  3.11+ y fijar la versión que Render ofrezca al llegar a la Fase 6.
