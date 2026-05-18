"""GemmAid — Transformers Backend Wrapper (Opsiyonel)

Bu dosya optional/kaggle/ altındaki GemmAidTriager'a yönlendirme yapar.
GEMMAID_BACKEND=transformers kullanmak için:
  pip install torch transformers accelerate

Detaylar: optional/kaggle/README.md
"""
import logging
import sys
import threading
from pathlib import Path

log = logging.getLogger(__name__)

_optional_kaggle = str(Path(__file__).resolve().parent.parent / "optional" / "kaggle")

_triager = None
_triager_lock = threading.Lock()


def _init_triager():
    """GemmAidTriager'ı optional/kaggle'dan yükle."""
    sys.path.insert(0, _optional_kaggle)
    try:
        from gemma4_inference import GemmAidTriager
    except ImportError:
        raise ImportError(
            "Transformers backend için gerekli paketler kurulu değil.\n"
            "Kurulum: pip install torch transformers accelerate\n"
            "Detaylar: optional/kaggle/README.md"
        )
    return GemmAidTriager()


def call_transformers(message: str, target_lang: str = "en") -> dict:
    """Transformers backend ile triaj (opsiyonel — Kaggle/GPU)."""
    global _triager
    if _triager is None:
        with _triager_lock:
            if _triager is None:
                log.info("[Transformers] Gemma 4 yükleniyor...")
                _triager = _init_triager()
                log.info("[Transformers] ✅ Gemma 4 hazır!")

    result = _triager.triage(message, target_lang=target_lang)
    result.pop("_raw", None)
    return result


def is_model_loaded() -> bool:
    return _triager is not None


def preload_model():
    try:
        call_transformers("test")
    except Exception as e:
        log.warning(f"[Transformers] Ön yükleme başarısız: {e}")
