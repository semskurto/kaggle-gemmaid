# GemmAid — Kaggle Deployment (Opsiyonel)

Bu klasör, GemmAid'i **Kaggle Notebook** ortamında GPU ile çalıştırmak için gerekli dosyaları içerir.

## Ne Zaman Kullanılır?

- Kaggle Hackathon submission için
- GPU erişimi olduğunda (T4/P100)
- HuggingFace Transformers pipeline ile çalışmak istediğinizde

## Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `gemma4_inference.py` | Gemma 4 triaj motoru (GemmAidTriager sınıfı) |
| `gemmaid_notebook.ipynb` | Kaggle submission notebook'u |
| `transformers_inference.py` | API wrapper (GEMMAID_BACKEND=transformers) |

## Kaggle'da Kullanım

### 1. Notebook Upload
1. https://kaggle.com → "New Notebook"
2. `gemmaid_notebook.ipynb` dosyasını upload edin
3. Runtime: GPU (T4/P100)

### 2. Hücreleri Çalıştırın
Notebook sırasıyla:
1. `transformers` ve `torch` kurulumu
2. `GemmAidTriager` başlatma
3. 5 dil demo (TR/AR/FR/EN/AZ)
4. Sonuçları görselleştirme

## Lokal API ile Kullanım

Eğer GPU'lu bir makineniz varsa, GemmAid API'yi transformers backend ile çalıştırabilirsiniz:

```bash
# Gerekli paketler
pip install torch transformers accelerate

# API başlat
GEMMAID_BACKEND=transformers python api/api.py
```

## Teknik Detaylar

### GemmAidTriager Sınıfı
```python
from gemma4_inference import GemmAidTriager

triager = GemmAidTriager(
    model_id="google/gemma-4-e4b-it",  # Resmi HuggingFace ID
    device="auto",                       # GPU varsa CUDA, yoksa CPU
)

result = triager.triage("Komşumuz enkaz altında")
# → Yapılandırılmış triaj JSON döndürür
```

### HuggingFace Pipeline API (Resmi)
```python
from transformers import pipeline

pipe = pipeline(
    task="any-to-any",          # Gemma 4 resmi task tipi
    model="google/gemma-4-e4b-it",
    device_map="auto",
    dtype="auto",
)
```

## Ana Sisteme Geri Dönüş

Kaggle backend sorunlu olursa birincil llama.cpp backend'e dönün:

```bash
GEMMAID_BACKEND=local python api/api.py
```
