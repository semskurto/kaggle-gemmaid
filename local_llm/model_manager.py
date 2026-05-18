#!/usr/bin/env python3
"""GemmAid — Model İndirici
Gemma 4 E4B GGUF modelini HuggingFace Hub'dan indirir.

Kullanım:
    python local_llm/model_manager.py
"""
import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.config import LOCAL_MODEL_PATH

log = logging.getLogger(__name__)

# ── Model Bilgileri ──────────────────────────────────────────
# Q4_K_M: CPU için optimal denge (hız/kalite/boyut)
# ~5GB disk, ~6GB RAM
REPO_ID       = "unsloth/gemma-4-E4B-it-GGUF"
FILENAME      = "gemma-4-E4B-it-Q4_K_M.gguf"   # HuggingFace'deki tam dosya adı
MODEL_DIR     = Path(LOCAL_MODEL_PATH).parent
MODEL_PATH    = Path(LOCAL_MODEL_PATH)

# Alternatif: daha küçük model (daha hızlı ama daha az kalite)
REPO_ID_Q3   = "unsloth/gemma-4-E4B-it-GGUF"
FILENAME_Q3  = "gemma-4-E4B-it-Q3_K_S.gguf"    # ~3.9GB, en küçük kaliteli seçenek


def check_model_exists() -> bool:
    """Model dosyası mevcut mu?"""
    return MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 100_000_000  # >100MB


def download_model(quant: str = "Q4_K_M", force: bool = False) -> Path:
    """
    Gemma 4 E4B GGUF modelini indir.

    Args:
        quant: Quantization seviyesi ("Q4_K_M" veya "Q3_K_S")
        force: True ise mevcut dosyayı sil ve yeniden indir

    Returns:
        İndirilen model dosyasının yolu
    """
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("❌ huggingface-hub kurulu değil. Kuruluyor...")
        os.system(f"{sys.executable} -m pip install huggingface-hub -q")
        from huggingface_hub import hf_hub_download

    # Hedef dosya adını seç
    if quant == "Q3_K_S":
        fname = FILENAME_Q3
    else:
        fname = FILENAME

    target = MODEL_DIR / fname

    if target.exists() and not force:
        size_gb = target.stat().st_size / 1e9
        print(f"✅ Model zaten mevcut: {target} ({size_gb:.1f} GB)")
        return target

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print(f"📥 Model indiriliyor...")
    print(f"   Repo  : {REPO_ID}")
    print(f"   Dosya : {fname}")
    print(f"   Hedef : {MODEL_DIR}/")
    print(f"   Boyut : ~{'5.0' if quant == 'Q4_K_M' else '3.9'} GB")
    print("   (İlk indirme uzun sürebilir, internet hızınıza bağlı)\n")

    path = hf_hub_download(
        repo_id=REPO_ID,
        filename=fname,
        local_dir=str(MODEL_DIR),
    )

    print(f"\n✅ İndirme tamamlandı: {path}")
    return Path(path)


def get_model_info() -> dict:
    """Model hakkında bilgi döndür."""
    if check_model_exists():
        size = MODEL_PATH.stat().st_size
        return {
            "status": "ready",
            "path": str(MODEL_PATH),
            "size_gb": round(size / 1e9, 2),
        }
    return {
        "status": "not_found",
        "path": str(MODEL_PATH),
        "size_gb": 0,
    }


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="GemmAid Model İndirici")
    parser.add_argument("--quant", default="Q4_K_M", choices=["Q4_K_M", "Q3_K_S"],
                        help="Quantization seviyesi (varsayılan: Q4_K_M)")
    parser.add_argument("--force", action="store_true",
                        help="Mevcut modeli sil ve yeniden indir")
    args = parser.parse_args()

    print("=" * 55)
    print("GemmAid — Gemma 4 E4B Model İndirici")
    print("=" * 55)
    print()

    if check_model_exists() and not args.force:
        info = get_model_info()
        print(f"✅ Model zaten hazır!")
        print(f"   Yol  : {info['path']}")
        print(f"   Boyut: {info['size_gb']} GB")
        print("\nLokal API'yi başlatmak için:")
        print("  GEMMAID_BACKEND=local python api/api.py")
    else:
        download_model(quant=args.quant, force=args.force)
