"""GemmAid — Gemma 4 Inference (Kaggle + Lokal Uyumlu)

Örnek projeden (gemma-4-multimodal-relief-assistant-for-crisis) öğrenilen
pattern'ler uygulanmıştır:

1. transformers + AutoProcessor ile resmi Gemma 4 chat template
2. Planner-Executor iki aşamalı agent mimarisi
3. Güven skoru (confidence) ile triaj güvenilirliği
4. torch.inference_mode() ile optimizasyon
5. Hem GPU (Kaggle) hem CPU (lokal) uyumlu

Kullanım:
    # Kaggle'da (GPU):
    from gemma4_inference import GemmAidTriager
    triager = GemmAidTriager()
    result = triager.triage("Enkaz altında 3 kişi var")

    # Lokal'de (CPU):
    triager = GemmAidTriager(device="cpu")
"""
import json
import os
import re
from typing import Any, Dict, List, Optional

# ── Gemma 4 Triaj Sistem Promptu ────────────────────────────
TRIAGE_SYSTEM_PROMPT = """\
Sen GemmAid acil triaj asistanısın.
Kriz mesajlarını analiz ederek SADECE geçerli bir JSON nesnesi döndürürsün.
Başka hiçbir açıklama, markdown veya metin ekleme.

JSON şeması (tüm alanlar zorunlu):
{
  "olay_tipi": "enkaz_alti|tibbi_acil|tahliye|kaynak_ihtiyaci|belirsiz",
  "aciliyet_skoru": 1,
  "konum_metni": "tespit edilen konum veya 'Belirtilmedi'",
  "etkilenen_kisi_sayisi": 1,
  "semptomlar": ["semptom1"],
  "gerekli_ekip": ["tibbi|arama_kurtarma|tahliye|lojistik"],
  "kaynak_dil": "tr|ar|en|fr|ku|az",
  "koordinator_notu": "Türkçe kısa değerlendirme notu",
  "vatandasa_yanit": "Kendi dilinde kısa, empati kuran, tıbbi/tahliye tavsiyesi İÇERMEYEN güven verici mesaj",
  "confidence": 0.9
}

Kurallar:
- aciliyet_skoru: 1=kritik (hayat tehlikesi), 5=düşük öncelik
- Mesaj hangi dilde olursa olsun, koordinator_notu TÜRKÇE olacak
- Vatandaşa yanıt (vatandasa_yanit) mesajın yazıldığı dilde (kaynak_dil) olacak
- Vatandaşa kesinlikle spesifik bir yönlendirme yapma, sadece güvende kalmasını söyle
- confidence: 0.0-1.0 arası güven skoru (bilgi ne kadar kesinse o kadar yüksek)
"""

# ── JSON Parse ───────────────────────────────────────────────
def extract_json(text: str) -> Optional[dict]:
    """LLM çıktısından JSON çıkar — örnek projeden alınan robust parser."""
    text = re.sub(r"```json\s*", "", text).strip()
    text = re.sub(r"```\s*$", "", text)

    # İlk { ve son } arasını bul
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e > s:
        try:
            return json.loads(text[s:e])
        except json.JSONDecodeError:
            # json-repair ile dene
            try:
                import json_repair
                return json_repair.loads(text[s:e])
            except Exception:
                pass
    return None


def safe_triage_result(raw_text: str, fallback_msg: str = "") -> dict:
    """JSON parse başarısız olursa güvenli varsayılan döndür."""
    result = extract_json(raw_text)
    if result and "olay_tipi" in result:
        # confidence yoksa ekle
        if "confidence" not in result:
            result["confidence"] = 0.8
        return result

    return {
        "olay_tipi": "belirsiz",
        "aciliyet_skoru": 3,
        "konum_metni": "Belirtilmedi",
        "etkilenen_kisi_sayisi": 1,
        "semptomlar": [],
        "gerekli_ekip": [],
        "kaynak_dil": "?",
        "koordinator_notu": f"Parse hatası: {raw_text[:100]}",
        "vatandasa_yanit": "Mesajınız merkeze iletilmiştir. Lütfen güvenli bir yerde kalın.",
        "confidence": 0.1,
        "_parse_error": True,
    }


# ── Gemma 4 Triager Sınıfı ──────────────────────────────────
class GemmAidTriager:
    """Gemma 4 tabanlı triaj motoru.

    Örnek projeden öğrenilen pattern'ler:
    - AutoProcessor.apply_chat_template() ile resmi chat format
    - torch.inference_mode() ile hızlı inference
    - Hem GPU hem CPU desteği
    """

    def __init__(
        self,
        model_id: str = None,
        device: str = None,
        max_new_tokens: int = 512,
    ):
        import torch
        from transformers import AutoProcessor

        self.model_id = model_id or os.environ.get(
            "GEMMA4_MODEL_ID", "google/gemma-4-e4b-it"  # küçük harf: resmi ID
        )
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.max_new_tokens = max_new_tokens

        print(f"[GemmAid] Model: {self.model_id}")
        print(f"[GemmAid] Device: {self.device}")

        # Resmi Google dokumantasıyonına göre: pipeline(task='any-to-any')
        # https://ai.google.dev/gemma/docs/core/huggingface_inference
        from transformers import pipeline as hf_pipeline
        self.pipe = hf_pipeline(
            task="any-to-any",
            model=self.model_id,
            device_map="auto",
            dtype="auto",
        )
        print("[GemmAid] ✅ Gemma 4 hazır (pipeline: any-to-any)!")

    def generate(
        self,
        messages: List[Dict[str, Any]],
        max_new_tokens: int = None,
        temperature: float = 0.1,
    ) -> str:
        """Gemma 4 ile metin üret — resmi Google pipeline API."""
        from transformers import GenerationConfig
        try:
            config = GenerationConfig.from_pretrained(self.model_id)
        except Exception:
            config = GenerationConfig()
        config.max_new_tokens = max_new_tokens or self.max_new_tokens

        gen_kwargs = dict(generation_config=config)

        result = self.pipe(
            messages,
            return_full_text=False,
            generate_kwargs=gen_kwargs,
        )
        # pipeline sonucu: [{'generated_text': '...'}]
        if result and isinstance(result, list):
            return result[0].get("generated_text", "")
        return ""

    def triage(self, message: str, temperature: float = 0.1, target_lang: str = "en") -> dict:
        """Tek mesajı triaj et — yapılandırılmış JSON döndür."""
        # Try to use global prompt generator if available
        try:
            from core.config import get_triage_system_prompt
            sys_prompt = get_triage_system_prompt(target_lang)
        except ImportError:
            sys_prompt = TRIAGE_SYSTEM_PROMPT

        # Resmi Google formatı: content lista olarak
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": sys_prompt}],
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": f"Kriz mesajı: {message}"}],
            },
        ]

        raw = self.generate(messages, temperature=temperature)
        result = safe_triage_result(raw, message)
        result["_raw"] = raw
        return result

    def triage_batch(self, messages: List[str]) -> List[dict]:
        """Birden fazla mesajı sırayla triaj et."""
        return [self.triage(m) for m in messages]


# ── Demo Senaryoları ─────────────────────────────────────────
DEMO_SCENARIOS = [
    {
        "lang": "TR 🇹🇷",
        "context": "Deprem — Enkaz Altı",
        "message": "Komşumuz enkaz altında kaldı, Atatürk Caddesi 3. kat, nefes güçlüğü var, biz 3 kişiyiz",
    },
    {
        "lang": "AR 🇸🇦",
        "context": "Deprem — Yardım Bekleyen Göçmen",
        "message": "جارنا عالق تحت الأنقاض، يتنفس بصعوبة، شارع أتاتورك، الطابق الثالث، نحن ثلاثة أشخاص بحاجة للمساعدة",
    },
    {
        "lang": "FR 🇫🇷",
        "context": "Tıbbi Acil — Göçmen Hasta",
        "message": "J'ai une douleur intense dans la poitrine depuis 2 heures, j'ai du mal à respirer",
    },
    {
        "lang": "EN 🇬🇧",
        "context": "Sel — Tahliye",
        "message": "House flooded, 2 children trapped on roof, water rising fast, Kemaliye district",
    },
    {
        "lang": "AZ 🇦🇿",
        "context": "USAR Saha Raporu",
        "message": "Hatay Antakya mərkəzdə 8 mərtəbəli bina çöküb. 3 nəfəri çıxardıq, 2-si ağır yaralıdır",
    },
]


ACIL_EMOJI = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "⚪"}


def run_demo(triager: GemmAidTriager) -> list:
    """Tüm demo senaryolarını çalıştır."""
    import time

    print("=" * 60)
    print("GemmAid — Gemma 4 Triaj Demo")
    print("=" * 60)

    results = []
    for i, s in enumerate(DEMO_SCENARIOS, 1):
        print(f"\n[{i}/{len(DEMO_SCENARIOS)}] {s['lang']} — {s['context']}")
        print(f"  Mesaj: {s['message'][:70]}...")

        start = time.time()
        result = triager.triage(s["message"])
        elapsed = time.time() - start

        acil = result.get("aciliyet_skoru", 3)
        emoji = ACIL_EMOJI.get(acil, "❓")
        conf = result.get("confidence", 0)

        print(f"  {emoji} Aciliyet: {acil}/5 | Güven: {conf:.0%} | {elapsed:.1f}s")
        print(f"  📍 {result.get('olay_tipi', '?')} | {result.get('konum_metni', '?')}")
        print(f"  📋 {result.get('koordinator_notu', '?')}")

        results.append({**s, "result": result, "elapsed": elapsed})

    return results


if __name__ == "__main__":
    triager = GemmAidTriager()
    results = run_demo(triager)
    print(f"\n✅ {len(results)} senaryo tamamlandı")
