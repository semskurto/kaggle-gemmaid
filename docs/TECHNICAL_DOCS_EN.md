# GemmAid — Comprehensive Technical Documentation

**Version:** 4.0 | **Date:** May 18, 2026
**Hackathon:** Kaggle Gemma 4 Good | **License:** Apache 2.0

---

## 1. Project Summary

GemmAid is a multilingual triage system for disaster and crisis situations, built **entirely on Gemma 4**. Citizens send messages to Telegram in their native language (140+ languages), and Gemma 4 transforms this message into a structured case card (JSON). The prioritized case list is then displayed on the coordinator's screen.

**The entire intelligence layer is Gemma 4. No other LLMs are used.**

**Primary deployment:** llama.cpp (llama-cpp-python) + Gemma 4 E4B GGUF — Intel CPU, 8GB RAM, Ubuntu.

---

## 2. Gemma 4 — The Heart of the Project

### 2.1 Why Gemma 4?

| Gemma 4 Feature | Counterpart in GemmAid |
|---|---|
| **Native support for 140+ languages** | Triage capabilities in Arabic, Kurdish, Azerbaijani, French, etc. |
| **Structured JSON output** | Free-text message → reliable triage case card |
| **256K context window** | Long reports, chained conversation history |
| **E4B edge architecture** | Runs on-device with CPU and 8GB RAM |
| **26B MoE (A4B)** | Powerful cloud triage via Google AI API |
| **Apache 2.0 license** | Open-source, suitable for commercial use |

### 2.2 Gemma 4 Variants Used

| Variant | Model ID | Usage Context | Inference Engine |
|---------|----------|---------------|-----------------|
| **Gemma 4 E4B** | `google/gemma-4-e4b-it` | Local CPU (DEFAULT) | llama-cpp-python (GGUF) |
| **Gemma 4 E4B** | `google/gemma-4-e4b-it` | Kaggle notebook (optional) | HF pipeline (any-to-any) |
| **Gemma 4 26B A4B** | `gemma-4-26b-a4b-it` | Google AI API (optional) | google-generativeai SDK |

### 2.3 Gemma 4 Official Chat Format

The official Gemma 4 model card utilizes standard roles:

```python
messages = [
    {"role": "system", "content": "You are a triage assistant."},
    {"role": "user",   "content": "My neighbor is under the debris."},
]
```

- **llama-cpp-python** → `lm.create_chat_completion(messages=messages, ...)` (GGUF chat template applied automatically)
- **HF Transformers** → `pipeline(...)(messages)` (AutoProcessor.apply_chat_template)

**Recommended sampling parameters (official):**
```
temperature = 1.0, top_p = 0.95, top_k = 64
```
Because GemmAid aims to extract structured JSON, it deliberately uses `temperature=0.1`.

---

## 3. System Architecture

### 3.1 General Workflow

```
┌──────────────────────────────────────────────────────┐
│                   USER LAYER                         │
├──────────────────────────────────────────────────────┤
│  👤 Citizen (140+ langs)    👨‍💼 Coordinator           │
│  Telegram message           Gradio Dashboard         │
│       │                           ▲                  │
│       ▼                           │                  │
│  ┌──────────┐            ┌────────────────┐          │
│  │ Telegram │            │ Gradio :7860   │          │
│  │   Bot    │            │ Auto-refresh   │          │
│  └────┬─────┘            └───────┬────────┘          │
├───────┼──────────────────────────┼───────────────────┤
│       │        API LAYER         │                   │
│       ▼                          │                   │
│  ┌────────────────────────────────────┐              │
│  │     FastAPI — Triage API :8000     │              │
│  │  POST /triage  GET /cases          │              │
│  │  GET /stats    GET /health         │              │
│  │  POST /demo    DELETE /cases       │              │
│  └──────────────┬─────────────────────┘              │
├──────────────────┼──────────────────────────────────┤
│                  │   GEMMA 4 LAYER                   │
│     ┌────────────┼────────────┐                      │
│     ▼            ▼            ▼                      │
│  ┌───────┐ ┌──────────┐ ┌────────┐                  │
│  │ local │ │transform.│ │ cloud  │                  │
│  │Gemma4 │ │ Gemma 4  │ │Gemma4  │                  │
│  │E4B    │ │ E4B      │ │26B MoE │                  │
│  │GGUF   │ │ pipeline │ │API     │                  │
│  └───┬───┘ └────┬─────┘ └───┬────┘                  │
│      └──────────┴───────────┘                        │
│               │                                      │
│               ▼                                      │
│      ┌─────────────────┐                             │
│      │  Triage JSON    │                             │
│      └──────┬──────────┘                             │
├─────────────┼────────────────────────────────────────┤
│             │    DATA LAYER                          │
│             ▼                                        │
│      ┌──────────────────────────────────┐            │
│      │  SQLite DB (gemmaid.db)          │            │
│      └──────────────────────────────────┘            │
└──────────────────────────────────────────────────────┘
```

### 3.2 Single Triage Request Data Flow

```
Crisis Message (any language)
    │
    ▼
Telegram Bot / Dashboard / API
    │  POST /triage {"message": "..."}
    ▼
FastAPI run_triage()
    │  Dispatch based on GEMMAID_BACKEND env variable
    ├─ local        → local_llm/inference.py             (DEFAULT, llama-cpp)
    ├─ transformers → local_llm/transformers_inference.py (optional)
    └─ gemini       → api/api.py::call_gemini()          (optional, cloud)
    │
    ▼
Gemma 4 (selected backend)
    │  System prompt + crisis message → JSON output
    ▼
core/triage_schema.py::parse_triage_json()
    │  JSON parse → Pydantic TriageResult validation
    ▼
core/database.py::save_case()
    │  Save to SQLite
    ▼
HTTP 200 Triage JSON + Telegram message + Dashboard update
```

---

## 4. Deployment Modes

### 4.1 MODE A — llama-cpp-python (DEFAULT, Primary)

```
GEMMAID_BACKEND=local
Hardware: Ubuntu PC, 8GB+ RAM, Intel/AMD CPU
Model   : Gemma 4 E4B (GGUF Q4_K_M, ~2.5GB)
Engine  : llama-cpp-python (C++ based)
Internet: NOT REQUIRED after model is downloaded
Advantage: Continues to work in disaster zones even if the internet is cut off
```

**Installation:**
```bash
bash deploy/setup.sh     # Fully automatic
# or manual:
CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" pip install llama-cpp-python
python scripts/download_model.py   # Download ~2.5GB
python api/api.py                  # GEMMAID_BACKEND=local (default)
```

**Technical Detail — llama.cpp GGUF:**
- GGUF: quantized model format
- Q4_K_M: 4-bit quantization — excellent quality/size balance
- `n_ctx=2048`: context window
- `n_gpu_layers=0`: all layers on CPU
- `n_threads=4`: parallel CPU threads (recommended for 8GB RAM)
- Chat template: Official Gemma 4 `chat_template` within GGUF is automatically applied

### 4.2 MODE B — HuggingFace Transformers (Optional — Kaggle/GPU)

```
GEMMAID_BACKEND=transformers
Hardware: GPU (Kaggle T4/P100) or CPU
Model   : google/gemma-4-e4b-it (HuggingFace Hub)
Engine  : transformers pipeline (task=any-to-any)
Detail  : optional/kaggle/README.md
```

### 4.3 MODE C — Google AI API (Optional — Cloud)

```
GEMMAID_BACKEND=gemini
Model   : gemma-4-26b-a4b-it (26B MoE, Google AI Studio)
Engine  : google-generativeai SDK
Internet: Required
Detail  : optional/gemini_cloud/README.md
```

### 4.4 MODE D — Modal Serverless (Optional — Cloud GPU)

```
Detail  : optional/modal/README.md
Deploy  : modal deploy optional/modal/modal_deploy.py
```

---

## 5. File-by-File Technical Explanations

### 5.1 `core/config.py` — Central Configuration

**Critical Variables:**

| Variable | Default | Description |
|----------|-----------|----------|
| `GEMMAID_BACKEND` | `local` | Backend: `local`, `transformers`, `gemini` |
| `LOCAL_MODEL_PATH` | `./models/gemma-4-E4B-it-Q4_K_M.gguf` | GGUF model file |
| `LOCAL_N_THREADS` | `4` | CPU thread count |
| `LOCAL_N_CTX` | `2048` | Context window |
| `GEMINI_API_KEY` | `""` | Google AI API key (optional) |
| `TELEGRAM_TOKEN` | `""` | BotFather token |
| `API_PORT` | `8000` | FastAPI port |
| `DASHBOARD_PORT` | `7860` | Gradio port |

### 5.2 `local_llm/inference.py` — llama-cpp-python Inference (PRIMARY)

**Role:** Primary backend running Gemma 4 E4B GGUF on CPU.

**Singleton Pattern (Thread-Safe):**
```python
_model = None
_model_lock = threading.Lock()
def _get_model():
    # Single model instance via double-check locking
```

**Chat completion (official method):**
```python
output = lm.create_chat_completion(
    messages=[
        {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
        {"role": "user",   "content": f"Crisis message: {message}"},
    ],
    max_tokens=512,
    temperature=0.1,
    top_p=0.95,
    repeat_penalty=1.1,
)
raw_text = output["choices"][0]["message"]["content"]
```

### 5.3 `api/api.py` — FastAPI Central Service

**Backend Dispatch Mechanism:**
```python
dispatch = {
    "local":        call_local,         # llama-cpp-python (DEFAULT)
    "transformers": call_transformers,  # HF pipeline (optional)
    "gemini":       call_gemini,        # Google AI API (optional)
}
fn = dispatch.get(BACKEND, call_local)
```

**Endpoint Reference:**

| Method | Endpoint | Description |
|--------|----------|----------|
| POST | `/triage` | Triage the crisis message |
| GET | `/cases` | Case list (ordered by urgency) |
| GET | `/stats` | Statistics |
| POST | `/cases/{case_id}/close` | Close a resolved case |
| DELETE | `/cases/{case_id}` | Delete a single case permanently |
| GET | `/health` | API + model status |
| POST | `/demo` | 4-language demo |
| DELETE | `/cases` | Delete all cases |

### 5.4 `bot/bot.py` — Telegram Bot

Detailed guide: `docs/TELEGRAM_SETUP_EN.md`

**Commands:** `/start`, `/status`, `/demo`, `/temizle`
**Message flow:** Text → API POST → Triage JSON → Format → Reply

### 5.5 `dashboard/dashboard.py` — Coordinator Dashboard

**Components:** Status bar, statistics cards, case table, manual triage, demo
**Auto-Refresh:** `gr.Timer(value=30)` — Updates every 30 seconds

### 5.6 `deploy/` — Primary Deploy Folder

| File | Purpose |
|-------|------|
| `setup.sh` | Fully automatic installation (deps + model) |
| `start.sh` | Start API + Dashboard + Bot |
| `health_check.sh` | System health check |

---

## 6. Triage JSON Schema

```json
{
  "olay_tipi": "enkaz_alti | tibbi_acil | tahliye | kaynak_ihtiyaci | belirsiz",
  "aciliyet_skoru": 1,
  "konum_metni": "detected location or 'Belirtilmedi' (Not specified)",
  "etkilenen_kisi_sayisi": 3,
  "semptomlar": ["nefes_guclugu", "kanama"],
  "gerekli_ekip": ["tibbi", "arama_kurtarma"],
  "kaynak_dil": "tr | ar | en | fr | ku | az",
  "eksik_bilgiler": ["location missing", "contact missing"],
  "koordinator_notu": "Coordinator evaluation note in Turkish",
  "eylem_plani": "Coordinator-specific step-by-step action plan",
  "vatandasa_yanit": "Reassuring message in victim's native language"
}
```

---

## 7. Dependency Reference

```
# Primary
fastapi, uvicorn        # REST API
pydantic                # JSON validation
python-dotenv           # .env management
httpx                   # Async HTTP (bot ↔ API)
llama-cpp-python        # PRIMARY: GGUF inference (CPU)
huggingface-hub         # Model downloading
gradio                  # Dashboard
python-telegram-bot     # Telegram Bot
json-repair             # Malformed JSON recovery

# Optional
google-generativeai     # Google AI API (gemini backend)
torch, transformers     # HF pipeline (transformers backend)
```

---

## 8. Performance and Limitations

| Hardware | Cold Start | Triage Time |
|---------|------------|-------------|
| 4-core CPU, 8GB RAM | ~90 seconds | ~30-60 seconds |
| 8-core CPU, 16GB RAM | ~45 seconds | ~15-30 seconds |
| GPU (Kaggle T4) | ~10 seconds | ~2-5 seconds |

**Known Limitations:**
- Initial load takes 30-90s (subsequent requests are fast due to singleton)
- Q4_K_M has a 5-10% quality drop compared to Q8_0 — completely acceptable for triage
- SQLite: WAL mode is recommended in scenarios with extremely high concurrent writes

---

## 9. Brief Compliance Check

| Brief Item | Status | Implementation |
|-------------|-------|----------------|
| Telegram bot | ✅ | `bot/bot.py` — polling, 4 commands |
| Gemma 4 local deploy (primary) | ✅ | `local_llm/inference.py` — llama-cpp |
| Gemma 4 Kaggle deploy (optional) | ✅ | `optional/kaggle/` — HF pipeline |
| Gemma 4 cloud deploy (optional) | ✅ | `api/api.py::call_gemini()` |
| Modal serverless (optional) | ✅ | `optional/modal/modal_deploy.py` |
| Official Gemma 4 chat format | ✅ | Standard system/user roles |
| Gradio coordinator dashboard | ✅ | `dashboard/dashboard.py` |
| 4+ language demo | ✅ | TR/AR/FR/EN |
| SQLite persistent storage | ✅ | `core/database.py` |
| Deploy folder | ✅ | `deploy/` — setup.sh, start.sh |
| Conversational Memory | ✅ | Context fed via API |
| Dynamic Action Plan | ✅ | Strategies generated by Gemma 4 |

---

*Last update: May 18, 2026 — GemmAid v4.0*
