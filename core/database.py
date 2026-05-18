"""GemmAid — SQLite Veritabanı Katmanı
Vakaları kalıcı olarak depolar; API restart'ta veri kaybolmaz.
"""
import json
import sqlite3
import logging
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import List, Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.config import DB_PATH

log = logging.getLogger(__name__)

# ── DDL ──────────────────────────────────────────────────────
_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS cases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,
    raw_message     TEXT    NOT NULL,
    sender_name     TEXT    DEFAULT '',
    telegram_id     TEXT    DEFAULT '',
    olay_tipi       TEXT    NOT NULL DEFAULT 'belirsiz',
    aciliyet_skoru  INTEGER NOT NULL DEFAULT 3,
    konum_metni     TEXT    DEFAULT 'Belirtilmedi',
    etkilenen_kisi  INTEGER DEFAULT 1,
    semptomlar      TEXT    DEFAULT '[]',   -- JSON array
    gerekli_ekip    TEXT    DEFAULT '[]',   -- JSON array
    kaynak_dil      TEXT    DEFAULT 'tr',
    koordinator_notu TEXT   DEFAULT '',
    backend         TEXT    DEFAULT 'unknown',
    parse_error     INTEGER DEFAULT 0,      -- 0=ok, 1=hata
    vatandasa_yanit TEXT    DEFAULT '',
    eylem_plani     TEXT    DEFAULT '',
    status          TEXT    DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS contacts (
    telegram_id     TEXT PRIMARY KEY,
    sender_name     TEXT    DEFAULT '',
    telegram_username TEXT DEFAULT '',
    first_seen      TEXT    NOT NULL,
    last_seen       TEXT    NOT NULL,
    message_count   INTEGER NOT NULL DEFAULT 1,
    latest_case_id  INTEGER DEFAULT NULL
);
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_aciliyet ON cases (aciliyet_skoru);
CREATE INDEX IF NOT EXISTS idx_timestamp ON cases (timestamp);
"""


@contextmanager
def _get_conn():
    """Thread-safe SQLite bağlantısı."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Veritabanını başlat (tablo yoksa oluştur)."""
    with _get_conn() as conn:
        conn.executescript(_CREATE_TABLE + _CREATE_INDEX)
        
        # Sürüm güncellemesi (yeni eklenen kolonlar için)
        try:
            conn.execute("ALTER TABLE cases ADD COLUMN sender_name TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE cases ADD COLUMN telegram_id TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE cases ADD COLUMN vatandasa_yanit TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE cases ADD COLUMN status TEXT DEFAULT 'active'")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE cases ADD COLUMN eylem_plani TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

    log.info(f"[DB] SQLite başlatıldı: {DB_PATH}")


def save_case(
    triage_data: dict,
    raw_message: str,
    backend: str = "unknown",
    sender_name: str = "",
    telegram_id: str = "",
    telegram_username: str = "",
) -> int:
    """
    Bir triaj vakasını kaydet veya mevcut vakayı güncelle.

    Args:
        triage_data: parse_triage_json() çıktısı
        raw_message: Ham kriz mesajı
        backend: Kullanılan backend (local/gemini/transformers)

    Returns:
        Kaydın (yeni veya güncellenmiş) ID'si
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    contact_key = (telegram_id or triage_data.get("iletisim_bilgisi", "") or "").strip()
    contact_name = (sender_name or triage_data.get("gonderen_kisi", "") or "").strip()
    
    existing_case_id = None
    
    # Kullanıcı varsa en son vakasını bul (API katmanı mesajı çoktan birleştirdi, sadece ID buluyoruz)
    if contact_key and contact_key not in {"Bilinmiyor", "", "?"}:
        with _get_conn() as conn:
            row = conn.execute("SELECT id, status FROM cases WHERE telegram_id = ? ORDER BY timestamp DESC LIMIT 1", (contact_key,)).fetchone()
            if row and row["status"] != "closed":
                existing_case_id = row["id"]

    with _get_conn() as conn:
        if existing_case_id:
            sql = """
            UPDATE cases SET
                timestamp = ?,
                raw_message = ?,
                sender_name = ?,
                olay_tipi = ?,
                aciliyet_skoru = ?,
                konum_metni = ?,
                etkilenen_kisi = ?,
                semptomlar = ?,
                gerekli_ekip = ?,
                kaynak_dil = ?,
                koordinator_notu = ?,
                backend = ?,
                parse_error = ?,
                vatandasa_yanit = ?,
                eylem_plani = ?
            WHERE id = ?
            """
            params = (
                now,
                raw_message,
                contact_name,
                triage_data.get("olay_tipi", "belirsiz"),
                int(triage_data.get("aciliyet_skoru", 3)),
                triage_data.get("konum_metni", "Belirtilmedi"),
                int(triage_data.get("etkilenen_kisi_sayisi", 1)),
                json.dumps(triage_data.get("semptomlar", []), ensure_ascii=False),
                json.dumps(triage_data.get("gerekli_ekip", []), ensure_ascii=False),
                triage_data.get("kaynak_dil", "?"),
                triage_data.get("koordinator_notu", ""),
                backend,
                1 if triage_data.get("_parse_error") else 0,
                triage_data.get("vatandasa_yanit", ""),
                triage_data.get("eylem_plani", ""),
                existing_case_id
            )
            conn.execute(sql, params)
            new_id = existing_case_id
            log.info(f"[DB] Vaka güncellendi: ID={new_id}")
        else:
            sql = """
            INSERT INTO cases
                (timestamp, raw_message, sender_name, telegram_id, olay_tipi, aciliyet_skoru,
                 konum_metni, etkilenen_kisi, semptomlar, gerekli_ekip,
                 kaynak_dil, koordinator_notu, backend, parse_error, vatandasa_yanit, eylem_plani)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                now,
                raw_message,
                contact_name,
                contact_key,
                triage_data.get("olay_tipi", "belirsiz"),
                int(triage_data.get("aciliyet_skoru", 3)),
                triage_data.get("konum_metni", "Belirtilmedi"),
                int(triage_data.get("etkilenen_kisi_sayisi", 1)),
                json.dumps(triage_data.get("semptomlar", []), ensure_ascii=False),
                json.dumps(triage_data.get("gerekli_ekip", []), ensure_ascii=False),
                triage_data.get("kaynak_dil", "?"),
                triage_data.get("koordinator_notu", ""),
                backend,
                1 if triage_data.get("_parse_error") else 0,
                triage_data.get("vatandasa_yanit", ""),
                triage_data.get("eylem_plani", ""),
            )
            cur = conn.execute(sql, params)
            new_id = cur.lastrowid
            log.info(f"[DB] Yeni Vaka kaydedildi: ID={new_id}")

        if contact_key and contact_key not in {"Bilinmiyor", "", "?"}:
            conn.execute(
                """
                INSERT INTO contacts (telegram_id, sender_name, telegram_username, first_seen, last_seen, message_count, latest_case_id)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    sender_name = CASE
                        WHEN excluded.sender_name != '' AND excluded.sender_name != 'Bilinmiyor' THEN excluded.sender_name
                        ELSE contacts.sender_name
                    END,
                    telegram_username = CASE
                        WHEN excluded.telegram_username != '' THEN excluded.telegram_username
                        ELSE contacts.telegram_username
                    END,
                    last_seen = excluded.last_seen,
                    message_count = contacts.message_count + 1,
                    latest_case_id = excluded.latest_case_id
                """,
                (contact_key, contact_name, telegram_username or "", now, now, new_id),
            )
    return new_id


def get_cases(limit: int = 100, min_aciliyet: Optional[int] = None) -> List[dict]:
    """
    Vakaları aciliyet sırasına göre döndür (en kritik önce).

    Args:
        limit: Maksimum kayıt sayısı
        min_aciliyet: Bu değerden düşük aciliyet skoru olan vakalar gelsin (1=sadece kritik)
    """
    sql = "SELECT * FROM cases WHERE status = 'active'"
    params = []
    if min_aciliyet is not None:
        sql += " AND aciliyet_skoru <= ?"
        params.append(min_aciliyet)
    sql += " ORDER BY aciliyet_skoru ASC, timestamp ASC LIMIT ?"
    params.append(limit)

    with _get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    results = []
    for row in rows:
        d = dict(row)
        # JSON alanları parse et
        d["semptomlar"]   = json.loads(d.get("semptomlar") or "[]")
        d["gerekli_ekip"] = json.loads(d.get("gerekli_ekip") or "[]")
        # Dashboard uyumluluğu için alias
        d["etkilenen_kisi_sayisi"] = d.pop("etkilenen_kisi", 1)
        results.append(d)
    return results


def get_contact(telegram_id: str) -> Optional[dict]:
    """Telegram kimliğine göre en son bilinen kişi bilgisini döndür."""
    if not telegram_id:
        return None
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM contacts WHERE telegram_id = ?",
            (telegram_id,),
        ).fetchone()
    return dict(row) if row else None


def get_stats() -> dict:
    """Dashboard için özet istatistikler."""
    with _get_conn() as conn:
        total  = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        kritik = conn.execute("SELECT COUNT(*) FROM cases WHERE aciliyet_skoru = 1 AND status = 'active'").fetchone()[0]
        yuksek = conn.execute("SELECT COUNT(*) FROM cases WHERE aciliyet_skoru = 2 AND status = 'active'").fetchone()[0]
        bekle  = conn.execute("SELECT COUNT(*) FROM cases WHERE aciliyet_skoru >= 4 AND status = 'active'").fetchone()[0]
        closed = conn.execute("SELECT COUNT(*) FROM cases WHERE status = 'closed'").fetchone()[0]
        son    = conn.execute(
            "SELECT MAX(timestamp) FROM cases WHERE status = 'active'"
        ).fetchone()[0] or "—"

        # Olay tipi dağılımı
        dagilim_rows = conn.execute(
            "SELECT olay_tipi, COUNT(*) as cnt FROM cases GROUP BY olay_tipi ORDER BY cnt DESC"
        ).fetchall()
        dagilim = {r["olay_tipi"]: r["cnt"] for r in dagilim_rows}

    return {
        "toplam": total,
        "kapatilan": closed,
        "kritik": kritik,
        "yuksek_oncelik": yuksek,
        "bekleyebilir": bekle,
        "son_vaka": son,
        "olay_dagilimi": dagilim,
    }


def clear_cases() -> int:
    """Tüm vakaları sil (test/demo için). Silinen kayıt sayısını döndür."""
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM cases")
        deleted = cur.rowcount
    log.warning(f"[DB] {deleted} vaka silindi.")
    return deleted

def get_latest_case_by_telegram_id(telegram_id: str) -> Optional[dict]:
    """Belirli bir telegram_id için en son aktif vakayı döndür."""
    if not telegram_id or telegram_id in {"Bilinmiyor", "", "?"}:
        return None
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM cases WHERE telegram_id = ? AND status != 'closed' ORDER BY timestamp DESC LIMIT 1", (telegram_id,)).fetchone()
        if row:
            d = dict(row)
            d["semptomlar"] = json.loads(d.get("semptomlar") or "[]")
            d["gerekli_ekip"] = json.loads(d.get("gerekli_ekip") or "[]")
            return d
    return None

def append_message_to_case(case_id: int, append_text: str) -> bool:
    """Belirli bir vakanın raw_message alanına yeni bir mesaj ekler (Örn: Koordinatör cevabı)."""
    with _get_conn() as conn:
        row = conn.execute("SELECT raw_message FROM cases WHERE id = ?", (case_id,)).fetchone()
        if row:
            now_time = datetime.now(timezone.utc).strftime("%H:%M")
            new_raw = f"{row['raw_message']}\n\n[{now_time}] {append_text}"
            conn.execute("UPDATE cases SET raw_message = ? WHERE id = ?", (new_raw, case_id))
            return True
    return False

def close_case(case_id: int) -> bool:
    """Belirtilen vakayı kapat."""
    with _get_conn() as conn:
        cur = conn.execute("UPDATE cases SET status = 'closed' WHERE id = ?", (case_id,))
        return cur.rowcount > 0

def delete_case(case_id: int) -> bool:
    """Belirtilen vakayı kalıcı olarak sil."""
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM cases WHERE id = ?", (case_id,))
        return cur.rowcount > 0
