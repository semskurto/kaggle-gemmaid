#!/bin/bash
# GemmAid — Lokal Kurulum Scripti (llama.cpp / Gemma 4 E4B)
# Hedef: Intel CPU, 8GB RAM, Ubuntu
# Kullanım: bash deploy/setup.sh

set -e

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     GemmAid — Lokal Kurulum (llama.cpp Backend)     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "📁 Proje dizini: $PROJ_ROOT"
echo "🎯 Hedef: Intel CPU, 8GB RAM, Ubuntu"
echo ""

# ── 1. Python kontrolü ──────────────────────────────────────
echo -e "${BLUE}[1/6] Python sürümü kontrol ediliyor...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
if python3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
    echo -e "  ${GREEN}✅ Python $PYTHON_VERSION — uyumlu${NC}"
else
    echo -e "  ${RED}❌ Python $PYTHON_VERSION — 3.10+ gerekli${NC}"
    exit 1
fi

# ── 2. Sistem bağımlılıkları ────────────────────────────────
echo -e "${BLUE}[2/6] Sistem bağımlılıkları kuruluyor...${NC}"
echo "  cmake, build-essential, libopenblas-dev (llama.cpp optimizasyonu için)"
if command -v apt-get &> /dev/null; then
    sudo apt-get update -qq 2>/dev/null || true
    sudo apt-get install -y cmake build-essential pkg-config git libopenblas-dev -q 2>/dev/null || \
        echo -e "  ${YELLOW}⚠️  Sistem paketi kurulumu başarısız — sudo gerekli${NC}"
else
    echo -e "  ${YELLOW}⚠️  apt-get bulunamadı — manuel kurulum gerekebilir${NC}"
fi
echo -e "  ${GREEN}✅ Tamamlandı${NC}"

# ── 3. Python paketleri ──────────────────────────────────────
echo -e "${BLUE}[3/6] Python paketleri kuruluyor...${NC}"

# Ana paketler
echo "  Ana paketler kuruluyor..."
pip install -r requirements.txt --quiet 2>/dev/null || pip install -r requirements.txt
echo -e "  ${GREEN}✅ Ana paketler kuruldu${NC}"

# llama-cpp-python (OpenBLAS optimizasyonu ile)
echo "  llama-cpp-python kuruluyor (OpenBLAS ile)..."
if python3 -c "from llama_cpp import Llama; print('OK')" 2>/dev/null; then
    echo -e "  ${GREEN}✅ llama-cpp-python zaten kurulu${NC}"
else
    CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" \
        pip install llama-cpp-python --quiet 2>/dev/null || {
        echo -e "  ${YELLOW}⚠️  OpenBLAS ile kurulum başarısız, basit kurulum deneniyor...${NC}"
        pip install llama-cpp-python --quiet 2>/dev/null || {
            echo -e "  ${RED}❌ llama-cpp-python kurulamadı${NC}"
            echo "  Manuel deneyin: pip install llama-cpp-python"
            exit 1
        }
    }
    echo -e "  ${GREEN}✅ llama-cpp-python kuruldu${NC}"
fi

# ── 4. .env dosyası ─────────────────────────────────────────
echo -e "${BLUE}[4/6] Ortam değişkenleri yapılandırılıyor...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "  ${YELLOW}⚠️  .env dosyası oluşturuldu — lütfen düzenleyin:${NC}"
    echo "     nano .env"
    echo "     (Telegram Bot için: TELEGRAM_TOKEN gerekli)"
else
    echo -e "  ${GREEN}✅ .env zaten mevcut${NC}"
fi

# ── 5. Model indirme ────────────────────────────────────────
echo -e "${BLUE}[5/6] Gemma 4 E4B GGUF modeli kontrol ediliyor...${NC}"
mkdir -p models

if ls models/*.gguf 1> /dev/null 2>&1; then
    MODEL_SIZE=$(du -sh models/*.gguf | head -1 | awk '{print $1}')
    echo -e "  ${GREEN}✅ GGUF model mevcut ($MODEL_SIZE)${NC}"
else
    echo "  📥 Model indiriliyor (~2.5 GB)..."
    echo "  Bu işlem internet hızınıza bağlı olarak birkaç dakika sürebilir."
    python3 scripts/download_model.py || {
        echo -e "  ${RED}❌ Model indirme başarısız${NC}"
        echo "  Manuel: python scripts/download_model.py"
        echo "  Veya: huggingface-cli download unsloth/gemma-4-E4B-it-GGUF gemma-4-e4b-it-Q4_K_M.gguf --local-dir ./models/"
        exit 1
    }
    echo -e "  ${GREEN}✅ Model indirildi${NC}"
fi

# ── 6. Özet ─────────────────────────────────────────────────
echo ""
echo -e "${BLUE}[6/6] Kurulum tamamlandı!${NC}"
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                   Sonraki Adımlar                   ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "1. Telegram bot kullanmak istiyorsanız .env dosyasını düzenleyin:"
echo "   nano .env"
echo "   (TELEGRAM_TOKEN ekleyin — rehber: docs/TELEGRAM_SETUP.md)"
echo ""
echo "2. GemmAid'i başlatın (llama.cpp backend, tek komut):"
echo "   bash deploy/start.sh"
echo ""
echo "   Veya tekil:"
echo "   Terminal 1: python api/api.py           # API (llama.cpp)"
echo "   Terminal 2: python dashboard/dashboard.py"
echo "   Terminal 3: python bot/bot.py            (token gerekli)"
echo ""
echo "3. Sağlık kontrolü:"
echo "   bash deploy/health_check.sh"
echo ""
echo "4. Triaj testi:"
echo "   python scripts/test_triage.py"
echo ""
echo -e "${GREEN}🆘 GemmAid hazır — llama.cpp + Gemma 4 E4B${NC}"
echo ""
