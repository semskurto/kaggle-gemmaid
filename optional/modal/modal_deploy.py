"""GemmAid — Modal Serverless Deployment

Modal üzerinde Gemma 4 E4B GGUF modelini serverless GPU ile çalıştırır.
Scale-to-zero: sadece istek geldiğinde GPU başlar, boşta maliyet yok.

Kurulum:
    pip install modal
    modal setup

Deploy:
    modal deploy optional/modal/modal_deploy.py

Test:
    curl -X POST https://YOUR_URL/triage \\
      -H "Content-Type: application/json" \\
      -d '{"message": "Komşumuz enkaz altında"}'
"""
import modal
import json
import re
from pathlib import Path

# ── Modal App ────────────────────────────────────────────────
app = modal.App("gemmaid-triage")

# Model Volume — GGUF dosyasını kalıcı olarak saklar
model_volume = modal.Volume.from_name("gemmaid-models", create_if_missing=True)
MODEL_DIR = "/models"
MODEL_FILENAME = "gemma-4-e4b-it-Q4_K_M.gguf"
MODEL_PATH = f"{MODEL_DIR}/{MODEL_FILENAME}"

# Container image
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "llama-cpp-python>=0.2.90",
        "huggingface-hub>=0.23.0",
        "fastapi>=0.115.0",
    )
)

# ── Triaj Sistem Promptu ─────────────────────────────────────
TRIAGE_SYSTEM_PROMPT = """Sen GemmAid acil triaj asistanısın.
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
  "kaynak_dil": "tr|ar|en|fr|de|es|diğer",
  "koordinator_notu": "Türkçe kısa değerlendirme notu",
  "vatandasa_yanit": "Kendi dilinde kısa, empati kuran güven verici mesaj"
}

Kurallar:
- aciliyet_skoru: 1=kritik (hayat tehlikesi), 5=düşük öncelik
- koordinator_notu TÜRKÇE olacak
- vatandasa_yanit mesajın yazıldığı dilde olacak"""


def parse_json(text: str) -> dict:
    """LLM çıktısından JSON çıkar."""
    text = re.sub(r"```json\s*", "", text).strip()
    text = re.sub(r"```\s*", "", text)
    s = text.find("{")
    e = text.rfind("}") + 1
    if s != -1 and e > s:
        try:
            return json.loads(text[s:e])
        except json.JSONDecodeError:
            pass
    return {
        "olay_tipi": "belirsiz",
        "aciliyet_skoru": 3,
        "koordinator_notu": f"Parse hatası: {text[:80]}",
    }


@app.cls(
    image=image,
    gpu="T4",
    volumes={MODEL_DIR: model_volume},
    timeout=300,
    container_idle_timeout=120,
)
class GemmAidModel:
    """Gemma 4 E4B GGUF — Modal Serverless."""

    @modal.enter()
    def load_model(self):
        """Container başlangıcında model yükle."""
        from llama_cpp import Llama

        # Model yoksa indir
        if not Path(MODEL_PATH).exists():
            print(f"📥 Model indiriliyor: {MODEL_FILENAME}")
            from huggingface_hub import hf_hub_download
            hf_hub_download(
                repo_id="unsloth/gemma-4-E4B-it-GGUF",
                filename=MODEL_FILENAME,
                local_dir=MODEL_DIR,
                local_dir_use_symlinks=False,
            )
            model_volume.commit()
            print("✅ Model indirildi ve volume'a kaydedildi")

        print("🔄 Model yükleniyor...")
        self.model = Llama(
            model_path=MODEL_PATH,
            n_ctx=2048,
            n_threads=4,
            n_gpu_layers=99,  # Modal GPU → tüm katmanlar GPU'da
            verbose=False,
        )
        print("✅ Model hazır!")

    @modal.method()
    def triage(self, message: str) -> dict:
        """Tek mesajı triaj et."""
        output = self.model.create_chat_completion(
            messages=[
                {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                {"role": "user", "content": f"Kriz mesajı: {message}"},
            ],
            max_tokens=512,
            temperature=0.1,
            top_p=0.95,
        )
        raw = output["choices"][0]["message"]["content"]
        result = parse_json(raw)
        result["inference_location"] = "cloud_modal"
        return result


# ── Web Endpoint ─────────────────────────────────────────────
@app.function(image=image)
@modal.web_endpoint(method="POST")
def triage_endpoint(body: dict):
    """HTTP POST /triage — Modal web endpoint."""
    message = body.get("message", "")
    if not message.strip():
        return {"error": "Mesaj boş olamaz"}

    model = GemmAidModel()
    result = model.triage.remote(message)
    return result


# ── CLI Test ─────────────────────────────────────────────────
@app.local_entrypoint()
def main():
    """Lokal test: modal run optional/modal/modal_deploy.py"""
    model = GemmAidModel()
    test_msg = "Komşumuz enkaz altında kaldı, Atatürk Caddesi 3. kat, nefes güçlüğü var"
    print(f"\nTest mesajı: {test_msg}")
    result = model.triage.remote(test_msg)
    print(json.dumps(result, ensure_ascii=False, indent=2))
