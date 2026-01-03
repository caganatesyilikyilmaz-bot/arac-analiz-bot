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
