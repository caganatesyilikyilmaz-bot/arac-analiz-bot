import os
from datetime import date
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

DAILY_LIMIT = 3
USER_LIMITS = {}

def get_user_record(user_id: int):
    today = date.today().isoformat()
    record = USER_LIMITS.get(user_id)

    if record is None or record["date"] != today:
        USER_LIMITS[user_id] = {"date": today, "count": 0}

    return USER_LIMITS[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Araç Analiz Botu aktif.\n\n"
        "🆓 Günlük ücretsiz hak: 3 analiz\n"
        "Mesaj göndererek test edebilirsin."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    record = get_user_record(user_id)

    if record["count"] >= DAILY_LIMIT:
        await update.message.reply_text(
            "⛔ Günlük ücretsiz analiz hakkın doldu.\n"
            "Daha fazlası için üyelik gerekir."
        )
        return

    record["count"] += 1
    kalan = DAILY_LIMIT - record["count"]

    # TEST AMAÇLI SABİT KARAR
    decision = (
        "🔥 AL-SAT İÇİN UYGUN\n\n"
        "Bu ilan piyasa ortalamasının belirgin şekilde altında.\n"
        "Hızlı alım-satım için uygun, marj yüksek."
    )

    await update.message.reply_text(
        f"{decision}\n\n"
        f"🧮 Kalan ücretsiz hak: {kalan}"
    )

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN bulunamadı")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

CACHE = {}
CACHE_TTL = 1800  # 30 dk

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def cache_get(key):
    item = CACHE.get(key)
    if not item:
        return None
    value, ts = item
    if time.time() - ts > CACHE_TTL:
        del CACHE[key]
        return None
    return value

def cache_set(key, value):
    CACHE[key] = (value, time.time())

def parse_basic_info_from_title(title: str):
    # Çok basit ilk MVP: "Fiat Egea 1.4 Fire 2019" gibi başlıklardan
    words = title.split()
    brand = words[0] if len(words) > 0 else ""
    model = words[1] if len(words) > 1 else ""
    year = ""
    for w in words:
        if w.isdigit() and len(w) == 4:
            year = w
            break
    return brand, model, year

def fetch_market_average(brand, model, year):
    key = f"{brand}-{model}-{year}"
    cached = cache_get(key)
    if cached:
        return cached

    query = f"site:sahibinden.com {brand} {model} {year}"
    url = f"https://www.google.com/search?q={quote_plus(query)}"

    r = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    prices = []
    for span in soup.find_all("span"):
        txt = span.get_text()
        if "TL" in txt or "₺" in txt:
            digits = "".join(c for c in txt if c.isdigit())
            if digits.isdigit():
                p = int(digits)
                if 50_000 < p < 5_000_000:
                    prices.append(p)

        if len(prices) >= 10:
            break

    if not prices:
        return None

    avg = sum(prices) // len(prices)
    cache_set(key, avg)
    return avg
