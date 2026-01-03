import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Merhaba 👋\n"
        "Araç İlan Analiz Botu aktif.\n\n"
        "Lütfen bir sahibinden.com ilan linki gönder."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "sahibinden.com/ilan" not in text:
        await update.message.reply_text(
            "❌ Lütfen sadece sahibinden.com ilan linki gönderiniz."
        )
        return

    await update.message.reply_text(
        "✅ Link alındı.\n"
        "Analiz modülü yakında aktif olacak."
    )

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
