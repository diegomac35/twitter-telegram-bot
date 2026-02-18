import cron from "node-cron";
import TelegramBot from "node-telegram-bot-api";
import { chromium } from "playwright";

// ================= ENV =================
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

// URLs de tus listas
const LIST_URLS = [
  "https://x.com/i/lists/2023175604594467083",
  "https://x.com/i/lists/2023174944079647146",
  "https://x.com/i/lists/2023914064791949648",
  "https://x.com/i/lists/2023914667295305748",
  "https://x.com/i/lists/2023171777426309170",
  "https://x.com/i/lists/2023176436958314922"
];

// Zona horaria Argentina
const TZ = "America/Argentina/Buenos_Aires";

if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
  console.error("❌ Faltan variables TELEGRAM");
  process.exit(1);
}

const bot = new TelegramBot(TELEGRAM_BOT_TOKEN, { polling: true });

/**
 * Scrapea tweets recientes de una lista
 */
async function scrapeList(url, hours) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    storageState: "state.json" // cookies guardadas
  });

  const page = await context.newPage();

  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });

  // Scroll para cargar tweets
  for (let i = 0; i < 5; i++) {
    await page.mouse.wheel(0, 5000);
    await page.waitForTimeout(1500);
  }

  const tweets = await page.$$eval("article", nodes =>
    nodes.map(n => {
      const text = n.innerText;
      const timeEl = n.querySelector("time");
      const date = timeEl?.getAttribute("datetime");
      return { text, date };
    })
  );

  await browser.close();

  const cutoff = Date.now() - hours * 60 * 60 * 1000;

  return tweets.filter(t => t.date && new Date(t.date).getTime() > cutoff);
}

/**
 * Junta tweets de todas las listas
 */
async function getAllTweets(hours) {
  let all = [];

  for (const url of LIST_URLS) {
    try {
      const tweets = await scrapeList(url, hours);
      all = all.concat(tweets);
    } catch (e) {
      console.error("Error scraping:", url, e.message);
    }
  }

  return all;
}

/**
 * Resumen simple
 */
function summarize(tweets) {
  if (!tweets.length) return "⚠️ No hubo tweets en este período.";

  return tweets
    .slice(0, 20)
    .map(t => "• " + t.text.split("\n")[0])
    .join("\n\n");
}

/**
 * Envía resumen
 */
async function sendSummary(hours = 12) {
  const tweets = await getAllTweets(hours);
  const text = summarize(tweets);

  await bot.sendMessage(
    TELEGRAM_CHAT_ID,
    `📰 Resumen últimas ${hours}h\n\n${text}`
  );
}

// ================= CRON =================

// 6 AM Argentina
cron.schedule(
  "0 6 * * *",
  () => {
    console.log("⏰ 6AM resumen");
    sendSummary(12);
  },
  { timezone: TZ }
);

// 6 PM Argentina
cron.schedule(
  "0 18 * * *",
  () => {
    console.log("⏰ 6PM resumen");
    sendSummary(12);
  },
  { timezone: TZ }
);

// ================= COMANDOS =================

bot.onText(/\/resumen (\d+)h/, async (msg, match) => {
  const hours = parseInt(match[1]);
  await sendSummary(hours);
  bot.sendMessage(msg.chat.id, "✅ Listo.");
});

bot.onText(/\/test/, async msg => {
  await sendSummary(1);
  bot.sendMessage(msg.chat.id, "✅ Test OK.");
});
