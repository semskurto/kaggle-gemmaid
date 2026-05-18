# GemmAid — Google AI API / Gemini Cloud Backend (Opsiyonel)

Bu klasör, GemmAid'i **Google AI API** (Gemma 4 26B bulut modeli) ile çalıştırmak için dokümantasyon sağlar.

## Ne Zaman Kullanılır?

- Lokal makine çok yavaş olduğunda
- Hızlı yanıt süresi gerektiğinde
- En güçlü Gemma 4 modelini (26B MoE) kullanmak istediğinizde
- İnternet bağlantısının güvenilir olduğu ortamlarda

> **Not:** Bu backend internet gerektirir — afet bölgesinde internet kopuksa **kullanılamaz**.
> Birincil backend (llama.cpp) internet olmadan çalışır.

## Kurulum

### 1. API Key Alın

1. https://aistudio.google.com → API Keys
2. "Create API Key" tıklayın
3. Key'i kopyalayın

### 2. .env Dosyasını Ayarlayın

```bash
nano .env
```

Şu değişkenleri ayarlayın:
```env
GEMMAID_BACKEND=gemini
GEMINI_API_KEY=AIzaSy...your_key_here
GEMINI_MODEL=gemma-4-26b-a4b-it
```

### 3. Google AI SDK Kurun

```bash
pip install google-generativeai
```

### 4. API'yi Başlatın

```bash
GEMMAID_BACKEND=gemini python api/api.py
```

## Kullanılabilir Modeller

| Model ID | Parametre | Tip | Önerilen |
|----------|-----------|-----|----------|
| `gemma-4-26b-a4b-it` | 26B MoE (A4B) | Bulut | ✅ Önerilen |
| `gemma-4-31b-it` | 31B Dense | Bulut | Alternatif |

## Maliyet

Google AI Studio ücretsiz tier:
- 60 istek/dakika
- 1500 istek/gün
- Afet triaj senaryoları için genellikle yeterli

## Test

```bash
# Sağlık kontrolü
curl http://localhost:8000/health

# Triaj testi
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"message": "Komşumuz enkaz altında, nefes güçlüğü var"}'
```

## Kod Referansı

Gemini backend kodu `api/api.py` içindeki `call_gemini()` fonksiyonundadır:

```python
import google.generativeai as genai
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    GEMINI_MODEL,
    system_instruction=TRIAGE_SYSTEM_PROMPT,
)
resp = model.generate_content(
    f"Kriz mesajı: {message}",
    generation_config={"temperature": 0.1, "max_output_tokens": 512},
)
```

## Ana Sisteme Geri Dönüş

```bash
GEMMAID_BACKEND=local python api/api.py
```
