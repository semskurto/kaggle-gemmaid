"""GemmAid — Lokal LLM Inference
llama-cpp-python ile Gemma 4 E4B GGUF'u CPU'da çalıştırır.
Thread-safe singleton pattern ile tek model instance kullanır.
"""
import logging
import sys
import os
import threading
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.config import LOCAL_MODEL_PATH, LOCAL_N_THREADS, LOCAL_N_CTX, get_triage_system_prompt
from core.triage_schema import parse_triage_json

log = logging.getLogger(__name__)

# ── Singleton ─────────────────────────────────────────────────
_model = None
_model_lock = threading.Lock()


def _get_model():
    """Thread-safe model yükleme (ilk çağrıda yükler)."""
    global _model
    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:  # double-check
            return _model

        model_path = Path(LOCAL_MODEL_PATH)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model bulunamadı: {model_path}\n"
                f"İndirmek için: python local_llm/model_manager.py"
            )

        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python kurulu değil.\n"
                "Ubuntu CPU için:\n"
                "  CMAKE_ARGS='-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS' "
                "pip install llama-cpp-python\n"
                "Veya basit kurulum:\n"
                "  pip install llama-cpp-python"
            )

        log.info(f"[LocalLLM] Model yükleniyor: {model_path}")
        log.info(f"[LocalLLM] Threads: {LOCAL_N_THREADS}, Context: {LOCAL_N_CTX}")

        _model = Llama(
            model_path=str(model_path),
            n_ctx=LOCAL_N_CTX,
            n_threads=LOCAL_N_THREADS,
            n_gpu_layers=0,        # CPU only
            verbose=False,
            logits_all=False,
        )

        log.info("[LocalLLM] Model hazır!")
        return _model


def call_local(message: str, target_lang: str = "en") -> dict:
    """
    Lokal Gemma 4 E4B ile triaj çalıştır.

    Args:
        message: Ham kriz mesajı (herhangi bir dilde)
        target_lang: Çıktı dili (örn. 'en' veya 'tr')

    Returns:
        Yapılandırılmış triaj sözlüğü
    """
    lm = _get_model()

    # Resmi Gemma 4 model kartı (ai.google.dev/gemma/docs/core/model_card_4):
    # "Transformers ve llama.cpp gibi birçok kitaplığın, sohbet şablonunun
    #  karmaşıklıklarını sizin için ele aldığını unutmayın."
    # → create_chat_completion, GGUF içindeki resmi chat_template'i otomatik uygular.
    # Standart roller: system / user / assistant.
    log.info(f"[LocalLLM] Triaj başlatıldı: {message[:60]}...")

    try:
        output = lm.create_chat_completion(
            messages=[
                {"role": "system", "content": get_triage_system_prompt(target_lang)},
                {"role": "user",   "content": f"Kriz mesajı: {message}"},
            ],
            max_tokens=512,
            temperature=0.1,        # JSON için kasıtlı düşük (model kartı: 1.0 yaratıcı kullanım için)
            top_p=0.95,
            repeat_penalty=1.1,
        )
        raw_text = output["choices"][0]["message"]["content"]
        log.debug(f"[LocalLLM] Ham çıktı: {raw_text[:200]}")
        return parse_triage_json(raw_text)

    except Exception as e:
        log.error(f"[LocalLLM] Inference hatası: {e}")
        return {
            "olay_tipi": "belirsiz",
            "aciliyet_skoru": 3,
            "konum_metni": "Belirtilmedi",
            "etkilenen_kisi_sayisi": 1,
            "semptomlar": [],
            "gerekli_ekip": [],
            "kaynak_dil": "?",
            "koordinator_notu": f"Lokal model hatası: {e}",
            "vatandasa_yanit": "Mesajınız merkeze iletilmiştir. Lütfen güvenli bir yerde kalın.",
            "_parse_error": True,
        }


def is_model_loaded() -> bool:
    """Model hafızaya yüklenmiş mi?"""
    return _model is not None


def get_model_status() -> dict:
    """Model durumu hakkında bilgi döndür."""
    model_path = Path(LOCAL_MODEL_PATH)
    return {
        "loaded": is_model_loaded(),
        "path": str(model_path),
        "exists": model_path.exists(),
        "size_gb": round(model_path.stat().st_size / 1e9, 2) if model_path.exists() else 0,
        "threads": LOCAL_N_THREADS,
        "n_ctx": LOCAL_N_CTX,
    }


def preload_model():
    """API başlangıcında modeli önceden yükle (ilk istek gecikmesini önler)."""
    try:
        _get_model()
        log.info("[LocalLLM] Model başarıyla önceden yüklendi.")
    except Exception as e:
        log.warning(f"[LocalLLM] Ön yükleme başarısız (ilk istekte yüklenecek): {e}")


# ── Komut satırı testi ───────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    TEST_MSG = "Komşumuz enkaz altında kaldı, Atatürk Caddesi 3. kat, nefes güçlüğü var"
    print("\n" + "=" * 55)
    print("GemmAid — Lokal LLM Test")
    print("=" * 55)
    print(f"Mesaj: {TEST_MSG}\n")

    result = call_local(TEST_MSG)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
