"""GemmAid — Gemma 4 Transformers Backend (GPU/CPU)

llama-cpp-python'a alternatif olarak HuggingFace transformers ile
Gemma 4 çalıştırır. Kaggle notebook ile aynı kodu paylaşır.

Kaggle'da GPU varsa otomatik CUDA kullanır.
Lokal'de CPU'da çalışır (daha yavaş ama uyumlu).

Kullanım:
    GEMMAID_BACKEND=transformers python api/api.py
"""
import logging
import sys
import os
import threading
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

log = logging.getLogger(__name__)

_triager = None
_triager_lock = threading.Lock()


def _get_triager():
    """Thread-safe singleton — GemmAidTriager."""
    global _triager
    if _triager is not None:
        return _triager

    with _triager_lock:
        if _triager is not None:
            return _triager

        # kaggle modülünden import et
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "kaggle"))
        from gemma4_inference import GemmAidTriager

        log.info("[Transformers] Gemma 4 yükleniyor...")
        _triager = GemmAidTriager()
        log.info("[Transformers] ✅ Gemma 4 hazır!")
        return _triager


def call_transformers(message: str) -> dict:
    """Transformers backend ile triaj."""
    triager = _get_triager()
    result = triager.triage(message)
    # _raw alanını kaldır (API yanıtında gereksiz)
    result.pop("_raw", None)
    return result


def is_model_loaded() -> bool:
    return _triager is not None


def preload_model():
    try:
        _get_triager()
    except Exception as e:
        log.warning(f"[Transformers] Ön yükleme başarısız: {e}")
