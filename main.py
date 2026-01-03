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

USER_STATE = {}
USER_TEMP = {}

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

# ---------------- BOT ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYP_
