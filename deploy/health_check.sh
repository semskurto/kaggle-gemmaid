#!/bin/bash
# GemmAid — Sistem Sağlık Kontrolü
# Kullanım: bash deploy/health_check.sh

PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║           GemmAid — Sağlık Kontrolü                 ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

PASS=0
FAIL=0

# 1. Python
echo -n "  [1] Python 3.10+    : "
if python3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
    VER=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✅ $VER${NC}"
    ((PASS++))
else
    echo -e "${RED}❌ Kurulu değil veya eski sürüm${NC}"
    ((FAIL++))
fi

# 2. llama-cpp-python
echo -n "  [2] llama-cpp-python: "
if python3 -c "from llama_cpp import Llama; print('OK')" 2>/dev/null; then
    echo -e "${GREEN}✅ Kurulu${NC}"
    ((PASS++))
else
    echo -e "${RED}❌ Kurulu değil — pip install llama-cpp-python${NC}"
    ((FAIL++))
fi

# 3. GGUF model
echo -n "  [3] GGUF Model      : "
# .env'den model yolunu oku
if [ -f ".env" ]; then
    MODEL_PATH=$(grep -E "^LOCAL_MODEL_PATH=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
fi
MODEL_PATH="${MODEL_PATH:-./models/gemma-4-E4B-it-Q4_K_M.gguf}"

if [ -f "$MODEL_PATH" ]; then
    SIZE=$(du -sh "$MODEL_PATH" | awk '{print $1}')
    echo -e "${GREEN}✅ Mevcut ($SIZE)${NC}"
    ((PASS++))
else
    echo -e "${RED}❌ Bulunamadı: $MODEL_PATH${NC}"
    echo "                        → python scripts/download_model.py"
    ((FAIL++))
fi

# 4. RAM
echo -n "  [4] Boş RAM         : "
FREE_RAM=$(free -m | awk '/^Mem:/{print $7}')
if [ "$FREE_RAM" -gt 3000 ]; then
    echo -e "${GREEN}✅ ${FREE_RAM} MB (yeterli)${NC}"
    ((PASS++))
elif [ "$FREE_RAM" -gt 2000 ]; then
    echo -e "${YELLOW}⚠️  ${FREE_RAM} MB (sınırda — diğer uygulamaları kapatın)${NC}"
    ((PASS++))
else
    echo -e "${RED}❌ ${FREE_RAM} MB (yetersiz — minimum 3 GB gerekli)${NC}"
    ((FAIL++))
fi

# 5. API
echo -n "  [5] API :8000       : "
API_PORT=$(grep -E "^API_PORT=" .env 2>/dev/null | cut -d'=' -f2 || echo "8000")
API_PORT="${API_PORT:-8000}"
if curl -s "http://localhost:${API_PORT}/health" > /dev/null 2>&1; then
    BACKEND=$(curl -s "http://localhost:${API_PORT}/health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('backend','?'))" 2>/dev/null)
    echo -e "${GREEN}✅ Çevrimiçi (backend=${BACKEND})${NC}"
    ((PASS++))
else
    echo -e "${YELLOW}⚠️  Çevrimdışı — bash deploy/start.sh ile başlatın${NC}"
    ((FAIL++))
fi

# 6. Dashboard
echo -n "  [6] Dashboard :7860 : "
DASH_PORT=$(grep -E "^DASHBOARD_PORT=" .env 2>/dev/null | cut -d'=' -f2 || echo "7860")
DASH_PORT="${DASH_PORT:-7860}"
if curl -s "http://localhost:${DASH_PORT}" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Çevrimiçi${NC}"
    ((PASS++))
else
    echo -e "${YELLOW}⚠️  Çevrimdışı${NC}"
    ((FAIL++))
fi

# 7. .env dosyası
echo -n "  [7] .env dosyası    : "
if [ -f ".env" ]; then
    echo -e "${GREEN}✅ Mevcut${NC}"
    ((PASS++))
else
    echo -e "${RED}❌ Bulunamadı — cp .env.example .env${NC}"
    ((FAIL++))
fi

# 8. Telegram token
echo -n "  [8] Telegram Token  : "
if [ -f ".env" ]; then
    TG_TOKEN=$(grep -E "^TELEGRAM_TOKEN=" .env | cut -d'=' -f2)
    if [ -n "$TG_TOKEN" ] && [ "$TG_TOKEN" != "BURAYA_TOKEN_YAZ" ]; then
        echo -e "${GREEN}✅ Ayarlanmış${NC}"
        ((PASS++))
    else
        echo -e "${YELLOW}⚠️  Ayarlanmamış (bot opsiyonel)${NC}"
        ((PASS++))
    fi
else
    echo -e "${YELLOW}⚠️  .env yok${NC}"
    ((FAIL++))
fi

# Özet
echo ""
echo "──────────────────────────────────────────────────────"
TOTAL=$((PASS + FAIL))
if [ "$FAIL" -eq 0 ]; then
    echo -e "${GREEN}✅ Tüm kontroller başarılı ($PASS/$TOTAL)${NC}"
else
    echo -e "${YELLOW}⚠️  $PASS/$TOTAL başarılı, $FAIL sorun var${NC}"
fi
echo ""
