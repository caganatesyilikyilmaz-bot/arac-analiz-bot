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

def can_use(user_id: int) -> bool:
    today = date.today().isoformat()
    record = USER_LIMITS.get(user_id)

    if record is None or record["date"] != today:
        USER_LIMITS[user_id] = {"date": today, "count": 0}
        return True

    return record["count"] < DAILY_LIMIT

def increase(user_id: int):
    USER_LIMITS[user_id]["count"] += 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot aktif\n\n"
        "🆓 Günlük ücretsiz kullanım: 3 analiz\n"
        "Bir mesaj göndererek test edebilirsin."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not can_use(user_id):
        await update.message.reply_text(
            "⛔ Günlük ücretsiz hakkın doldu.\n"
            "Daha fazlası için üyelik gerekir."
        )
        return

    increase(user_id)
    kalan = DAILY_LIMIT - USER_LIMITS[user_id]["count"]

    await update.message.reply_text(
        f"✅ İşlem alındı.\n"
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
