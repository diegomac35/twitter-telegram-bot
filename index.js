import fetch from "node-fetch";
import TelegramBot from "node-telegram-bot-api";

// Variables de entorno
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;
const TWITTERAPI_KEY = process.env.TWITTERAPI_KEY;
const LIST_IDS = process.env.LIST_USERNAMES.split(","); // IDs de listas públicas, separadas por coma

// Inicia bot de Telegram
const bot = new TelegramBot(TELEGRAM_BOT_TOKEN, { polling: true });

// Función para traer tweets de una lista
async function getTweetsFromList(listId, sinceHours = 12) {
  const now = new Date();
  const since = new Date(now.getTime() - sinceHours * 60 * 60 * 1000).toISOString();
  const url = `https://api.twitterapi.io/list_timeline/${listId}?since=${since}&api_key=${TWITTERAPI_KEY}`;

  const res = await fetch(url);
  const data = await res.json();
  return data.tweets || [];
}

// Función para resumir tweets
function summarizeTweets(tweets) {
  if (!tweets.length) return "No hay tweets en este periodo.";
  return tweets.map(t => `- ${t.text}`).join("\n\n");
}

// Función para enviar resumen a Telegram
async function sendSummary(hours = 12) {
  let allTweets = [];
  for (let listId of LIST_IDS) {
    const tweets = await getTweetsFromList(listId, hours);
    allTweets = allTweets.concat(tweets);
  }
  const summary = summarizeTweets(allTweets);
  await bot.sendMessage(TELEGRAM_CHAT_ID, `Resumen últimas ${hours} horas:\n\n${summary}`);
}

// Comando on-demand en Telegram: /resumen 8h
bot.onText(/\/resumen (\d+)h/, async (msg, match) => {
  const hours = parseInt(match[1]);
  await sendSummary(hours);
  bot.sendMessage(msg.chat.id, `✅ Resumen de ${hours}h enviado.`);
});

// Test manual
bot.onText(/\/test/, async (msg) => {
  await sendSummary(1);
  bot.sendMessage(msg.chat.id, "✅ Test completado.");
});

// Export para scheduler
export default sendSummary;
