import os
import time
import requests
from datetime import date
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
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

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ---------------- SAFE MARKET ----------------

def parse_basic_info_from_title(title: str):
    words = title.split()
    brand = words[0] if len(words) > 0 else ""
    model = words[1] if len(words) > 1 else ""
    year = ""
    for w in words:
        if w.isdigit() and len(w) == 4:
            year = w
            break
    return brand, model, year

def fetch_market_average_safe(brand, model, year):
    try:
        query = f"site:sahibinden.com {brand} {model} {year}"
        url = f"https://www.google.com/search?q={quote_plus(query)}"

        r = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")

        prices = []
        for span in soup.find_all("span"):
            txt = span.get_text()
            digits = "".join(c for c in txt if c.isdigit())
            if digits.isdigit():
                p = int(digits)
                if 50_000 < p < 5_000_000:
                    prices.append(p)
            if len(prices) >= 5:
                break

        if not prices:
            return None

        return sum(prices) // len(prices)

    except Exception:
        return None

def extract_price_from_text(text: str):
    digits = "".join(c for c in text if c.isdigit())
    if not digits:
        return None
    price = int(digits)
    if price < 50_000 or price > 10_000_000:
        return None
    return price

# ---------------- USER LIMIT ----------------

def get_user_record(user_id: int):
    today = date.today().isoformat()
    record = USER_LIMITS.get(user_id)

    if record is None or record["date"] != today:
        USER_LIMITS[user_id] = {"date": today, "count": 0}

    return USER_LIMITS[user_id]

# ---------------- BOT ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Araç Analiz Botu aktif\n\n"
        "Örnek kullanım:\n"
        "Fiat Egea 2019 645000"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    record = get_user_record(user_id)

    if record["count"] >= DAILY_LIMIT:
        await update.message.reply_text(
            "⛔ Günlük ücretsiz analiz hakkın doldu."
        )
        return

    record["count"] += 1
    kalan = DAILY_LIMIT - record["count"]

    text = update.message.text or ""
    brand, model, year = parse_basic_info_from_title(text)
    price = extract_price_from_text(text)
    market_avg = fetch_market_average_safe(brand, model, year)

    if market_avg and price:
        diff = ((market_avg - price) / market_avg) * 100
    else:
        diff = 0

    if diff >= 15:
        decision = "🔥 AL-SAT İÇİN UYGUN"
    elif diff >= 8:
        decision = "⚠️ PAZARLIKLA DEĞERLENDİRİLEBİLİR"
    else:
        decision = "❌ UZAK DUR / BEKLE"

    await update.message.reply_text(
        f"{decision}\n"
        f"Fark: %{diff:.1f}\n\n"
        f"🧮 Kalan hak: {kalan}"
    )

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
