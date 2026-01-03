import os
import requests
from bs4 import BeautifulSoup
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

USER_LIMITS = {}
DAILY_LIMIT = 3

MARKET_AVERAGE = 600_000
OPPORTUNITY_THRESHOLD = 15  # %

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Merhaba 👋\n"
        "Araç İlan Analiz Botu aktif.\n\n"
        "🆓 Ücretsiz kullanım: Günde 3 ilan\n"
        "📊 Fırsat kuralı: %15 ve üzeri\n\n"
        "Lütfen sadece sahibinden ilan linki gönder."
    )

def can_analyze(user_id: int) -> bool:
    today = date.today().isoformat()
    record = USER_LIMITS.get(user_id)

    if record is None or record["date"] != today:
        USER_LIMITS[user_id] = {"date": today, "count": 0}
        return True

    return record["count"] < DAILY_LIMIT

def increase_count(user_id: int):
    USER_LIMITS[user_id]["count"] += 1

def get_listing_data(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        # Başlık
        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else "İlan"

        # Fiyat
        price_tag = soup.find("span", {"class": "classified-price"})
        if not price_tag:
            return None, None

        price_text = price_tag.get_text()
        price = int(
            price_text.replace(".", "")
            .replace("TL", "")
            .replace("₺", "")
            .strip()
        )

        return title, price

    except Exception:
        return None, None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    user_id = update.effective_user.id

    if "sahibinden.com/ilan" not in text:
        await update.message.reply_text(
            "❌ Lütfen sadece sahibinden.com ilan linki gönderiniz."
        )
        return

    if not can_analyze(user_id):
        await update.message.reply_text(
            "⛔ Günlük ücretsiz analiz hakkın doldu.\n\n"
            "⭐ Standart Üyelik (49 TL / 7 gün)\n"
            "👑 Gold Üyelik (499 TL / 30 gün)\n\n"
            "Daha fazla analiz için /uyelik"
        )
        return

    title, price = get_listing_data(text)

    if price is None:
        await update.message.reply_text(
            "⚠️ İlan bilgileri okunamadı.\n"
            "Lütfen farklı bir ilan deneyin."
        )
        return

    increase_count(user_id)

    diff_percent = (MARKET_AVERAGE - price) / MARKET_AVERAGE * 100
    remaining = DAILY_LIMIT - USER_LIMITS[user_id]["count"]

    if diff_percent >= OPPORTUNITY_THRESHOLD:
        result = "✅ FIRSAT İLAN"
    else:
        result = "❌ FIRSAT DEĞİL"

    await update.message.reply_text(
        f"🚗 {title}\n\n"
        f"💰 İlan Fiyatı: {price:,} TL\n"
        f"📈 Piyasa Ort.: {MARKET_AVERAGE:,} TL\n"
        f"📉 Fark: %{diff_percent:.1f}\n\n"
        f"{result}\n\n"
        f"🧮 Kalan ücretsiz analiz: {remaining}"
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

