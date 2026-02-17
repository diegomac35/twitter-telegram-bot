# Bot de Twitter → Telegram con Claude AI

## Qué hace
Lee tus 4 listas de Twitter y te manda un resumen por Telegram a las 6 AM y 6 PM (hora Argentina), generado por Claude AI.

## Cómo desplegarlo en Railway

### Paso 1: Subir el código a GitHub
1. Abrí GitHub y creá un repositorio nuevo (nombre sugerido: `twitter-telegram-bot`)
2. Subí estos 3 archivos: `bot.py`, `requirements.txt`, `Procfile`

### Paso 2: Conectar Railway con GitHub
1. Entrá a railway.app
2. Clickeá "New Project" → "Deploy from GitHub repo"
3. Seleccioná el repositorio que acabás de crear

### Paso 3: Configurar las variables de entorno
En Railway, andá a tu proyecto → "Variables" y agregá estas 4 variables:

| Variable | Valor |
|---|---|
| TWITTER_BEARER_TOKEN | (tu bearer token de Twitter) |
| ANTHROPIC_API_KEY | (tu API key de Anthropic) |
| TELEGRAM_TOKEN | (el token que te dio BotFather) |
| TELEGRAM_CHAT_ID | 1432937471 |

### Paso 4: Listo
Railway va a instalar todo automáticamente y el bot va a empezar a correr.
Vas a recibir el primer resumen a las 6 AM o 6 PM del día siguiente.

## Para probar que funciona
En Railway podés ver los logs en tiempo real. Deberías ver:
`Bot iniciado. Esperando 6 AM y 6 PM (Argentina)...`
