import os
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

# ---------------- MEMBERSHIP ----------------

USER_PLANS = {}   # user_id -> free / standard / gold
USER_LIMITS = {}  # günlük sayaç

def get_user_plan(user_id: int):
    return USER_PLANS.get(user_id, "free")

def get_daily_limit(plan: str):
    if plan == "gold":
        return 10_000
    if plan == "standard":
        return 10
    return 3

# ---------------- MARKET ----------------

HEADERS = {"User-Agent": "Mozilla/5.0"}

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
            digits = "".join(c for c in span.get_text() if c.isdigit())
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
    if 50_000 < price < 10_000_000:
        return price
    return None

# ---------------- LIMIT ----------------

def get_user_record(user_id: int):
    today = date.today().isoformat()
    record = USER_LIMITS.get(user_id)
    if record is None or record["date"] != today:
        USER_LIMITS[user_id] = {"date": today, "count": 0}
    return USER_LIMITS[user_id]

# ---------------- BOT ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Araç Analiz Botu\n\n"
        "🆓 Ücretsiz: Günde 3 analiz\n"
        "⭐ Standart: Günde 10 analiz – 49 TL\n"
        "💎 Gold: Sınırsız (30 gün) – 499 TL\n\n"
        "Örnek kullanım:\n"
        "Fiat Egea 2019 645000"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    plan = get_user_plan(user_id)
    daily_limit = get_daily_limit(plan)

    record = get_user_record(user_id)

    if record["count"] >= daily_limit:
        await update.message.reply_text(
            "⛔ Günlük kullanım hakkın doldu.\n\n"
            "⭐ Standart: Günde 10 analiz – 49 TL\n"
            "💎 Gold: Sınırsız (30 gün) – 499 TL\n\n"
            "Satın alma yakında aktif olacak."
        )
        return

    record["count"] += 1
    kalan = daily_limit - record["count"]

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
