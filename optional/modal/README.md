# GemmAid — Modal Serverless Deployment (Opsiyonel)

Bu klasör, GemmAid'i **Modal** üzerinde serverless GPU ile çalıştırmak için gerekli dosyaları içerir.

## Ne Zaman Kullanılır?

- Lokal makine yeterli gelmediğinde (örn. hızlı yanıt süresi gerektiğinde)
- GPU erişimi olmadığında ama bulut GPU kullanmak istediğinizde
- Scale-to-zero (sadece kullandığın kadar öde) modeli istediğinizde
- Lokal llama.cpp backend'e yedek olarak

## Gereksinimler

1. Modal hesabı: https://modal.com (ücretsiz tier mevcut)
2. Modal CLI kurulumu

```bash
pip install modal
modal setup   # Kimlik doğrulama
```

## Deployment

### 1. Deploy Et

```bash
cd optional/modal
modal deploy modal_deploy.py
```

Bu komut:
- Modal üzerinde bir web endpoint oluşturur
- GGUF modelini Modal Volume'a indirir (ilk seferde)
- OpenAI uyumlu API endpoint'i sunar

### 2. API Endpoint'ini Kullan

Deploy sonrası size bir URL verilir:
```
https://your-username--gemmaid-triage.modal.run
```

Bu URL'yi GemmAid API'nin bulut backend'i olarak yapılandırabilirsiniz.

### 3. Test Et

```bash
curl -X POST https://your-username--gemmaid-triage.modal.run/triage \
  -H "Content-Type: application/json" \
  -d '{"message": "Komşumuz enkaz altında, nefes güçlüğü var"}'
```

## Maliyet

| Kaynak | Fiyat (yaklaşık) |
|--------|-------------------|
| T4 GPU | ~$0.59/saat |
| A10G GPU | ~$1.10/saat |
| İşlem dışı | $0 (scale-to-zero) |

> **Not:** Modal ücretsiz tier'de aylık $30 kredi sunar — demo/test için yeterli.

## Mimari

```
[Telegram Bot / Dashboard]
        │
        ▼
[Lokal FastAPI :8000]
        │
        ├── Birincil: llama.cpp (lokal CPU)
        │
        └── Yedek: Modal API (bulut GPU) ← Bu klasör
                │
                ▼
        [Modal Serverless]
        [Gemma 4 E4B GGUF]
        [GPU T4/A10G]
```

## Ana Sisteme Geri Dönüş

```bash
GEMMAID_BACKEND=local python api/api.py
```
