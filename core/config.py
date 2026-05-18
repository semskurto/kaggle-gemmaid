"""GemmAid — Konfigürasyon Yönetimi
Tüm environment değişkenlerini merkezi olarak yönetir.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Proje kökünü bul ve .env yükle
_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT / ".env"

if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)
else:
    # .env yok ise .env.example'ı yükle (varsayılan değerler için)
    _ENV_EXAMPLE = _ROOT / ".env.example"
    if _ENV_EXAMPLE.exists():
        load_dotenv(_ENV_EXAMPLE)

# ── Backend Seçimi ────────────────────────────────────────────
BACKEND: str = os.getenv("GEMMAID_BACKEND", "local").lower()
# Geçerli değerler:
#   local        → llama-cpp-python + GGUF (CPU, VARSAYILAN — lokal deploy)
#   transformers → HuggingFace transformers (GPU/CPU, Kaggle uyumlu)
#   gemini       → Google AI API (Gemma 4 26B bulut)
VALID_BACKENDS = {"local", "transformers", "gemini"}
if BACKEND not in VALID_BACKENDS:
    BACKEND = "local"

# ── Lokal Model (llama.cpp — Birincil Backend) ────────────────
LOCAL_MODEL_PATH: str = os.getenv("LOCAL_MODEL_PATH", str(_ROOT / "models" / "gemma-4-E4B-it-Q4_K_M.gguf"))
LOCAL_N_THREADS: int  = int(os.getenv("LOCAL_N_THREADS", "4"))
LOCAL_N_CTX: int      = int(os.getenv("LOCAL_N_CTX", "2048"))

# ── Google AI API (Gemma 4 bulut erişimi) ────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str   = os.getenv("GEMINI_MODEL", "gemma-4-26b-a4b-it")

# ── Telegram ─────────────────────────────────────────────────
TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")

# ── Sunucu ───────────────────────────────────────────────────
API_HOST: str  = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int  = int(os.getenv("API_PORT", "8000"))
API_BASE_URL: str = f"http://localhost:{API_PORT}"

DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "7860"))

# ── Database ─────────────────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", str(_ROOT / "gemmaid.db"))

# ── Triaj Sistem Prompt ──────────────────────────────────────
# Varsayılan (fallback için korunuyor)
TRIAGE_SYSTEM_PROMPT = """Sen GemmAid acil triaj asistanısın.
Kriz mesajlarını analiz ederek SADECE geçerli bir JSON nesnesi döndürürsün.
Başka hiçbir açıklama, markdown veya metin ekleme.

JSON şeması (tüm alanlar zorunlu):
{
  "olay_tipi": "enkaz_alti|tibbi_acil|tahliye|kaynak_ihtiyaci|belirsiz",
  "aciliyet_skoru": 1,
  "konum_metni": "tespit edilen konum veya 'Belirtilmedi'",
  "etkilenen_kisi_sayisi": 1,
  "semptomlar": ["semptom1", "semptom2"],
  "gerekli_ekip": ["tibbi|arama_kurtarma|tahliye|lojistik"],
  "kaynak_dil": "tr|ar|en|fr|de|es|diğer",
  "koordinator_notu": "Türkçe kısa değerlendirme notu",
  "eylem_plani": "Koordinatör için vakaya özel, adım adım operasyonel eylem planı (Türkçe)",
  "vatandasa_yanit": "Kendi dilinde kısa, empati kuran, tıbbi/tahliye tavsiyesi İÇERMEYEN 'mesajınız alındı, güvende kalın' mesajı"
}

Kurallar:
- aciliyet_skoru: 1=kritik (hayat tehlikesi), 5=düşük öncelik
- Mesaj hangi dilde olursa olsun, koordinator_notu TÜRKÇE olacak
- Vatandaşa yanıt (vatandasa_yanit) mesajın yazıldığı dilde (kaynak_dil) olacak
- Vatandaşa kesinlikle spesifik bir yönlendirme yapma, sadece güvende kalmasını söyle
- Konum metni varsa çıkar, yoksa 'Belirtilmedi' yaz
- etkilenen_kisi_sayisi: tahmin edemiyorsan 1 yaz"""

def get_triage_system_prompt(target_lang="en"):
    """
    Hedef dile (dashboard diline) göre yapılandırılmış sistem prompt'unu döndürür.
    target_lang parametresi koordinator_notu alanının dilini etkiler.
    """
    lang_name = "ENGLISH" if target_lang.lower() == "en" else "TÜRKÇE"
    
    return f"""You are the GemmAid emergency triage assistant.
Analyze crisis messages and return ONLY a valid JSON object.
Do not add any explanations, markdown, or text.

JSON schema (all fields required):
{{
  "olay_tipi": "enkaz_alti|tibbi_acil|tahliye|kaynak_ihtiyaci|belirsiz",
  "aciliyet_skoru": 1,
  "konum_metni": "detected location or 'Not specified'",
  "etkilenen_kisi_sayisi": 1,
  "gonderen_kisi": "detected name or 'Bilinmiyor'",
  "iletisim_bilgisi": "detected phone/contact or 'Bilinmiyor'",
  "semptomlar": ["symptom1", "symptom2"],
  "gerekli_ekip": ["tibbi|arama_kurtarma|tahliye|lojistik"],
  "kaynak_dil": "tr|ar|en|fr|de|es|other",
  "eksik_bilgiler": ["location missing", "contact missing"],
  "koordinator_notu": "A short and precise coordinator evaluation note in {lang_name}",
  "eylem_plani": "A specific, step-by-step operational action plan for the rescue teams/coordinator in {lang_name}, based on the crisis context and risk level. Do NOT use generic advice, make it specific to the incident (e.g., 'dispatch hazmat' for chemicals, 'send heavy lifters' for rubble).",
  "vatandasa_yanit": "A very calming, empathetic message to the citizen in their source language (kaynak_dil). Gently ask for any missing key info. Do NOT cause panic."
}}

Rules:
- aciliyet_skoru (Urgency score): 1=critical (life-threatening), 5=low priority
- No matter what language the message is written in, koordinator_notu MUST be written in {lang_name}.
- vatandasa_yanit MUST be in the source language of the message.
- Provide psychological first-aid in vatandasa_yanit. Calm the person down, validate their feelings.
- IMPORTANT for vatandasa_yanit: Do NOT say alarming or overly sympathetic things like 'You are in a very difficult situation' or make false promises like 'Help is on the way immediately' if unverified. Instead, say 'We hear you, your message has been received by our center. Please stay as safe as possible.'
- If essential information (like exact location or contact number) is not provided, ask for it kindly in vatandasa_yanit.
- List those missing information points in the eksik_bilgiler array.
- Do NOT direct the citizen to specific actions, just tell them to stay safe.
- Extract location if available; if not, output 'Not specified' or 'Belirtilmedi'.
- etkilenen_kisi_sayisi: If you cannot guess, set it to 1.
"""


def print_config():
    """Mevcut konfigürasyonu yazdır (debug için)."""
    print(f"[Config] Backend: {BACKEND}")
    print(f"[Config] API: {API_HOST}:{API_PORT}")
    print(f"[Config] Dashboard Port: {DASHBOARD_PORT}")
    print(f"[Config] DB: {DB_PATH}")
    if BACKEND == "local":
        print(f"[Config] Model Path: {LOCAL_MODEL_PATH}")
        print(f"[Config] Threads: {LOCAL_N_THREADS}, Context: {LOCAL_N_CTX}")
    elif BACKEND == "transformers":
        print(f"[Config] HF pipeline: any-to-any")
    elif BACKEND == "gemini":
        masked = GEMINI_API_KEY[:8] + "..." if GEMINI_API_KEY else "(YOK)"
        print(f"[Config] Gemini API Key: {masked}")
