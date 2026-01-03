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

    # ŞİMDİLİK SABİT TEST DEĞERİ
    diff_percent = 16  

    if diff_percent >= 15:
        decision = (
            "🔥 AL-SAT İÇİN UYGUN\n\n"
            "Bu ilan piyasa ortalamasının belirgin şekilde altında.\n"
            "Hızlı alım-satım için uygun, marj yüksek."
        )
    elif diff_percent >= 8:
        decision = (
            "⚠️ PAZARLIKLA DEĞERLENDİRİLEBİLİR\n\n"
            "Fiyat kısmen uygun.\n"
            "Pazarlık yapılmadan işlem önerilmez."
        )
    else:
        decision = (
            "❌ UZAK DUR / BEKLE\n\n"
            "Fiyat piyasa seviyesinde.\n"
            "Al-sat için yeterli marj yok."
        )

    await update.message.reply_text(
        f"{decision}\n\n"
        f"🧮 Kalan ücretsiz hak: {kalan}"
    )
