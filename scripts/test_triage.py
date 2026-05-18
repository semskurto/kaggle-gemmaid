#!/usr/bin/env python3
"""GemmAid — 4 Dil Test Senaryosu
API'ya 4 farklı dilde kriz mesajı gönderip triaj sonuçlarını gösterir.

Kullanım:
    python scripts/test_triage.py
    python scripts/test_triage.py --backend gemini
"""
import argparse
import httpx
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

API_URL = "http://localhost:8000"

ACIL_EMOJI = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "⚪"}

SCENARIOS = [
    {
        "lang": "TR",
        "flag": "🇹🇷",
        "message": "Komşumuz enkaz altında kaldı, Atatürk Caddesi 3. kat, nefes güçlüğü var, 3 kişiyiz",
        "expected_olay": "enkaz_alti",
        "expected_acil": 1,
    },
    {
        "lang": "AR",
        "flag": "🇸🇦",
        "message": "جارنا عالق تحت الأنقاض، يتنفس بصعوبة، شارع أتاتورك، الطابق الثالث، نحن ثلاثة أشخاص",
        "expected_olay": "enkaz_alti",
        "expected_acil": 1,
    },
    {
        "lang": "FR",
        "flag": "🇫🇷",
        "message": "J'ai une douleur intense dans la poitrine depuis 2 heures, j'ai du mal à respirer",
        "expected_olay": "tibbi_acil",
        "expected_acil": 1,
    },
    {
        "lang": "EN",
        "flag": "🇬🇧",
        "message": "House flooded, 2 children trapped on roof, water rising fast, Kemaliye district",
        "expected_olay": "tahliye",
        "expected_acil": 2,
    },
]


def run_test(scenario: dict, timeout: int = 120) -> dict:
    """Tek senaryoyu test et."""
    try:
        resp = httpx.post(
            f"{API_URL}/triage",
            json={"message": scenario["message"]},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return {"success": True, "data": data}
    except httpx.ConnectError:
        return {"success": False, "error": "API bağlantısı yok — `python api/api.py` çalıştırın"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def print_result(scenario: dict, result: dict):
    """Test sonucunu renkli yazdır."""
    lang = scenario["lang"]
    flag = scenario["flag"]
    print(f"\n{'─'*55}")
    print(f"{flag} [{lang}] {scenario['message'][:70]}")
    print(f"{'─'*55}")

    if not result["success"]:
        print(f"  ❌ HATA: {result['error']}")
        return False

    d     = result["data"]
    acil  = d.get("aciliyet_skoru", "?")
    olay  = d.get("olay_tipi", "?")
    emoji = ACIL_EMOJI.get(acil, "❓")
    ekip  = ", ".join(d.get("gerekli_ekip", []))
    konum = d.get("konum_metni", "?")
    not_  = d.get("koordinator_notu", "?")

    print(f"  {emoji} Aciliyet     : {acil}/5")
    print(f"  📍 Olay Tipi   : {olay}")
    print(f"  🗺️  Konum       : {konum}")
    print(f"  👥 Kişi Sayısı : {d.get('etkilenen_kisi_sayisi', '?')}")
    print(f"  🚨 Gerekli Ekip: {ekip or 'Belirtilmedi'}")
    print(f"  🌐 Tespit Dil  : {d.get('kaynak_dil', '?').upper()}")
    print(f"  📋 Koordinatör : {not_}")

    # Beklenti kontrolü
    exp_olay = scenario.get("expected_olay")
    exp_acil = scenario.get("expected_acil")
    passed = True

    if exp_olay and olay != exp_olay:
        print(f"  ⚠️  Olay beklentisi: {exp_olay} → alınan: {olay}")
        passed = False

    if exp_acil and acil > exp_acil + 1:
        print(f"  ⚠️  Aciliyet beklentisi: <={exp_acil} → alınan: {acil}")
        passed = False

    if passed:
        print(f"  ✅ Test BAŞARILI")
    else:
        print(f"  ⚠️  Test kısmen başarısız (yukarıdaki uyarılara bakın)")

    return passed


def main():
    parser = argparse.ArgumentParser(description="GemmAid Triaj Test Senaryoları")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Her test için timeout süresi (saniye)")
    parser.add_argument("--json", action="store_true",
                        help="Sonuçları JSON formatında yazdır")
    args = parser.parse_args()

    print("=" * 55)
    print("GemmAid — 4 Dil Triaj Test Senaryosu")
    print("=" * 55)

    # API sağlık kontrolü
    try:
        health = httpx.get(f"{API_URL}/health", timeout=5).json()
        backend = health.get("backend", "?")
        print(f"\n✅ API Çevrimiçi | Backend: {backend.upper()}")
    except Exception:
        print("\n❌ API çevrimdışı! Önce API'yi başlatın:")
        print("   python api/api.py")
        sys.exit(1)

    results = []
    passed = 0

    for scenario in SCENARIOS:
        result = run_test(scenario, timeout=args.timeout)
        ok = print_result(scenario, result)
        if ok:
            passed += 1
        results.append({"scenario": scenario["lang"], "result": result, "passed": ok})

    print(f"\n{'='*55}")
    print(f"📊 Sonuç: {passed}/{len(SCENARIOS)} test başarılı")
    print(f"{'='*55}")

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
