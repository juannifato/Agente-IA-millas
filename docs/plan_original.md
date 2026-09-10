# IA Comparadora de Millas (Costo Cero)

> Documento original del proyecto, tal como lo trajo Juan el 2026-09-09.
> Se transcribe acá para que el repositorio sea autosuficiente.
>
> **Lo que cambió respecto de este plan** está anotado al final. El plan se
> conserva sin modificar para no perder la intención original.

Este documento detalla el paso a paso para construir un agente autónomo que
extrae, analiza y compara pasajes en millas, utilizando infraestructura 100%
gratuita, técnicas de evasión de bloqueos en lugar de servicios pagos, y un
sistema de auto-documentación de código.

## FASE 1: Preparación del Entorno y Auto-Documentación

1. **Instalar Git y Editor de Código:** Descargar e instalar Git y Visual Studio
   Code (para el backend) y Visual Studio (para el frontend en Visual Basic).
2. **Crear Repositorio en GitHub:** Crear una cuenta en GitHub y abrir un
   repositorio nuevo (ej. `agente-millas-ia`).
3. **Configurar la Auto-Bitácora (GitHub Actions):**
   - Dentro del repositorio, crear una carpeta `.github/workflows`.
   - Adentro, crear un archivo llamado `autodoc.yml`.
   - En ese archivo, programaremos una regla que diga: "Cada vez que el usuario
     hace un Push, tomá el mensaje del commit, pasalo por la API gratuita de
     Groq (Llama 3) para que redacte un resumen técnico de lo que se construyó,
     y agregá ese texto al archivo `Bitacora_Construccion.txt`".
4. **Vincular el Entorno Local:** Clonar el repositorio en tu computadora
   (`git clone`). Todo lo que programes a partir de ahora, al hacer push,
   actualizará tu manual solo.

## FASE 2: Cuentas e Infraestructura 100% Gratuita

1. **Cuenta en Render:** Registrarse en Render.com usando tu cuenta de GitHub.
   Render nos dará el servidor gratuito para alojar el backend sin pedir tarjeta
   de crédito.
2. **Obtener API de IA (Groq):** Ingresar a console.groq.com, crear una cuenta
   gratis y generar tu `API_KEY`. Esto nos dará acceso al modelo Llama 3
   ultrarrápido a costo cero.
3. **Variables de Entorno:** Guardar tu `GROQ_API_KEY` en un archivo `.env` en tu
   entorno local para que la IA tenga acceso de forma segura.

## FASE 3: El Motor de Extracción (Scraping Sin Costo ni CAPTCHAs)

1. **Estructura del Backend:** Inicializar un proyecto en Node.js o Python (lo
   que te resulte más cómodo para el backend).
2. **Ingeniería Inversa de la API (Plan A):**
   - En lugar de abrir un navegador visual, programar un script que intercepte
     la "API oculta" de Aerolíneas Argentinas.
   - Simularemos las peticiones HTTP (Fetch/Axios) que hace la página web
     original por detrás. Si logramos esto, recibiremos los datos directamente
     en formato JSON limpio, saltando el CAPTCHA completamente y a la velocidad
     de la luz.
3. **Playwright Stealth (Plan B - Fallback):**
   - Si la API oculta está muy protegida, instalamos `playwright` y el plugin
     `playwright-stealth`.
   - Este plugin inyecta scripts que camuflan a tu bot borrando el rastro de que
     es un proceso automatizado (falsifica el User-Agent, esconde los atributos
     de Webdriver, etc.).
   - Programar la navegación: Inyectar las cookies de tu cuenta (para no tener
     que iniciar sesión), ir a la URL de vuelos, extraer el texto (`innerText`)
     y cerrar el navegador.

## FASE 4: El Cerebro Analítico (IA Groq / Llama 3)

1. **Módulo de Conexión IA:** Crear un archivo `analisis_ia.js` (o `.py`).
2. **Diseño del Prompt:** Escribir un bloque de instrucciones estrictas:
   "Recibirás un texto extraído de Aerolíneas Argentinas o un JSON. Tu objetivo
   es encontrar el origen, destino, fecha y precio en millas de cada vuelo.
   Debes comparar todos los vuelos de esa fecha y devolverme SOLO un JSON
   estructurado con el vuelo más barato. No agregues texto adicional."
3. **Integración:** El script de la Fase 3 le pasa sus resultados a este módulo
   de la Fase 4, la IA procesa la info y devuelve el resultado limpio.

## FASE 5: Desarrollo de la Interfaz (Visual Basic)

1. **Diseño del Formulario:** En Visual Studio, crear una aplicación de Windows
   Forms (WPF o WinForms). Agregar TextBoxes para "Origen (ej. BUE)", "Destino
   (ej. MAD)", y "Fecha (DD/MM/AAAA)".
2. **Botón de Ejecución:** Programar el botón "Buscar Mejor Vuelo".
3. **Conexión REST HTTP:** Codificar en Visual Basic una función usando
   `HttpClient` que empaquete los datos ingresados y haga una solicitud POST a
   la URL pública que nos va a dar Render (ej. `https://tu-api.onrender.com/buscar`).
4. **Renderizado de la Respuesta:** Tomar el JSON que devuelve Render (creado
   por la IA) y mostrarlo bonito en etiquetas (Labels) o un DataGrid en tu
   aplicación visual.

## FASE 6: Despliegue Serverless en Render

1. **Configurar el Deploy Continuo:** En la plataforma de Render, crear un nuevo
   "Web Service" y conectarlo a tu repositorio de GitHub.
2. **Definir el Comando de Arranque:** Indicarle a Render cómo prender tu
   servidor (ej. `npm start` o `python app.py`).
3. **Configurar el Auto-Deploy:** Activar la opción para que, cada vez que hagas
   un `git push` a tu repositorio, Render automáticamente descargue el nuevo
   código y actualice tu servidor en la nube sin que vos toques nada.
4. **Prueba Final:** Abrir tu aplicación de Visual Basic, ingresar un vuelo,
   darle a buscar y ver cómo la app se comunica con Render, Render hace el
   scraping sigiloso, la IA analiza, y la respuesta vuelve a tu pantalla.

## FASE 7: Escalabilidad (Agregar más Aerolíneas)

1. **Estructura Modular:** En tu backend, asegurarse de tener una carpeta
   `/scrapers/`. Adentro, el archivo `aerolineas_arg.js`.
2. **Añadir Nuevas:** El día de mañana, cuando quieras sumar Smiles o American
   Airlines, simplemente creás `smiles.js` en esa carpeta.
3. **Ruteo Dinámico:** Modificar tu código para que si en Visual Basic elegís
   "Smiles", el backend ejecute el scraper correspondiente y le pase esa
   información a la misma IA de siempre para que haga el análisis estandarizado.

---

## Desvíos respecto de este plan

Decisiones tomadas durante la construcción que cambian lo que dice arriba:

| Del plan | Lo que se hizo | Por qué |
|---|---|---|
| Node.js o Python | **Python 3.14 + Flask** | Preferencia de Juan. Node también estaba disponible |
| Llama 3 en Groq | **`openai/gpt-oss-120b`** | Groq pasó los modelos Llama al tier Enterprise: la cuenta gratuita no los tiene |
| Fase 3, Plan B: Playwright Stealth | **descartado** | Ver abajo |
| `aerolineas_arg.js` | `scrapers/aerolineas_arg.py` | Consecuencia de usar Python |

**Sobre el Plan B de la Fase 3.** Se acordó con Juan el 2026-09-09 no construir
la capa de camuflaje del bot ni el salteo de CAPTCHA: eso es evadir un control
de acceso puesto a propósito. Se consume la API JSON pública con User-Agent
propio y sin reintentos agresivos ante 403 o 429.

En la práctica no costó nada, porque el **Plan A funcionó**: la API de
Aerolíneas devuelve los vuelos en millas en JSON limpio, que es exactamente lo
que este documento buscaba.
