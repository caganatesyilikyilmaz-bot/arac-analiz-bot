import os
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Merhaba 👋\n"
        "Araç İlan Analiz Botu aktif.\n\n"
        "Lütfen bir sahibinden.com ilan linki gönder."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""

    if "sahibinden.com/ilan" not in text:
        await update.message.reply_text(
            "❌ Lütfen sadece sahibinden.com ilan linki gönderiniz."
        )
        return

    await update.message.reply_text(
        "✅ Link alındı.\n"
        "Analiz modülü yakında aktif olacak."
    )

async def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN bulunamadı")

    app: Application = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app.initialize()
    await app.start()
    await app.bot.initialize()
    await app.run_polling()
    await app.stop()
    await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
