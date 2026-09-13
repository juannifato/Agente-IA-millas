# Fase 6 — Deploy del backend en Render

Poner el backend en internet, gratis y sin tarjeta, para que la app de escritorio
no dependa de tener la PC con el servidor prendido. Todo esto lo hace Juan una vez.

## Antes de empezar

- Cuenta en **render.com** (se puede con la cuenta de GitHub, sin tarjeta).
- El repo ya está en GitHub, con `render.yaml` y `.python-version` incluidos.
- **Ojo con la versión de Python**: Render no tiene la 3.14 de la PC local. Por eso
  el código se mantuvo compatible con 3.11+ y `.python-version` fija **3.12**. Si
  Render se queja de esa versión, cambiá ese archivo por la que ofrezca (ej. 3.13).

## Deploy con el Blueprint (recomendado)

1. En Render: **New +** → **Blueprint**.
2. Conectá el repositorio `Agente-IA-millas`. Render lee `render.yaml` solo y arma
   un Web Service con el build (`pip install -r requirements.txt`) y el arranque
   (`gunicorn app:app --workers 1`).
3. Antes de crear, Render pide las claves marcadas como secretas. Cargá:
   - `GROQ_API_KEY` → tu clave de Groq.
   - `AEROLINEAS_TOKEN` → un token vigente (sacado del navegador, como siempre).
4. **Create**. En unos minutos queda una URL tipo `https://agente-millas-ia.onrender.com`.

## Probar que anda

Abrí en el navegador (o con curl):
```
https://TU-APP.onrender.com/salud
```
Tiene que responder `{"ok": true, ...}`. También `/aerolineas` y `/aeropuertos`.

## Apuntar la app de escritorio a Render

En `MillasApp/ClienteApi.vb`, cambiá la constante:
```vb
Public Const BaseUrl As String = "https://TU-APP.onrender.com"
```
(estaba en `http://127.0.0.1:3000`). Recompilás la app y ya le pega a Render en vez
de a tu PC. Así se la podés pasar a un allegado y le funciona sin levantar nada.

## Auto-deploy

Cada `git push` a `main` hace que Render vuelva a desplegar solo. No hay que tocar
nada más.

## Lo que hay que saber del plan gratis

- **Se duerme**: tras ~15 min sin uso, Render apaga el servicio. La primera búsqueda
  después tarda ~30-60 s en "despertarlo"; las siguientes van normales.
- **El token al dormir**: cuando el servicio se reinicia (al despertar o redeployar),
  el token que hayas cargado en caliente desde la app se pierde y vuelve al
  `AEROLINEAS_TOKEN` de las variables de Render. Si ese venció, entrás a la app,
  botón **🔑 Token**, pegás uno nuevo y listo (queda hasta el próximo reinicio).
  Para uso personal alcanza; automatizarlo requeriría un navegador headless y plan
  pago (se descartó). Si querés que dure más entre reinicios, actualizá también la
  variable `AEROLINEAS_TOKEN` en el panel de Render de tanto en tanto.
- **Un solo worker**: el arranque usa `--workers 1` a propósito, porque el token y el
  caché de búsquedas viven en memoria; con varios workers quedarían descoordinados.

## Si algo falla

- Mirá los **Logs** en el panel de Render.
- 502 al arrancar: casi siempre es la versión de Python (`.python-version`) o una
  dependencia. Los logs lo dicen.
- El backend responde JSON hasta en los errores, así que la app nunca se rompe:
  muestra el `motivo` y el texto.
