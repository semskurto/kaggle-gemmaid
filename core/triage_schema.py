"""GemmAid — Triaj JSON Şeması & Doğrulama
Brif'teki function calling şemasını Pydantic modele çevirir.
"""
import json
import re
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


# ── Enum Değerleri ───────────────────────────────────────────
OLAY_TIPLERI = frozenset([
    "enkaz_alti", "tibbi_acil", "tahliye", "kaynak_ihtiyaci", "belirsiz"
])

EKIP_TIPLERI = frozenset([
    "tibbi", "arama_kurtarma", "tahliye", "lojistik"
])


# ── Pydantic Modeli ──────────────────────────────────────────
class TriageResult(BaseModel):
    """Gemma 4'ten gelen yapılandırılmış triaj verisi."""
    olay_tipi: str = Field(default="belirsiz", description="Olay kategorisi")
    aciliyet_skoru: int = Field(default=3, ge=1, le=5, description="1=kritik, 5=düşük")
    konum_metni: str = Field(default="Belirtilmedi")
    etkilenen_kisi_sayisi: int = Field(default=1, ge=1)
    gonderen_kisi: str = Field(default="Bilinmiyor", description="Mesajı gönderenin adı/kimliği")
    iletisim_bilgisi: str = Field(default="Bilinmiyor", description="Telefon numarası veya iletişim kanalı")
    semptomlar: List[str] = Field(default_factory=list)
    gerekli_ekip: List[str] = Field(default_factory=list)
    kaynak_dil: str = Field(default="tr")
    eksik_bilgiler: List[str] = Field(default_factory=list, description="Konum, kişi sayısı, iletişim gibi eksik sistemik veriler")
    koordinator_notu: str = Field(default="")
    eylem_plani: str = Field(default="")
    vatandasa_yanit: str = Field(default="Mesajınız merkeze iletilmiştir. Lütfen güvenli bir yerde kalın.", description="Vatandaşa kendi dilinde verilecek psikolojik destek ve bilgi toplama mesajı.")

    @field_validator("olay_tipi")
    @classmethod
    def validate_olay(cls, v: str) -> str:
        return v if v in OLAY_TIPLERI else "belirsiz"

    @field_validator("gerekli_ekip", mode="before")
    @classmethod
    def validate_ekip(cls, v):
        if isinstance(v, list):
            return [e for e in v if e in EKIP_TIPLERI]
        return []

    @field_validator("aciliyet_skoru", mode="before")
    @classmethod
    def validate_aciliyet(cls, v):
        try:
            score = int(v)
            return max(1, min(5, score))
        except (TypeError, ValueError):
            return 3


# ── JSON Çıktı Ayrıştırıcı ──────────────────────────────────
def parse_triage_json(text: str) -> dict:
    """
    LLM'den gelen ham metni TriageResult'e dönüştürür.
    Markdown bloklarını, trailing metin vb. temizler.
    """
    if not text:
        return _error_result("Boş yanıt")

    # Markdown code block temizle
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    # JSON nesnesini çıkar
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start == -1 or end <= start:
        return _error_result(f"JSON bulunamadı: {text[:100]}")

    json_str = text[start:end]
    try:
        raw = json.loads(json_str)
        # Pydantic ile doğrula ve normalize et
        result = TriageResult(**raw)
        return result.model_dump()
    except json.JSONDecodeError as e:
        return _error_result(f"JSON parse hatası: {e} | {json_str[:100]}")
    except Exception as e:
        # Kısmi verilerle devam et
        try:
            raw_dict = json.loads(json_str)
            return {**_error_result(str(e)), **raw_dict}
        except Exception:
            return _error_result(str(e))


def _error_result(reason: str) -> dict:
    """Hata durumunda varsayılan triaj sonucu."""
    return {
        "olay_tipi": "belirsiz",
        "aciliyet_skoru": 3,
        "konum_metni": "Belirtilmedi",
        "etkilenen_kisi_sayisi": 1,
        "gonderen_kisi": "Bilinmiyor",
        "iletisim_bilgisi": "Bilinmiyor",
        "semptomlar": [],
        "gerekli_ekip": [],
        "kaynak_dil": "?",
        "eksik_bilgiler": [],
        "koordinator_notu": f"Otomatik triaj başarısız: {reason}",
        "eylem_plani": "Manuel inceleme gereklidir.",
        "vatandasa_yanit": "Mesajınız alındı. Lütfen güvende kalın.",
        "_parse_error": True,
    }


# ── Function Calling Şeması (Gemini için) ───────────────────
TRIAGE_FUNCTION_SCHEMA = {
    "name": "extract_triage_data",
    "description": "Kriz mesajından yapılandırılmış triaj verisi çıkar",
    "parameters": {
        "type": "object",
        "properties": {
            "olay_tipi": {
                "type": "string",
                "enum": list(OLAY_TIPLERI),
            },
            "aciliyet_skoru": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5,
                "description": "1=kritik, 5=düşük öncelik",
            },
            "konum_metni": {"type": "string"},
            "etkilenen_kisi_sayisi": {"type": "integer"},
            "gonderen_kisi": {"type": "string"},
            "iletisim_bilgisi": {"type": "string"},
            "semptomlar": {"type": "array", "items": {"type": "string"}},
            "eksik_bilgiler": {"type": "array", "items": {"type": "string"}},
            "gerekli_ekip": {
                "type": "array",
                "items": {"enum": list(EKIP_TIPLERI)},
            },
            "kaynak_dil": {"type": "string"},
            "koordinator_notu": {"type": "string"},
            "eylem_plani": {"type": "string", "description": "Vakaya özel, koordinatörün atması gereken adımları listeleyen operasyonel eylem planı (Türkçe veya İngilizce)."},
            "vatandasa_yanit": {"type": "string", "description": "Vatandaşa kendi dilinde iletilecek, empati kuran ancak teknik tıbbi veya tahliye tavsiyesi İÇERMEYEN güven verici kısa mesaj."},
        },
        "required": ["olay_tipi", "aciliyet_skoru", "gerekli_ekip", "vatandasa_yanit"],
    },
}
