#!/usr/bin/env python3
"""GemmAid Koordinatör Dashboard — Gradio

Özellikler:
  - Gerçek zamanlı vaka listesi (30 sn auto-refresh)
  - Özet istatistik kartları
  - Manuel triaj testi
  - Vaka ayrıntı paneli
  - 4 dil demo senaryosu
  - Çift dil desteği (İngilizce/Türkçe)

Başlatma:
  python dashboard/dashboard.py
"""
import requests
import json
import sys
import httpx
import gradio as gr
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.config import API_BASE_URL, DASHBOARD_PORT

# ── Sabitler ─────────────────────────────────────────────────
CASES_URL  = f"{API_BASE_URL}/cases"
TRIAGE_URL = f"{API_BASE_URL}/triage"
STATS_URL  = f"{API_BASE_URL}/stats"
HEALTH_URL = f"{API_BASE_URL}/health"
DEMO_URL   = f"{API_BASE_URL}/demo"

# UI Dilleri İçin Sözlük
UI_TEXT = {
    "English": {
        "header": "# 🆘 GemmAid — Emergency Coordination Center\n**Gemma 4 powered multilingual triage system** | Kaggle Gemma 4 Good Hackathon",
        "api_status_label": "🔌 System Status",
        "check_api": "🔍 Check API",
        "stat_total": "📋 Total Cases",
        "stat_critical": "🔴 Critical",
        "stat_high": "🟠 High Priority",
        "stat_wait": "⚪ Can Wait",
        "active_cases_header": "## 📋 Active Cases",
        "case_status_label": "Status",
        "table_headers": ["#", "Urgency", "Event Type", "Contact", "Location", "People", "Missing", "Team", "Lang", "Note", "Time"],
        "btn_refresh": "🔄 Refresh",
        "btn_demo": "🎬 Run Demo",
        "btn_clear": "🗑️ Clear",
        "manual_triage_header": "## ✏️ Manual Triage Test",
        "msg_input_label": "Crisis Message",
        "msg_input_placeholder": "Type a crisis message in any language...\nTR / AR / FR / EN / KU supported",
        "json_output_label": "📄 JSON Output",
        "btn_triage": "🚨 Start Triage",
        "details_panel": "🔍 Case Insights & Artificial Intelligence Recommendations",
        "demo_panel": "🎬 4-Language Demo Panel",
        "info_panel": "ℹ️ About GemmAid",
        "tab_main": "🖥️ Operation Center",
        "tab_test": "🧪 Test & Demo Modules",
        "info_md": """
        ### How GemmAid Works?
        1. **Citizen/Patient** → Sends crisis message to Telegram in their local language
        2. **Telegram Bot** → Forwards message to API
        3. **Gemma 4 (Local/Cloud)** → Analyzes message, produces structured JSON
        4. **This Dashboard** → Shows prioritized case list to coordinator
        """,
        "loading": "Loading...",
        "api_offline": "❌ API offline — start with `python api/api.py`",
        "active_cases_msg": "✅ {count} active cases | Last update: {time}",
        "cloud": "☁️ Cloud",
        "device": "🖥️ Device",
        "aciliyet": {"1": "🔴 CRITICAL", "2": "🟠 HIGH", "3": "🟡 MEDIUM", "4": "🟢 LOW", "5": "⚪ CAN WAIT"},
        "olay": {"enkaz_alti": "⛏️ Under Rubble", "tibbi_acil": "🏥 Medical Emergency", "tahliye": "🚌 Evacuation", "kaynak_ihtiyaci": "📦 Resource Needed", "belirsiz": "❓ Unclear"},
        "ekip": {"tibbi": "🚑 Medical", "arama_kurtarma": "⛑️ Search&Rescue", "tahliye": "🚌 Evacuation", "lojistik": "📦 Logistics"},
        
        "lbl_detail_id": "Case ID",
        "lbl_detail_contact": "Contact / Sender",
        "lbl_detail_missing": "Detected Missing Info",
        "lbl_detail_raw": "Original Message",
        "lbl_detail_ai_note": "AI Triage Summary",
        "val_detail_action": "*(Click on a case from the table above to view details)*",
        "md_ai_reply": "### ✉️ AI-Assisted Quick Reply (Foreign Language Translation)",
        "lbl_reply_input": "Coordinator Reply (Your Language)",
        "ph_reply_input": "Enter the message for the citizen...",
        "btn_reply_send": "Send to Citizen",
        "lbl_reply_trans": "AI Translation & Sent Message",
        "lbl_reply_status": "Delivery Status",
        
        "rec_plan": "### 🚀 Operational Action Plan\n\n",
        "rec_crit": "🔴 **[CRITICAL INTERVENTION]** Priority high risk. Dispatch fully equipped response teams immediately!\n\n",
        "rec_high": "🟠 **[HIGH PRIORITY]** Serious risk. Must be responded to right after critical (red) cases.\n\n",
        "rec_med": "🟡 **[MEDIUM RISK]** Standard procedures. Maintain contact via phone/messages to prevent worsening.\n\n",
        "rec_sr": "- ⛑️ **Search & Rescue:** Send heavy S&R equipment. Potential debris and stabilization risk.\n",
        "rec_medt": "- 🚑 **Medical Response:** Dispatch ambulance & first aid. Reported condition: *{semp}*\n",
        "rec_evac": "- 🚌 **Evacuation:** Arrange transport vehicles (Bus, Boat, etc.) for rapid removal.\n",
        "rec_log": "- 📦 **Logistics:** Dispatch supplies like tents, food, blankets.\n",
        "rec_missing_warn": "\n⚠️ **ATTENTION - MISSING INFO:** *{missing}*\n**Recommendation:** Please contact (`{contact}`) to clarify the missing '{missing}' details. The system requested this from the citizen.\n",
        "rec_all_good": "\n✅ **Information Status:** Case details are sufficient. Minimal risk of address/contact issues when dispatching teams.",
        "rec_low": "🟢 **[LOW RISK]** Condition stable. Monitor in the coming hours.\n\n",
        "rec_wait": "⚪ **[CAN WAIT]** Does not require immediate intervention.\n\n",
        "err_data": "❌ Data error",
        "err_api": "❌ Case ID not in API.",
        "msg_unknown": "Unknown",
        "err_empty_msg": "Empty message or invalid case.",
        "err_cancel": "Operation cancelled.",
        "err_no_text": "[No text received]",
        "err_status_unk": "Status unknown",
        "err_server": "Server Error",
        "err_http": "Error",
        "err_empty_input": "⚠️ Please enter a message",
        "missing_location": "Location",
        "missing_contact": "Contact Info",
        "stat_closed": "🗄️ Closed",
        "btn_close_case": "🟢 Close Case",
        "btn_delete_case": "🗑️ Delete Case",
        "msg_case_closed": "Case closed.",
        "msg_case_deleted": "Case deleted.",
        "msg_demo_warn": "> ⚠️ **About Demo:** This demo includes **15 diverse scenarios** \u2014 cases in TR, AR, FR, EN, DE, ES, FA, KU, UK, RU with urgency scores from 1 to 5. Since each case takes about **30-45 seconds**, the total duration might be **~8-10 minutes**. The system has not crashed during this time, please wait. Results will appear in this panel when completed.",
        "msg_demo_start": "⏳ Demo is running... 15 scenarios are being processed sequentially. Keep this window open.",
        "msg_triage_start": "{\n  \"status\": \"⏳ AI is analyzing, this process may take 30-45 seconds. Please wait, system is not frozen...\"\n}",
        "demo_completed": "🌍 {count} Scenarios Completed | Backend: {backend}",
        "demo_distribution": "📊 Urgency Distribution:"
    },
    "Türkçe": {
        "header": "# 🆘 GemmAid — Acil Koordinasyon Merkezi\n**Gemma 4 destekli çok dilli triaj sistemi** | Kaggle Gemma 4 Good Hackathon",
        "api_status_label": "🔌 Sistem Durumu",
        "check_api": "🔍 API Kontrol",
        "stat_total": "📋 Toplam Vaka",
        "stat_critical": "🔴 Kritik",
        "stat_high": "🟠 Yüksek Öncelik",
        "stat_wait": "⚪ Bekleyebilir",
        "active_cases_header": "## 📋 Aktif Vakalar",
        "case_status_label": "Durum",
        "table_headers": ["#", "Aciliyet", "Olay Tipi", "İletişim", "Konum", "Kişi", "Eksikler", "Ekip", "Dil", "Not", "Zaman"],
        "btn_refresh": "🔄 Yenile",
        "btn_demo": "🎬 Demo Çalıştır",
        "btn_clear": "🗑️ Temizle",
        "manual_triage_header": "## ✏️ Manuel Triaj Testi",
        "msg_input_label": "Kriz Mesajı",
        "msg_input_placeholder": "Herhangi bir dilde kriz mesajı yazın...\nTR / AR / FR / EN / KU desteklenir",
        "json_output_label": "📄 JSON Çıktı",
        "btn_triage": "🚨 Triaj Başlat",
        "details_panel": "🔍 Vaka İnceleme & Yapay Zeka Operasyon Önerileri",
        "demo_panel": "🎬 4 Dil Demo Paneli",
        "info_panel": "ℹ️ GemmAid Hakkında",
        "tab_main": "🖥️ Operasyon Merkezi",
        "tab_test": "🧪 Test & Demo Modülleri",
        "info_md": """
        ### GemmAid Nasıl Çalışır?
        1. **Vatandaş/Hasta** → Telegram'a kendi dilinde kriz mesajı yazar
        2. **Telegram Bot** → Mesajı alıp API'ya gönderir
        3. **Gemma 4 (Lokal/Bulut)** → Mesajı analiz eder, yapılandırılmış JSON üretir
        4. **Bu Dashboard** → Koordinatöre öncelikli vaka listesi gösterir
        """,
        "loading": "Yükleniyor...",
        "api_offline": "❌ API bağlantısı yok — `python api/api.py` ile başlatın",
        "active_cases_msg": "✅ {count} aktif vaka | Son güncelleme: {time}",
        "cloud": "☁️ Bulut",
        "device": "🖥️ Cihaz",
        "aciliyet": {"1": "🔴 KRİTİK", "2": "🟠 YÜKSEK", "3": "🟡 ORTA", "4": "🟢 DÜŞÜK", "5": "⚪ BEKLEYEBİLİR"},
        "olay": {"enkaz_alti": "⛏️ Enkaz Altı", "tibbi_acil": "🏥 Tıbbi Acil", "tahliye": "🚌 Tahliye", "kaynak_ihtiyaci": "📦 Kaynak İhtiyacı", "belirsiz": "❓ Belirsiz"},
        "ekip": {"tibbi": "🚑 Tıbbi", "arama_kurtarma": "⛑️ Arama Kurtarma", "tahliye": "🚌 Tahliye", "lojistik": "📦 Lojistik"},
        
        "lbl_detail_id": "Vaka ID",
        "lbl_detail_contact": "İletişim / Gönderen",
        "lbl_detail_missing": "Tespit Edilen Eksik Bilgiler",
        "lbl_detail_raw": "Vatandaşın Orijinal Mesajı",
        "lbl_detail_ai_note": "Yapay Zeka Triaj Özeti",
        "val_detail_action": "*(Detaylarını görmek için yukarıdaki tablodan bir vakaya tıklayın)*",
        "md_ai_reply": "### ✉️ AI Destekli Hızlı Yanıt (Yabancı Dil Çevirisi)",
        "lbl_reply_input": "Koordinatör Cevabı (Türkçe/İstediğiniz Dilde)",
        "ph_reply_input": "Vatandaşa iletilecek mesajı girin...",
        "btn_reply_send": "Vatandaşa Geri Dön",
        "lbl_reply_trans": "Yapay Zeka Çevirisi & İletilen Mesaj",
        "lbl_reply_status": "İletim Durumu",
        
        "rec_plan": "### 🚀 Operasyonel Eylem Planı\n\n",
        "rec_crit": "🔴 **[KRİTİK MÜDAHALE]** Bu olay öncelikli acil sınıfındadır. İvedilikle tam teçhizatlı müdahale ekipleri sevk edilmelidir!\n\n",
        "rec_high": "🟠 **[YÜKSEK ÖNCELİK]** Ciddi risk barındırır. Kritik (kırmızı) vakalar dondurulduktan hemen sonra ilk müdahale edileceklerdir.\n\n",
        "rec_med": "🟡 **[ORTA RİSK]** Standart prosedürler izlenmeli, durumun kötüleşmemesi için telefon/mesaj yoluyla iletişimde kalın.\n\n",
        "rec_sr": "- ⛑️ **Arama Kurtarma Sevk:** Konuma ağır ekipmanlı arama kurtarma personeli çıkarın. Enkaz ve stabilizasyon tehlikesi olabilir.\n",
        "rec_medt": "- 🚑 **Tıbbi Müdahale:** Ambulans ve ilk yardım ekibi yönlendirin. Bildirilen Tıbbi Durum: *{semp}*\n",
        "rec_evac": "- 🚌 **Tahliye/Ulaşım:** Bölgeden hızlı uzaklaştırma için ulaşım desteği aracı (Otobüs, Bot vb.) ayarlayın.\n",
        "rec_log": "- 📦 **Lojistik:** Çadır, yiyecek, battaniye gibi kaynak aktarımı yapılsın.\n",
        "rec_missing_warn": "\n⚠️ **DİKKAT - EKSİK BİLGİ:** *{missing}*\n**Öneri:** Lütfen irtibat kişisine (`{contact}`) ulaşıp eksik olan '{missing}' konusunu netleştirin. Sistemin vatandaşa dönecek mesajında eksik bilgiler talep edilmiştir.\n",
        "rec_all_good": "\n✅ **Bilgi Durumu:** Vaka bilgileri yeterli görünüyor. Ekipler yönlendirildiğinde adres/irtibat sıkıntısı yaşanması çok düşük ihtimal.",
        "rec_low": "🟢 **[DÜŞÜK RİSK]** Durum stabil. İlerleyen saatlerde takip edilecek.\n\n",
        "rec_wait": "⚪ **[BEKLEYEBİLİR]** Acil müdahale gerektirmez.\n\n",
        "err_data": "❌ Data error / Tablo okuma hatası.",
        "err_api": "❌ Vaka ID API'de bulunamadı.",
        "msg_unknown": "Bilinmiyor",
        "err_empty_msg": "Boş mesaj veya geçersiz vaka.",
        "err_cancel": "İşlem iptal edildi.",
        "err_no_text": "[Metin alınamadı]",
        "err_status_unk": "Durum bilinmiyor",
        "err_server": "Sunucu Hatası",
        "err_http": "Hata",
        "err_empty_input": "⚠️ Lütfen mesaj girin",
        "missing_location": "Konum",
        "missing_contact": "İletişim Bilgisi",
        "stat_closed": "🗄️ Kapatılan",
        "btn_close_case": "🟢 Vakayı Kapat",
        "btn_delete_case": "🗑️ Vakayı Sil",
        "msg_case_closed": "Vaka kapatıldı.",
        "msg_case_deleted": "Vaka silindi.",
        "msg_demo_warn": "> ⚠️ **Demo hakkında:** Bu demo **15 çeşitli senaryo** içerir \u2014 TR, AR, FR, EN, DE, ES, FA, KU, UK, RU dillerinde, aciliyet skoru 1'den 5'e kadar vakalar. Her vaka yaklaşık **30-45 saniye** sürdüğünden toplam süre **~8-10 dakika** olabilir. Bu süre boyunca sistem çökmemiştir, lütfen bekleyin. Tamamlandığında sonuçlar bu panelde görünecektir.",
        "msg_demo_start": "⏳ Demo çalışıyor... 15 senaryo sırayla işleniyor. Bu pencereyi açık tutun.",
        "msg_triage_start": "{\n  \"status\": \"⏳ Yapay zeka analiz ediyor, bu işlem 30-45 saniye sürebilir. Lütfen sistemin çökmediğini bilerek bekleyin...\"\n}",
        "demo_completed": "🌍 {count} Senaryo Tamamlandı | Backend: {backend}",
        "demo_distribution": "📊 Aciliyet Dağılımı:"
    }
}

DEMO_SCENARIOS = [
    ("TR 🇹🇷", "Konumum: Atatürk Mahallesi, 12. Sokak. Bina çöktü, bir komşumuz göçük altında, bacağı sıkışmış durumda. Lütfen acele edin."),
    ("AR 🇸🇦", "مرحباً، لدينا حريق كبير في مبنى سكني في شارع الملك فهد، الطابق الرابع. هناك أطفال محاصرون. نحتاج سيارة إطفاء وإسعاف."),
    ("FR 🇫🇷", "Accident de la route grave sur l'autoroute A4, près de la sortie 12. Deux voitures impliquées, il y a des blessés inconscients. Envoyez des secours."),
    ("EN 🇬🇧", "House flooded in Kemaliye district. 2 children and 1 elderly person are trapped on the roof. The water is rising very fast! My phone is running out of battery."),
    ("KU 🇹🇯", "Em li gundê Xiraba ne. Rê hatine girtin û xwarin û ava me nemaye. Rewşa zarokan xerab e. Alîkariyê bişînin."),
    ("ES 🇪🇸", "Necesitamos tiendas de campaña y mantas en el campamento central. Han llegado 50 refugiados nuevos y está nevando. No tenemos suministros."),
    ("TR 🇹🇷", "Burası çok karışık, ne yapacağımı bilmiyorum, lütfen hemen birilerini gönderin! Yardım edin!"), # Bilerek eksik bilgi veren mesaj (konum yok)
    ("DE 🇩🇪", "Ich habe starke Schmerzen in der Brust und Atembeschwerden. Ich bin allein in meiner Wohnung. Adresse: Goethestrasse 45, Wohnung 3."),
    ("EN 🇬🇧", "Need a helicopter. Our logistics truck broke down on the mountain pass and someone has a broken arm. Coordinates: 45.12, 12.34. Number: +441234567"),
]


# ── Yardımcı Fonksiyonlar ─────────────────────────────────────
def _api_get(url: str, timeout: int = 8):
    try:
        resp = httpx.get(url, timeout=timeout)
        return resp.json()
    except httpx.ConnectError:
        return None
    except Exception:
        return None


def _api_post(url: str, data: dict, timeout: int = 120):
    try:
        resp = httpx.post(url, json=data, timeout=timeout)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


# ── Refresh ──────────────────────────────────────────────────
def refresh_cases(lang):
    """Vaka listesini ve istatistikleri güncelle."""
    cases = _api_get(CASES_URL)
    stats = _api_get(STATS_URL)
    
    t = UI_TEXT[lang]

    # Bağlantı kontrolü
    if cases is None:
        status_msg = t["api_offline"]
        # Tablo formatını bozmamak için empty frame
        empty_grid = gr.Dataframe(headers=t["table_headers"], value=[])
        return empty_grid, status_msg, "—", "—", "—", "—", "—"

    # Satırları oluştur
    rows = []
    for c in cases:  # Zaten aciliyet sırasına göre sıralı
        acil = str(c.get("aciliyet_skoru", "?"))
        olay = c.get("olay_tipi", "?")
        
        # Ekip listesini çevir
        raw_ekipler = c.get("gerekli_ekip", [])
        ekip = ", ".join([t["ekip"].get(e, e) for e in raw_ekipler])
        
        # Eksik bilgileri formatla
        raw_missing = c.get("eksik_bilgiler", [])
        if isinstance(raw_missing, list):
            missing_info = ", ".join(raw_missing)
        else:
            missing_info = str(raw_missing)
            
        contact_str = f"{c.get('gonderen_kisi', '?')} - {c.get('iletisim_bilgisi', '?')}"
        ts   = c.get("timestamp", "")[:16].replace("T", " ")  # 2026-05-15 12:34
        
        rows.append([
            c.get("id", "?"),
            t["aciliyet"].get(acil, acil),
            t["olay"].get(olay, olay),
            contact_str[:40],
            c.get("konum_metni", "?"),
            c.get("etkilenen_kisi_sayisi", "?"),
            missing_info[:40],
            ekip,
            c.get("kaynak_dil", "?").upper(),
            (c.get("koordinator_notu") or "—")[:60],
            ts,
        ])

    # İstatistikler
    if stats:
        toplam   = str(stats.get("toplam", 0))
        kritik   = str(stats.get("kritik", 0))
        yuksek   = str(stats.get("yuksek_oncelik", 0))
        bekleyen = str(stats.get("bekleyebilir", 0))
        kapatilan = str(stats.get("kapatilan", 0))
    else:
        toplam = kritik = yuksek = bekleyen = kapatilan = "?"

    now = datetime.now().strftime("%H:%M:%S")
    status_msg = t["active_cases_msg"].format(count=len(cases), time=now)

    return gr.Dataframe(headers=t["table_headers"], value=rows), status_msg, toplam, kritik, yuksek, bekleyen, kapatilan


def manual_triage(message: str, lang: str):
    """Tek mesajı triaj et."""
    t = UI_TEXT[lang]
    if not message.strip():
        return t["err_empty_input"]
        
    target_lang = "en" if lang == "English" else "tr"
    result = _api_post(TRIAGE_URL, {"message": message, "target_lang": target_lang})
    
    if "error" in result:
        return f"❌ Error: {result['error']}"
    return json.dumps(result, ensure_ascii=False, indent=2)


def run_demo(lang="English"):
    """15 çeşitli senaryoyu API'den çek ve formatla."""
    t_lang = UI_TEXT[lang]
    result = _api_get(DEMO_URL, timeout=900)
    if result is None:
        return "❌ API bağlantısı başarısız"
    demos = result.get("demo_results", [])
    if not demos:
        return "❌ Demo sonucu boş döndü"
    
    EMOJI_SCORE = {1:"🔴",2:"🟠",3:"🟡",4:"🟢",5:"⚪"}
    TYPE_EMOJI  = {
        "enkaz_alti":     "🏗️ Enkaz Altı",
        "tibbi_acil":     "🚑 Tıbbi Acil",
        "tahliye":        "🚌 Tahliye",
        "kaynak_ihtiyaci":"📦 Kaynak İhtiyacı",
        "belirsiz":       "❔ Belirsiz",
    }

    lines = [
        t_lang["demo_completed"].format(count=len(demos), backend=result.get('backend', '?')),
        "="*60,
    ]
    score_counts = {}
    for i, d in enumerate(demos, 1):
        d_lang = d.get("lang", "?")
        if "error" in d:
            lines.append(f"{i:>2}. [{d_lang}] ❌ {d['error'][:80]}")
            continue
        t     = d.get("triage", {})
        acil  = t.get("aciliyet_skoru", "?")
        acil_int = int(acil) if str(acil).isdigit() else 0
        e_score = EMOJI_SCORE.get(acil_int, "❓")
        o_tip = TYPE_EMOJI.get(t.get("olay_tipi", "belirsiz"), "❔ Belirsiz")
        ekipler = ", ".join(t.get("gerekli_ekip", [])) or "—"
        konum   = t.get("konum_metni", "Belirtilmedi")[:35]
        not_kisa = t.get("koordinator_notu", "")[:70]
        score_counts[acil_int] = score_counts.get(acil_int, 0) + 1
        lines.append(f"{i:>2}. {e_score}[{d_lang}] {o_tip} | Skor:{acil} | Ekip:{ekipler}")
        lines.append(f"     📍 {konum}")
        lines.append(f"     📝 {not_kisa}")
        lines.append("")

    # Özet istatistik
    lines.append("-"*60)
    lines.append(t_lang["demo_distribution"])
    for s in sorted(score_counts):
        bar = "█" * score_counts[s]
        lines.append(f"  Skor {s} {EMOJI_SCORE.get(s,'')}: {bar} ({score_counts[s]} vaka)")
    return "\n".join(lines)


def clear_and_refresh(lang):
    """Tüm vakaları sil ve listeyi güncelle."""
    try:
        resp = httpx.delete(f"{API_BASE_URL}/cases", timeout=5)
        resp.raise_for_status()
    except Exception:
        pass  # Silme hatası olsa bile yenile
    return refresh_cases(lang)


def check_api_health(lang):
    """API sağlık durumunu kontrol et."""
    h = _api_get(HEALTH_URL)
    if h is None:
        return "❌ API Offline" if lang == "English" else "❌ API Çevrimdışı"
    backend = h.get("backend", "?")
    model_info = ""
    if h.get("model"):
        m = h["model"]
        if m.get("loaded"):
            model_info = f" | Model: ✅ ({m.get('size_gb', '?')} GB)"
        elif m.get("exists"):
            model_info = " | Model: disk"
        else:
            model_info = " | Model: ⚠️"
    return f"✅ API Online | Backend: {backend.upper()}{model_info}"

def update_ui_lang(lang):
    t = UI_TEXT[lang]
    # Sadece label'ları ve başlıkları güncelleyen bir callback oluşturuyoruz
    return (
        gr.update(value=t["header"]),
        gr.update(label=t["api_status_label"]),
        gr.update(value=t["check_api"]),
        gr.update(label=t["stat_total"]),
        gr.update(label=t["stat_critical"]),
        gr.update(label=t["stat_high"]),
        gr.update(label=t["stat_wait"]),
        gr.update(label=t["stat_closed"]),
        gr.update(value=t["active_cases_header"]),
        gr.update(label=t["case_status_label"]),
        gr.update(value=t["btn_refresh"]),
        gr.update(value=t["btn_demo"]),
        gr.update(value=t["btn_clear"]),
        gr.update(value=t["manual_triage_header"]),
        gr.update(label=t["msg_input_label"], placeholder=t["msg_input_placeholder"]),
        gr.update(label=t["json_output_label"]),
        gr.update(value=t["btn_triage"]),
        gr.update(label=t["details_panel"]),
        
        # New translation updates
        gr.update(label=t["lbl_detail_id"]),
        gr.update(label=t["lbl_detail_contact"]),
        gr.update(label=t["lbl_detail_missing"]),
        gr.update(label=t["lbl_detail_raw"]),
        gr.update(label=t["lbl_detail_ai_note"]),
        gr.update(value=t["val_detail_action"]),
        gr.update(value=t["md_ai_reply"]),
        gr.update(label=t["lbl_reply_input"], placeholder=t["ph_reply_input"]),
        gr.update(value=t["btn_reply_send"]),
        gr.update(label=t["lbl_reply_trans"]),
        gr.update(label=t["lbl_reply_status"]),
        gr.update(value=t["btn_close_case"]),
        gr.update(value=t["btn_delete_case"]),
        
        gr.update(label=t["demo_panel"]),
        gr.update(label=t["tab_main"]),
        gr.update(label=t["tab_test"]),
        gr.update(value=t["msg_demo_warn"]),
        gr.update(label=t["info_panel"]),
        gr.update(value=t["info_md"])
    )


# ── Gradio UI ─────────────────────────────────────────────────
with gr.Blocks(
    title="GemmAid — Dashboard",
    theme=gr.themes.Base(
        primary_hue="red",
        secondary_hue="orange",
        neutral_hue="slate",
    )
) as demo:
    
    with gr.Row():
        ui_lang = gr.Radio(choices=["English", "Türkçe"], value="English", label="Language / Dil", scale=1)

    t_init = UI_TEXT["English"]

    # ── Başlık ────────────────────────────────────────────────
    header_md = gr.Markdown(t_init["header"])

    # ── API Durum Satırı ─────────────────────────────────────
    with gr.Row():
        api_status = gr.Textbox(label=t_init["api_status_label"], value=t_init["loading"], interactive=False, scale=3)
        btn_check = gr.Button(t_init["check_api"], size="sm", scale=1)
        btn_check.click(check_api_health, inputs=[ui_lang], outputs=api_status)

    # ── İstatistik Kartları ───────────────────────────────────
    with gr.Row():
        stat_toplam  = gr.Textbox(label=t_init["stat_total"],  value="—", interactive=False, scale=1)
        stat_kritik  = gr.Textbox(label=t_init["stat_critical"], value="—", interactive=False, scale=1)
        stat_yuksek  = gr.Textbox(label=t_init["stat_high"], value="—", interactive=False, scale=1)
        stat_bekle   = gr.Textbox(label=t_init["stat_wait"], value="—", interactive=False, scale=1)
        stat_kapatilan = gr.Textbox(label=t_init["stat_closed"], value="—", interactive=False, scale=1)

    # ── Ana İçerik ────────────────────────────────────────────
    with gr.Tabs() as main_tabs:
        with gr.Tab(t_init["tab_main"]) as tab_main:
            active_cases_md = gr.Markdown(t_init["active_cases_header"])
            case_status = gr.Textbox(label=t_init["case_status_label"], value=t_init["loading"], interactive=False)
            case_table = gr.Dataframe(
                headers=t_init["table_headers"],
                datatype=["number", "str", "str", "str", "number", "str", "str", "str", "str", "str"],
                interactive=False,
                wrap=True,
                row_count=(10, "dynamic"),
            )
            
            # ── Ortak Çıktılar ────────────────────────────────────────
            refresh_outputs = [case_table, case_status, stat_toplam, stat_kritik, stat_yuksek, stat_bekle, stat_kapatilan]

            with gr.Row():
                refresh_btn = gr.Button(t_init["btn_refresh"], variant="primary", scale=1)
                clear_btn   = gr.Button(t_init["btn_clear"], variant="stop", scale=1)

            # ── Vaka İncelme ve Öneri Paneli (Yeni Kullanışlı Alan) ──
            with gr.Accordion(t_init["details_panel"], open=True) as details_acc:
                with gr.Row():
                    with gr.Column(scale=1):
                        detail_id = gr.Textbox(label=t_init["lbl_detail_id"], interactive=False)
                        detail_contact = gr.Textbox(label=t_init["lbl_detail_contact"], interactive=False)
                        detail_missing = gr.Textbox(label=t_init["lbl_detail_missing"], interactive=False)
                    with gr.Column(scale=2):
                        detail_raw = gr.Textbox(label=t_init["lbl_detail_raw"], lines=3, interactive=False)
                        detail_ai_note = gr.Textbox(label=t_init["lbl_detail_ai_note"], lines=3, interactive=False)
                with gr.Row():
                    detail_action = gr.Markdown(t_init["val_detail_action"])
                
                with gr.Group():
                    ai_help_md = gr.Markdown(t_init["md_ai_reply"])
                    with gr.Row():
                        reply_input = gr.Textbox(label=t_init["lbl_reply_input"], placeholder=t_init["ph_reply_input"], lines=2, scale=3)
                        reply_btn = gr.Button(t_init["btn_reply_send"], variant="primary", scale=1)
                    with gr.Row():
                        reply_translated = gr.Textbox(label=t_init["lbl_reply_trans"], interactive=False, lines=2)
                        reply_status = gr.Textbox(label=t_init["lbl_reply_status"], interactive=False)
                    with gr.Row():
                        btn_close = gr.Button(t_init["btn_close_case"], variant="secondary")
                        btn_delete = gr.Button(t_init["btn_delete_case"], variant="stop")

        with gr.Tab(t_init["tab_test"]) as tab_test:
            with gr.Row():
                # Sol: Manuel Triaj
                with gr.Column(scale=1):
                    manual_md = gr.Markdown(t_init["manual_triage_header"])
                    msg_input = gr.Textbox(label=t_init["msg_input_label"], placeholder=t_init["msg_input_placeholder"], lines=5)
                    triage_btn = gr.Button(t_init["btn_triage"], variant="stop")
                    
                    gr.Examples(
                        examples=[
                            [DEMO_SCENARIOS[0][1]],  # TR
                            [DEMO_SCENARIOS[1][1]],  # AR
                            [DEMO_SCENARIOS[2][1]],  # FR
                            [DEMO_SCENARIOS[3][1]],  # EN
                            [DEMO_SCENARIOS[4][1]],  # KU
                            [DEMO_SCENARIOS[5][1]],  # ES
                            [DEMO_SCENARIOS[6][1]],  # TR - Missing
                            [DEMO_SCENARIOS[7][1]],  # DE
                            [DEMO_SCENARIOS[8][1]],  # EN - Logistics
                        ],
                        inputs=msg_input,
                        label="📌 Pre-loaded Examples"
                    )
                
                # Sağ: Çıktılar ve Demo
                with gr.Column(scale=1):
                    triage_output = gr.Code(label=t_init["json_output_label"], language="json", lines=15)
                    
                    def _triage_start(lang_val):
                        return UI_TEXT[lang_val]["msg_triage_start"]
                        
                    triage_btn.click(
                        _triage_start, inputs=[ui_lang], outputs=triage_output
                    ).then(
                        manual_triage, inputs=[msg_input, ui_lang], outputs=triage_output
                    ).then(
                        refresh_cases, inputs=[ui_lang], outputs=refresh_outputs
                    )
                    
                    # ── Demo Paneli ───────────────────────────────────────────
                    with gr.Accordion(t_init["demo_panel"], open=True) as demo_acc:
                        demo_warn = gr.Markdown(value=t_init["msg_demo_warn"])
                        demo_btn = gr.Button(t_init["btn_demo"], variant="secondary", size="sm")
                        demo_output = gr.Textbox(label="Demo Sonuçları", lines=15, interactive=False)
                        
                        def _demo_start(lang_val):
                            return UI_TEXT[lang_val]["msg_demo_start"]
                        
                        demo_btn.click(
                            _demo_start, inputs=[ui_lang], outputs=demo_output
                        ).then(
                            run_demo, inputs=[ui_lang], outputs=demo_output
                        ).then(
                            refresh_cases, inputs=[ui_lang], outputs=refresh_outputs
                        )

    def close_case_ui(case_id_str, lang="Türkçe"):
        t = UI_TEXT[lang]
        if not case_id_str:
            return t["err_empty_msg"]
        resp = _api_post(f"{API_BASE_URL}/cases/{case_id_str}/close", {})
        if "error" in resp:
            return f"❌ {resp['error']}"
        return t["msg_case_closed"]
        
    def delete_case_ui(case_id_str, lang="Türkçe"):
        t = UI_TEXT[lang]
        if not case_id_str:
            return t["err_empty_msg"]
        try:
            r = httpx.delete(f"{API_BASE_URL}/cases/{case_id_str}", timeout=10)
            if r.status_code == 200:
                return t["msg_case_deleted"]
            return f"❌ HTTP {r.status_code}"
        except Exception as e:
            return f"❌ {e}"

    # Yanıt Gönderme Olayı
    def send_ai_reply(case_id_str, coordinator_message, lang="Türkçe"):
        t = UI_TEXT[lang]
        if not case_id_str or not coordinator_message.strip():
            return t["err_empty_msg"], t["err_cancel"]
            
        try:
            case_id = int(case_id_str)
            resp = requests.post(f"{API_BASE_URL}/reply_to_case", json={
                "case_id": case_id,
                "coordinator_message": coordinator_message
            }, timeout=30)
            
            if resp.status_code == 200:
                data = resp.json()
                return data.get("translated_message", t["err_no_text"]), data.get("delivery_status", t["err_status_unk"])
            else:
                return f"{t['err_http']}: {resp.status_code}", resp.text
        except Exception as e:
            return t["err_server"], str(e)
            
    reply_btn.click(send_ai_reply, inputs=[detail_id, reply_input, ui_lang], outputs=[reply_translated, reply_status])

    # Seçim Olayı Bağlama
    import pandas as pd
    def on_case_select(evt: gr.SelectData, cases_df, lang: str):
        t = UI_TEXT[lang]
        if cases_df is None or len(cases_df) == 0:
            return "", "", "", "", "", t["err_data"]
            
        row_idx = evt.index[0]
        # cases_df is a pandas DataFrame because gradio Dataframes return pd.DataFrame by default, or just lists
        try:
            if hasattr(cases_df, 'iloc'):
                case_id = cases_df.iloc[row_idx, 0]
            else:
                case_id = cases_df[row_idx][0]
        except Exception:
            return "", "", "", "", "", t["err_data"]

        cases = _api_get(CASES_URL)
        selected_case = next((c for c in cases if str(c.get("id")) == str(case_id)), None)
        
        if not selected_case:
            return str(case_id), "", "", "", "", t["err_api"]
            
        contact = f"{selected_case.get('gonderen_kisi', '?')} — {selected_case.get('iletisim_bilgisi', '?')}"
        
        # EXPERIMENTAL LOGIC for MISSING DATA
        missing_val = selected_case.get("eksik_bilgiler", [])
        if isinstance(missing_val, list):
            missing_list = missing_val.copy()
        else:
            missing_list = [str(missing_val)] if missing_val else []
            
        # Manually check for missing essential info regardless of LLM's 'eksik_bilgiler'
        konum = selected_case.get('konum_metni', 'Belirtilmedi')
        if konum in ['Belirtilmedi', 'Bilinmiyor', '?', '']:
            if not any('konum' in m.lower() for m in missing_list) and not any('location' in m.lower() for m in missing_list):
                missing_list.append(t['missing_location'])
                
        iletisim = selected_case.get('iletisim_bilgisi', 'Bilinmiyor')
        if iletisim in ['Bilinmiyor', 'Belirtilmedi', '?', '']:
            if not any('iletişim' in m.lower() for m in missing_list) and not any('iletisim' in m.lower() for m in missing_list) and not any('contact' in m.lower() for m in missing_list):
                missing_list.append(t['missing_contact'])
                
        missing = ", ".join(missing_list)
        # End of new logic
            
        raw = selected_case.get("raw_message", "")
        ai_note = selected_case.get("koordinator_notu", "")
        skor = selected_case.get("aciliyet_skoru", 3)
        ekipler = selected_case.get("gerekli_ekip", [])
        semptomlar = selected_case.get("semptomlar", [])
        
        # Yapay Zeka Dinamik Eylem Planı
        recs = t["rec_plan"]
        
        eylem_plani = selected_case.get("eylem_plani")
        if eylem_plani:
            recs += eylem_plani + "\n"
        else:
            recs += "⚠️ Yapay zeka henüz bu vaka için spesifik bir eylem planı oluşturmadı (Eski vaka olabilir).\n"
            
        if missing:
            recs += t["rec_missing_warn"].format(missing=missing, contact=contact)
        else:
            recs += t["rec_all_good"]

        return str(case_id), contact, missing, raw, ai_note, recs

    case_table.select(
        on_case_select, 
        inputs=[case_table, ui_lang], 
        outputs=[detail_id, detail_contact, detail_missing, detail_raw, detail_ai_note, detail_action]
    )

    # ── Bilgi Paneli ─────────────────────────────────────────
    with gr.Accordion(t_init["info_panel"], open=False) as info_acc:
        info_md = gr.Markdown(t_init["info_md"])

    # ── Dil Değişimi ──────────────────────────────────────────
    # Dil seçildiğinde tüm UI text'lerini güncelle ve listeyi tazele
    ui_lang.change(
        update_ui_lang, 
        inputs=[ui_lang], 
        outputs=[
            header_md, api_status, btn_check, stat_toplam, stat_kritik,
            stat_yuksek, stat_bekle, stat_kapatilan, active_cases_md, case_status,
            refresh_btn, demo_btn, clear_btn, manual_md, msg_input,
            triage_output, triage_btn, details_acc,
            detail_id, detail_contact, detail_missing, detail_raw, detail_ai_note,
            detail_action, ai_help_md, reply_input, reply_btn, reply_translated, reply_status,
            btn_close, btn_delete,
            demo_acc, demo_warn, info_acc, info_md, tab_main, tab_test
        ]
    ).then(
        refresh_cases, inputs=[ui_lang], outputs=[case_table, case_status, stat_toplam, stat_kritik, stat_yuksek, stat_bekle, stat_kapatilan]
    )
    
    # ── Close/Delete Events ───────────────────────────
    def clear_details():
        return "", "", "", "", "", "", "", ""
        
    clear_outputs = [
        detail_id, detail_contact, detail_missing, detail_raw, detail_ai_note, detail_action,
        reply_input, reply_translated
    ]

    btn_close.click(close_case_ui, inputs=[detail_id, ui_lang], outputs=[reply_status]).then(
        clear_details, outputs=clear_outputs
    ).then(
        refresh_cases, inputs=[ui_lang], outputs=refresh_outputs
    )
    
    btn_delete.click(delete_case_ui, inputs=[detail_id, ui_lang], outputs=[reply_status]).then(
        clear_details, outputs=clear_outputs
    ).then(
        refresh_cases, inputs=[ui_lang], outputs=refresh_outputs
    )
    
    demo.load(refresh_cases, inputs=[ui_lang], outputs=refresh_outputs)

    # Gradio Timer
    timer = gr.Timer(value=30)
    timer.tick(refresh_cases, inputs=[ui_lang], outputs=refresh_outputs)
    
    refresh_btn.click(refresh_cases, inputs=[ui_lang], outputs=refresh_outputs)
    clear_btn.click(clear_and_refresh, inputs=[ui_lang], outputs=refresh_outputs)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=DASHBOARD_PORT, share=False, show_error=True)
