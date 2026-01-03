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

# ================== STATE ==================

USER_STATE = {}
USER_TEMP = {}

# ================== HELPERS ==================

def extract_listing_id(url: str):
    match = re.search(r"-([0-9]{6,})", url)
    return match.group(1) if match else None

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

def trimmed_mean(values, ratio=0.1):
    if len(values) < 5:
        return sum(values) / len(values)
    values = sorted(values)
    k = int(len(values) * ratio)
    trimmed = values[k:-k] if k > 0 else values
    return sum(trimmed) / len(trimmed)

def standard_deviation(values):
    avg = sum(values) / len(values)
    variance = sum((x - avg) ** 2 for x in values) / len(values)
    return math.sqrt(variance)

def advanced_market_analysis(data):
    km_min = int(data["km"] * 0.85)
    km_max = int(data["km"] * 1.15)
    yil_min = data["yil"] - 1 if data["yil"] else 0
    yil_max = data["yil"] + 1 if data["yil"] else 9999

    cursor.execute("""
    SELECT fiyat FROM listings
    WHERE marka = ?
      AND model = ?
      AND hasar = ?
      AND km BETWEEN ? AND ?
      AND yil BETWEEN ? AND ?
    """, (
        data["marka"],
        data["model"],
        data["hasar"],
        km_min,
        km_max,
        yil_min,
        yil_max
    ))

    prices = [r[0] for r in cursor.fetchall()]

    if len(prices) < 10:
        return None

    avg = sum(prices) / len(prices)
    std = standard_deviation(prices)

    # outlier temizleme (±2 std)
    filtered = [p for p in prices if avg - 2*std <= p <= avg + 2*std]
    if len(filtered) < 8:
        filtered = prices

    med = median(filtered)
    tmean = trimmed_mean(filtered)
    mean = sum(filtered) / len(filtered)

    reference_price = (0.5 * med) + (0.3 * tmean) + (0.2 * mean)
    diff_percent = ((reference_price - data["fiyat"]) / reference_price) * 100
    std_ratio = (std / reference_price) * 100

    # güven skoru
    confidence = 50
    confidence += min(len(filtered), 20) * 1.5
    confidence -= min(std_ratio, 20)
    confidence = max(40, min(95, int(confidence)))

    return {
        "count": len(filtered),
        "reference": int(reference_price),
        "diff": diff_percent,
        "std_ratio": std_ratio,
        "confidence": confidence
    }

# ================== BOT HANDLERS ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Araç Veri Botu\n\n"
        "İlan linkini gönder.\n"
        "Bot senden fiyat, km ve hasar bilgisi isteyecek\n"
        "ve yeterli veri varsa piyasa analizi yapacak."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    state = USER_STATE.get(user_id, "idle")

    # -------- LINK --------
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
        await update.message.reply_text("📌 Fiyatı (TL) yaz:")
        return

    # -------- FİYAT --------
    if state == "await_price":
        if not text.isdigit():
            await update.message.reply_text("❌ Sadece rakam gir.")
            return
        USER_TEMP[user_id]["fiyat"] = int(text)
        USER_STATE[user_id] = "await_km"
        await update.message.reply_text("📌 Km bilgisini yaz:")
        return

    # -------- KM --------
    if state == "await_km":
        if not text.isdigit():
            await update.message.reply_text("❌ Sadece rakam gir.")
            return
        USER_TEMP[user_id]["km"] = int(text)
        USER_STATE[user_id] = "await_damage"
        await update.message.reply_text("📌 Hasar durumu? (Boyasız / Değişen var / Bilmiyorum)")
        return

    # -------- HASAR + ANALİZ --------
    if state == "await_damage":
        USER_TEMP[user_id]["hasar"] = text
        data = USER_TEMP[user_id]

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

        analysis = advanced_market_analysis(data)

        USER_STATE[user_id] = "idle"
        USER_TEMP.pop(user_id, None)

        if not analysis:
            await update.message.reply_text(
                "✅ İlan kaydedildi.\n"
                "🔍 Analiz için yeterli veri yok (min 10)."
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

        if std_ratio > 15:
            risk = "⚠️ Piyasa verisi dağınık"
        elif std_ratio > 8:
            risk = "ℹ️ Piyasa normal dalgalı"
        else:
            risk = "✅ Piyasa stabil"

        await update.message.reply_text(
            f"📊 Gelişmiş Piyasa Analizi\n\n"
            f"Benzer ilan: {analysis['count']}\n"
            f"Referans fiyat: {analysis['reference']:,} TL\n"
            f"Bu ilan: {data['fiyat']:,} TL\n"
            f"Fark: %{diff:.1f}\n\n"
            f"{decision}\n"
            f"{risk}\n\n"
            f"🔐 Analiz Güveni: %{analysis['confidence']}"
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
