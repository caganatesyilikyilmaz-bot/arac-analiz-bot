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

# Basit bellek içi sayaç (şimdilik yeterli)
# Yapı: { user_id: {"date": YYYY-MM-DD, "count": int} }
USER_LIMITS = {}
DAILY_LIMIT = 3

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Merhaba 👋\n"
        "Araç İlan Analiz Botu aktif.\n\n"
        "🆓 Ücretsiz kullanım: Günde 3 ilan analizi\n"
        "Lütfen bir sahibinden.com ilan linki gönder."
    )

def can_analyze(user_id: int) -> bool:
    today = date.today().isoformat()
    record = USER_LIMITS.get(user_id)

    if record is None or record["date"] != today:
        # Yeni gün veya ilk kullanım
        USER_LIMITS[user_id] = {"date": today, "count": 0}
        return True

    return record["count"] < DAILY_LIMIT

def increase_count(user_id: int):
    USER_LIMITS[user_id]["count"] += 1

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    user_id = update.effective_user.id

    # Sadece ilan linki kabul
    if "sahibinden.com/ilan" not in text:
        await update.message.reply_text(
            "❌ Lütfen sadece sahibinden.com ilan linki gönderiniz."
        )
        return

    # Limit kontrolü
    if not can_analyze(user_id):
        await update.message.reply_text(
            "⛔ Günlük ücretsiz analiz hakkın doldu.\n\n"
            "⭐ Standart Üyelik (49 TL / 7 gün)\n"
            "👑 Gold Üyelik (499 TL / 30 gün)\n\n"
            "Daha fazla analiz için /uyelik"
        )
        return

    # Sayaç artır
    increase_count(user_id)

    # Şimdilik sahte analiz cevabı (bir sonraki adımda gerçek analiz gelecek)
    remaining = DAILY_LIMIT - USER_LIMITS[user_id]["count"]
    await update.message.reply_text(
        "✅ Link alındı.\n"
        "Analiz tamamlandı (test modu).\n\n"
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
