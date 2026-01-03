import os
import re
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

# ---------------- DATABASE ----------------

conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    listing_id TEXT,
    marka TEXT,
    model TEXT,
    yil INTEGER,
    km INTEGER,
    fiyat INTEGER,
    hasar TEXT,
    created_at TEXT
)
""")
conn.commit()

# ---------------- USER STATES ----------------

USER_STATE = {}   # user_id -> state
USER_TEMP = {}    # geçici veri

# ---------------- HELPERS ----------------

def extract_listing_id(url: str):
    m = re.search(r"-([0-9]{6,})", url)
    return m.group(1) if m else None

def parse_basic_from_url(url: str):
    parts = url.split("-")
    marka = parts[1].capitalize() if len(parts) > 1 else ""
    model = parts[2].capitalize() if len(parts) > 2 else ""
    yil = None
    for p in parts:
        if p.isdigit() and len(p) == 4:
            yil = int(p)
            break
    return marka, model, yil

# ---------------- BOT HANDLERS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Araç Veri Botu\n\n"
        "Sahibinden veya benzeri bir sitede gördüğün\n"
        "ilanın linkini gönder.\n\n"
        "Bot ilanı açmaz, sadece senin verdiğin\n"
        "bilgilerle kendi veritabanını oluşturur."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    state = USER_STATE.get(user_id, "idle")

    # --- LINK GELDİ ---
    if state == "idle" and text.startswith("http"):
        listing_id = extract_listing_id(text)
        marka, model, yil = parse_basic_from_url(text)

        USER_TEMP[user_id] = {
            "source": "sahibinden",
            "listing_id": listing_id,
            "marka": marka,
            "model": model,
            "yil": yil,
        }

        USER_STATE[user_id] = "await_price"

        await update.message.reply_text(
            "🔗 İlan alındı.\n\n"
            "Bu ilanı kaydetmek için lütfen\n"
            "📌 Fiyatı (TL) yaz:"
        )
        return

    # --- FİYAT ---
    if state == "await_price":
        if not text.isdigit():
            await update.message.reply_text(
                "❌ Lütfen sadece rakam gir.\nÖrnek: 645000"
            )
            return

        USER_TEMP[user_id]["fiyat"] = int(text)
        USER_STATE[user_id] = "await_km"

        await update.message.reply_text("📌 Km bilgisini yaz:")
        return

    # --- KM ---
    if state == "await_km":
        if not text.isdigit():
            await update.message.reply_text(
                "❌ Lütfen sadece rakam gir.\nÖrnek: 72000"
            )
            return

        USER_TEMP[user_id]["km"] = int(text)
        USER_STATE[user_id] = "await_damage"

        await update.message.reply_text(
            "📌 Hasar durumu?\n"
            "(Boyasız / Değişen var / Bilmiyorum)"
        )
        return

    # --- HASAR ---
    if state == "await_damage":
        USER_TEMP[user_id]["hasar"] = text

        data = USER_TEMP[user_id]

        cursor.execute("""
        INSERT INTO listings (
            source, listing_id, marka, model, yil,
            km, fiyat, hasar, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("source"),
            data.get("listing_id"),
            data.get("marka"),
            data.get("model"),
            data.get("yil"),
            data.get("km"),
            data.get("fiyat"),
            data.get("hasar"),
            datetime.now().isoformat()
        ))
        conn.commit()

        USER_STATE[user_id] = "idle"
        USER_TEMP.pop(user_id, None)

        await update.message.reply_text(
            "✅ İlan veritabanına kaydedildi.\n\n"
            "Bu araç için yeterli veri oluştuğunda\n"
            "piyasa analizi yapılacaktır."
        )
        return

    # --- DİĞER MESAJLAR ---
    await update.message.reply_text(
        "ℹ️ Lütfen analiz etmek istediğin\n"
        "ilanın linkini gönder."
    )

# ---------------- MAIN ----------------

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN ortam değişkeni tanımlı değil")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", s_
