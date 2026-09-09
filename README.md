# Agente Millas IA

Agente que busca pasajes en millas, los analiza con IA (Llama 3 vía Groq) y
devuelve el vuelo más conveniente. Infraestructura 100% gratuita.

## Arquitectura

```
Windows Forms (Visual Basic)          <-- Fase 5
        |  POST /buscar  (JSON)
        v
Backend Node.js en Render             <-- Fases 3 y 6
        |
        +--> /scrapers/  consulta la API de la aerolínea  --> JSON crudo
        |
        +--> /ia/        Groq + Llama 3 analiza y compara --> JSON limpio
```

## Estado de las fases

- [x] **Fase 1** — Entorno, repositorio y auto-bitácora con GitHub Actions
- [ ] **Fase 2** — Cuentas: Render + Groq, variables de entorno
- [ ] **Fase 3** — Motor de extracción (API de Aerolíneas Argentinas)
- [ ] **Fase 4** — Cerebro analítico (Groq / Llama 3)
- [ ] **Fase 5** — Interfaz de escritorio en Visual Basic
- [ ] **Fase 6** — Despliegue en Render con auto-deploy
- [ ] **Fase 7** — Escalabilidad: más aerolíneas (Smiles, AA, ...)

## Auto-bitácora

Cada `git push` a `main` dispara `.github/workflows/autodoc.yml`: toma el mensaje
del commit y la lista de archivos tocados, se los pasa a Llama 3 en Groq y agrega
un resumen técnico a `Bitacora_Construccion.txt`. Requiere el secret
`GROQ_API_KEY` cargado en el repositorio.

Para saltear la bitácora en un commit puntual, incluí `[skip bitacora]` en el mensaje.

## Configuración local

```bash
cp .env.example .env    # y completá GROQ_API_KEY
npm install
npm start
```

El archivo `.env` está en `.gitignore` y nunca se sube al repositorio.
