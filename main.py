# TEST AMAÇLI sahte fark yüzdesi
diff_percent = 16  # şimdilik sabit, sonraki adımda gerçek olacak

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
