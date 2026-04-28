import streamlit as st
import sqlite3
import bcrypt
import re
import struct
from pathlib import Path
from datetime import datetime
from io import BytesIO, StringIO
import csv
import secrets
import time
import base64
import pandas as pd

# ---------------- Database Setup ------------------
DB_PATH = Path(__file__).parent / "madrasa_modern.sqlite3"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL DEFAULT '',
            atype TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS control_settings (
            year TEXT PRIMARY KEY,
            start_date TEXT,
            end_date TEXT,
            cash_in_hand REAL NOT NULL DEFAULT 0,
            min_cash REAL NOT NULL DEFAULT 0,
            max_cash REAL NOT NULL DEFAULT 0,
            last_jvno INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year TEXT NOT NULL,
            entry_date TEXT,
            jv_no INTEGER,
            jv_ext INTEGER,
            branch TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT '',
            code TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            receipt_no INTEGER,
            voucher_no INTEGER,
            entry_kind TEXT NOT NULL DEFAULT '',
            income REAL NOT NULL DEFAULT 0,
            payment REAL NOT NULL DEFAULT 0,
            checked_flag INTEGER NOT NULL DEFAULT 0,
            group_no INTEGER,
            source_file TEXT NOT NULL DEFAULT 'MODERN',
            source_row INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(code) REFERENCES accounts(code)
        );
        CREATE TABLE IF NOT EXISTS app_users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_entries_source
            ON entries(year, source_file, source_row)
            WHERE source_row IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_entries_year_date ON entries(year, entry_date);
        CREATE INDEX IF NOT EXISTS idx_entries_year_code ON entries(year, code);
    """)
    seed_default_user(conn)
    conn.commit()
    conn.close()

def seed_default_user(conn):
    exists = conn.execute("SELECT username FROM app_users WHERE username = 'admin'").fetchone()
    if not exists:
        hashed = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        conn.execute("INSERT INTO app_users (username, password_hash, display_name) VALUES (?, ?, ?)",
                     ("admin", hashed, "Administrator"))

# ---------------- Custom CSS for Colorful Design ----------------
def local_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        html, body, [class*="css"]  {
            font-family: 'Inter', sans-serif;
        }
        .main-header {
            background: linear-gradient(135deg, #0e695c 0%, #1db89a 100%);
            padding: 2rem 1rem;
            border-radius: 16px;
            color: white;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }
        .main-header h1 {
            font-weight: 700;
            font-size: 2.2rem;
            margin: 0;
        }
        .card {
            background: white;
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            margin-bottom: 1rem;
            border: 1px solid #eef2f7;
        }
        .metric-card {
            background: white;
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.04);
            text-align: center;
            border-top: 4px solid #0e695c;
        }
        .metric-card.income {
            border-top-color: #0e695c;
            background: linear-gradient(to bottom, #f0fdf8, white);
        }
        .metric-card.expense {
            border-top-color: #b56a20;
            background: linear-gradient(to bottom, #fef8f0, white);
        }
        .metric-card.balance {
            border-top-color: #2790b0;
            background: linear-gradient(to bottom, #f0f8fc, white);
        }
        .stButton > button {
            border-radius: 10px;
            font-weight: 600;
            transition: all 0.2s;
            background-image: linear-gradient(to bottom, #0e695c, #0a5548);
            color: white;
            border: none;
        }
        .stButton > button:hover {
            background-image: linear-gradient(to bottom, #1db89a, #0e695c);
            transform: translateY(-1px);
            box-shadow: 0 4px 15px rgba(14,105,92,0.4);
        }
        .sidebar .stButton > button {
            background: #f0f4f9;
            color: #162033;
            border: 1px solid #dce3eb;
            font-weight: 500;
        }
        .sidebar .stButton > button:hover {
            background: #e0e7f0;
            color: #0e695c;
        }
        .dataframe table {
            border-collapse: collapse;
            width: 100%;
            font-size: 14px;
        }
        .dataframe th {
            background-color: #eef3fb !important;
            color: #162033 !important;
            font-weight: 600;
        }
        .dataframe tr:nth-child(even) {
            background-color: #fbfcfe;
        }
        .dataframe td, .dataframe th {
            padding: 10px 8px !important;
            border-bottom: 1px solid #eef0f5;
        }
        /* RTL Support */
        body.rtl {
            direction: rtl;
            text-align: right;
        }
        body.rtl .stRadio > div {
            flex-direction: row-reverse;
        }
    </style>
    """, unsafe_allow_html=True)

# ---------------- Colorful Header ----------------
def colored_header(title, subtitle=None):
    st.markdown(f"""
    <div class="main-header">
        <h1>{title}</h1>
        <p style="font-size: 1.1rem; opacity: 0.9; margin-top: 0.5rem;">{subtitle or ''}</p>
    </div>
    """, unsafe_allow_html=True)

# ---------------- Multilingual Support ----------------
I18N = {
    "en": {
        "login_title": "Madrasa Accounting",
        "username": "Username",
        "password": "Password",
        "login_btn": "🔐 Login",
        "logout": "🚪 Logout",
        "tab_income": "💰 Income Entry",
        "tab_expense": "💸 Expense Entry",
        "tab_reports": "📊 Reports",
        "tab_ledger": "📒 Ledger",
        "tab_accounts": "🗂 Accounts",
        "tab_overview": "📈 Overview",
        "tab_settings": "⚙ Settings",
        "year": "📅 Working Year",
        "language": "🌐 Language",
        "reload_year": "🔄 Reload Year",
        "upload_legacy": "📁 Upload Old Data",
        "import_year": "📥 Import Current Year",
        "upload_files": "📤 Upload Files",
        "save_income": "💾 Save Income",
        "save_expense": "💾 Save Expense",
        "reset": "🔄 Reset",
        "date": "📆 Date",
        "code": "🔢 Code",
        "account_head": "🏦 Account Head",
        "branch": "🏢 Branch",
        "category": "🏷 Category",
        "receipt_no": "🧾 Receipt No",
        "voucher_no": "🎫 Voucher No",
        "jv_no": "📝 JV No",
        "description": "📄 Description",
        "amount": "💵 Amount",
        "save_account_head": "💾 Save Account Head",
        "total_entries": "📋 Total Entries",
        "total_income": "💰 Total Income",
        "total_expense": "💸 Total Expense",
        "net_balance": "⚖ Net Balance",
        "opening_balance": "🔓 Opening Balance",
        "cash_in_hand": "💵 Cash In Hand",
        "edit": "✏ Edit",
        "delete": "🗑 Delete",
        "actions": "⚡ Actions",
        "report_type": "📑 Report Type",
        "from_date": "📅 From Date",
        "to_date": "📅 To Date",
        "view_report": "👁 View Report",
        "download_csv": "📥 Download CSV",
        "download_pdf": "📥 Download PDF",
        "print": "🖨 Print",
        "monthly_flow": "📊 Monthly Flow",
        "top_accounts": "🏆 Top Accounts",
        "settings_title": "⚙ Year Settings",
        "save_settings": "💾 Save Settings",
        "entry_type": "🔖 Entry Type",
        "search": "🔍 Search",
        "refresh_ledger": "🔄 Refresh Ledger",
        "code_hint": "Type the code, account head will appear automatically.",
        "account_not_found": "❌ Head not found",
        "no_data": "ℹ No data found",
        "select_year": "Select Year",
        "create_year": "Create Year",
    },
    "ur": {
        "login_title": "مدرسہ اکاؤنٹنگ",
        "username": "یوزر نیم",
        "password": "پاس ورڈ",
        "login_btn": "🔐 لاگ ان",
        "logout": "🚪 لاگ آؤٹ",
        "tab_income": "💰 انکم انٹری",
        "tab_expense": "💸 پیمنٹس انٹری",
        "tab_reports": "📊 رپورٹس",
        "tab_ledger": "📒 لیجر",
        "tab_accounts": "🗂 اکاؤنٹس",
        "tab_overview": "📈 جائزہ",
        "tab_settings": "⚙ سیٹنگز",
        "year": "📅 کام کا سال",
        "language": "🌐 زبان",
        "reload_year": "🔄 سال دوبارہ لوڈ",
        "upload_legacy": "📁 پرانا ڈیٹا اپلوڈ",
        "import_year": "📥 موجودہ سال امپورٹ",
        "upload_files": "📤 فائلیں اپلوڈ کریں",
        "save_income": "💾 انکم محفوظ کریں",
        "save_expense": "💾 پیمنٹ محفوظ کریں",
        "reset": "🔄 ری سیٹ",
        "date": "📆 تاریخ",
        "code": "🔢 کوڈ",
        "account_head": "🏦 اکاؤنٹ ہیڈ",
        "branch": "🏢 برانچ",
        "category": "🏷 کیٹیگری",
        "receipt_no": "🧾 رسید نمبر",
        "voucher_no": "🎫 واؤچر نمبر",
        "jv_no": "📝 جے وی نمبر",
        "description": "📄 تفصیل",
        "amount": "💵 رقم",
        "save_account_head": "💾 اکاؤنٹ ہیڈ محفوظ",
        "total_entries": "📋 کل انٹریز",
        "total_income": "💰 کل انکم",
        "total_expense": "💸 کل پیمنٹ",
        "net_balance": "⚖ خالص بیلنس",
        "opening_balance": "🔓 اوپننگ بیلنس",
        "cash_in_hand": "💵 کیش ان ہینڈ",
        "edit": "✏ ترمیم",
        "delete": "🗑 حذف",
        "actions": "⚡ اقدامات",
        "report_type": "📑 رپورٹ کی قسم",
        "from_date": "📅 شروع تاریخ",
        "to_date": "📅 آخری تاریخ",
        "view_report": "👁 رپورٹ دیکھیں",
        "download_csv": "📥 CSV ڈاؤن لوڈ",
        "download_pdf": "📥 PDF ڈاؤن لوڈ",
        "print": "🖨 پرنٹ",
        "monthly_flow": "📊 ماہانہ بہاؤ",
        "top_accounts": "🏆 اہم اکاؤنٹس",
        "settings_title": "⚙ سال کی سیٹنگز",
        "save_settings": "💾 سیٹنگز محفوظ",
        "entry_type": "🔖 انٹری قسم",
        "search": "🔍 تلاش",
        "refresh_ledger": "🔄 لیجر ریفریش",
        "code_hint": "کوڈ لکھتے ہی متعلقہ اکاؤنٹ ہیڈ خود نظر آئے گا۔",
        "account_not_found": "❌ ہیڈ نہیں ملا",
        "no_data": "ℹ کوئی ڈیٹا نہیں",
        "select_year": "سال منتخب کریں",
        "create_year": "سال بنائیں",
    }
}

def t(key):
    lang = st.session_state.get("lang", "en")
    return I18N.get(lang, I18N["en"]).get(key, key)

# ---------------- DBF Import Functions (unchanged, only included necessary) ----------------
BRAND_NAME = "JAMIA MILLIA ISLAMIA AND MSJID MADRASA WALI"
DEFAULT_LEGACY_DIR = Path("uploaded_legacy")
YEAR_PATTERN = re.compile(r"^JIID(\d{4})\.DBF$", re.IGNORECASE)

# Include all DBF import functions from original (scan_legacy_years, parse_dbf_date, etc.) as in previous response.
# I'll add them here but they are unchanged.
def scan_legacy_years(legacy_dir: Path):
    if not legacy_dir.exists():
        return []
    years = []
    for item in legacy_dir.iterdir():
        match = YEAR_PATTERN.match(item.name)
        if match:
            years.append(match.group(1))
    return sorted(set(years))

def parse_dbf_date(value):
    clean = value.strip()
    if not clean or clean == "00000000":
        return None
    try:
        return datetime.strptime(clean, "%Y%m%d").date().isoformat()
    except ValueError:
        return None

def parse_dbf_number(value, decimals):
    clean = value.strip()
    if not clean:
        return None
    try:
        num = float(clean)
    except ValueError:
        return None
    if decimals == 0:
        return int(num)
    return round(num, decimals)

def parse_dbf_bool(value):
    return value.strip().upper() in {"Y", "T"}

def iterate_dbf(path_or_bytes, is_file=True):
    if is_file:
        handle = open(path_or_bytes, "rb")
    else:
        handle = BytesIO(path_or_bytes)
    try:
        header = handle.read(32)
        if len(header) < 32:
            return
        record_count = struct.unpack("<I", header[4:8])[0]
        header_length = struct.unpack("<H", header[8:10])[0]
        record_length = struct.unpack("<H", header[10:12])[0]
        fields = []
        while True:
            descriptor = handle.read(32)
            if not descriptor or descriptor[0] == 0x0D:
                break
            name = descriptor[:11].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
            field_type = chr(descriptor[11])
            length = descriptor[16]
            decimals = descriptor[17]
            fields.append((name, field_type, length, decimals))
        handle.seek(header_length)
        for row_index in range(1, record_count + 1):
            raw_record = handle.read(record_length)
            if not raw_record:
                break
            if raw_record[0:1] == b"*":
                continue
            position = 1
            row = {}
            for name, field_type, length, decimals in fields:
                chunk = raw_record[position:position+length]
                position += length
                text = chunk.decode("cp1252", errors="ignore")
                if field_type == "D":
                    row[name] = parse_dbf_date(text)
                elif field_type == "N":
                    row[name] = parse_dbf_number(text, decimals)
                elif field_type == "L":
                    row[name] = parse_dbf_bool(text)
                else:
                    row[name] = text.rstrip()
            yield row_index, row
    finally:
        handle.close()

def choose_account_record(current, candidate):
    if current is None:
        return candidate
    score_current = (1 if current["atype"] else 0, len(current["name"].strip()))
    score_candidate = (1 if candidate["atype"] else 0, len(candidate["name"].strip()))
    return candidate if score_candidate >= score_current else current

def import_accounts(conn, legacy_dir):
    path = legacy_dir / "JIICODED.DBF"
    if not path.exists():
        return 0
    deduped = {}
    for _, row in iterate_dbf(path):
        code = str(row.get("CODE") or "").strip()
        if not code:
            continue
        candidate = {"code": code.zfill(3), "name": str(row.get("NAME") or "").strip(), "atype": str(row.get("ATYPE") or "").strip()}
        deduped[candidate["code"]] = choose_account_record(deduped.get(candidate["code"]), candidate)
    for rec in deduped.values():
        conn.execute("""INSERT INTO accounts (code, name, atype, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(code) DO UPDATE SET
                        name = excluded.name,
                        atype = CASE WHEN excluded.atype <> '' THEN excluded.atype ELSE accounts.atype END,
                        updated_at = CURRENT_TIMESTAMP""",
                     (rec["code"], rec["name"], rec["atype"]))
    conn.commit()
    return len(deduped)

def ensure_account(conn, code):
    if not code:
        return
    conn.execute("INSERT INTO accounts (code, name, atype, updated_at) VALUES (?, '', '', CURRENT_TIMESTAMP) ON CONFLICT(code) DO NOTHING",
                 (code.zfill(3),))

def import_control_settings(conn, legacy_dir, year):
    path = legacy_dir / f"JIIC{year}.DBF"
    if not path.exists():
        return 0
    chosen = None
    for _, row in iterate_dbf(path):
        if row.get("SDATE") or row.get("EDATE") or row.get("CIH") is not None:
            chosen = row
            break
    if not chosen:
        return 0
    conn.execute("""INSERT INTO control_settings (year, start_date, end_date, cash_in_hand, min_cash, max_cash, last_jvno, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(year) DO UPDATE SET
                    start_date = excluded.start_date, end_date = excluded.end_date,
                    cash_in_hand = excluded.cash_in_hand, min_cash = excluded.min_cash,
                    max_cash = excluded.max_cash, last_jvno = excluded.last_jvno,
                    updated_at = CURRENT_TIMESTAMP""",
                 (year, chosen.get("SDATE"), chosen.get("EDATE"), float(chosen.get("CIH") or 0),
                  float(chosen.get("MINCIN") or 0), float(chosen.get("MAXCIN") or 0), int(chosen.get("JVNO") or 0)))
    conn.commit()
    return 1

def import_entries(conn, legacy_dir, year):
    path = legacy_dir / f"JIID{year}.DBF"
    if not path.exists():
        return 0
    conn.execute("DELETE FROM entries WHERE year = ? AND source_file <> 'MODERN'", (year,))
    count = 0
    source_name = path.name.upper()
    for row_index, row in iterate_dbf(path):
        code = str(row.get("CODE") or "").strip().zfill(3)
        ensure_account(conn, code)
        conn.execute("""INSERT INTO entries (year, entry_date, jv_no, jv_ext, branch, category, code, description,
                        receipt_no, voucher_no, entry_kind, income, payment, checked_flag, group_no, source_file, source_row, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                     (year, row.get("DATE"), row.get("JVNO"), row.get("JVEXT"), str(row.get("BRANCH") or "").strip(),
                      str(row.get("CATEGORY") or "").strip(), code, str(row.get("DESC1") or "").strip(),
                      row.get("R_NO"), row.get("V_NO"), str(row.get("CJ") or "").strip(),
                      float(row.get("INCOME") or 0), float(row.get("PAYMENT") or 0),
                      1 if row.get("CHECKED") else 0, row.get("GROUP"), source_name, row_index))
        count += 1
    conn.commit()
    return count

def import_year(conn, legacy_dir, year):
    entries = import_entries(conn, legacy_dir, year)
    settings = import_control_settings(conn, legacy_dir, year)
    return {"year": year, "entries": entries, "settings": settings}

def import_all_years(conn, legacy_dir):
    import_accounts(conn, legacy_dir)
    years = scan_legacy_years(legacy_dir)
    for y in years:
        import_year(conn, legacy_dir, y)

# ---------------- Data Fetch Functions (same as before) ----------------
def get_years():
    conn = get_connection()
    rows = conn.execute("SELECT year, COUNT(*) as entries FROM entries GROUP BY year ORDER BY year").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_dashboard(conn, year):
    summary = conn.execute("""SELECT COUNT(*) AS entries_count, ROUND(COALESCE(SUM(income),0),2) AS total_income,
                              ROUND(COALESCE(SUM(payment),0),2) AS total_payment,
                              ROUND(COALESCE(SUM(income-payment),0),2) AS balance,
                              ROUND(COALESCE(SUM(CASE WHEN entry_kind='B' THEN income-payment ELSE 0 END),0),2) AS opening_balance
                              FROM entries WHERE year=?""", (year,)).fetchone()
    monthly = conn.execute("""SELECT substr(entry_date,1,7) as month, ROUND(SUM(income),2) as income, ROUND(SUM(payment),2) as payment
                              FROM entries WHERE year=? AND entry_date IS NOT NULL GROUP BY month ORDER BY month""", (year,)).fetchall()
    top_acc = conn.execute("""SELECT e.code, COALESCE(a.name,'') as name, COALESCE(a.atype,'') as atype,
                             ROUND(SUM(e.income),2) as income, ROUND(SUM(e.payment),2) as payment,
                             ROUND(SUM(e.income-e.payment),2) as balance
                             FROM entries e LEFT JOIN accounts a ON a.code=e.code
                             WHERE e.year=? GROUP BY e.code ORDER BY ABS(SUM(e.income-e.payment)) DESC LIMIT 10""", (year,)).fetchall()
    settings = conn.execute("SELECT * FROM control_settings WHERE year=?", (year,)).fetchone()
    return {"summary": dict(summary), "monthly": [dict(r) for r in monthly], "top_accounts": [dict(r) for r in top_acc],
            "settings": dict(settings) if settings else None}

def fetch_entries(conn, year, date_from=None, date_to=None, code=None, search=None, mode=None, limit=None, sort_ascending=False):
    sql = ["SELECT e.*, COALESCE(a.name,'') as account_name FROM entries e LEFT JOIN accounts a ON a.code=e.code WHERE e.year=?"]
    params = [year]
    if date_from:
        sql.append("AND COALESCE(e.entry_date,'') >= ?")
        params.append(date_from)
    if date_to:
        sql.append("AND COALESCE(e.entry_date,'') <= ?")
        params.append(date_to)
    if code:
        sql.append("AND e.code = ?")
        params.append(code.zfill(3))
    if search:
        wild = f"%{search}%"
        sql.append("AND (e.description LIKE ? OR e.category LIKE ? OR e.code LIKE ? OR a.name LIKE ?)")
        params.extend([wild, wild, wild, wild])
    if mode == 'income':
        sql.append("AND e.income > 0")
    elif mode == 'expense':
        sql.append("AND e.payment > 0")
    order = "ASC" if sort_ascending else "DESC"
    sql.append(f"ORDER BY COALESCE(e.entry_date,'') {order}, e.id {order}")
    if limit:
        sql.append("LIMIT ?")
        params.append(limit)
    return conn.execute("\n".join(sql), params).fetchall()

def get_accounts(conn, year):
    rows = conn.execute("""SELECT a.code, a.name, a.atype,
                          ROUND(COALESCE(SUM(e.income),0),2) as income,
                          ROUND(COALESCE(SUM(e.payment),0),2) as payment,
                          ROUND(COALESCE(SUM(e.income-e.payment),0),2) as balance,
                          COUNT(e.id) as entries_count
                          FROM accounts a LEFT JOIN entries e ON e.code=a.code AND e.year=?
                          GROUP BY a.code ORDER BY a.code""", (year,)).fetchall()
    return [dict(r) for r in rows]

def upsert_entry(conn, payload, entry_id=None):
    year = payload.get("year")
    code = payload.get("code").zfill(3)
    ensure_account(conn, code)
    values = (year, payload.get("entry_date"), payload.get("jv_no"), payload.get("jv_ext"),
              payload.get("branch","G"), payload.get("category","GENERAL"), code,
              payload.get("description"), payload.get("receipt_no"), payload.get("voucher_no"),
              payload.get("entry_kind","C"), payload.get("income",0), payload.get("payment",0),
              1 if payload.get("checked_flag") else 0, payload.get("group_no"))
    if entry_id is None:
        cur = conn.execute("""INSERT INTO entries (year, entry_date, jv_no, jv_ext, branch, category, code, description,
                              receipt_no, voucher_no, entry_kind, income, payment, checked_flag, group_no, source_file, updated_at)
                              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'MODERN', CURRENT_TIMESTAMP)""", values)
        conn.commit()
        return cur.lastrowid
    else:
        existing = conn.execute("SELECT year FROM entries WHERE id=?", (entry_id,)).fetchone()
        if not existing or existing["year"] != year:
            raise ValueError("Entry not found or year mismatch")
        conn.execute("""UPDATE entries SET year=?, entry_date=?, jv_no=?, jv_ext=?, branch=?, category=?, code=?,
                        description=?, receipt_no=?, voucher_no=?, entry_kind=?, income=?, payment=?, checked_flag=?,
                        group_no=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""", values + (entry_id,))
        conn.commit()
        return entry_id

def delete_entry(conn, entry_id, year):
    conn.execute("DELETE FROM entries WHERE id=? AND year=?", (entry_id, year))
    conn.commit()

def upsert_account(conn, code, name, atype):
    conn.execute("""INSERT INTO accounts (code, name, atype, updated_at) VALUES (?,?,?,CURRENT_TIMESTAMP)
                    ON CONFLICT(code) DO UPDATE SET name=excluded.name, atype=excluded.atype, updated_at=CURRENT_TIMESTAMP""",
                 (code.zfill(3), name, atype.upper()))
    conn.commit()

def upsert_settings(conn, year, start_date, end_date, cash_in_hand, min_cash, max_cash, last_jvno):
    conn.execute("""INSERT INTO control_settings (year, start_date, end_date, cash_in_hand, min_cash, max_cash, last_jvno, updated_at)
                    VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
                    ON CONFLICT(year) DO UPDATE SET start_date=excluded.start_date, end_date=excluded.end_date,
                    cash_in_hand=excluded.cash_in_hand, min_cash=excluded.min_cash, max_cash=excluded.max_cash,
                    last_jvno=excluded.last_jvno, updated_at=CURRENT_TIMESTAMP""",
                 (year, start_date, end_date, cash_in_hand, min_cash, max_cash, last_jvno))
    conn.commit()

def build_report_data(conn, report_type, year, date_from=None, date_to=None):
    if report_type == "ledger":
        rows = fetch_entries(conn, year, date_from=date_from, date_to=date_to, sort_ascending=True)
        columns = ["Date","Code","Account","Description","Receipt","Voucher","Income","Expense"]
        data = []
        for r in rows:
            data.append([r["entry_date"] or "", r["code"], r["account_name"], r["description"],
                         r["receipt_no"] or "", r["voucher_no"] or "", r["income"], r["payment"]])
    elif report_type == "cashbook":
        rows = fetch_entries(conn, year, date_from=date_from, date_to=date_to, sort_ascending=True)
        columns = ["Date","Code","Account","Description","Receipt","Payment","Balance"]
        running = 0
        data = []
        for r in rows:
            running += r["income"] - r["payment"]
            data.append([r["entry_date"] or "", r["code"], r["account_name"], r["description"],
                         r["income"], r["payment"], running])
    elif report_type == "trial-balance":
        rows = conn.execute("""SELECT e.code, COALESCE(a.name,'') as name, COALESCE(a.atype,'') as atype,
                              SUM(e.income) as income, SUM(e.payment) as payment
                              FROM entries e LEFT JOIN accounts a ON a.code=e.code
                              WHERE e.year=? GROUP BY e.code""", (year,)).fetchall()
        columns = ["Code","Account","Type","Income","Expense","Balance"]
        data = [[r["code"], r["name"], r["atype"], r["income"], r["payment"], r["income"]-r["payment"]] for r in rows]
    elif report_type == "opening-balance":
        cutoff = date_from if date_from else (conn.execute("SELECT start_date FROM control_settings WHERE year=?", (year,)).fetchone() or {"start_date":""})["start_date"]
        rows = conn.execute("""SELECT e.code, COALESCE(a.name,'') as name,
                              SUM(e.income) as income, SUM(e.payment) as payment
                              FROM entries e LEFT JOIN accounts a ON a.code=e.code
                              WHERE e.year=? AND (? IS NULL OR COALESCE(e.entry_date,'') <= ?)
                              GROUP BY e.code""", (year, cutoff, cutoff)).fetchall()
        columns = ["Code","Account","Income","Expense","Balance"]
        data = [[r["code"], r["name"], r["income"], r["payment"], r["income"]-r["payment"]] for r in rows]
    elif report_type == "income-expense":
        rows = conn.execute("""SELECT e.code, COALESCE(a.name,'') as name, COALESCE(a.atype,'') as atype,
                              SUM(e.income) as income, SUM(e.payment) as payment
                              FROM entries e LEFT JOIN accounts a ON a.code=e.code
                              WHERE e.year=? GROUP BY e.code""", (year,)).fetchall()
        columns = ["Code","Account","Type","Income","Expense","Net"]
        data = [[r["code"], r["name"], r["atype"], r["income"], r["payment"], r["income"]-r["payment"]] for r in rows]
    else:
        return None, None
    return columns, data

# ---------------- Login Page ----------------
def login_page():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
        st.image("https://img.icons8.com/clouds/100/accounting.png", width=80)  # generic icon
        st.markdown(f"<h1 style='color:#0e695c;'>{t('login_title')}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#5e6e87;'>{BRAND_NAME}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input(t("username"), value="admin")
            password = st.text_input(t("password"), type="password", value="admin123")
            if st.form_submit_button(t("login_btn")):
                conn = get_connection()
                user = conn.execute("SELECT * FROM app_users WHERE username=?", (username,)).fetchone()
                if user and bcrypt.checkpw(password.encode('utf-8'), user["password_hash"].encode('utf-8')):
                    st.session_state.authenticated = True
                    st.session_state.user = user["username"]
                    st.session_state.display_name = user["display_name"]
                    st.session_state.lang = "en"
                    conn.close()
                    st.rerun()
                else:
                    st.error("Invalid username or password")
                conn.close()

# ---------------- Main App with Colorful UI ----------------
def main_app():
    st.set_page_config(page_title="Madrasa Accounting", layout="wide", initial_sidebar_state="expanded")
    local_css()
    # Apply RTL if Urdu
    if st.session_state.get("lang") == "ur":
        st.markdown('<script>document.body.classList.add("rtl");</script>', unsafe_allow_html=True)
    else:
        st.markdown('<script>document.body.classList.remove("rtl");</script>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center; margin-bottom:20px;">
            <h2 style="color:#0e695c; font-weight:700;">📚 {BRAND_NAME}</h2>
            <p style="color:#5e6e87;">👤 {st.session_state.get('display_name','')}</p>
        </div>
        """, unsafe_allow_html=True)

        # Year selection
        years = get_years()
        year_list = [y["year"] for y in years]
        if not year_list:
            st.warning("No years available")
            selected_year = st.text_input(t("select_year"), value=datetime.now().year)
            if st.button(t("create_year")):
                conn = get_connection()
                conn.execute("INSERT OR IGNORE INTO control_settings (year) VALUES (?)", (selected_year,))
                conn.commit()
                conn.close()
                st.rerun()
        else:
            selected_year = st.selectbox(t("year"), year_list, index=len(year_list)-1)
        st.session_state.year = selected_year

        # Language toggle
        lang_names = ["🇬🇧 English", "🇵🇰 اردو"]
        lang_index = 0 if st.session_state.get("lang","en")=="en" else 1
        lang_choice = st.radio(t("language"), lang_names, index=lang_index)
        st.session_state.lang = "en" if lang_choice.startswith("🇬🇧") else "ur"

        st.markdown("---")
        # Navigation with colorful buttons
        nav_options = {
            t("tab_income"): "💰",
            t("tab_expense"): "💸",
            t("tab_reports"): "📊",
            t("tab_ledger"): "📒",
            t("tab_accounts"): "🗂",
            t("tab_overview"): "📈",
            t("tab_settings"): "⚙",
        }
        view = None
        for label, icon in nav_options.items():
            if st.button(f"{icon} {label}", use_container_width=True):
                view = label
                st.session_state.view = label

        # Upload section
        st.markdown("---")
        st.subheader(t("upload_legacy"))
        uploaded_files = st.file_uploader("Choose DBF files", accept_multiple_files=True, type=["dbf","DBF","acb","ACB","cdx","CDX","fpt","FPT"])
        if uploaded_files and st.button(t("upload_files")):
            save_dir = Path("uploaded_legacy") / datetime.now().strftime("%Y%m%d_%H%M%S")
            save_dir.mkdir(parents=True, exist_ok=True)
            for f in uploaded_files:
                with open(save_dir / f.name, "wb") as out:
                    out.write(f.getbuffer())
            conn = get_connection()
            import_all_years(conn, save_dir)
            conn.close()
            st.success("✅ Files imported successfully!")
            st.rerun()

        if st.button(f"🚪 {t('logout')}", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    # Main content
    if "view" not in st.session_state:
        st.session_state.view = t("tab_income")

    view = st.session_state.view
    conn = get_connection()
    year = st.session_state.year

    # Colorful header for each section
    if view == t("tab_income"):
        colored_header("💰 " + t("tab_income"), t("quickIncomeNote"))
        col1, col2 = st.columns(2)
        with col1:
            with st.form("income_form"):
                st.markdown("### ✍️ New Income Entry")
                date = st.date_input(t("date"))
                code = st.text_input(t("code"), max_chars=3, key="inc_code")
                # auto account head
                head_val = ""
                if code:
                    acc = conn.execute("SELECT name, atype FROM accounts WHERE code=?", (code.zfill(3),)).fetchone()
                    head_val = f"{acc['name']} ({acc['atype']})" if acc and acc['atype'] else (acc['name'] if acc else t("account_not_found"))
                st.text_input(t("account_head"), value=head_val, disabled=True)
                branch = st.text_input(t("branch"), value="G")
                category = st.text_input(t("category"), value="GENERAL")
                receipt = st.number_input(t("receipt_no"), min_value=0, value=0, step=1)
                jv = st.number_input(t("jv_no"), min_value=0, value=0, step=1)
                desc = st.text_area(t("description"))
                amount = st.number_input(t("amount"), min_value=0.0, format="%.2f")
                submitted = st.form_submit_button(t("save_income"))
                if submitted:
                    if not code or not date:
                        st.error("Code and Date required")
                    else:
                        payload = {
                            "year": year,
                            "entry_date": date.isoformat(),
                            "code": code.zfill(3),
                            "branch": branch, "category": category,
                            "receipt_no": receipt, "jv_no": jv,
                            "description": desc, "income": amount, "payment": 0,
                            "entry_kind": "C"
                        }
                        try:
                            upsert_entry(conn, payload)
                            st.success("✅ Income saved")
                        except Exception as e:
                            st.error(str(e))
        with col2:
            st.markdown("### 🕒 Recent Income")
            recent = fetch_entries(conn, year, mode="income", limit=10)
            if recent:
                df = pd.DataFrame([dict(r) for r in recent])[["entry_date","code","account_name","description","income"]]
                st.dataframe(df.style.format({"income": "{:.2f}"}), use_container_width=True)
            else:
                st.info(t("no_data"))

    elif view == t("tab_expense"):
        colored_header("💸 " + t("tab_expense"), t("quickExpenseNote"))
        col1, col2 = st.columns(2)
        with col1:
            with st.form("expense_form"):
                st.markdown("### ✍️ New Expense Entry")
                date = st.date_input(t("date"))
                code = st.text_input(t("code"), max_chars=3, key="exp_code")
                head_val = ""
                if code:
                    acc = conn.execute("SELECT name, atype FROM accounts WHERE code=?", (code.zfill(3),)).fetchone()
                    head_val = f"{acc['name']} ({acc['atype']})" if acc and acc['atype'] else (acc['name'] if acc else t("account_not_found"))
                st.text_input(t("account_head"), value=head_val, disabled=True)
                branch = st.text_input(t("branch"), value="G")
                category = st.text_input(t("category"), value="GENERAL")
                voucher = st.number_input(t("voucher_no"), min_value=0, value=0, step=1)
                jv = st.number_input(t("jv_no"), min_value=0, value=0, step=1)
                desc = st.text_area(t("description"))
                amount = st.number_input(t("amount"), min_value=0.0, format="%.2f")
                submitted = st.form_submit_button(t("save_expense"))
                if submitted:
                    if not code or not date:
                        st.error("Code and Date required")
                    else:
                        payload = {
                            "year": year,
                            "entry_date": date.isoformat(),
                            "code": code.zfill(3),
                            "branch": branch, "category": category,
                            "voucher_no": voucher, "jv_no": jv,
                            "description": desc, "income": 0, "payment": amount,
                            "entry_kind": "C"
                        }
                        try:
                            upsert_entry(conn, payload)
                            st.success("✅ Expense saved")
                        except Exception as e:
                            st.error(str(e))
        with col2:
            st.markdown("### 🕒 Recent Expenses")
            recent = fetch_entries(conn, year, mode="expense", limit=10)
            if recent:
                df = pd.DataFrame([dict(r) for r in recent])[["entry_date","code","account_name","description","payment"]]
                st.dataframe(df.style.format({"payment": "{:.2f}"}), use_container_width=True)
            else:
                st.info(t("no_data"))

    elif view == t("tab_reports"):
        colored_header("📊 " + t("tab_reports"), "Select report type and date range")
        report_type = st.selectbox(t("report_type"), ["ledger","cashbook","trial-balance","opening-balance","income-expense"])
        col1, col2 = st.columns(2)
        date_from = col1.date_input(t("from_date"), value=None)
        date_to = col2.date_input(t("to_date"), value=None)
        if st.button(t("view_report")):
            cols, data = build_report_data(conn, report_type, year,
                                           date_from.isoformat() if date_from else None,
                                           date_to.isoformat() if date_to else None)
            if cols and data:
                df = pd.DataFrame(data, columns=cols)
                st.dataframe(df.style.set_properties(**{'background-color': '#f9fafc'}), use_container_width=True)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(label=t("download_csv"), data=csv, file_name=f"{report_type}_{year}.csv", mime="text/csv")
            else:
                st.info(t("no_data"))

    elif view == t("tab_ledger"):
        colored_header("📒 " + t("tab_ledger"), "Search and filter entries")
        col1, col2, col3 = st.columns(3)
        search = col1.text_input(t("search"))
        code_filter = col2.text_input(t("code"))
        mode = col3.selectbox(t("entry_type"), ["All","Income","Expense"])
        col4, col5 = st.columns(2)
        date_from = col4.date_input(t("from_date"), value=None)
        date_to = col5.date_input(t("to_date"), value=None)
        mode_map = {"All": None, "Income": "income", "Expense": "expense"}
        if st.button(t("refresh_ledger")):
            entries = fetch_entries(conn, year,
                                    date_from=date_from.isoformat() if date_from else None,
                                    date_to=date_to.isoformat() if date_to else None,
                                    search=search if search else None,
                                    code=code_filter if code_filter else None,
                                    mode=mode_map[mode],
                                    limit=500)
            if entries:
                df = pd.DataFrame([dict(r) for r in entries])[["entry_date","code","account_name","description","income","payment","source_file","id"]]
                st.dataframe(df.style.applymap(lambda x: 'color: #0e695c' if isinstance(x, (int, float)) and x > 0 else ''), use_container_width=True)
            else:
                st.info(t("no_data"))

    elif view == t("tab_accounts"):
        colored_header("🗂 " + t("tab_accounts"), "Manage account heads")
        accounts = get_accounts(conn, year)
        if accounts:
            df = pd.DataFrame(accounts)[["code","name","atype","entries_count","balance"]]
            st.dataframe(df.style.format({"balance": "{:.2f}"}), use_container_width=True)
        else:
            st.info(t("no_data"))
        with st.expander("➕ Add New Account Head"):
            with st.form("account_form"):
                new_code = st.text_input(t("code"), max_chars=3)
                new_name = st.text_input("Account Name")
                new_type = st.selectbox("Type", ["BS","TA","PA",""], index=3)
                if st.form_submit_button(t("save_account_head")):
                    if new_code:
                        upsert_account(conn, new_code, new_name, new_type)
                        st.success("Account saved")
                        st.rerun()
                    else:
                        st.error("Enter a code")

    elif view == t("tab_overview"):
        colored_header("📈 " + t("tab_overview"), "Key performance indicators")
        dash = get_dashboard(conn, year)
        if dash["summary"]["entries_count"] > 0:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("<div class='metric-card income'>", unsafe_allow_html=True)
                st.metric(t("total_income"), f"{dash['summary']['total_income']:,.2f}")
                st.markdown("</div>", unsafe_allow_html=True)
            with c2:
                st.markdown("<div class='metric-card expense'>", unsafe_allow_html=True)
                st.metric(t("total_expense"), f"{dash['summary']['total_payment']:,.2f}")
                st.markdown("</div>", unsafe_allow_html=True)
            with c3:
                st.markdown("<div class='metric-card balance'>", unsafe_allow_html=True)
                st.metric(t("net_balance"), f"{dash['summary']['balance']:,.2f}")
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("---")
            st.subheader(t("monthly_flow"))
            if dash["monthly"]:
                df_monthly = pd.DataFrame(dash["monthly"]).set_index("month")
                st.bar_chart(df_monthly[["income","payment"]], use_container_width=True)
            st.subheader(t("top_accounts"))
            if dash["top_accounts"]:
                df_top = pd.DataFrame(dash["top_accounts"])[["code","name","balance"]]
                st.dataframe(df_top.style.format({"balance": "{:.2f}"}), use_container_width=True)
            else:
                st.info(t("no_data"))
        else:
            st.info(t("no_data"))

    elif view == t("tab_settings"):
        colored_header("⚙ " + t("tab_settings"), "Configure year parameters")
        settings = conn.execute("SELECT * FROM control_settings WHERE year=?", (year,)).fetchone()
        if not settings:
            settings = {"start_date": "", "end_date": "", "cash_in_hand":0.0, "min_cash":0.0, "max_cash":0.0, "last_jvno":0}
        with st.form("settings_form"):
            col1, col2 = st.columns(2)
            start = col1.text_input("Start Date", value=settings["start_date"] or "")
            end = col2.text_input("End Date", value=settings["end_date"] or "")
            cih = col1.number_input(t("cash_in_hand"), value=float(settings["cash_in_hand"]))
            minc = col2.number_input("Min Cash", value=float(settings["min_cash"]))
            maxc = col1.number_input("Max Cash", value=float(settings["max_cash"]))
            jvno = col2.number_input("Last JV No", value=int(settings["last_jvno"]))
            if st.form_submit_button(t("save_settings")):
                upsert_settings(conn, year, start, end, cih, minc, maxc, jvno)
                st.success("✅ Settings saved")
    conn.close()

# ---------------- Initialization ----------------
init_db()
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.lang = "en"

if st.session_state.authenticated:
    main_app()
else:
    login_page()
