# GemmAid — Disaster Scenarios & Execution Guide

**This document is a continuation of TECHNICAL_DOCS_EN.md.**

---

## 7. Comprehensive Disaster Scenarios

### 7.1 Real-World Reference: February 6, 2023, Kahramanmaraş Earthquake

> **Real Incident:** On February 6, 2023, a 7.4 magnitude earthquake struck the Pazarcık district of Kahramanmaraş, Turkey. The Ministry of Interior declared a **Level 4 alarm** — the highest level in the Turkish Disaster Response Plan, which includes a call for international assistance. AFAD, via the Ministry of Foreign Affairs, issued a call for international urban search and rescue assistance through the **ERCC (Emergency Response Coordination Centre)**.
>
> The earthquake was intensely felt in surrounding provinces, primarily **Kahramanmaraş, Hatay, Osmaniye, Gaziantep, Şanlıurfa, Diyarbakır, Malatya, and Adana**. 32 aftershocks were recorded, the largest being 6.6 magnitude.

**How does GemmAid solve problems in this real-world scenario?**

Observed problems in the field and GemmAid's solutions:

| Real Problem | GemmAid Solution |
|-------------|----------------|
| 112 emergency lines were locked down in the first minutes, thousands of calls went unanswered | Parallel messaging channel via Telegram — works even on extremely low bandwidths like 2G/EDGE/GPRS |
| Rescue teams from Azerbaijan, Pakistan, and Qatar couldn't coordinate due to lack of a common language | 140+ language support: translates messages from any language into a Turkish coordinator note |
| Multiple teams arrived at some locations while other locations waited for hours | Accurately distributes resources via urgency ranking and location extraction on the Dashboard |
| WhatsApp/Telegram messages could not be processed systematically | Every message is automatically converted into a structured JSON case card |
| International teams arriving via ERCC wrote field reports in different languages | French/English/Arabic reports are automatically triaged and translated into Turkish notes |
| In an earthquake affecting 10 provinces, it was unclear which province had what level of demand | Automatic prioritization via location text extraction + urgency score |

### 7.2 Demo Scenario: Malatya Earthquake Simulation

**Scenario context:** A Level 4 alarm is declared after a 7.4 magnitude earthquake. There is destruction in 8 provinces. International search and rescue teams (France, UK, Azerbaijan) are in the field. Thousands of Syrian and Iraqi refugees also live in the affected areas. 112 lines are locked down, 4.5G/LTE cellular base stations have collapsed. Only the old **2G (EDGE/GPRS)** infrastructure is partially standing, creating a "fragile internet" environment.

GemmAid operates with a "Local-First" architecture under these extraordinary conditions. Only text messages (a few KBs) reach Telegram over the weak 2G network. The device at the coordination center performs the heavy Gemma 4 inference **on its own processor (on-device)** without relying on the internet. The Dashboard is broadcasted on the local area network (LAN) which does not require an external internet connection.

---

#### Scenario A — Citizen Reaching Out to Rescue Team (Active Call for Help)

**Profile:** Ahmet, 35, Turkish citizen, managed to get down to the street from the 3rd floor but his neighbor is under the debris

**Message (Turkish):**
```
Komşumuz enkaz altında kaldı, Atatürk Caddesi 3. kat, nefes güçlüğü var, biz 3 kişiyiz
(Our neighbor is trapped under the debris, Atatürk Street 3rd floor, having difficulty breathing, there are 3 of us)
```

**GemmAid Triage Output:**
```json
{
  "olay_tipi": "enkaz_alti",
  "aciliyet_skoru": 1,
  "konum_metni": "Atatürk Caddesi, 3. kat",
  "etkilenen_kisi_sayisi": 3,
  "semptomlar": ["nefes_guclugu"],
  "gerekli_ekip": ["arama_kurtarma", "tibbi"],
  "kaynak_dil": "tr",
  "koordinator_notu": "Enkaz altında solunum güçlüğü var, arama kurtarma ve tıbbi ekip acil gerekli",
  "vatandasa_yanit": "Yardım ekiplerine bilgi iletildi. Lütfen sakin olun ve güvenli bir bölgede bekleyin."
}
```

**Coordinator Action:** Appears as 🔴 CRITICAL on the Dashboard. Search & rescue and medical teams are dispatched.

---

#### Scenario B — Person Waiting for Help (Passive/Desperate)

**Profile:** Fatima, 28, Syrian refugee, speaks Arabic, her family's building collapsed, waiting outside on the street

**Message (Arabic):**
```
جارنا عالق تحت الأنقاض، الطابق الثالث، شارع أتاتورك، يتنفس بصعوبة، نحن ثلاثة أشخاص بحاجة للمساعدة، لا نستطيع التواصل مع أحد
(Our neighbor is trapped under the debris, 3rd floor, Atatürk Street, having difficulty breathing, we are 3 people in need of help, we can't contact anyone)
```

**GemmAid Triage Output:**
```json
{
  "olay_tipi": "enkaz_alti",
  "aciliyet_skoru": 1,
  "konum_metni": "Atatürk Caddesi, 3. kat",
  "etkilenen_kisi_sayisi": 3,
  "semptomlar": ["nefes_guclugu"],
  "gerekli_ekip": ["arama_kurtarma", "tibbi"],
  "kaynak_dil": "ar",
  "koordinator_notu": "Arapça konuşan aile, enkaz altında solunum semptomu, iletişim kuramıyorlar. Öncelikli müdahale ve çevirmen gerekli.",
  "vatandasa_yanit": "تم إرسال المعلومات لفريق الإنقاذ. الرجاء البقاء هادئين والانتظار."
}
```

**Difference:** The system automatically detected the language (Arabic). The coordinator note was written in Turkish — so the Turkish coordinator understands it. The need for a translator was noted.

---

#### Scenario C — Evacuation After Flooding (Family with Children)

**Profile:** Elif, 32, took shelter on the upper floor with her 2 children, water is rising

**Message (Turkish):**
```
Evimiz sular altında, 2 çocuğumuz var, üst kata çıktık ama su yükseliyor, Kemaliye Mahallesi, lütfen yardım
(Our house is flooded, we have 2 children, we went to the upper floor but the water is rising, Kemaliye Neighborhood, please help)
```

**GemmAid Triage Output:**
```json
{
  "olay_tipi": "tahliye",
  "aciliyet_skoru": 2,
  "konum_metni": "Kemaliye Mahallesi",
  "etkilenen_kisi_sayisi": 3,
  "semptomlar": [],
  "gerekli_ekip": ["tahliye"],
  "kaynak_dil": "tr",
  "koordinator_notu": "Sel baskını, çocuklu aile üst katta mahsur. Su seviyesi yükseliyor, tahliye ekibi öncelikli.",
  "vatandasa_yanit": "Tahliye ekipleri yönlendirildi. Lütfen mümkünse daha yüksek bir kata çıkın ve telefonunuzun şarjına dikkat edin."
}
```

---

#### Scenario D — Foreign Rescue Team Coordination

**Profile:** Jean-Pierre, French USAR team coordinator, sending a situation report from the field

**Message (French):**
```
Nous avons localisé 5 survivants dans un immeuble effondré, rue Cumhuriyet. Deux personnes ont des fractures, une personne inconsciente. Besoin d'équipe médicale urgente.
(We located 5 survivors in a collapsed building on Cumhuriyet Street. Two people have fractures, one person is unconscious. Urgent medical team needed.)
```

**GemmAid Triage Output:**
```json
{
  "olay_tipi": "enkaz_alti",
  "aciliyet_skoru": 1,
  "konum_metni": "Cumhuriyet Caddesi",
  "etkilenen_kisi_sayisi": 5,
  "semptomlar": ["kirik", "bilinc_kaybi"],
  "gerekli_ekip": ["tibbi", "arama_kurtarma"],
  "kaynak_dil": "fr",
  "koordinator_notu": "Fransız kurtarma ekibi 5 kişi tespit etmiş. Bilinç kaybı ve kırık mevcut. Acil tıbbi destek yönlendirilmeli.",
  "vatandasa_yanit": "Les équipes médicales et de secours ont été alertées. Veuillez rester sur place si c'est sûr et signaler votre position."
}
```

---

#### Scenario E — Refugee Patient Health Crisis

**Profile:** Mohammad, 55, Iraqi refugee, experiencing chest pain, facing a language barrier in the hospital emergency room

**Message (Arabic):**
```
عندي ألم شديد في صدري منذ ساعتين، أتنفس بصعوبة، أنا في المستشفى لكن لا أحد يفهمني
(I have severe chest pain for 2 hours, I have difficulty breathing, I am in the hospital but no one understands me)
```

**GemmAid Triage Output:**
```json
{
  "olay_tipi": "tibbi_acil",
  "aciliyet_skoru": 1,
  "konum_metni": "Hastane acil servisi",
  "etkilenen_kisi_sayisi": 1,
  "semptomlar": ["gogus_agrisi", "nefes_guclugu"],
  "gerekli_ekip": ["tibbi"],
  "kaynak_dil": "ar",
  "koordinator_notu": "Kardiyak semptom şüphesi. Hasta hastanede ancak dil bariyeri var. Acil Arapça çevirmen ve kardiyoloji değerlendirmesi gerekli.",
  "vatandasa_yanit": "تم إخطار الفريق الطبي. الرجاء البقاء هادئين والانتظار بدون الحراكة."
}
```

---

#### Scenario F — Resource Need (48 Hours Post-Earthquake)

**Profile:** Kurdish community leader, with a group of 50 people in a shelter

**Message (Kurdish/Turkish mixed):**
```
Em 50 kes in, zarokên me hene, av û nan tune, em li parkê ne, ji kerema xwe alîkariyê bişînin. Çadır ve battaniye lazım
(We are 50 people, we have children, there is no water or bread, we are waiting in the park, please send help. Tents and blankets needed)
```

**GemmAid Triage Output:**
```json
{
  "olay_tipi": "kaynak_ihtiyaci",
  "aciliyet_skoru": 2,
  "konum_metni": "Park alanı",
  "etkilenen_kisi_sayisi": 50,
  "semptomlar": [],
  "gerekli_ekip": ["lojistik"],
  "kaynak_dil": "ku",
  "koordinator_notu": "50 kişilik grup, çocuklar dahil. Temel ihtiyaçlar: su, gıda, çadır, battaniye. Lojistik ekip yönlendirilmeli.",
  "vatandasa_yanit": "Alîkarî hatin. Ji kerema xwe li ciyekî ewle bimînin û agahiya zarokên xwe bidin me."
}
```

---

#### Scenario G — English Speaking Tourist

**Profile:** Sarah, 26, English tourist, hotel collapsed, injured her leg

**Message (English):**
```
I'm trapped in my hotel room, 4th floor, the building partially collapsed. My leg is injured and I can't move. Hotel Malatya Grand, room 412. Please send help immediately.
```

**GemmAid Triage Output:**
```json
{
  "olay_tipi": "enkaz_alti",
  "aciliyet_skoru": 1,
  "konum_metni": "Hotel Malatya Grand, 4. kat, oda 412",
  "etkilenen_kisi_sayisi": 1,
  "semptomlar": ["bacak_yaralanmasi", "hareket_kisitliligi"],
  "gerekli_ekip": ["arama_kurtarma", "tibbi"],
  "kaynak_dil": "en",
  "koordinator_notu": "Otel çökmesi, 4. kat oda 412. Bacak yaralanması, hareket edemiyor. Arama kurtarma ve tıbbi ekip acil.",
  "vatandasa_yanit": "Help is on the way. Please stay calm, avoid moving your leg, and make noise if you hear rescuers nearby."
}
```

---

#### Scenario H — Azerbaijan Search and Rescue Team (ERCC Coordination)

**Profile:** Elçin, 40, Azerbaijan MES (Ministry of Emergency Situations) USAR team commander. Arrived in the field via the ERCC channel, working in Hatay, sending a field report in Azerbaijani

**Message (Azerbaijani):**
```
Hatay Antakya mərkəzdə 8 mərtəbəli bina çöküb. Alt mərtəbələrdə sağ qalanlar var, səslər eşidirik. 3 nəfəri çıxardıq, 2-si ağır yaralıdır. Tibbi yardım və əlavə avadanlıq lazımdır. GPS: 36.2025, 36.1613
(An 8-story building collapsed in Hatay Antakya center. There are survivors on the lower floors, we hear voices. We extracted 3 people, 2 are seriously injured. Medical help and additional equipment needed.)
```

**GemmAid Triage Output:**
```json
{
  "olay_tipi": "enkaz_alti",
  "aciliyet_skoru": 1,
  "konum_metni": "Hatay Antakya merkez, 8 katlı bina, GPS: 36.2025, 36.1613",
  "etkilenen_kisi_sayisi": 5,
  "semptomlar": ["agir_yaralanma"],
  "gerekli_ekip": ["arama_kurtarma", "tibbi"],
  "kaynak_dil": "az",
  "koordinator_notu": "Azerbaycan USAR ekibi enkaz altında hayat belirtisi tespit etmiş. 3 kişi kurtarıldı, 2 ağır yaralı. Tıbbi destek ve ek arama-kurtarma ekipmanı acil yönlendirilmeli. GPS koordinatı mevcut.",
  "vatandasa_yanit": "Tibbi yardım və xilasetmə qrupları yönləndirilib. Zəhmət olmasa, təhlükəsiz zonada gözləyin."
}
```

**GemmAid's value add:** Azerbaijani → Turkish coordinator note. The language bridge between international teams and the local coordinator was established automatically.

---

#### Scenario I — Multi-Province AFAD Coordination (Level 4 Alarm)

**Profile:** Mehmet, 45, Diyarbakır AFAD provincial directorate field coordinator. Sending a situation report to the center

**Message (Turkish):**
```
Diyarbakır Sur ilçesinde 12 bina hasarlı, 3 bina tamamen çökmüş. Tahmini 200 kişi etkilendi. 2 sahadaki ekiplerimiz yetersiz kalıyor. Gaziantep ve Şanlıurfa'dan takviye ekip istiyoruz. Hastane acil servisi dolu, sahra hastanesi kurulması gerekiyor
(In Diyarbakır Sur district, 12 buildings are damaged, 3 buildings completely collapsed. An estimated 200 people are affected. Our 2 field teams are insufficient. We request reinforcement teams from Gaziantep and Şanlıurfa. The hospital emergency room is full, a field hospital needs to be established)
```

**GemmAid Triage Output:**
```json
{
  "olay_tipi": "enkaz_alti",
  "aciliyet_skoru": 1,
  "konum_metni": "Diyarbakır Sur ilçesi",
  "etkilenen_kisi_sayisi": 200,
  "semptomlar": [],
  "gerekli_ekip": ["arama_kurtarma", "tibbi", "lojistik"],
  "kaynak_dil": "tr",
  "koordinator_notu": "Çok kritik: 200 kişi etkilenmiş, 3 bina çökmüş. Mevcut 2 ekip yetersiz. İller arası takviye gerekli. Sahra hastanesi kurulması acil. Seviye 4 alarm kapsamında ERCC kaynaklarından destek değerlendirilmeli.",
  "vatandasa_yanit": "Takviye ekipler ve sahra hastanesi için koordinasyon başlatıldı. Lütfen mevcut kaynakları koruyun ve yeni talepleri bu kanal üzerinden bildirin."
}
```

---

### 7.3 Scenario Timeline (Level 4 Earthquake)

```
EARTHQUAKE STRIKES (T+0) — 7.4 magnitude, Kahramanmaraş/Pazarcık
    │
    │ Initial shock. GSM infrastructure partially damaged. 112 lines saturate within seconds.
    │ Level 4 alarm declared → ERCC call for international help
    │
    ├── T+0-5min: Communication breakdown and Fragile Internet
    │   └── 4.5G collapses, 112 locks down. However, 2G/EDGE cellular network allows text transmission.
    │   └── Telegram delivers messages to the GemmAid center even on low bandwidth.
    │
    ├── T+5-30min: First cries for help
    │   ├── Scenario A (Ahmet, TR) — Active: Neighbor under debris, personally calling for help
    │   ├── Scenario B (Fatima, AR) — Passive: Syrian family, cannot reach anyone, waiting
    │   └── Scenario G (Sarah, EN) — Tourist: Hotel collapsed, asking for help in English
    │
    │   >>> First 🔴 CRITICAL cases appear on the GemmAid Dashboard
    │   >>> Coordinator dispatches the nearest search and rescue teams
    │
    ├── T+30min-2hours: National/international teams in the field
    │   ├── Scenario D (Jean-Pierre, FR) — French USAR field report
    │   ├── Scenario H (Elçin, AZ) — Azerbaijan MES team, rescuing in Hatay
    │   └── Scenario E (Mohammad, AR) — Language barrier in hospital, refugee patient
    │
    │   >>> ERCC coordination active — multilingual reports centralized via GemmAid
    │   >>> Turkish coordinator reads all international team reports in Turkish
    │
    ├── T+2-6hours: Secondary threats + multi-province coordination
    │   ├── Scenario C (Elif, TR) — Post-earthquake pipe burst → flooding
    │   └── Scenario I (Mehmet, TR) — Diyarbakır AFAD requests reinforcements
    │
    │   >>> Requests from 8 provinces listed on the Dashboard by priority
    │
    ├── T+6-24hours: Aftershocks + ongoing rescue operations
    │   └── 32 aftershocks (largest 6.6) — secondary collapses
    │   └── New messages arrive, GemmAid produces continuous triage
    │
    └── T+24-72hours: Resource and shelter needs
        └── Scenario F (Community leader, KU) — 50 people: water, tents, blankets
        └── Humanitarian logistics coordination

CONCLUSION: GemmAid provided uninterrupted triage across 9 different scenarios, in 7 different languages (TR/AR/FR/EN/KU/AZ/+), under Level 4 earthquake conditions.
```

---

## 8. Step-by-Step Execution Guide

### 8.1 Pre-Setup (Done Once)

**Step 1 — Navigate to the project directory:**
```bash
cd /home/sems/Documents/GitHub/kaggle-gemma4_gemmaid
```

**Step 2 — Automatic installation (recommended):**
```bash
bash deploy/setup.sh
```
> This script installs llama-cpp-python with OpenBLAS and downloads the Gemma 4 GGUF model.

Manual installation:
```bash
pip install -r requirements.txt
CMAKE_ARGS='-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS' pip install llama-cpp-python
```

**Step 3 — Create the .env file:**
```bash
cp .env.example .env
nano .env
```

**Step 4 — Configure the .env file:**

Default (llama.cpp + Gemma 4 E4B GGUF, on-device):
```env
GEMMAID_BACKEND=local
LOCAL_N_THREADS=4
```
> Works even if the internet in the disaster zone goes down — inference is done entirely on the CPU.

Optional — Cloud (Google AI API):
```env
GEMMAID_BACKEND=gemini
GEMINI_API_KEY=YOUR_GEMINI_KEY_HERE
```
> Gemini API Key: https://aistudio.google.com/apikey

**Step 5 — Download the GGUF model:**
```bash
python scripts/download_model.py
```
> Downloads ~2.5 GB. `deploy/setup.sh` does this automatically.

---

### 8.2 Start and Test the System

#### Method A: Single Command (Recommended)

```bash
bash deploy/start.sh
```
This command starts the API + Dashboard. If a Telegram token is present, the bot also starts.

#### Method B: Separately (For Debugging)

**Terminal 1 — Start API:**
```bash
cd /home/sems/Documents/GitHub/kaggle-gemma4_gemmaid
python api/api.py
```
Expected output:
```
[Config] Backend: local
[Config] API: 0.0.0.0:8000
[Config] Model Path: ./models/gemma-4-E4B-it-Q4_K_M.gguf
[Config] Threads: 4, Context: 2048
✅ GemmAid API started (backend=local, port=8000)
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Terminal 2 — Start Dashboard:**
```bash
python dashboard/dashboard.py
```
Open in browser: **http://localhost:7860**

**Terminal 3 — Run Tests:**
```bash
python scripts/test_triage.py
```

---

### 8.3 Manually Test the API

**Health check:**
```bash
curl http://localhost:8000/health
```

**Single triage test:**
```bash
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"message": "Komşumuz enkaz altında, Atatürk Caddesi, nefes güçlüğü var"}'
```

**Arabic test:**
```bash
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"message": "جارنا عالق تحت الأنقاض، يتنفس بصعوبة"}'
```

**Swagger UI:** Open **http://localhost:8000/docs** in your browser.

---

### 8.4 Telegram Bot Setup

Detailed guide: **docs/TELEGRAM_SETUP_EN.md**

Brief summary:
1. `@BotFather` → `/newbot` → Get token
2. Add `TELEGRAM_TOKEN=xxx` to `.env`
3. Run `python bot/bot.py`
4. Send a message to your bot on Telegram

> **Important:** The API must be running while the bot is running.

---

### 8.5 Test the Dashboard

1. Open **http://localhost:7860** in your browser
2. Click the "🔍 API Check" button → It should say "✅ API is online"
3. Perform a manual triage test or click the "🎬 Run Demo" button

---

### 8.6 Running on Kaggle

1. Go to https://kaggle.com → "New Notebook"
2. Upload the `optional/kaggle/gemmaid_notebook.ipynb` file
3. Runtime: GPU (T4/P100)
4. Run the cells sequentially

---

### 8.7 Troubleshooting

| Problem | Solution |
|-------|-------|
| `Model not found` | Download with `python scripts/download_model.py` |
| `llama-cpp-python import error` | `pip install llama-cpp-python` |
| `No API connection` | Run `python api/api.py` |
| Bot says "TELEGRAM_TOKEN is not set" | Add token to `.env` (guide: docs/TELEGRAM_SETUP_EN.md) |
| Local model is too slow | Increase `LOCAL_N_THREADS` or use `BACKEND=gemini` |
| Out of memory | Use `LOCAL_N_CTX=1024` or use a Q2_K model |
| Health check | Run `bash deploy/health_check.sh` |

---

*GemmAid Technical Documentation | May 18, 2026*
*Kaggle Gemma 4 Good Hackathon — Deadline: May 18, 2026*
