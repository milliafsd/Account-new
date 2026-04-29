import streamlit as st
import sqlite3
import bcrypt
import re
import struct
from pathlib import Path
from datetime import datetime
from io import BytesIO
import secrets
import base64
import pandas as pd

# ─────────────────────────────────────────────
#  Database Setup
# ─────────────────────────────────────────────
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
    _seed_default_user(conn)
    conn.commit()
    conn.close()

def _seed_default_user(conn):
    exists = conn.execute("SELECT username FROM app_users WHERE username = 'admin'").fetchone()
    if not exists:
        hashed = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        conn.execute(
            "INSERT INTO app_users (username, password_hash, display_name) VALUES (?, ?, ?)",
            ("admin", hashed, "Administrator"),
        )

# ─────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* ── Sidebar ─────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0b3d2e !important;
}
[data-testid="stSidebar"] * {
    color: #d4f0e4 !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stFileUploader label {
    color: #8ecfb0 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
    background: #0f4f39 !important;
    border: 1px solid #1a6e4e !important;
    color: #d4f0e4 !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: #d4f0e4 !important;
    border-radius: 10px !important;
    font-size: 0.85rem !important;
    padding: 0.5rem 0.8rem !important;
    text-align: left !important;
    width: 100% !important;
    transition: all 0.2s !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.1) !important;
    border-color: rgba(255,255,255,0.3) !important;
    transform: translateX(3px) !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.1) !important;
}

/* ── Main area ───────────────────────────── */
.main .block-container {
    padding-top: 1.5rem !important;
    max-width: 1200px;
}

/* ── Page header ─────────────────────────── */
.page-header {
    background: linear-gradient(135deg, #0b3d2e 0%, #1a7a52 50%, #22c97a 100%);
    padding: 1.6rem 2rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.page-header::after {
    content: '';
    position: absolute;
    right: -40px; top: -40px;
    width: 200px; height: 200px;
    border-radius: 50%;
    background: rgba(255,255,255,0.05);
}
.page-header h1 {
    color: #fff !important;
    font-size: 1.7rem !important;
    font-weight: 700 !important;
    margin: 0 !important;
}
.page-header p {
    color: rgba(255,255,255,0.75) !important;
    margin: 4px 0 0 !important;
    font-size: 0.9rem !important;
}

/* ── KPI cards ───────────────────────────── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin-bottom: 1.5rem;
}
.kpi-card {
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    position: relative;
    overflow: hidden;
}
.kpi-card.green  { background: linear-gradient(135deg,#e6faf2,#c7f3df); border-left: 4px solid #1db87a; }
.kpi-card.orange { background: linear-gradient(135deg,#fff4e5,#ffe8c5); border-left: 4px solid #e07b20; }
.kpi-card.blue   { background: linear-gradient(135deg,#e8f4ff,#c8e4fd); border-left: 4px solid #2176ae; }
.kpi-card .kpi-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; color: #5a7068; font-weight: 600; }
.kpi-card .kpi-value { font-size: 1.7rem; font-weight: 700; margin: 4px 0 0; }
.kpi-card.green  .kpi-value { color: #0b5c36; }
.kpi-card.orange .kpi-value { color: #7a3d00; }
.kpi-card.blue   .kpi-value { color: #0c3a6e; }
.kpi-card .kpi-sub { font-size: 0.75rem; color: #6b8072; margin-top: 2px; }

/* ── Form card ───────────────────────────── */
.form-card {
    background: #fff;
    border-radius: 16px;
    padding: 1.5rem;
    border: 1px solid #e6ede9;
    box-shadow: 0 2px 12px rgba(11,61,46,0.06);
}
.form-card h3 {
    color: #0b3d2e;
    font-size: 1rem;
    font-weight: 600;
    margin: 0 0 1rem 0;
    padding-bottom: 0.6rem;
    border-bottom: 2px solid #e6faf2;
}

/* ── Data table ──────────────────────────── */
[data-testid="stDataFrame"] table {
    border-collapse: collapse !important;
    font-size: 13px !important;
}
[data-testid="stDataFrame"] th {
    background: #e8f5f0 !important;
    color: #0b3d2e !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 10px 12px !important;
}
[data-testid="stDataFrame"] td {
    padding: 9px 12px !important;
    border-bottom: 1px solid #f0f4f2 !important;
    color: #1a2e24 !important;
}
[data-testid="stDataFrame"] tr:hover td {
    background: #f0faf5 !important;
}

/* ── Inputs ──────────────────────────────── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > textarea,
.stSelectbox > div > div {
    border-radius: 10px !important;
    border: 1.5px solid #d0e4d8 !important;
    transition: border 0.2s !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stTextArea > div > textarea:focus {
    border-color: #1db87a !important;
    box-shadow: 0 0 0 3px rgba(29,184,122,0.12) !important;
}

/* ── Primary button ──────────────────────── */
.main .stButton > button[kind="primary"],
.main .stFormSubmitButton > button {
    background: linear-gradient(135deg, #0b3d2e, #1a7a52) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.4rem !important;
    transition: all 0.2s !important;
    box-shadow: 0 4px 12px rgba(11,61,46,0.25) !important;
}
.main .stButton > button[kind="primary"]:hover,
.main .stFormSubmitButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 18px rgba(11,61,46,0.35) !important;
}

/* ── Badge / info boxes ──────────────────── */
.head-found {
    background: #e6faf2;
    border: 1px solid #a8e6c8;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 0.85rem;
    color: #0b5c36;
    font-weight: 600;
    margin-bottom: 6px;
}
.head-missing {
    background: #fff2f0;
    border: 1px solid #f5c0b8;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 0.85rem;
    color: #9a2e1a;
    margin-bottom: 6px;
}

/* ── Section divider ─────────────────────── */
.section-title {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #5a8070;
    font-weight: 700;
    margin: 1.2rem 0 0.6rem;
}

/* ── Login ───────────────────────────────── */
.login-wrap {
    max-width: 400px;
    margin: 5vh auto 0;
}
.login-logo {
    text-align: center;
    margin-bottom: 1.5rem;
}
.login-logo h1 {
    font-size: 1.8rem;
    color: #0b3d2e;
    font-weight: 700;
    margin: 0;
}
.login-logo .urdu-title {
    font-family: 'Noto Nastaliq Urdu', serif;
    font-size: 1.2rem;
    color: #1a7a52;
    direction: rtl;
    margin-top: 4px;
}
.login-logo .sub {
    color: #6b8072;
    font-size: 0.85rem;
    margin-top: 4px;
}
.login-card {
    background: white;
    border-radius: 20px;
    padding: 2rem;
    box-shadow: 0 8px 40px rgba(11,61,46,0.12);
    border: 1px solid #e0ede6;
}

/* ── Nav active state (via JS class trick) ── */
.nav-active button {
    background: rgba(34,201,122,0.15) !important;
    border-color: #22c97a !important;
    color: #22c97a !important;
}

/* ── Scrollbar ───────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f0f4f2; }
::-webkit-scrollbar-thumb { background: #9ecfb5; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  i18n
# ─────────────────────────────────────────────
BRAND_NAME = "JAMIA MILLIA ISLAMIA AND MASJID MADRASA WALI"
BRAND_URDU = "جامعہ ملیہ اسلامیہ و مسجد مدرسہ ولی"

I18N = {
    "en": {
        "login_title": "Madrasa Accounting",
        "username": "Username", "password": "Password",
        "login_btn": "Login", "logout": "Logout",
        "tab_income": "Income Entry", "tab_expense": "Expense Entry",
        "tab_reports": "Reports", "tab_ledger": "Ledger",
        "tab_accounts": "Accounts", "tab_overview": "Overview",
        "tab_settings": "Settings", "year": "Working Year",
        "language": "Language",
        "save_income": "Save Income", "save_expense": "Save Expense",
        "date": "Date", "code": "Account Code", "account_head": "Account Head",
        "branch": "Branch", "category": "Category",
        "receipt_no": "Receipt No", "voucher_no": "Voucher No",
        "jv_no": "JV No", "description": "Description", "amount": "Amount (Rs.)",
        "save_account_head": "Save Account",
        "total_entries": "Total Entries", "total_income": "Total Income",
        "total_expense": "Total Expense", "net_balance": "Net Balance",
        "cash_in_hand": "Cash In Hand",
        "report_type": "Report Type", "from_date": "From Date", "to_date": "To Date",
        "view_report": "View Report", "download_csv": "Download CSV",
        "monthly_flow": "Monthly Cash Flow", "top_accounts": "Top Accounts",
        "settings_title": "Year Settings", "save_settings": "Save Settings",
        "entry_type": "Entry Type", "search": "Search",
        "refresh_ledger": "Refresh", "account_not_found": "Account not found",
        "no_data": "No data found", "select_year": "Select Year",
        "create_year": "Create Year", "upload_legacy": "Import Old Data",
        "upload_files": "Upload & Import",
        "new_income": "New Income Entry", "new_expense": "New Expense Entry",
        "recent_income": "Recent Income", "recent_expenses": "Recent Expenses",
    },
    "ur": {
        "login_title": "مدرسہ اکاؤنٹنگ",
        "username": "یوزر نیم", "password": "پاس ورڈ",
        "login_btn": "لاگ ان", "logout": "لاگ آؤٹ",
        "tab_income": "انکم انٹری", "tab_expense": "ادائیگی انٹری",
        "tab_reports": "رپورٹس", "tab_ledger": "لیجر",
        "tab_accounts": "اکاؤنٹس", "tab_overview": "جائزہ",
        "tab_settings": "سیٹنگز", "year": "مالی سال",
        "language": "زبان",
        "save_income": "انکم محفوظ کریں", "save_expense": "ادائیگی محفوظ کریں",
        "date": "تاریخ", "code": "کوڈ", "account_head": "اکاؤنٹ ہیڈ",
        "branch": "برانچ", "category": "کیٹیگری",
        "receipt_no": "رسید نمبر", "voucher_no": "واؤچر نمبر",
        "jv_no": "جے وی نمبر", "description": "تفصیل", "amount": "رقم (روپے)",
        "save_account_head": "اکاؤنٹ محفوظ",
        "total_entries": "کل انٹریز", "total_income": "کل آمدن",
        "total_expense": "کل اخراجات", "net_balance": "خالص بیلنس",
        "cash_in_hand": "نقد رقم",
        "report_type": "رپورٹ کی قسم", "from_date": "شروع تاریخ", "to_date": "آخری تاریخ",
        "view_report": "رپورٹ دیکھیں", "download_csv": "CSV ڈاؤن لوڈ",
        "monthly_flow": "ماہانہ کیش فلو", "top_accounts": "اہم اکاؤنٹس",
        "settings_title": "سال کی سیٹنگز", "save_settings": "سیٹنگز محفوظ",
        "entry_type": "انٹری قسم", "search": "تلاش",
        "refresh_ledger": "ریفریش", "account_not_found": "اکاؤنٹ نہیں ملا",
        "no_data": "کوئی ڈیٹا نہیں", "select_year": "سال منتخب کریں",
        "create_year": "سال بنائیں", "upload_legacy": "پرانا ڈیٹا امپورٹ",
        "upload_files": "اپلوڈ اور امپورٹ",
        "new_income": "نئی انکم انٹری", "new_expense": "نئی ادائیگی انٹری",
        "recent_income": "حالیہ آمدن", "recent_expenses": "حالیہ اخراجات",
    },
}

def t(key):
    lang = st.session_state.get("lang", "en")
    return I18N.get(lang, I18N["en"]).get(key, key)

# ─────────────────────────────────────────────
#  DBF Import
# ─────────────────────────────────────────────
DEFAULT_LEGACY_DIR = Path("uploaded_legacy")
YEAR_PATTERN = re.compile(r"^JIID(\d{4})\.DBF$", re.IGNORECASE)

def scan_legacy_years(legacy_dir: Path):
    if not legacy_dir.exists():
        return []
    return sorted({YEAR_PATTERN.match(i.name).group(1) for i in legacy_dir.iterdir() if YEAR_PATTERN.match(i.name)})

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
    return int(num) if decimals == 0 else round(num, decimals)

def parse_dbf_bool(value):
    return value.strip().upper() in {"Y", "T"}

def iterate_dbf(path_or_bytes, is_file=True):
    handle = open(path_or_bytes, "rb") if is_file else BytesIO(path_or_bytes)
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
            length, decimals = descriptor[16], descriptor[17]
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
                chunk = raw_record[position:position + length]
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

def _choose_account_record(current, candidate):
    if current is None:
        return candidate
    sc = (1 if current["atype"] else 0, len(current["name"].strip()))
    sn = (1 if candidate["atype"] else 0, len(candidate["name"].strip()))
    return candidate if sn >= sc else current

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
        deduped[candidate["code"]] = _choose_account_record(deduped.get(candidate["code"]), candidate)
    for rec in deduped.values():
        conn.execute("""INSERT INTO accounts (code,name,atype,updated_at) VALUES (?,?,?,CURRENT_TIMESTAMP)
                        ON CONFLICT(code) DO UPDATE SET
                        name=excluded.name,
                        atype=CASE WHEN excluded.atype<>'' THEN excluded.atype ELSE accounts.atype END,
                        updated_at=CURRENT_TIMESTAMP""",
                     (rec["code"], rec["name"], rec["atype"]))
    conn.commit()
    return len(deduped)

def ensure_account(conn, code):
    if not code:
        return
    conn.execute("INSERT INTO accounts(code,name,atype,updated_at) VALUES(?,'',' ',CURRENT_TIMESTAMP) ON CONFLICT(code) DO NOTHING",
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
    conn.execute("""INSERT INTO control_settings (year,start_date,end_date,cash_in_hand,min_cash,max_cash,last_jvno,updated_at)
                    VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
                    ON CONFLICT(year) DO UPDATE SET start_date=excluded.start_date,end_date=excluded.end_date,
                    cash_in_hand=excluded.cash_in_hand,min_cash=excluded.min_cash,max_cash=excluded.max_cash,
                    last_jvno=excluded.last_jvno,updated_at=CURRENT_TIMESTAMP""",
                 (year, chosen.get("SDATE"), chosen.get("EDATE"), float(chosen.get("CIH") or 0),
                  float(chosen.get("MINCIN") or 0), float(chosen.get("MAXCIN") or 0), int(chosen.get("JVNO") or 0)))
    conn.commit()
    return 1

def import_entries(conn, legacy_dir, year):
    path = legacy_dir / f"JIID{year}.DBF"
    if not path.exists():
        return 0
    conn.execute("DELETE FROM entries WHERE year=? AND source_file<>'MODERN'", (year,))
    source_name = path.name.upper()
    count = 0
    for row_index, row in iterate_dbf(path):
        code = str(row.get("CODE") or "").strip().zfill(3)
        ensure_account(conn, code)
        conn.execute("""INSERT INTO entries (year,entry_date,jv_no,jv_ext,branch,category,code,description,
                        receipt_no,voucher_no,entry_kind,income,payment,checked_flag,group_no,source_file,source_row,updated_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
                     (year, row.get("DATE"), row.get("JVNO"), row.get("JVEXT"),
                      str(row.get("BRANCH") or "").strip(), str(row.get("CATEGORY") or "").strip(),
                      code, str(row.get("DESC1") or "").strip(), row.get("R_NO"), row.get("V_NO"),
                      str(row.get("CJ") or "").strip(), float(row.get("INCOME") or 0),
                      float(row.get("PAYMENT") or 0), 1 if row.get("CHECKED") else 0,
                      row.get("GROUP"), source_name, row_index))
        count += 1
    conn.commit()
    return count

def import_all_years(conn, legacy_dir):
    import_accounts(conn, legacy_dir)
    for y in scan_legacy_years(legacy_dir):
        import_entries(conn, legacy_dir, y)
        import_control_settings(conn, legacy_dir, y)

# ─────────────────────────────────────────────
#  Data helpers
# ─────────────────────────────────────────────
def get_years():
    conn = get_connection()
    rows = conn.execute("SELECT year, COUNT(*) as entries FROM entries GROUP BY year ORDER BY year").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_dashboard(conn, year):
    summary = conn.execute("""
        SELECT COUNT(*) AS entries_count,
               ROUND(COALESCE(SUM(income),0),2) AS total_income,
               ROUND(COALESCE(SUM(payment),0),2) AS total_payment,
               ROUND(COALESCE(SUM(income-payment),0),2) AS balance
        FROM entries WHERE year=?""", (year,)).fetchone()
    monthly = conn.execute("""
        SELECT substr(entry_date,1,7) as month,
               ROUND(SUM(income),2) as income,
               ROUND(SUM(payment),2) as payment
        FROM entries WHERE year=? AND entry_date IS NOT NULL
        GROUP BY month ORDER BY month""", (year,)).fetchall()
    top_acc = conn.execute("""
        SELECT e.code, COALESCE(a.name,'') as name,
               ROUND(SUM(e.income),2) as income,
               ROUND(SUM(e.payment),2) as payment,
               ROUND(SUM(e.income-e.payment),2) as balance
        FROM entries e LEFT JOIN accounts a ON a.code=e.code
        WHERE e.year=? GROUP BY e.code
        ORDER BY ABS(SUM(e.income-e.payment)) DESC LIMIT 10""", (year,)).fetchall()
    settings = conn.execute("SELECT * FROM control_settings WHERE year=?", (year,)).fetchone()
    return {
        "summary": dict(summary),
        "monthly": [dict(r) for r in monthly],
        "top_accounts": [dict(r) for r in top_acc],
        "settings": dict(settings) if settings else None,
    }

def fetch_entries(conn, year, date_from=None, date_to=None, code=None,
                  search=None, mode=None, limit=None, sort_ascending=False):
    sql = ["SELECT e.*, COALESCE(a.name,'') as account_name FROM entries e "
           "LEFT JOIN accounts a ON a.code=e.code WHERE e.year=?"]
    params = [year]
    if date_from:
        sql.append("AND COALESCE(e.entry_date,'') >= ?"); params.append(date_from)
    if date_to:
        sql.append("AND COALESCE(e.entry_date,'') <= ?"); params.append(date_to)
    if code:
        sql.append("AND e.code=?"); params.append(code.zfill(3))
    if search:
        wild = f"%{search}%"
        sql.append("AND (e.description LIKE ? OR e.category LIKE ? OR e.code LIKE ? OR a.name LIKE ?)")
        params.extend([wild, wild, wild, wild])
    if mode == "income":
        sql.append("AND e.income > 0")
    elif mode == "expense":
        sql.append("AND e.payment > 0")
    order = "ASC" if sort_ascending else "DESC"
    sql.append(f"ORDER BY COALESCE(e.entry_date,'') {order}, e.id {order}")
    if limit:
        sql.append("LIMIT ?"); params.append(limit)
    return conn.execute("\n".join(sql), params).fetchall()

def get_accounts(conn, year):
    rows = conn.execute("""
        SELECT a.code, a.name, a.atype,
               ROUND(COALESCE(SUM(e.income),0),2) as income,
               ROUND(COALESCE(SUM(e.payment),0),2) as payment,
               ROUND(COALESCE(SUM(e.income-e.payment),0),2) as balance,
               COUNT(e.id) as entries_count
        FROM accounts a LEFT JOIN entries e ON e.code=a.code AND e.year=?
        GROUP BY a.code ORDER BY a.code""", (year,)).fetchall()
    return [dict(r) for r in rows]

def upsert_entry(conn, payload, entry_id=None):
    year = payload["year"]
    code = payload["code"].zfill(3)
    ensure_account(conn, code)
    vals = (year, payload.get("entry_date"), payload.get("jv_no"), payload.get("jv_ext"),
            payload.get("branch", "G"), payload.get("category", "GENERAL"), code,
            payload.get("description", ""), payload.get("receipt_no"), payload.get("voucher_no"),
            payload.get("entry_kind", "C"), payload.get("income", 0), payload.get("payment", 0),
            1 if payload.get("checked_flag") else 0, payload.get("group_no"))
    if entry_id is None:
        cur = conn.execute("""INSERT INTO entries (year,entry_date,jv_no,jv_ext,branch,category,code,description,
                              receipt_no,voucher_no,entry_kind,income,payment,checked_flag,group_no,source_file,updated_at)
                              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'MODERN',CURRENT_TIMESTAMP)""", vals)
        conn.commit()
        return cur.lastrowid
    else:
        existing = conn.execute("SELECT year FROM entries WHERE id=?", (entry_id,)).fetchone()
        if not existing or existing["year"] != year:
            raise ValueError("Entry not found or year mismatch")
        conn.execute("""UPDATE entries SET year=?,entry_date=?,jv_no=?,jv_ext=?,branch=?,category=?,code=?,
                        description=?,receipt_no=?,voucher_no=?,entry_kind=?,income=?,payment=?,checked_flag=?,
                        group_no=?,updated_at=CURRENT_TIMESTAMP WHERE id=?""", vals + (entry_id,))
        conn.commit()
        return entry_id

def delete_entry(conn, entry_id, year):
    conn.execute("DELETE FROM entries WHERE id=? AND year=?", (entry_id, year))
    conn.commit()

def upsert_account(conn, code, name, atype):
    conn.execute("""INSERT INTO accounts(code,name,atype,updated_at) VALUES(?,?,?,CURRENT_TIMESTAMP)
                    ON CONFLICT(code) DO UPDATE SET name=excluded.name,atype=excluded.atype,
                    updated_at=CURRENT_TIMESTAMP""",
                 (code.zfill(3), name, atype.upper()))
    conn.commit()

def upsert_settings(conn, year, start_date, end_date, cash_in_hand, min_cash, max_cash, last_jvno):
    conn.execute("""INSERT INTO control_settings(year,start_date,end_date,cash_in_hand,min_cash,max_cash,last_jvno,updated_at)
                    VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
                    ON CONFLICT(year) DO UPDATE SET start_date=excluded.start_date,end_date=excluded.end_date,
                    cash_in_hand=excluded.cash_in_hand,min_cash=excluded.min_cash,max_cash=excluded.max_cash,
                    last_jvno=excluded.last_jvno,updated_at=CURRENT_TIMESTAMP""",
                 (year, start_date, end_date, cash_in_hand, min_cash, max_cash, last_jvno))
    conn.commit()

def build_report_data(conn, report_type, year, date_from=None, date_to=None):
    if report_type in ("ledger", "Ledger / لیجر"):
        rows = fetch_entries(conn, year, date_from=date_from, date_to=date_to, sort_ascending=True)
        cols = ["Date", "Code", "Account", "Description", "Receipt", "Voucher", "Income", "Expense"]
        data = [[r["entry_date"] or "", r["code"], r["account_name"], r["description"],
                 r["receipt_no"] or "", r["voucher_no"] or "", r["income"], r["payment"]] for r in rows]
    elif report_type in ("cashbook", "Cash Book / کیش بک"):
        rows = fetch_entries(conn, year, date_from=date_from, date_to=date_to, sort_ascending=True)
        cols = ["Date", "Code", "Account", "Description", "Receipt", "Payment", "Running Balance"]
        running = 0
        data = []
        for r in rows:
            running += r["income"] - r["payment"]
            data.append([r["entry_date"] or "", r["code"], r["account_name"], r["description"],
                         r["income"], r["payment"], round(running, 2)])
    elif report_type in ("trial-balance", "Trial Balance / میزان"):
        rows = conn.execute("""
            SELECT e.code, COALESCE(a.name,'') as name, COALESCE(a.atype,'') as atype,
                   SUM(e.income) as income, SUM(e.payment) as payment
            FROM entries e LEFT JOIN accounts a ON a.code=e.code
            WHERE e.year=? GROUP BY e.code""", (year,)).fetchall()
        cols = ["Code", "Account", "Type", "Income", "Expense", "Balance"]
        data = [[r["code"], r["name"], r["atype"], r["income"], r["payment"], r["income"] - r["payment"]] for r in rows]
    elif report_type in ("income-expense", "Income & Expense / آمدن و اخراجات"):
        rows = conn.execute("""
            SELECT e.code, COALESCE(a.name,'') as name, COALESCE(a.atype,'') as atype,
                   SUM(e.income) as income, SUM(e.payment) as payment
            FROM entries e LEFT JOIN accounts a ON a.code=e.code
            WHERE e.year=? GROUP BY e.code""", (year,)).fetchall()
        cols = ["Code", "Account", "Type", "Income", "Expense", "Net"]
        data = [[r["code"], r["name"], r["atype"], r["income"], r["payment"], r["income"] - r["payment"]] for r in rows]
    else:
        return None, None
    return cols, data

# ─────────────────────────────────────────────
#  UI helpers
# ─────────────────────────────────────────────
def page_header(title, subtitle=""):
    st.markdown(f"""
    <div class="page-header">
        <h1>{title}</h1>
        {'<p>' + subtitle + '</p>' if subtitle else ''}
    </div>""", unsafe_allow_html=True)

def kpi_row(income, expense, balance, entries):
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card green">
            <div class="kpi-label">{t('total_income')}</div>
            <div class="kpi-value">Rs. {income:,.0f}</div>
            <div class="kpi-sub">{entries} {t('total_entries')}</div>
        </div>
        <div class="kpi-card orange">
            <div class="kpi-label">{t('total_expense')}</div>
            <div class="kpi-value">Rs. {expense:,.0f}</div>
        </div>
        <div class="kpi-card blue">
            <div class="kpi-label">{t('net_balance')}</div>
            <div class="kpi-value">Rs. {balance:,.0f}</div>
        </div>
    </div>""", unsafe_allow_html=True)

def account_head_widget(conn, code_key, label=""):
    """Show live account head lookup below the code input."""
    code = st.session_state.get(code_key, "")
    if code and len(code.strip()) > 0:
        acc = conn.execute("SELECT name, atype FROM accounts WHERE code=?", (code.strip().zfill(3),)).fetchone()
        if acc and acc["name"]:
            display = acc["name"] + (f" [{acc['atype']}]" if acc["atype"].strip() else "")
            st.markdown(f'<div class="head-found">✅ {display}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="head-missing">❌ {t("account_not_found")}</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  Login page
# ─────────────────────────────────────────────
def login_page():
    st.markdown("""
    <div class="login-wrap">
        <div class="login-logo">
            <h1>📚 Madrasa Accounting</h1>
            <div class="urdu-title">مدرسہ مالیاتی نظام</div>
            <div class="sub">Jamia Millia Islamia & Masjid Madrasa Wali, Faisalabad</div>
        </div>
    </div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("👤 " + t("username"), value="admin")
            password = st.text_input("🔒 " + t("password"), type="password")
            submitted = st.form_submit_button("🔐 " + t("login_btn"), use_container_width=True)
            if submitted:
                conn = get_connection()
                user = conn.execute("SELECT * FROM app_users WHERE username=?", (username,)).fetchone()
                conn.close()
                if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
                    st.session_state.authenticated = True
                    st.session_state.user = user["username"]
                    st.session_state.display_name = user["display_name"]
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")
        st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  Main app
# ─────────────────────────────────────────────
def main_app():
    st.set_page_config(
        page_title="Madrasa Accounting",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()

    # ── Sidebar ──────────────────────────────
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:1rem 0.5rem 0.5rem;">
            <div style="font-size:1.1rem;font-weight:700;color:#a8e6c8;">📚 {BRAND_URDU}</div>
            <div style="font-size:0.75rem;color:#6baf8c;margin-top:2px;">👤 {st.session_state.get('display_name','')}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("---")
        # Year
        years = get_years()
        year_list = [y["year"] for y in years]
        if year_list:
            selected_year = st.selectbox("📅 " + t("year"), year_list, index=len(year_list) - 1)
        else:
            st.warning("No years. Create one below.")
            new_yr = st.text_input(t("select_year"), value=str(datetime.now().year))
            if st.button(t("create_year")):
                c = get_connection()
                c.execute("INSERT OR IGNORE INTO control_settings (year) VALUES (?)", (new_yr,))
                c.commit(); c.close()
                st.rerun()
            selected_year = str(datetime.now().year)
        st.session_state.year = selected_year

        # Language
        lang_choice = st.radio("🌐 " + t("language"), ["🇬🇧 English", "🇵🇰 اردو"],
                                index=0 if st.session_state.get("lang", "en") == "en" else 1,
                                horizontal=True)
        st.session_state.lang = "en" if "English" in lang_choice else "ur"

        st.markdown("---")
        # Navigation
        st.markdown('<div class="section-title">Navigation</div>', unsafe_allow_html=True)
        VIEWS = [
            ("💰", t("tab_income")),
            ("💸", t("tab_expense")),
            ("📈", t("tab_overview")),
            ("📒", t("tab_ledger")),
            ("📊", t("tab_reports")),
            ("🗂", t("tab_accounts")),
            ("⚙", t("tab_settings")),
        ]
        if "view" not in st.session_state:
            st.session_state.view = VIEWS[0][1]
        for icon, label in VIEWS:
            if st.button(f"{icon}  {label}", use_container_width=True, key=f"nav_{label}"):
                st.session_state.view = label

        st.markdown("---")
        # DBF import
        st.markdown('<div class="section-title">' + t("upload_legacy") + '</div>', unsafe_allow_html=True)
        uploaded_files = st.file_uploader("DBF files", accept_multiple_files=True, type=["dbf", "DBF"])
        if uploaded_files and st.button("📥 " + t("upload_files")):
            save_dir = Path("uploaded_legacy") / datetime.now().strftime("%Y%m%d_%H%M%S")
            save_dir.mkdir(parents=True, exist_ok=True)
            for f in uploaded_files:
                (save_dir / f.name).write_bytes(f.getbuffer())
            c = get_connection()
            import_all_years(c, save_dir)
            c.close()
            st.success("✅ Imported!")
            st.rerun()

        st.markdown("---")
        if st.button("🚪 " + t("logout"), use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    # ── Main content ──────────────────────────
    view = st.session_state.get("view", VIEWS[0][1])
    conn = get_connection()
    year = st.session_state.year

    # ── Income Entry ─────────────────────────
    if view == t("tab_income"):
        page_header("💰 " + t("tab_income"), BRAND_NAME + " · " + year)
        col1, col2 = st.columns([1, 1], gap="large")

        with col1:
            st.markdown('<div class="form-card"><h3>✍️ ' + t("new_income") + '</h3>', unsafe_allow_html=True)
            with st.form("income_form", clear_on_submit=True):
                d1, d2 = st.columns(2)
                date = d1.date_input(t("date"))
                jv = d2.number_input(t("jv_no"), min_value=0, value=0, step=1)
                code = st.text_input(t("code"), max_chars=3, key="inc_code_inp",
                                     help="3-digit account code")
                if code:
                    acc = conn.execute("SELECT name,atype FROM accounts WHERE code=?",
                                       (code.zfill(3),)).fetchone()
                    if acc and acc["name"]:
                        st.markdown(f'<div class="head-found">✅ {acc["name"]} [{acc["atype"]}]</div>',
                                    unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="head-missing">❌ {t("account_not_found")}</div>',
                                    unsafe_allow_html=True)

                b1, b2 = st.columns(2)
                branch = b1.text_input(t("branch"), value="G")
                category = b2.text_input(t("category"), value="GENERAL")
                receipt = st.number_input(t("receipt_no"), min_value=0, value=0, step=1)
                desc = st.text_area(t("description"), height=80)
                amount = st.number_input(t("amount"), min_value=0.0, format="%.2f")
                if st.form_submit_button("💾 " + t("save_income"), use_container_width=True):
                    if not code or not date:
                        st.error("Code and Date are required")
                    elif amount <= 0:
                        st.error("Amount must be greater than 0")
                    else:
                        try:
                            upsert_entry(conn, {
                                "year": year, "entry_date": date.isoformat(),
                                "code": code.zfill(3), "branch": branch, "category": category,
                                "receipt_no": receipt, "jv_no": jv, "description": desc,
                                "income": amount, "payment": 0, "entry_kind": "C",
                            })
                            st.success("✅ Income saved successfully!")
                        except Exception as e:
                            st.error(str(e))
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="section-title">🕒 ' + t("recent_income") + '</div>',
                        unsafe_allow_html=True)
            recent = fetch_entries(conn, year, mode="income", limit=15)
            if recent:
                df = pd.DataFrame([dict(r) for r in recent])[
                    ["entry_date", "code", "account_name", "description", "income"]]
                df.columns = ["Date", "Code", "Account", "Description", "Income (Rs.)"]
                st.dataframe(df.style.format({"Income (Rs.)": "{:,.2f}"}), use_container_width=True, hide_index=True)
            else:
                st.info(t("no_data"))

    # ── Expense Entry ─────────────────────────
    elif view == t("tab_expense"):
        page_header("💸 " + t("tab_expense"), BRAND_NAME + " · " + year)
        col1, col2 = st.columns([1, 1], gap="large")

        with col1:
            st.markdown('<div class="form-card"><h3>✍️ ' + t("new_expense") + '</h3>', unsafe_allow_html=True)
            with st.form("expense_form", clear_on_submit=True):
                d1, d2 = st.columns(2)
                date = d1.date_input(t("date"))
                jv = d2.number_input(t("jv_no"), min_value=0, value=0, step=1)
                code = st.text_input(t("code"), max_chars=3, key="exp_code_inp")
                if code:
                    acc = conn.execute("SELECT name,atype FROM accounts WHERE code=?",
                                       (code.zfill(3),)).fetchone()
                    if acc and acc["name"]:
                        st.markdown(f'<div class="head-found">✅ {acc["name"]} [{acc["atype"]}]</div>',
                                    unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="head-missing">❌ {t("account_not_found")}</div>',
                                    unsafe_allow_html=True)

                b1, b2 = st.columns(2)
                branch = b1.text_input(t("branch"), value="G")
                category = b2.text_input(t("category"), value="GENERAL")
                voucher = st.number_input(t("voucher_no"), min_value=0, value=0, step=1)
                desc = st.text_area(t("description"), height=80)
                amount = st.number_input(t("amount"), min_value=0.0, format="%.2f")
                if st.form_submit_button("💾 " + t("save_expense"), use_container_width=True):
                    if not code or not date:
                        st.error("Code and Date are required")
                    elif amount <= 0:
                        st.error("Amount must be greater than 0")
                    else:
                        try:
                            upsert_entry(conn, {
                                "year": year, "entry_date": date.isoformat(),
                                "code": code.zfill(3), "branch": branch, "category": category,
                                "voucher_no": voucher, "jv_no": jv, "description": desc,
                                "income": 0, "payment": amount, "entry_kind": "C",
                            })
                            st.success("✅ Expense saved successfully!")
                        except Exception as e:
                            st.error(str(e))
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="section-title">🕒 ' + t("recent_expenses") + '</div>',
                        unsafe_allow_html=True)
            recent = fetch_entries(conn, year, mode="expense", limit=15)
            if recent:
                df = pd.DataFrame([dict(r) for r in recent])[
                    ["entry_date", "code", "account_name", "description", "payment"]]
                df.columns = ["Date", "Code", "Account", "Description", "Expense (Rs.)"]
                st.dataframe(df.style.format({"Expense (Rs.)": "{:,.2f}"}), use_container_width=True, hide_index=True)
            else:
                st.info(t("no_data"))

    # ── Overview ──────────────────────────────
    elif view == t("tab_overview"):
        page_header("📈 " + t("tab_overview"), BRAND_NAME + " · " + year)
        dash = get_dashboard(conn, year)
        s = dash["summary"]
        kpi_row(s["total_income"], s["total_payment"], s["balance"], s["entries_count"])

        if s["entries_count"] > 0:
            if dash["monthly"]:
                st.markdown('<div class="section-title">' + t("monthly_flow") + '</div>',
                            unsafe_allow_html=True)
                df_m = pd.DataFrame(dash["monthly"]).set_index("month")
                df_m.columns = ["Income (Rs.)", "Expense (Rs.)"]
                st.bar_chart(df_m, use_container_width=True, color=["#1db87a", "#e07b20"])

            if dash["top_accounts"]:
                st.markdown('<div class="section-title">' + t("top_accounts") + '</div>',
                            unsafe_allow_html=True)
                df_t = pd.DataFrame(dash["top_accounts"])
                df_t.columns = ["Code", "Account", "Income", "Expense", "Balance"]
                st.dataframe(
                    df_t.style.format({"Income": "{:,.2f}", "Expense": "{:,.2f}", "Balance": "{:,.2f}"}),
                    use_container_width=True, hide_index=True)
        else:
            st.info(t("no_data"))

    # ── Ledger ────────────────────────────────
    elif view == t("tab_ledger"):
        page_header("📒 " + t("tab_ledger"), BRAND_NAME + " · " + year)
        f1, f2, f3 = st.columns([2, 1, 1])
        search = f1.text_input("🔍 " + t("search"), placeholder="Description, account, code…")
        code_filter = f2.text_input(t("code"), placeholder="e.g. 025")
        mode = f3.selectbox(t("entry_type"), ["All", "Income", "Expense"])
        d1, d2 = st.columns(2)
        date_from = d1.date_input(t("from_date"), value=None)
        date_to = d2.date_input(t("to_date"), value=None)
        mode_map = {"All": None, "Income": "income", "Expense": "expense"}

        if st.button("🔄 " + t("refresh_ledger")):
            rows = fetch_entries(
                conn, year,
                date_from=date_from.isoformat() if date_from else None,
                date_to=date_to.isoformat() if date_to else None,
                search=search or None,
                code=code_filter or None,
                mode=mode_map[mode],
                limit=500,
            )
            if rows:
                df = pd.DataFrame([dict(r) for r in rows])[
                    ["entry_date", "code", "account_name", "description", "income", "payment", "source_file"]]
                df.columns = ["Date", "Code", "Account", "Description", "Income", "Expense", "Source"]
                st.dataframe(
                    df.style.format({"Income": "{:,.2f}", "Expense": "{:,.2f}"}),
                    use_container_width=True, hide_index=True)
                # Totals
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Income", f"Rs. {df['Income'].sum():,.2f}")
                c2.metric("Total Expense", f"Rs. {df['Expense'].sum():,.2f}")
                c3.metric("Net", f"Rs. {(df['Income'].sum()-df['Expense'].sum()):,.2f}")
            else:
                st.info(t("no_data"))

    # ── Reports ───────────────────────────────
    elif view == t("tab_reports"):
        page_header("📊 " + t("tab_reports"), BRAND_NAME + " · " + year)
        report_options = {
            "Ledger / لیجر": "ledger",
            "Cash Book / کیش بک": "cashbook",
            "Trial Balance / میزان": "trial-balance",
            "Income & Expense / آمدن و اخراجات": "income-expense",
        }
        report_label = st.selectbox("📑 " + t("report_type"), list(report_options.keys()))
        c1, c2 = st.columns(2)
        date_from = c1.date_input(t("from_date"), value=None)
        date_to = c2.date_input(t("to_date"), value=None)
        if st.button("👁 " + t("view_report")):
            cols, data = build_report_data(
                conn, report_options[report_label], year,
                date_from.isoformat() if date_from else None,
                date_to.isoformat() if date_to else None,
            )
            if cols and data:
                df = pd.DataFrame(data, columns=cols)
                st.dataframe(df, use_container_width=True, hide_index=True)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "📥 " + t("download_csv"), data=csv,
                    file_name=f"{report_options[report_label]}_{year}.csv",
                    mime="text/csv")
            else:
                st.info(t("no_data"))

    # ── Accounts ──────────────────────────────
    elif view == t("tab_accounts"):
        page_header("🗂 " + t("tab_accounts"), BRAND_NAME + " · " + year)
        accounts = get_accounts(conn, year)
        if accounts:
            df = pd.DataFrame(accounts)
            df = df[["code", "name", "atype", "entries_count", "income", "payment", "balance"]]
            df.columns = ["Code", "Account Name", "Type", "Entries", "Income", "Expense", "Balance"]
            st.dataframe(
                df.style.format({"Income": "{:,.2f}", "Expense": "{:,.2f}", "Balance": "{:,.2f}"}),
                use_container_width=True, hide_index=True)
        else:
            st.info(t("no_data"))

        with st.expander("➕ Add / Edit Account Head"):
            with st.form("account_form"):
                c1, c2, c3 = st.columns([1, 2, 1])
                new_code = c1.text_input(t("code"), max_chars=3, placeholder="e.g. 048")
                new_name = c2.text_input("Account Name / اکاؤنٹ نام")
                new_type = c3.selectbox("Type", ["BS", "TA", "PA", "EX", "CR", ""])
                if st.form_submit_button("💾 " + t("save_account_head")):
                    if new_code.strip():
                        upsert_account(conn, new_code, new_name, new_type)
                        st.success(f"✅ Account {new_code.zfill(3)} saved!")
                        st.rerun()
                    else:
                        st.error("Account code is required")

    # ── Settings ──────────────────────────────
    elif view == t("tab_settings"):
        page_header("⚙ " + t("tab_settings"), BRAND_NAME + " · " + year)
        settings = conn.execute("SELECT * FROM control_settings WHERE year=?", (year,)).fetchone()
        s = dict(settings) if settings else {"start_date": "", "end_date": "",
                                              "cash_in_hand": 0.0, "min_cash": 0.0,
                                              "max_cash": 0.0, "last_jvno": 0}
        st.markdown('<div class="form-card"><h3>⚙ ' + t("settings_title") + ' — ' + year + '</h3>',
                    unsafe_allow_html=True)
        with st.form("settings_form"):
            c1, c2 = st.columns(2)
            start = c1.text_input("📅 Start Date (YYYY-MM-DD)", value=s.get("start_date") or "")
            end = c2.text_input("📅 End Date (YYYY-MM-DD)", value=s.get("end_date") or "")
            cih = c1.number_input(t("cash_in_hand"), value=float(s.get("cash_in_hand", 0)))
            minc = c2.number_input("Min Cash", value=float(s.get("min_cash", 0)))
            maxc = c1.number_input("Max Cash", value=float(s.get("max_cash", 0)))
            jvno = c2.number_input("Last JV No", value=int(s.get("last_jvno", 0)), step=1)
            if st.form_submit_button("💾 " + t("save_settings")):
                upsert_settings(conn, year, start, end, cih, minc, maxc, jvno)
                st.success("✅ Settings saved!")
        st.markdown("</div>", unsafe_allow_html=True)

        # Change password
        with st.expander("🔑 Change Password"):
            with st.form("pwd_form"):
                old_pwd = st.text_input("Current Password", type="password")
                new_pwd = st.text_input("New Password", type="password")
                confirm = st.text_input("Confirm New Password", type="password")
                if st.form_submit_button("🔐 Update Password"):
                    if new_pwd != confirm:
                        st.error("Passwords do not match")
                    elif len(new_pwd) < 6:
                        st.error("Password must be at least 6 characters")
                    else:
                        user = conn.execute("SELECT * FROM app_users WHERE username=?",
                                            (st.session_state.user,)).fetchone()
                        if user and bcrypt.checkpw(old_pwd.encode(), user["password_hash"].encode()):
                            new_hash = bcrypt.hashpw(new_pwd.encode(), bcrypt.gensalt()).decode()
                            conn.execute("UPDATE app_users SET password_hash=? WHERE username=?",
                                         (new_hash, st.session_state.user))
                            conn.commit()
                            st.success("✅ Password updated!")
                        else:
                            st.error("Current password is incorrect")

    conn.close()

# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
init_db()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.lang = "en"

if not st.session_state.authenticated:
    st.set_page_config(page_title="Madrasa Accounting", page_icon="📚", layout="centered")
    inject_css()
    login_page()
else:
    main_app()
