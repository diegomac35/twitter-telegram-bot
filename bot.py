import os
import asyncio
import logging
from datetime import datetime
import httpx
import anthropic
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TWITTER_BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN", "")
ANTHROPIC_API_KEY    = os.environ.get("ANTHROPIC_API_KEY", "")
TELEGRAM_TOKEN       = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID     = os.environ.get("TELEGRAM_CHAT_ID", "")

logger.info(f"Variables cargadas: TWITTER={'OK' if TWITTER_BEARER_TOKEN else 'FALTA'}, ANTHROPIC={'OK' if ANTHROPIC_API_KEY else 'FALTA'}, TELEGRAM={'OK' if TELEGRAM_TOKEN else 'FALTA'}, CHAT_ID={'OK' if TELEGRAM_CHAT_ID else 'FALTA'}")

LIST_IDS = [
    "2023175604594467083",
    "2023174944079647146",
    "2023171777426309170",
    "2023176436958314922",
]

TIMEZONE = "America/Argentina/Buenos_Aires"

async def get_list_tweets(client: httpx.AsyncClient, list_id: str, max_results: int = 20) -> list:
    url = f"https://api.twitter.com/2/lists/{list_id}/tweets"
    params = {
        "max_results": max_results,
        "tweet.fields": "created_at,author_id,text",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
    try:
        r = await client.get(url, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        tweets = data.get("data", [])
        users  = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
        result = []
        for t in tweets:
            user = users.get(t.get("author_id", ""), {})
            result.append({
                "text":     t["text"],
                "username": user.get("username", "?"),
                "name":     user.get("name", "?"),
            })
        return result
    except Exception as e:
        logger.error(f"Error leyendo lista {list_id}: {e}")
        return []

def generate_summary(all_tweets: list) -> str:
    if not all_tweets:
        return "No se encontraron tweets en las listas."
    tweets_text = ""
    for i, t in enumerate(all_tweets, 1):
        tweets_text += f"{i}. @{t['username']}: {t['text']}\n\n"
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": f"""Sos mi asistente personal. Aca estan los tweets mas recientes de mis 4 listas de Twitter.
Haceme un resumen claro y util en español. Organizalo por temas importantes. Destaca lo mas relevante. Se conciso pero completo. Usa emojis para que sea facil de leer.

TWEETS:
{tweets_text}

Resumen:"""
        }]
    )
    return message.content[0].text

async def fetch_and_summarize() -> str:
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[get_list_tweets(client, lid) for lid in LIST_IDS])
    all_tweets = [t for sublist in results for t in sublist]
    logger.info(f"Total tweets: {len(all_tweets)}")
    return generate_summary(all_tweets)

async def send_scheduled_summary(period: str):
    logger.info(f"Enviando resumen programado: {period}")
    try:
        summary = await fetch_and_summarize()
        now = datetime.now(pytz.timezone(TIMEZONE))
        header = f"{'🌅' if period == 'morning' else '🌆'} *Resumen {'Mañana' if period == 'morning' else 'Tarde/Noche'}* — {now.strftime('%d/%m/%Y %H:%M')}\n\n"
        full_message = header + summary
        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            if len(full_message) > 4096:
                for chunk in [full_message[i:i+4096] for i in range(0, len(full_message), 4096)]:
                    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=chunk, parse_mode="Markdown")
                    await asyncio.sleep(1)
            else:
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=full_message, parse_mode="Markdown")
        logger.info("Resumen enviado.")
    except Exception as e:
        logger.error(f"Error enviando resumen: {e}")

async def cmd_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Generando resumen, esperá un momento...")
    try:
        summary = await fetch_and_summarize()
        now = datetime.now(pytz.timezone(TIMEZONE))
        header = f"🔍 *Resumen Manual* — {now.strftime('%d/%m/%Y %H:%M')}\n\n"
        full_message = header + summary
        if len(full_message) > 4096:
            for chunk in [full_message[i:i+4096] for i in range(0, len(full_message), 4096)]:
                await update.message.reply_text(chunk, parse_mode="Markdown")
                await asyncio.sleep(1)
        else:
            await update.message.reply_text(full_message, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hola! Soy tu bot de resumen de Twitter.\n\n"
        "Comandos:\n"
        "/resumen — Genera un resumen ahora mismo\n\n"
        "También te mando resúmenes automáticos a las 6 AM y 6 PM (Argentina)."
    )

async def post_init(application: Application):
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(lambda: asyncio.create_task(send_scheduled_summary("morning")), "cron", hour=6, minute=0)
    scheduler.add_job(lambda: asyncio.create_task(send_scheduled_summary("evening")), "cron", hour=18, minute=0)
    scheduler.start()
    logger.info("Scheduler iniciado. Bot esperando 6 AM y 6 PM (Argentina)...")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("resumen", cmd_resumen))
    logger.info("Arrancando bot con polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
