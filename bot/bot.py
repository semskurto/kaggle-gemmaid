#!/usr/bin/env python3
"""GemmAid Telegram Bot — Çok Dilli Acil Triaj Botu

Komutlar:
  /start   — Hoşgeldin mesajı ve kullanım talimatları
  /status  — API durumu ve aktif vaka sayısı
  /demo    — 3 dilde demo triaj çalıştır
  /temizle — Vakaları sıfırla (sadece test)

Herhangi bir metin mesajı → otomatik triaj

Başlatma:
  TELEGRAM_TOKEN=xxx python bot/bot.py
"""
import asyncio
import httpx
import json
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode
import html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.config import TELEGRAM_TOKEN, API_BASE_URL

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("gemmaid.bot")

# ── Sabitler ─────────────────────────────────────────────────
TRIAGE_URL  = f"{API_BASE_URL}/triage"
CASES_URL   = f"{API_BASE_URL}/cases"
HEALTH_URL  = f"{API_BASE_URL}/health"
STATS_URL   = f"{API_BASE_URL}/stats"
DEMO_URL    = f"{API_BASE_URL}/demo"
DELETE_URL  = f"{API_BASE_URL}/cases"

ACIL_EMOJI = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "⚪"}
OLAY_TR = {
    "enkaz_alti":    "Enkaz Altı",
    "tibbi_acil":    "Tıbbi Acil",
    "tahliye":       "Tahliye",
    "kaynak_ihtiyaci": "Kaynak İhtiyacı",
    "belirsiz":      "Belirsiz",
}
EKIP_TR = {
    "tibbi":          "🚑 Tıbbi",
    "arama_kurtarma": "⛑️ Arama&Kurtarma",
    "tahliye":        "🚌 Tahliye",
    "lojistik":       "📦 Lojistik",
}


# ── Yardımcı Fonksiyonlar ─────────────────────────────────────
def format_triage_reply(data: dict) -> str:
    """Triaj verisini Telegram mesajına dönüştür."""
    acil   = data.get("aciliyet_skoru", 3)
    emoji  = ACIL_EMOJI.get(acil, "❓")
    olay   = OLAY_TR.get(data.get("olay_tipi", "belirsiz"), data.get("olay_tipi", "?"))
    ekipler = [EKIP_TR.get(e, e) for e in data.get("gerekli_ekip", [])]
    semplar = data.get("semptomlar", [])
    dil     = data.get("kaynak_dil", "?").upper()
    case_id = data.get("id", "?")
    ts      = data.get("timestamp", datetime.utcnow().strftime("%H:%M UTC"))

    acil_str = {
        1: "KRİTİK — Anında müdahale",
        2: "YÜKSEK — Öncelikli",
        3: "ORTA — İzleme gerekli",
        4: "DÜŞÜK — Bekleyebilir",
        5: "DÜŞÜK ÖNCELİK",
    }.get(acil, str(acil))

    vatandas_msaji = data.get("vatandasa_yanit", "Mesajınız merkeze iletilmiştir. Lütfen güvenli bir yerde kalın.")
    vatandas_msaji_escaped = html.escape(vatandas_msaji)
    konum_escaped = html.escape(data.get('konum_metni', 'Belirtilmedi'))

    lines = [
        f"👤 <b>Size Yanıt:</b>",
        f"<i>{vatandas_msaji_escaped}</i>",
        f"",
        f"{"─"*30}",
        f"📋 <b>Sistem Çıktısı (Koordinatör İçin)</b> [#{case_id}]",
        f"{emoji} <b>Aciliyet:</b> {acil}/5 — {acil_str}",
        f"🔷 <b>Olay Tipi:</b> {olay}",
        f"📍 <b>Konum:</b> {konum_escaped}",
        f"👥 <b>Etkilenen:</b> {data.get('etkilenen_kisi_sayisi', '?')} kişi",
        f"🌐 <b>Dil:</b> {dil}",
    ]

    if ekipler:
        lines.append(f"🚨 <b>Gereken Ekip:</b> {', '.join(ekipler)}")
    if semplar:
        lines.append(f"🩺 <b>Semptom:</b> {', '.join(semplar)}")

    # Inference lokasyonu
    loc = data.get("inference_location", data.get("backend", ""))
    if loc in ("on_device", "local", "transformers"):
        lines.append(f"🖥️ <b>Inference:</b> On-device")
    elif loc in ("cloud", "gemini"):
        lines.append(f"☁️ <b>Inference:</b> Cloud")

    nota = data.get("koordinator_notu", "")
    if nota:
        lines.append(f"")
        lines.append(f"📋 <b>Koordinatör Notu:</b>")
        lines.append(f"<i>{html.escape(nota)}</i>")

    lines.append(f"")
    lines.append(f"🕐 {ts}")

    if data.get("_parse_error"):
        lines.append(f"⚠️ <i>Otomatik triaj kısmi — lütfen manuel değerlendirin</i>")

    return "\n".join(lines)


async def safe_api_post(url: str, data: dict, timeout: int = 90) -> dict:
    """API'ya güvenli POST isteği."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=data)
        resp.raise_for_status()
        return resp.json()


async def safe_api_get(url: str, timeout: int = 10) -> dict:
    """API'ya güvenli GET isteği."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


# ── Komut Handler'ları ────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hoşgeldin mesajı."""
    msg = (
        "🆘 <b>GemmAid — Multilingual Emergency System / Çok Dilli Acil Triaj Sistemi</b>\n\n"
        "🌍 <b>Just type your message in your own language. / Acil durumunuzu kendi dilinizde yazın.</b>\n"
        "🇹🇷 Türkçe • 🇬🇧 English • 🇸🇦 العربية • 🇫🇷 Français • 140+ Languages\n\n"
        "<b>[EN]</b> Please describe your situation, location, and the number of people involved.\n"
        "<b>[TR]</b> Lütfen durumunuzu, tam konumunuzu ve kişi sayınızı yazın.\n"
        "<b>[AR]</b> يرجى كتابة وضعك وموقعك وعدد الأشخاص المتأثرين.\n"
        "<b>[FR]</b> Veuillez décrire votre situation, votre position et le nombre de personnes.\n\n"
        "⚡ <i>Powered by Gemma 4</i>"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """API durumu."""
    await update.message.reply_text("⏳ Kontrol ediliyor...")
    try:
        health = await safe_api_get(HEALTH_URL)
        stats  = await safe_api_get(STATS_URL)

        backend_emoji = {"local": "💻", "gemini": "☁️", "transformers": "🤖"}.get(
            health.get("backend", "?"), "❓"
        )
        model_info = ""
        if health.get("model"):
            m = health["model"]
            if m.get("loaded"):
                model_info = f"\n🧠 <b>Model:</b> Yüklü ✅ ({m.get('size_gb', '?')} GB)"
            elif m.get("exists"):
                model_info = f"\n🧠 <b>Model:</b> Disk'te mevcut, hafızaya yüklenmedi"
            else:
                model_info = f"\n🧠 <b>Model:</b> Bulunamadı - indirmeniz gerekiyor"

        msg = (
            f"📊 <b>GemmAid Sistem Durumu</b>\n\n"
            f"🔌 <b>API:</b> Çevrimiçi ✅\n"
            f"{backend_emoji} <b>Backend:</b> {health.get('backend','?').upper()}"
            f"{model_info}\n\n"
            f"📋 <b>Vaka İstatistikleri:</b>\n"
            f"  Toplam: {stats.get('toplam', 0)}\n"
            f"  🔴 Kritik: {stats.get('kritik', 0)}\n"
            f"  🟠 Yüksek: {stats.get('yuksek_oncelik', 0)}\n"
            f"  ⚪ Bekleyebilir: {stats.get('bekleyebilir', 0)}"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    except httpx.ConnectError:
        await update.message.reply_text(
            "❌ <b>API'ya bağlanılamıyor</b>\n\n"
            "API'yi başlatın:\n<code>python api/api.py</code>",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {e}")


async def cmd_demo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """3 dilde demo çalıştır."""
    await update.message.reply_text(
        "🎬 <b>Demo senaryoları çalıştırılıyor...</b>\n"
        "<i>TR / AR / FR / EN — 4 dil test ediliyor</i>",
        parse_mode=ParseMode.HTML,
    )
    try:
        result = await safe_api_get(DEMO_URL, timeout=300)
        demos = result.get("demo_results", [])
        for d in demos:
            lang = d.get("lang", "?")
            msg_text = d.get("message", "")
            if "error" in d:
                await update.message.reply_text(
                    f"[{lang}] ❌ Hata: {d['error']}"
                )
            else:
                triage = d.get("triage", {})
                triage["id"]        = d.get("case_id", "?")
                triage["timestamp"] = datetime.utcnow().strftime("%H:%M UTC")
                reply = format_triage_reply(triage)
                await update.message.reply_text(
                    f"<b>[Demo — {lang}]</b>\n<i>{html.escape(msg_text[:80])}</i>\n\n{reply}",
                    parse_mode=ParseMode.HTML,
                )
    except httpx.ConnectError:
        await update.message.reply_text("❌ API çevrimdışı. `python api/api.py` ile başlatın.")
    except Exception as e:
        await update.message.reply_text(f"❌ Demo hatası: {e}")


async def cmd_temizle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vakaları sıfırla."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(DELETE_URL)
            data = resp.json()
        await update.message.reply_text(
            f"🗑️ {data.get('deleted', 0)} vaka silindi.",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {e}")


# ── Mesaj Handler ────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gelen metin veya konum mesajını triaj et."""
    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
        msg = f"[Kullanıcı Telegram Kanalından Konum Paylaştı]: Tam Koordinat: https://maps.google.com/?q={lat},{lon}"
        # Telegram sometimes sends caption with location if it's a Live Location or Venue, but usually it's just location
        if update.message.caption:
            msg += f"\n\nMesaj: {update.message.caption.strip()}"
    else:
        msg = update.message.text.strip() if update.message.text else ""

    user = update.effective_user.first_name or "Kullanıcı"
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or ""
    log.info(f"[{user}] Mesaj: {msg[:80]}")

    # Bekleme mesajı
    wait_msg = await update.message.reply_text(
        "⏳ <i>Analiz ediliyor...</i>",
        parse_mode=ParseMode.HTML,
    )

    try:
        payload = {
            "message": msg,
            "sender_name": user,
            "telegram_id": user_id,
            "telegram_username": username,
        }
        data = await safe_api_post(TRIAGE_URL, payload, timeout=120)
        data.setdefault("timestamp", datetime.utcnow().strftime("%H:%M UTC"))

        reply = format_triage_reply(data)

        # Bekleme mesajını sil, triaj sonucunu gönder
        await wait_msg.delete()
        await update.message.reply_text(reply, parse_mode=ParseMode.HTML)

    except httpx.ConnectError:
        await wait_msg.edit_text(
            "❌ <b>API Çevrimdışı</b>\n\n"
            "Lütfen API'yi başlatın:\n"
            "<code>python api/api.py</code>",
            parse_mode=ParseMode.HTML,
        )
    except httpx.TimeoutException:
        await wait_msg.edit_text(
            "⏰ <b>Zaman Aşımı</b>\n\n"
            "Lokal model yavaş yanıt verdi. "
            "Lütfen tekrar deneyin.",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        log.error(f"Mesaj işleme hatası: {e}", exc_info=True)
        await wait_msg.edit_text(f"❌ Hata oluştu: {html.escape(str(e))}")


# ── Ana Fonksiyon ─────────────────────────────────────────────
def main():
    if TELEGRAM_TOKEN == "" or TELEGRAM_TOKEN == "BURAYA_TOKEN_YAZ":
        print("❌ TELEGRAM_TOKEN ayarlanmamış!")
        print("   .env dosyasına TELEGRAM_TOKEN=xxx ekleyin")
        print("   veya: TELEGRAM_TOKEN=xxx python bot/bot.py")
        sys.exit(1)

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Komutlar
    application.add_handler(CommandHandler("start",    cmd_start))
    application.add_handler(CommandHandler("status",   cmd_status))
    application.add_handler(CommandHandler("demo",     cmd_demo))
    application.add_handler(CommandHandler("temizle",  cmd_temizle))

    # Komutlar ve Mesajlar
    application.add_handler(
        MessageHandler((filters.TEXT | filters.LOCATION | filters.Document.ALL) & ~filters.COMMAND, handle_message)
    )

    log.info("🤖 GemmAid Bot başlatıldı (polling modu)...")
    log.info(f"   API: {API_BASE_URL}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
