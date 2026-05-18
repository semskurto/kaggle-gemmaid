# GemmAid — Telegram Bot Setup and Connection Guide

This guide contains all the steps required to set up and run the GemmAid Telegram bot from scratch.

---

## Architecture: Telegram ↔ GemmAid Connection

```
┌──────────────────────────────────────────────────────────────┐
│                    CONNECTION ARCHITECTURE                   │
│                                                              │
│  [Citizen]                                                   │
│      │ Telegram message (in any language)                     │
│      ▼                                                       │
│  [Telegram Servers] ◄────── Polling ──────┐                  │
│      │ Message delivery                       │                  │
│      ▼                                       │                  │
│  ┌─────────────────────────┐    ┌─────────────────────────┐  │
│  │  GemmAid Telegram Bot   │    │  How it works?          │  │
│  │  (bot/bot.py)           │    │                         │  │
│  │  - Polling mode         │───▶│  The bot continuously   │  │
│  │  - Checks for new msgs  │    │  asks Telegram servers  │  │
│  │    every 1s             │    │  "is there a new msg?"  │  │
│  └────────┬────────────────┘    │  Webhook is NOT NEEDED. │  │
│           │ HTTP POST /triage   └─────────────────────────┘  │
│           ▼                                                  │
│  ┌─────────────────────────┐                                 │
│  │  GemmAid FastAPI        │                                 │
│  │  (api/api.py :8000)     │                                 │
│  │  - Receives message     │                                 │
│  │  - Sends to llama.cpp   │                                 │
│  │  - Returns Triage JSON  │                                 │
│  └────────┬────────────────┘                                 │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────────────┐                                 │
│  │  llama-cpp-python       │                                 │
│  │  Gemma 4 E4B GGUF       │                                 │
│  │  (Runs on CPU)          │                                 │
│  └─────────────────────────┘                                 │
│                                                              │
│  Result: Triage JSON → Bot → Telegram → Reply to Citizen     │
└──────────────────────────────────────────────────────────────┘
```

**Important:** The bot operates in **polling** mode. This means:
- No external access (webhook) to your server is required
- No need to open ports
- It works even behind NAT/firewall
- It works on any machine with an internet connection

---

## Step 1: Getting a Token from BotFather

### 1.1 Open BotFather
1. Open Telegram (mobile or desktop)
2. Type `@BotFather` into the search bar
3. Select the official BotFather (with the blue ✓ tick)

### 1.2 Create a New Bot
Type the following command to BotFather:
```
/newbot
```

### 1.3 Give Your Bot a Name
BotFather will ask for a name. Type:
```
GemmAid Triage Bot
```
> This is the display name users will see in their chat list.

### 1.4 Give a Username
BotFather will ask for a username. It must be **unique** and end with `_bot`:
```
gemmaid_triage_bot
```
> **Note:** If this username is already taken, try a different one:
> `gemmaid_crisis_bot`, `gemmaid_emergency_bot`, etc.

### 1.5 Copy the Token
BotFather will give you a token that looks like this:
```
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```
> ⚠️ **Do not share this token with anyone!** Your bot can be controlled with this token.

---

## Step 2: Adding the Token to the System

### 2.1 Open the .env File
```bash
cd /path/to/kaggle-gemma4_gemmaid
nano .env
```

### 2.2 Add the Token
Find the `TELEGRAM_TOKEN=` line and paste your token:
```env
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

### 2.3 Save
- If using `nano`: `Ctrl+O` → `Enter` → `Ctrl+X`

---

## Step 3: Starting the System

For the bot to work, **the API must also be running.**

### Method A: Single Command (Recommended)
```bash
bash deploy/start.sh
```
> This command starts the API + Dashboard + Bot all together.

### Method B: Separate Terminals
```bash
# Terminal 1 — API (this must start first)
python api/api.py

# Terminal 2 — Bot (while API is running)
python bot/bot.py
```

### Expected Output
```
🤖 GemmAid Bot started (polling mode)...
   API: http://localhost:8000
```

---

## Step 4: Testing in Telegram

### 4.1 Find Your Bot
Type your bot's username in the Telegram search bar:
```
@gemmaid_triage_bot
```

### 4.2 Start Command
Send this command to the bot:
```
/start
```
Response: Welcome message + usage instructions

### 4.3 Status Check
```
/status
```
Response: API status, backend info, case statistics

### 4.4 Crisis Message Test
Write a crisis message in any language:

**English:**
```
Our neighbor is trapped under the debris, Atatürk Street 3rd floor, having difficulty breathing
```

**Arabic:**
```
جارنا عالق تحت الأنقاض، يتنفس بصعوبة
```

**French:**
```
J'ai une douleur intense dans la poitrine depuis 2 heures
```

### 4.5 Demo
```
/demo
```
Runs an automated demo scenario in 4 languages.

---

## Bot Commands Reference

| Command | Function |
|-------|-------|
| `/start` | Welcome message + supported languages |
| `/status` | API connection, backend, model status |
| `/demo` | Automated demo triage in 4 languages (TR/AR/FR/EN) |
| `/temizle` | Clear cases (for testing only) |
| _any text_ | Automatic triage — message is sent directly to the API |

---

## Troubleshooting

### Bot Won't Start

| Problem | Solution |
|-------|-------|
| `TELEGRAM_TOKEN is not set` | Add token to `.env` file |
| `Token invalid` | Get a new token from BotFather: `/token` |
| `Unauthorized` | Check the token, make sure there are no spaces |

### Bot Not Responding

| Problem | Solution |
|-------|-------|
| `API Offline` | Run `python api/api.py` |
| `Timeout` | Model might be loading (first request takes ~90s) |
| `Connection refused` | Check API port: `lsof -i :8000` |

### Token Verification

To verify your token:
```bash
curl "https://api.telegram.org/bot<TOKEN>/getMe"
```

Successful response:
```json
{
  "ok": true,
  "result": {
    "id": 1234567890,
    "is_bot": true,
    "first_name": "GemmAid Triage Bot",
    "username": "gemmaid_triage_bot"
  }
}
```

---

## Advanced: Bot Configuration

### Polling vs Webhook

The GemmAid bot uses **polling** mode by default:

| Feature | Polling | Webhook |
|---------|---------|---------|
| Setup | Easy ✅ | Hard (SSL, domain required) |
| Firewall | No problem ✅ | Port must be open |
| Latency | ~1 second | Instant |
| Server | Any | Static IP/domain |

> **Recommendation:** Polling is ideal for disaster scenarios — simple, reliable, requires no extra configuration.

### Message Flow (Detailed)

```
1. User writes a message
2. Bot sends "⏳ Analyzing..."
3. Bot → HTTP POST http://localhost:8000/triage {"message": "..."}
4. API → llama.cpp → Gemma 4 → Generates Triage JSON
5. API → Returns JSON response
6. Bot → Deletes "⏳" message
7. Bot → Sends formatted triage report to the user
```

### Timeout Settings

By default, the bot has:
- **Triage request:** 120 seconds timeout
- **Status/Health:** 10 seconds timeout
- **Demo:** 300 seconds timeout (runs 4 languages sequentially)

These values can be adjusted inside `bot/bot.py`.

---

*GemmAid Telegram Guide — May 18, 2026*
