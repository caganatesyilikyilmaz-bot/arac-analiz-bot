import os
import re
import sqlite3
import math
from statistics import median
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== CONFIG ==================

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN ortam değişkeni tanımlı değil")

# ================== DATABASE ==================

conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    listing_id TEXT UNIQUE,
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

# ================== STATE ==================

USER_STATE = {}
USER_TEMP = {}

# ================== HELPERS ==================

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

def normalize_damage(text: str):
    t = text.lower()
    if "boya" in t and "değişen" not in t:
        return "boyasız"
    if "değişen" in t or "hasar" in t:
        return "hasarlı"
    return "bilinmiyor"

def trimmed_mean(values, ratio=0.1):
    if len(values) < 5:
        return sum(values) / len(values)
    values = sorted(values)
    k = int(len(values) * ratio)
    sliced = values[k:-k] if k > 0 else values
    return sum(sliced) / len(sliced)

def standard_deviation(values):
    avg = sum(values) / len(values)
    return math.sqrt(sum((x - avg) ** 2 for x in values) / len(values))

def advanced_market_analysis(data):
    km_min = int(data["km"] * 0.75)
    km_max = int(data["km"] * 1.25)

    yil = data["yil"] if isinstance(data["yil"], int) else None
    yil_min = yil - 1 if yil else 0
    yil_max = yil + 1 if yil else 9999

    cursor.execute("""
    SELECT fiyat FROM listings
    WHERE marka = ?
      AND model = ?
      AND hasar = ?
      AND km BETWEEN ? AND ?
      AND yil BETWEEN ? AND ?
      AND listing_id != ?
    """, (
        data["marka"],
        data["model"],
        data["hasar"],
        km_min,
        km_max,
        yil_min,
        yil_max,
        data["listing_id"]
    ))

    prices = [r[0] for r in cursor.fetchall()]

    # 🔴 MİNİMUM 5 ARAÇ ŞARTI
    if len(prices) < 5:
        return None

    avg = sum(prices) / len(prices)
    std = standard_deviation(prices)

    filtered = [p for p in prices if avg - 2*std <= p <= avg + 2*std]
    if len(filtered) < 4:
        filtered = prices

    ref = int(
        0.5 * median(filtered) +
        0.3 * trimmed_mean(filtered) +
        0.2 * (sum(filtered) / len(filtered))
    )

    if ref <= 0:
        return None

    diff = ((ref - data["fiyat"]) / ref) * 100
    std_ratio = (std / ref) * 100 if ref > 0 else 0

    confidence = int(max(40, min(95, 50 + len(filtered)*2 - std_ratio)))

    return {
        "count": len(filtered),
        "reference": ref,
        "diff": diff,
        "std_ratio": std_ratio,
        "confidence": confidence
    }

# ================== BOT ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Araç Analiz Botu\n\n"
        "İlan linkini gönder.\n"
        "Bot senden fiyat, km ve hasar bilgisi isteyecek."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    state = USER_STATE.get(user_id, "idle")

    if state == "idle" and text.startswith("http"):
        listing_id = extract_listing_id(text)
        if not listing_id:
            await update.message.reply_text("❌ Geçerli ilan ID bulunamadı.")
            return

        cursor.execute("SELECT 1 FROM listings WHERE listing_id = ?", (listing_id,))
        if cursor.fetchone():
            await update.message.reply_text("⚠️ Bu ilan daha önce kaydedilmiş.")
            return

        marka, model, yil = parse_basic_from_url(text)
        USER_TEMP[user_id] = {
            "source": "sahibinden",
            "listing_id": listing_id,
            "marka": marka,
            "model": model,
            "yil": yil,
        }
        USER_STATE[user_id] = "await_price"
        await update.message.reply_text("📌 Fiyatı (TL) yaz:")
        return

    if state == "await_price":
        if not text.isdigit():
            await update.message.reply_text("❌ Sadece rakam gir.")
            return
        USER_TEMP[user_id]["fiyat"] = int(text)
        USER_STATE[user_id] = "await_km"
        await update.message.reply_text("📌 Km bilgisini yaz:")
        return

    if state == "await_km":
        if not text.isdigit():
            await update.message.reply_text("❌ Sadece rakam gir.")
            return
        USER_TEMP[user_id]["km"] = int(text)
        USER_STATE[user_id] = "await_damage"
        await update.message.reply_text("📌 Hasar durumu?")
        return

    if state == "await_damage":
        data = USER_TEMP[user_id]
        data["hasar"] = normalize_damage(text)

        cursor.execute("""
        INSERT INTO listings (
            source, listing_id, marka, model, yil,
            km, fiyat, hasar, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["source"],
            data["listing_id"],
            data["marka"],
            data["model"],
            data["yil"],
            data["km"],
            data["fiyat"],
            data["hasar"],
            datetime.now().isoformat()
        ))
        conn.commit()

        try:
            analysis = advanced_market_analysis(data)
        except Exception:
            analysis = None

        USER_STATE[user_id] = "idle"
        USER_TEMP.pop(user_id, None)

        if not analysis:
            await update.message.reply_text(
                "✅ Kaydedildi.\n"
                "🔍 Analiz için yeterli benzer ilan yok (min 5)."
            )
            return

        diff = analysis["diff"]
        std_ratio = analysis["std_ratio"]

        if diff >= 15 and std_ratio < 12:
            decision = "🔥 AL-SAT İÇİN FIRSAT"
        elif diff >= 8:
            decision = "⚠️ PAZARLIKLA ALINABİLİR"
        else:
            decision = "❌ PİYASA FİYATI"

        await update.message.reply_text(
            f"📊 Piyasa Analizi\n\n"
            f"Benzer ilan: {analysis['count']}\n"
            f"Referans fiyat: {analysis['reference']:,} TL\n"
            f"Bu ilan: {data['fiyat']:,} TL\n"
            f"Fark: %{diff:.1f}\n\n"
            f"{decision}\n"
            f"🔐 Güven: %{analysis['confidence']}"
        )
        return

    await update.message.reply_text("ℹ️ Lütfen ilan linki gönder.")

# ================== MAIN ==================

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()

