# GemmAid — Lokal Deploy Rehberi (llama.cpp)

Bu klasör, GemmAid'i **Intel CPU + 8GB RAM + Ubuntu** üzerinde tamamen lokal olarak çalıştırmak için gereken her şeyi içerir.

## Sistem Gereksinimleri

| Gereksinim | Minimum | Önerilen |
|-----------|---------|----------|
| İşletim Sistemi | Ubuntu 20.04+ | Ubuntu 22.04+ |
| CPU | Herhangi bir x86_64 | Intel / AMD 4+ çekirdek |
| RAM | 4 GB | 8 GB |
| Disk | 5 GB boş alan | 10 GB |
| Python | 3.10+ | 3.11+ |
| İnternet | Sadece ilk kurulum için | — |

## Hızlı Başlangıç

### 1. İlk Kurulum (Bir kez yapılır)

```bash
cd /path/to/kaggle-gemma4_gemmaid
bash deploy/setup.sh
```

Bu script otomatik olarak:
- Python sürümünü kontrol eder
- Sistem bağımlılıklarını kurar (cmake, libopenblas-dev)
- Python paketlerini kurar (llama-cpp-python dahil)
- `.env` dosyasını oluşturur
- Gemma 4 E4B GGUF modelini indirir (~2.5 GB)

### 2. Servisleri Başlat

```bash
bash deploy/start.sh
```

Bu komut şunları başlatır:
- **API** → `http://localhost:8000` (Gemma 4 llama.cpp backend)
- **Dashboard** → `http://localhost:7860` (Koordinatör paneli)
- **Telegram Bot** → (TELEGRAM_TOKEN ayarlıysa otomatik başlar)

### 3. Sağlık Kontrolü

```bash
bash deploy/health_check.sh
```

## Nasıl Çalışır?

```
                        GemmAid Lokal Deploy
                        ═══════════════════

    ┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
    │  Telegram    │────▶│  FastAPI :8000    │────▶│  Gradio      │
    │  Bot         │     │  Triage API      │     │  Dashboard   │
    │              │     │                  │     │  :7860       │
    └──────────────┘     └────────┬─────────┘     └──────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  llama-cpp-python      │
                    │  Gemma 4 E4B GGUF      │
                    │  (Q4_K_M, ~2.5 GB)     │
                    │  CPU üzerinde çalışır  │
                    └────────┬───────────────┘
                             │
                             ▼
                    ┌────────────────────────┐
                    │  SQLite DB             │
                    │  (gemmaid.db)          │
                    └────────────────────────┘
```

## Model Bilgileri

| Özellik | Değer |
|---------|-------|
| Model | Gemma 4 E4B (google/gemma-4-e4b-it) |
| Format | GGUF (Q4_K_M) |
| Boyut | ~2.5 GB disk, ~3.5 GB RAM |
| Engine | llama-cpp-python (C++ tabanlı) |
| Kaynak | unsloth/gemma-4-E4B-it-GGUF (HuggingFace) |

## Ortam Değişkenleri

`.env` dosyasını düzenleyin:

```bash
nano .env
```

| Değişken | Varsayılan | Açıklama |
|----------|-----------|----------|
| `GEMMAID_BACKEND` | `local` | Backend (local/gemini/transformers) |
| `LOCAL_MODEL_PATH` | `./models/gemma-4-E4B-it-Q4_K_M.gguf` | GGUF model yolu |
| `LOCAL_N_THREADS` | `4` | CPU thread sayısı |
| `LOCAL_N_CTX` | `2048` | Context window |
| `TELEGRAM_TOKEN` | — | Telegram Bot token |
| `GEMINI_API_KEY` | — | Google AI API key (opsiyonel) |

## Performans Beklentisi

| Donanım | İlk Yükleme | Triaj Süresi |
|---------|------------|-------------|
| 4 çekirdek, 8 GB RAM | ~90 saniye | ~30-60 saniye |
| 8 çekirdek, 16 GB RAM | ~45 saniye | ~15-30 saniye |

> **Not:** İlk yüklemeden sonra model bellekte kalır (singleton pattern).
> Sonraki istekler çok daha hızlıdır.

## Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| `Model bulunamadı` | `python scripts/download_model.py` çalıştırın |
| `llama-cpp-python import hatası` | `pip install llama-cpp-python` |
| Port 8000 kullanımda | `lsof -i :8000` ile kontrol edin |
| Bellek yetersiz | `LOCAL_N_CTX=1024` yapın, Q2_K model kullanın |
| API başlamıyor | `python api/api.py` ile log'ları kontrol edin |

## Alternatif Backend'ler

Birincil backend (llama.cpp) çalışmadığında:

- **Google AI API (bulut):** `GEMMAID_BACKEND=gemini` → `optional/gemini_cloud/README.md`
- **Kaggle (GPU):** `GEMMAID_BACKEND=transformers` → `optional/kaggle/README.md`
- **Modal (serverless):** → `optional/modal/README.md`
