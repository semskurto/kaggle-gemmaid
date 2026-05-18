#!/usr/bin/env python3
"""GemmAid Triage API — FastAPI Servisi

Desteklenen backend'ler (GEMMAID_BACKEND env değişkeni ile seç):
  local        → llama-cpp-python + Gemma 4 E4B GGUF (CPU, VARSAYILAN)
  transformers → HuggingFace Transformers pipeline (GPU/CPU, Kaggle)
  gemini       → Google AI API + Gemma 4 26B MoE (bulut)

Başlatma:
  python api/api.py                              # local (varsayılan)
  GEMMAID_BACKEND=transformers python api/api.py # HF transformers
  GEMMAID_BACKEND=gemini python api/api.py       # bulut
"""
import json
import logging
import sys
import os
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Proje kökünü sys.path'e ekle
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import (
    BACKEND, API_HOST, API_PORT,
    GEMINI_API_KEY, GEMINI_MODEL,
    TRIAGE_SYSTEM_PROMPT,
    print_config,
)
from core.triage_schema import parse_triage_json
from core.database import init_db, save_case, get_cases, get_stats, clear_cases, get_latest_case_by_telegram_id, append_message_to_case, close_case, delete_case

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("gemmaid.api")


# ── Lifespan (startup/shutdown) ───────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama başlatma ve kapatma işlemleri."""
    # Startup
    print_config()
    init_db()
    if BACKEND in ("local", "transformers"):
        import threading
        def preload():
            try:
                if BACKEND == "local":
                    from local_llm.inference import preload_model
                    preload_model()
                else:
                    from local_llm.transformers_inference import preload_model
                    preload_model()
            except Exception as e:
                log.warning(f"Model ön yükleme başarısız: {e}")
        threading.Thread(target=preload, daemon=True).start()
    log.info(f"✅ GemmAid API başlatıldı (backend={BACKEND}, port={API_PORT})")
    yield
    # Shutdown (gerekirse temizlik burada)


# ── FastAPI ──────────────────────────────────────────────────
app = FastAPI(
    title="GemmAid Triage API",
    description="Çok dilli acil triaj sistemi — Gemma 4 destekli (llama.cpp)",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Backend Fonksiyonları ────────────────────────────────────
def call_gemini(message: str, target_lang: str = "en") -> dict:
    """Google Gemini API ile triaj."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY env değişkeni ayarlanmamış")
    try:
        import google.generativeai as genai
        from core.config import get_triage_system_prompt
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            system_instruction=get_triage_system_prompt(target_lang),
        )
        resp = model.generate_content(
            f"Kriz mesajı: {message}",
            generation_config={"temperature": 0.1, "max_output_tokens": 512},
        )
        return parse_triage_json(resp.text)
    except Exception as e:
        log.error(f"[Gemini] Hata: {e}")
        raise


def call_local(message: str, target_lang: str = "en") -> dict:
    """Lokal llama-cpp-python ile triaj (birincil backend)."""
    from local_llm.inference import call_local as _call
    return _call(message, target_lang=target_lang)


def call_transformers(message: str, target_lang: str = "en") -> dict:
    """HuggingFace transformers ile triaj (Kaggle uyumlu)."""
    from local_llm.transformers_inference import call_transformers as _call
    return _call(message, target_lang=target_lang)


def run_triage(message: str, target_lang: str = "en") -> dict:
    """Seçili backend ile triaj çalıştır. inference_location alanı ekler."""
    dispatch = {
        "local":        call_local,         # llama-cpp-python (VARSAYILAN)
        "transformers": call_transformers,  # HF pipeline
        "gemini":       call_gemini,        # Google AI API
    }
    fn = dispatch.get(BACKEND, call_local)
    result = fn(message, target_lang=target_lang)

    # inference_location varsayılan değerler
    if "inference_location" not in result:
        loc_map = {
            "local":        "on_device",
            "transformers": "on_device",
            "gemini":       "cloud",
        }
        result["inference_location"] = loc_map.get(BACKEND, "unknown")

    return result


# ── Pydantic Modeller ────────────────────────────────────────
class TriageRequest(BaseModel):
    message: str
    target_lang: str = "en"
    sender_name: Optional[str] = None
    telegram_id: Optional[str] = None
    telegram_username: Optional[str] = None

    model_config = {"json_schema_extra": {
        "example": {"message": "Komşumuz enkaz altında, Atatürk Caddesi 3. kat", "target_lang": "en"}
    }}


# ── Endpoints ────────────────────────────────────────────────
class ReplyRequest(BaseModel):
    case_id: int
    coordinator_message: str

@app.post("/triage", summary="Kriz mesajını triaj et")
async def triage(req: TriageRequest):
    """
    Ham kriz mesajını alıp yapılandırılmış triaj JSON'u döndürür.
    Mesaj herhangi bir dilde olabilir (TR, AR, EN, FR, KU, ...).
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Mesaj boş olamaz")

    message_to_triage = req.message
    
    # Kullanıcının mevcut vakası varsa önceki mesajları bağlam olarak LLM'e ver
    if req.telegram_id:
        existing = get_latest_case_by_telegram_id(req.telegram_id)
        if existing:
            now_str = datetime.now(timezone.utc).strftime("%H:%M")
            message_to_triage = f"{existing['raw_message']}\n\n[{now_str}] Yeni Mesaj: {req.message}"
            
    log.info(f"[{BACKEND}] Triaj ({req.target_lang}): {message_to_triage[:60]!r}")

    try:
        result = run_triage(message_to_triage, target_lang=req.target_lang)
        
        # Override with known Telegram identity if present
        if req.sender_name and result.get("gonderen_kisi") in ["Bilinmiyor", "", None]:
            result["gonderen_kisi"] = req.sender_name
        if req.telegram_id and result.get("iletisim_bilgisi") in ["Bilinmiyor", "", None]:
            result["iletisim_bilgisi"] = f"Telegram ID: {req.telegram_id}"
            
    except Exception as e:
        log.error(f"Triaj hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Veritabanına kaydet
    case_id = save_case(
        result,
        message_to_triage,
        backend=BACKEND,
        sender_name=req.sender_name or "",
        telegram_id=req.telegram_id or "",
        telegram_username=req.telegram_username or "",
    )
    result["id"] = case_id
    result["raw_message"] = req.message
    result["backend"] = BACKEND
    result.setdefault("inference_location", "on_device" if BACKEND != "gemini" else "cloud")
    result["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return result


def _generate_reply_with_llm(coordinator_message: str, current_prompt: str, user_lang: str) -> str:
    """Mesajı vatandaşın diline çevirip empatiyle harmanlar."""
    prompt = f"""Bir afet koordinasyon memuru afetzedeye şu mesajı iletmek istiyor:
"{coordinator_message}"

Senin görevin bu mesajı vatandaşın konuştuğu dile ({user_lang}) çevirmek.
Bu bir kriz durumudur. Resmi, net ve empati kuran bir üslup kullan.
Asla tıbbi veya kurtarma garantisi verme. Sadece aşağıdaki formata ve yukarıdaki mesaja bağlı kalarak sadece çeviriyi döndür. Başka hiçbir açıklama yazma.
"""
    dispatch = {
        "local": call_local_raw if "call_local_raw" in globals() else None,
        "transformers": call_transformers_raw if "call_transformers_raw" in globals() else None,
        "gemini": call_gemini_raw if "call_gemini_raw" in globals() else None,
    }
    # For simplicity if raw text endpoints are missing, we can construct a dummy json schema or just require generating text.
    pass

@app.post("/reply_to_case", summary="Vatandaşa AI destekli mesaj gönder")
async def reply_to_case(req: ReplyRequest):
    """
    Koordinatörün mesajını alır, kullanıcının diline çevirir ve (eğer Telegram kullanıcısıysa)
    Telegram üzerinden vatandaşa gönderir.
    """
    cases = get_cases(limit=1000)
    case = next((c for c in cases if c.get("id") == req.case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail="Vaka bulunamadı")

    target_lang = case.get("kaynak_dil", "tr")
    raw_message = case.get("raw_message", "")
    
    # 1. Gemma 4 ile mesajı translate/refine etme
    system_instruction = f"Bir kriz koordinatörü şu cevabı yazdı: '{req.coordinator_message}'. Bu cevabı '{target_lang}' diline profesyonel ve empatik bir dille çevir. Sadece hedef dildeki çeviriyi ver."
    
    # Simple fallback mechanism to rely on the existing backend (we'll implement basic raw text calls)
    try:
        if BACKEND == "gemini":
             import google.generativeai as genai
             model = genai.GenerativeModel("gemma-4-26b-a4b-it", system_instruction=system_instruction)
             resp = model.generate_content("Cevabı sağla.")
             final_message = resp.text.strip()
        elif BACKEND in ("local", "transformers"):
             if BACKEND == "local":
                 from local_llm.inference import _get_model
                 lm = _get_model()
                 output = lm.create_chat_completion(
                     messages=[
                         {"role": "system", "content": system_instruction},
                         {"role": "user", "content": "Cevabı sağla."}
                     ],
                     max_tokens=256,
                     temperature=0.1
                 )
                 final_message = output["choices"][0]["message"]["content"].strip()
             else:
                 final_message = f"[Çeviri Simulasyonu - {target_lang}]: {req.coordinator_message}"
    except Exception as e:
        log.error(f"AI Çeviri Hatası: {e}")
        final_message = req.coordinator_message # Fallback to original
        
    # JSON objesi vb var mı diye basitleştirici temizlik
    if "{" in final_message and "}" in final_message:
        # if it hallucinated json
        final_message = final_message.replace("{", "").replace("}", "").strip()

    # 2. Telegram üzerinden iade (Eğer telegram_id varsa)
    telegram_id = case.get("telegram_id")
    telegram_status = "Telegram IDs bulunamadı (API/manuel kayıt)"
    
    if telegram_id:
        from core.config import TELEGRAM_TOKEN
        import requests
        if TELEGRAM_TOKEN:
            try:
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                resp = requests.post(url, json={
                    "chat_id": telegram_id,
                    "text": f"🚨 *Koordinasyon Merkezi Öncelikli Mesajı*\n\n{final_message}",
                    "parse_mode": "Markdown"
                })
                if resp.status_code == 200:
                    telegram_status = "✅ Mesaj Telegram üzerinden vatandaşa başarıyla iletildi."
                else:
                    telegram_status = f"❌ Telegram iletim hatası: {resp.text}"
            except Exception as e:
                telegram_status = f"❌ Telegram API bağlanamadı: {e}"
        else:
             telegram_status = "⚠️ TELEGRAM_TOKEN ayarlı değil."
             
    # Koordinatör yanıtını veritabanına ekle (Bağlam kaybolmasın diye)
    append_message_to_case(req.case_id, f"Koordinatör ({target_lang}): {final_message}")
             
    return {
        "original_message": req.coordinator_message,
        "translated_message": final_message,
        "language": target_lang,
        "delivery_status": telegram_status
    }

@app.get("/cases", summary="Tüm vakaları listele")
async def list_cases(
    limit: int = Query(default=100, ge=1, le=500),
    min_aciliyet: int = Query(default=None, ge=1, le=5, description="Bu değerden düşük aciliyet skorlu vakalar"),
):
    """Vakaları aciliyet sırasına göre döndür (1=kritik önce)."""
    return get_cases(limit=limit, min_aciliyet=min_aciliyet)


@app.get("/stats", summary="Özet istatistikler")
async def stats():
    """Dashboard için vaka istatistikleri."""
    return get_stats()


@app.get("/health", summary="API sağlık durumu")
async def health():
    """API ve backend durumu."""
    info = {
        "status": "ok",
        "backend": BACKEND,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if BACKEND == "local":
        try:
            from local_llm.inference import get_model_status
            info["model"] = get_model_status()
        except Exception as e:
            info["model"] = {"error": str(e)}
    return info


@app.delete("/cases", summary="Tüm vakaları sil (sadece test için)")
async def delete_cases():
    """Demo sıfırlama: tüm vakaları sil."""
    deleted = clear_cases()
    return {"deleted": deleted, "message": f"{deleted} vaka silindi"}


@app.post("/cases/{case_id}/close", summary="Vakayı kapat")
async def api_close_case(case_id: int):
    """Vakanın durumunu 'closed' (kapalı) yapar."""
    success = close_case(case_id)
    if not success:
        raise HTTPException(status_code=404, detail="Vaka bulunamadı")
    return {"status": "success", "message": f"Vaka {case_id} kapatıldı."}


@app.delete("/cases/{case_id}", summary="Tek bir vakayı sil")
async def api_delete_case(case_id: int):
    """Vakayı tamamen siler."""
    success = delete_case(case_id)
    if not success:
        raise HTTPException(status_code=404, detail="Vaka bulunamadı")
    return {"status": "success", "message": f"Vaka {case_id} silindi."}


# ── Demo Endpoint'i ──────────────────────────────────────────
@app.get("/demo", summary="Demo senaryolarını çalıştır")
async def run_demo():
    """4 dilde demo senaryosu çalıştır (TR/AR/FR/EN) ve sonuçları döndür."""
    scenarios = [
        # Skor 1 — Kritik / Hayati Tehlike
        ("TR",  "Komşumuz enkaz altında kaldı, Atatürk Caddesi 3. kat, nefes güçlüğü var, 3 kişiyiz"),
        ("AR",  "جارنا عالق تحت الأنقاض يتنفس بصعوبة شارع أتاتورك مدينة هطاي"),
        ("EN",  "Multi-vehicle crash on highway, 2 cars on fire, people trapped inside, km 47 near Ankara"),
        ("FA",  "آتش سوزی در ساختمان چهار طبقه، مردم در طبقه سوم گیر کرده‌اند، آتش‌نشانی را خبر کنید"),

        # Skor 2 — Yüksek Öncelik
        ("FR",  "J'ai une douleur intense dans la poitrine depuis 2 heures, j'ai du mal à respirer, je suis seul à la maison"),
        ("EN",  "House flooded, 2 children trapped on roof, water rising fast, Kemaliye district, no boat available"),
        ("DE",  "Meine Mutter hat einen Schlaganfall, sie kann nicht sprechen und eine Seite ihres Körpers ist gelähmt, wir sind in der Hauptstraße 12"),
        ("KU",  "Gundê me ji ber berfê girtiye, 20 malbat hene, xwarin û germî tune ye, nexweş jî hene"),

        # Skor 3 — Orta Risk
        ("TR",  "Yaşlı komşumuz 3 gündür evde tek başına kilitli kaldı, kapıyı açamıyoruz, ilaçlarına erişemiyor, Gültepe mahallesi"),
        ("ES",  "Hay una fuga de gas en el edificio, huele muy fuerte pero no veo llamas, la gente está nerviosa y quiere salir"),
        ("UK",  "У нас немає електрики та тепла вже 4 дні, у нас є маленькі діти та літні люди, потрібні ковдри та їжа"),

        # Skor 4 — Düşük Öncelik / Kaynak İhtiyacı
        ("EN",  "We are a group of 30 volunteers at community center in district 5. We have food and water but need medical supplies and blankets for 50 displaced people"),
        ("RU",  "В нашем районе нет чистой питьевой воды уже 2 дня, около 200 семей, дети и пожилые люди страдают, нужны бутылки с водой"),

        # Skor 5 — Düşük / Bilgi/Destek Talebi
        ("TR",  "Afet bölgesine yakın bir köydeyiz, şu an tehlike yok ama ne zaman tahliye edileceğimizi bilmek istiyoruz, telefon hatları çok zayıf"),
        ("FR",  "Nous sommes en sécurité mais très stressés, nous avons perdu contact avec notre famille à Iskenderun depuis hier soir, comment les retrouver"),
    ]
    results = []
    for lang, msg in scenarios:
        try:
            result = run_triage(msg)
            case_id = save_case(result, msg, backend=BACKEND)
            results.append({
                "lang": lang,
                "message": msg,
                "triage": result,
                "case_id": case_id,
            })
        except Exception as e:
            results.append({"lang": lang, "message": msg, "error": str(e)})
    return {"demo_results": results, "backend": BACKEND}


# ── Ana Giriş ────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        reload=False,
        log_level="info",
    )
