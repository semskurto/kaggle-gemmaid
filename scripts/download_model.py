#!/usr/bin/env python3
"""GemmAid — GGUF Model İndirici

Gemma 4 E4B GGUF modelini HuggingFace Hub'dan indirir (~2.5 GB).
Birincil backend (GEMMAID_BACKEND=local) için gereklidir.

Kullanım:
    python scripts/download_model.py
    python scripts/download_model.py --quant Q2_K   # daha küçük (~1.4GB)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from local_llm.model_manager import download_model, check_model_exists, get_model_info
import argparse


def main():
    parser = argparse.ArgumentParser(description="GemmAid Model İndirici")
    parser.add_argument(
        "--quant",
        default="Q4_K_M",
        choices=["Q4_K_M", "Q3_K_S"],
        help="Quantization seviyesi:\n"
             "  Q4_K_M: ~5GB, önerilen (hız/kalite dengesi)\n"
             "  Q3_K_S: ~3.9GB, daha küçük ama daha düşük kalite",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Mevcut modeli sil ve yeniden indir",
    )
    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║         GemmAid — Gemma 4 E4B Model İndirici        ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    info = get_model_info()
    if info["status"] == "ready" and not args.force:
        print(f"✅ Model zaten hazır!")
        print(f"   📁 Yol  : {info['path']}")
        print(f"   💾 Boyut: {info['size_gb']} GB")
        print()
        print("API'yi başlatmak için:")
        print("  python api/api.py")
        return

    print(f"📦 Seçilen Quantization: {args.quant}")
    print(f"{'~5.0 GB (önerilen)' if args.quant == 'Q4_K_M' else '~3.9 GB (küçük)'}")
    print()

    try:
        model_path = download_model(quant=args.quant, force=args.force)
        print()
        print("╔══════════════════════════════════════════════════════╗")
        print("║                  ✅ İndirme Başarılı!               ║")
        print("╚══════════════════════════════════════════════════════╝")
        print()
        print(f"Model: {model_path}")
        print()
        print("Sonraki adımlar:")
        print("  python api/api.py          # llama.cpp backend (varsayılan)")
        print("  bash deploy/start.sh       # tüm servisleri başlat")

    except Exception as e:
        print(f"\n❌ İndirme hatası: {e}")
        print("\nAlternatif: Modeli manuel indirmek için:")
        print("  pip install huggingface-hub")
        print("  huggingface-cli download unsloth/gemma-4-E4B-it-GGUF gemma-4-E4B-it-Q4_K_M.gguf --local-dir ./models/")
        sys.exit(1)


if __name__ == "__main__":
    main()
