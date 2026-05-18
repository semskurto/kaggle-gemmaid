#!/bin/bash
# GemmAid — Tüm Servisleri Başlat (llama.cpp Backend)
# Kullanım: bash deploy/start.sh
# Not: Ctrl+C ile hepsini durdurabilirsiniz.

set -e
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     GemmAid — Servis Başlatıcı (llama.cpp)          ║"
echo "╚══════════════════════════════════════════════════════╝"

# .env yükle
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
    echo "✅ .env yüklendi (backend=${GEMMAID_BACKEND:-local})"
else
    echo "⚠️  .env bulunamadı — varsayılan değerler kullanılıyor (backend=local)"
fi

# Model kontrolü
if [ "${GEMMAID_BACKEND:-local}" = "local" ]; then
    MODEL_PATH="${LOCAL_MODEL_PATH:-./models/gemma-4-E4B-it-Q4_K_M.gguf}"
    if [ ! -f "$MODEL_PATH" ]; then
        echo ""
        echo "❌ Model dosyası bulunamadı: $MODEL_PATH"
        echo "   Önce kurulumu çalıştırın: bash deploy/setup.sh"
        echo "   Veya: python scripts/download_model.py"
        exit 1
    fi
    MODEL_SIZE=$(du -sh "$MODEL_PATH" | awk '{print $1}')
    echo "🧠 Model: $MODEL_PATH ($MODEL_SIZE)"
fi

# Loglar için dizin
mkdir -p logs

echo ""
echo "📡 Servisler başlatılıyor..."
echo ""

# API
echo "  [1] API başlatılıyor (port ${API_PORT:-8000})..."
python api/api.py > logs/api.log 2>&1 &
API_PID=$!
echo "     PID: $API_PID → logs/api.log"

# API'nin ayağa kalkmasını bekle
sleep 3

# Dashboard
echo "  [2] Dashboard başlatılıyor (port ${DASHBOARD_PORT:-7860})..."
python dashboard/dashboard.py > logs/dashboard.log 2>&1 &
DASH_PID=$!
echo "     PID: $DASH_PID → logs/dashboard.log"

# Bot (token varsa)
if [ -n "$TELEGRAM_TOKEN" ] && [ "$TELEGRAM_TOKEN" != "BURAYA_TOKEN_YAZ" ]; then
    echo "  [3] Telegram Bot başlatılıyor..."
    python bot/bot.py > logs/bot.log 2>&1 &
    BOT_PID=$!
    echo "     PID: $BOT_PID → logs/bot.log"
else
    echo "  [3] ⚠️  TELEGRAM_TOKEN ayarlı değil — Bot atlandı"
    echo "     Rehber: docs/TELEGRAM_SETUP.md"
    BOT_PID=""
fi

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                  Servisler Aktif!                   ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  🔌 API       : http://localhost:${API_PORT:-8000}"
echo "  📊 Dashboard : http://localhost:${DASHBOARD_PORT:-7860}"
echo "  📖 API Docs  : http://localhost:${API_PORT:-8000}/docs"
echo "  🧠 Backend   : ${GEMMAID_BACKEND:-local} (llama.cpp + Gemma 4 E4B)"
echo ""
echo "Durdurmak için: Ctrl+C"
echo ""

# Temizleme
cleanup() {
    echo ""
    echo "🛑 Servisler durduruluyor..."
    [ -n "$API_PID"  ] && kill $API_PID  2>/dev/null && echo "  API durduruldu"
    [ -n "$DASH_PID" ] && kill $DASH_PID 2>/dev/null && echo "  Dashboard durduruldu"
    [ -n "$BOT_PID"  ] && kill $BOT_PID  2>/dev/null && echo "  Bot durduruldu"
    echo "✅ Temiz çıkış"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Logları takip et
echo "📝 API Logları (Ctrl+C ile dur):"
echo "──────────────────────────────────"
tail -f logs/api.log logs/dashboard.log 2>/dev/null
