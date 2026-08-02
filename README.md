# 🆘 GemmAid — Multilingual Emergency Triage System

> **GemmAid allows people to freely express their needs in their native language during crises and emergencies; Gemma 4 translates these expressions into structured triage data, ensuring the right help reaches the right person in a coordinated manner.**

[![Kaggle Hackathon](https://img.shields.io/badge/Kaggle-Gemma%204%20Good%20Hackathon-20BEFF?logo=kaggle)](https://kaggle.com)
[![Gemma 4](https://img.shields.io/badge/Model-Gemma%204%20E4B-4285F4?logo=google)](https://ai.google.dev/gemma)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com)

- [Technical Docs (EN)](docs/TECHNICAL_DOCS_EN.md)
- [Telegram Setup (EN)](docs/TELEGRAM_SETUP_EN.md)
- [Scenarios & Guide (EN)](docs/SCENARIOS_AND_GUIDE_EN.md)

---

## 🎯 Problem & Solution

### Why GemmAid?

During the 2023 Kahramanmaraş earthquake:
- Emergency hotlines (112) were locked down within the first few minutes.
- Foreign rescue teams couldn't coordinate due to language barriers.
- Massive piles of WhatsApp/Telegram messages could not be systematically evaluated.

**GemmAid bridges 3 major gaps:**
| Gap | Solution |
|--------|-------|
| Expression | Accepts messages in any language (140+) |
| Memory | Combines consecutive messages belonging to the same incident (Conversational Memory) |
| Understanding | Generates structured triage and dynamic action plans via Gemma 4 |
| Coordination | Displays prioritized cases on an Advanced Dashboard |

---

## 🏗️ System Architecture

```
[CITIZEN/PATIENT]
Sends a message to Telegram in their native language
        │
        ▼
[TELEGRAM BOT — python-telegram-bot]
Receives message, forwards to API
        │
        ▼
[FASTAPI — Triage API :8000]
Routes according to the selected backend
        │
        ├── GEMMAID_BACKEND=local        → llama-cpp-python + GGUF (CPU, DEFAULT)
        ├── GEMMAID_BACKEND=gemini       → Google AI API (Gemma 4 26B cloud, optional)
        └── GEMMAID_BACKEND=transformers → HuggingFace pipeline (GPU/Kaggle, optional)
        │
        ▼
[STRUCTURED CASE CARD — JSON + SQLite]
        │
        ├──► [COORDINATOR DASHBOARD — Gradio :7860]
        │    Priority queues, statistics, auto-refresh
        │
        └──► [TELEGRAM BOT — Feedback Loop]
             Replies to the citizen: Triage info + coordinator's direct note
```

---

## 🚀 Quick Start

### Prerequisites
- Ubuntu 20.04+ / Debian
- Python 3.10+
- RAM: minimum 4GB (8GB recommended)
- Disk: ~5GB free space (for the model)

### 1. Installation (Single Command)

```bash
git clone https://github.com/your-username/kaggle-gemma4_gemmaid.git
cd kaggle-gemma4_gemmaid
bash deploy/setup.sh
```

This script automatically:
- Installs system dependencies
- Installs Python packages (including llama-cpp-python)
- Downloads the Gemma 4 E4B GGUF model (~2.5 GB)
- Creates the `.env` file

### 2. Telegram Bot Setup (Optional)

```bash
# Add your token to the .env file
nano .env
# TELEGRAM_TOKEN=your_token_here

# Detailed guide: docs/TELEGRAM_SETUP_EN.md
```

### 3. Start All Services

```bash
bash deploy/start.sh
```

Services:
- **API** → `http://localhost:8000` (llama.cpp + Gemma 4)
- **Dashboard** → `http://localhost:7860` (Coordinator panel)
- **Bot** → Telegram (if token is configured)

### 4. Test

```bash
# Health check
bash deploy/health_check.sh

# 4-Language triage test
python scripts/test_triage.py

# Manual test (curl)
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"message": "Our neighbor is under the debris, having difficulty breathing"}'
```
Additional Note: If you’d like to explore GemmAid a bit more, I’ve also prepared a small companion website with additional details and a limited interactive demo:

👉 https://gemmaid.lovable.app/ 🩵

It provides a quick way to experience how the triage flow works.  
  
🛟For a fully organic, offline-first experience, you can follow the GitHub documentation and run GemmAid locally on your own machine — the setup is lightweight, and on-device inference gives the most realistic feel of the system.

---

## 📁 Project Structure

```
kaggle-gemma4_gemmaid/
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
│
├── core/                     # Shared modules
│   ├── config.py             # Central configuration
│   ├── triage_schema.py      # Triage JSON schema (Pydantic)
│   └── database.py           # SQLite case storage
│
├── api/
│   └── api.py                # FastAPI — /triage, /cases, /stats, /health
│
├── bot/
│   └── bot.py                # Telegram Bot
│
├── dashboard/
│   └── dashboard.py          # Gradio Coordinator Dashboard
│
├── local_llm/                # Primary inference module (llama.cpp)
│   ├── model_manager.py      # GGUF model management
│   ├── inference.py          # llama-cpp-python wrapper
│   └── transformers_inference.py  # HF wrapper (optional)
│
├── deploy/                   # 🚀 Primary deployment (llama.cpp)
│   ├── README.md             # Deployment guide
│   ├── setup.sh              # 1-click installation
│   ├── start.sh              # Start all services
│   └── health_check.sh       # System health check
│
├── optional/                 # Optional alternative backends
│   ├── kaggle/               # Kaggle deployment (HF Transformers)
│   ├── modal/                # Modal serverless deployment
│   └── gemini_cloud/         # Google AI API (cloud)
│
├── scripts/
│   ├── download_model.py     # GGUF model downloader
│   └── test_triage.py        # Test scenarios in 4 languages
│
└── docs/
    ├── TECHNICAL_DOCS_EN.md     # Comprehensive technical documentation
    ├── SCENARIOS_AND_GUIDE_EN.md # Disaster scenarios and usage guide
    └── TELEGRAM_SETUP_EN.md     # Telegram bot setup guide
```

---

## 🧪 Demo Scenarios

### Scenario 1 — Under Debris (Arabic)
```
Message: جارنا عالق تحت الأنقاض، يتنفس بصعوبة، شارع أتاتورك

Triage output:
  🔴 Urgency: 1/5 (CRITICAL)
  📍 Incident: Trapped Under Debris
  🗺️  Location: Atatürk Street
  🚨 Team: Search & Rescue + Medical
  📋 Note: Respiratory symptom is critical, priority response required
```

### Scenario 2 — Medical Emergency (French)
```
Message: J'ai une douleur intense dans la poitrine depuis 2 heures

Triage output:
  🔴 Urgency: 1/5 (CRITICAL)
  🏥 Incident: Medical Emergency
  🚨 Team: Medical
  📋 Note: Suspected cardiac symptom, immediate evaluation needed
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|----------|
| POST | `/triage` | Triage the crisis message |
| GET | `/cases` | List active cases (by urgency) |
| GET | `/stats` | Summary statistics |
| POST | `/cases/{case_id}/close` | Close a resolved case |
| DELETE | `/cases/{case_id}` | Delete a fake/invalid case |
| GET | `/health` | API and model health status |
| POST | `/demo` | Execute 15 multi-language demo scenarios |
| DELETE | `/cases` | Delete all cases (for testing) |

**Swagger UI:** http://localhost:8000/docs

---

## ⚙️ Backend Options

### Primary: llama.cpp (Default)
```bash
GEMMAID_BACKEND=local python api/api.py
```
- Runs on CPU, no GPU required
- Works completely offline (once the model is downloaded)
- Ideal for disconnected disaster zones

### Optional: Google AI API (Cloud)
```bash
GEMMAID_BACKEND=gemini GEMINI_API_KEY=xxx python api/api.py
```
- Most powerful reasoning model (26B MoE)
- Requires active internet connection
- Details: `optional/gemini_cloud/README.md`

### Optional: Kaggle/Transformers (GPU)
```bash
GEMMAID_BACKEND=transformers python api/api.py
```
- Extremely fast if a GPU is present
- Fully compatible with Kaggle notebooks
- Details: `optional/kaggle/README.md`

### Optional: Modal (Serverless)
```bash
modal deploy optional/modal/modal_deploy.py
```
- Scalable Cloud GPUs (scale-to-zero)
- Pay-as-you-go efficiency
- Details: `optional/modal/README.md`

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|-----------|----------|
| `GEMMAID_BACKEND` | `local` | Backend: `local`, `gemini`, `transformers` |
| `LOCAL_MODEL_PATH` | `./models/gemma-4-E4B-it-Q4_K_M.gguf` | GGUF model path |
| `LOCAL_N_THREADS` | `4` | CPU thread count |
| `LOCAL_N_CTX` | `2048` | Context window size |
| `GEMINI_API_KEY` | — | Google AI API key (optional) |
| `TELEGRAM_TOKEN` | — | Telegram Bot token |
| `API_PORT` | `8000` | FastAPI port |
| `DASHBOARD_PORT` | `7860` | Gradio port |
| `DB_PATH` | `./gemmaid.db` | SQLite database file |

---

## 👥 Contribution

**Kaggle Gemma 4 Good Hackathon 2026**
Deadline: May 18, 2026, 23:59 UTC

---

*GemmAid — Multilingual emergency triage system powered by Gemma 4*
