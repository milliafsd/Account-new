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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');

:root {
    --ink: #25182f;
    --plum: #4a173d;
    --plum-2: #641f51;
    --violet: #7b3ff2;
    --orange: #ff6b2b;
    --orange-2: #ff9b45;
    --paper: #ffffff;
    --muted: #8b8492;
    --line: rgba(74, 23, 61, 0.10);
    --wash: #f3f0f6;
    --green: #22aa53;
    --shadow: 0 22px 55px rgba(59, 28, 73, 0.13);
    --soft-shadow: 0 12px 26px rgba(59, 28, 73, 0.09);
}

html, body, [class*="css"] {
    font-family: 'Inter', 'Noto Nastaliq Urdu', system-ui, sans-serif !important;
}

.stApp {
    background:
        radial-gradient(circle at 9% 8%, rgba(255, 107, 43, 0.15), transparent 24rem),
        radial-gradient(circle at 88% 12%, rgba(123, 63, 242, 0.16), transparent 25rem),
        linear-gradient(135deg, #f7edf2 0%, #edf0f6 48%, #f7f2ea 100%) !important;
    color: var(--ink);
}

header[data-testid="stHeader"] { background: transparent !important; }
.main .block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
    max-width: 1220px;
}

/* Sidebar: image #2 dark mobile template feel */
[data-testid="stSidebar"] {
    background:
        radial-gradient(circle at 25% 6%, rgba(255, 107, 43, 0.22), transparent 10rem),
        linear-gradient(180deg, #3a1230 0%, #250c20 100%) !important;
    border-right: 0 !important;
    box-shadow: 16px 0 42px rgba(51, 17, 43, 0.24);
}
[data-testid="stSidebar"] > div:first-child { padding: 1.35rem 1rem !important; }
[data-testid="stSidebar"] * { color: #fff7fb !important; }
[data-testid="stSidebar"] hr {
    border: 0 !important;
    height: 1px !important;
    background: rgba(255,255,255,0.10) !important;
    margin: 1rem 0 !important;
}
.side-brand {
    background: linear-gradient(145deg, rgba(255,255,255,0.13), rgba(255,255,255,0.06));
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 26px;
    padding: 1.05rem;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.18), 0 16px 34px rgba(0,0,0,0.20);
}
.side-brand .brand-mark {
    width: 54px;
    height: 54px;
    border-radius: 18px;
    display: grid;
    place-items: center;
    margin-bottom: .75rem;
    font-size: 1.55rem;
    background: linear-gradient(135deg, #ffb25d, #ff552d 55%, #641f51);
    box-shadow: 0 12px 26px rgba(255, 107, 43, 0.28);
}
.side-brand .brand-title {
    font-weight: 900;
    line-height: 1.25;
    font-size: 1rem;
}
.side-brand .brand-sub {
    color: rgba(255,247,251,0.62) !important;
    font-size: .72rem;
    margin-top: .35rem;
}
[data-testid="stSidebar"] .section-title {
    color: rgba(255,247,251,0.55) !important;
    margin: 1.05rem 0 .55rem !important;
}
[data-testid="stSidebar"] .stButton > button {
    width: 100% !important;
    min-height: 3.05rem;
    border-radius: 18px !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    background: rgba(255,255,255,0.08) !important;
    color: #fff7fb !important;
    font-weight: 800 !important;
    text-align: left !important;
    padding: .72rem .9rem !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.10);
    transition: transform .18s ease, background .18s ease, border .18s ease !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    transform: translateX(4px);
    background: linear-gradient(135deg, rgba(255,107,43,0.92), rgba(255,155,69,0.84)) !important;
    border-color: rgba(255,255,255,0.30) !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stFileUploader label {
    color: rgba(255,247,251,0.65) !important;
    font-size: .72rem !important;
    font-weight: 800 !important;
    text-transform: uppercase;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: rgba(255,255,255,0.10) !important;
    border: 1px solid rgba(255,255,255,0.14) !important;
    border-radius: 16px !important;
}

/* Page header */
.page-header {
    background:
        linear-gradient(135deg, rgba(255,255,255,0.92), rgba(255,255,255,0.74)),
        linear-gradient(135deg, rgba(255,107,43,0.13), rgba(123,63,242,0.10));
    border: 1px solid rgba(255,255,255,0.78);
    border-radius: 30px;
    padding: 1.25rem 1.45rem;
    margin-bottom: 1.25rem;
    position: relative;
    overflow: hidden;
    box-shadow: var(--shadow);
}
.page-header::before {
    content: "";
    position: absolute;
    right: -42px;
    top: -52px;
    width: 190px;
    height: 190px;
    border-radius: 999px;
    background: linear-gradient(135deg, rgba(255,107,43,.24), rgba(123,63,242,.16));
}
.page-header::after {
    content: "UI/UX";
    position: absolute;
    right: 1.2rem;
    bottom: .9rem;
    color: rgba(74,23,61,0.08);
    font-weight: 900;
    font-size: 2.4rem;
}
.page-kicker {
    color: var(--orange);
    font-size: .72rem;
    text-transform: uppercase;
    letter-spacing: .12em;
    font-weight: 900;
    margin-bottom: .28rem;
}
.page-header h1 {
    color: var(--ink) !important;
    font-size: clamp(1.55rem, 3vw, 2.25rem) !important;
    line-height: 1.1 !important;
    font-weight: 900 !important;
    margin: 0 !important;
    position: relative;
    z-index: 1;
}
.page-header p {
    color: var(--muted) !important;
    margin: .45rem 0 0 !important;
    font-size: .88rem !important;
    font-weight: 700 !important;
    position: relative;
    z-index: 1;
}

/* KPI cards */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px;
    margin-bottom: 1.35rem;
}
.kpi-card {
    min-height: 132px;
    border-radius: 28px;
    padding: 1.15rem 1.25rem;
    position: relative;
    overflow: hidden;
    box-shadow: var(--soft-shadow);
}
.kpi-card::after {
    content: "";
    position: absolute;
    right: -26px;
    bottom: -38px;
    width: 125px;
    height: 125px;
    border-radius: 999px;
    background: rgba(255,255,255,0.20);
}
.kpi-card.green  { background: linear-gradient(145deg, #4a173d 0%, #7a275d 100%); }
.kpi-card.orange { background: linear-gradient(145deg, #ff6b2b 0%, #ffb25d 100%); }
.kpi-card.blue   { background: linear-gradient(145deg, #ffffff 0%, #f0edf5 100%); border: 1px solid rgba(74,23,61,.08); }
.kpi-icon {
    width: 42px;
    height: 42px;
    border-radius: 15px;
    display: grid;
    place-items: center;
    background: rgba(255,255,255,0.20);
    font-size: 1.15rem;
    margin-bottom: .55rem;
}
.kpi-card.blue .kpi-icon { background: rgba(255,107,43,.13); }
.kpi-card .kpi-label {
    font-size: .70rem;
    text-transform: uppercase;
    letter-spacing: .10em;
    color: rgba(255,255,255,.72);
    font-weight: 900;
}
.kpi-card.blue .kpi-label { color: var(--muted); }
.kpi-card .kpi-value {
    color: #fff;
    font-size: clamp(1.45rem, 3vw, 2rem);
    font-weight: 900;
    letter-spacing: -0.02em;
    margin-top: .12rem;
}
.kpi-card.blue .kpi-value { color: var(--plum); }
.kpi-card .kpi-sub {
    font-size: .78rem;
    color: rgba(255,255,255,.72);
    font-weight: 700;
    margin-top: .18rem;
}
.kpi-card.blue .kpi-sub { color: var(--muted); }

/* Forms and white mobile cards */
.form-card {
    background: rgba(255,255,255,0.90);
    border: 1px solid rgba(255,255,255,0.80);
    border-radius: 30px;
    padding: 1.25rem;
    box-shadow: var(--shadow);
    overflow: hidden;
    position: relative;
}
.form-card::before {
    content: "";
    position: absolute;
    inset: 0 0 auto 0;
    height: 6px;
    background: linear-gradient(90deg, var(--plum), var(--orange));
}
.form-card h3 {
    color: var(--plum);
    font-size: 1.03rem;
    font-weight: 900;
    margin: .25rem 0 1rem 0;
}

.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > textarea,
.stDateInput input,
.stSelectbox > div > div,
[data-baseweb="select"] > div {
    border-radius: 18px !important;
    border: 1px solid rgba(74,23,61,0.10) !important;
    background: #fff !important;
    min-height: 2.85rem;
    color: var(--ink) !important;
    box-shadow: 0 4px 12px rgba(59,28,73,0.04);
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stTextArea > div > textarea:focus {
    border-color: rgba(255,107,43,0.65) !important;
    box-shadow: 0 0 0 4px rgba(255,107,43,0.13) !important;
}
label {
    color: var(--plum) !important;
    font-weight: 800 !important;
    font-size: .78rem !important;
}

.main .stButton > button[kind="primary"],
.main .stFormSubmitButton > button,
.main .stDownloadButton > button {
    background: linear-gradient(135deg, var(--plum) 0%, var(--orange) 100%) !important;
    color: white !important;
    border: 0 !important;
    border-radius: 18px !important;
    min-height: 3rem;
    font-weight: 900 !important;
    box-shadow: 0 16px 28px rgba(255,107,43,.20) !important;
    transition: transform .18s ease, box-shadow .18s ease !important;
}
.main .stButton > button[kind="primary"]:hover,
.main .stFormSubmitButton > button:hover,
.main .stDownloadButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 20px 34px rgba(74,23,61,.22) !important;
}
.main .stButton > button:not([kind="primary"]) {
    border-radius: 16px !important;
    border: 1px solid var(--line) !important;
}

/* Tables */
.stDataFrame, [data-testid="stDataFrame"] {
    border-radius: 26px !important;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.84) !important;
    box-shadow: var(--soft-shadow) !important;
}
[data-testid="stDataFrame"] th {
    background: #4a173d !important;
    color: #fff7fb !important;
    font-weight: 900 !important;
    font-size: 11px !important;
    text-transform: uppercase;
}
[data-testid="stDataFrame"] td {
    color: var(--ink) !important;
    border-bottom: 1px solid rgba(74,23,61,0.06) !important;
}
[data-testid="stDataFrame"] tr:hover td { background: #fff5ee !important; }

.head-found {
    background: rgba(34,170,83,.10);
    border: 1px solid rgba(34,170,83,.22);
    border-radius: 16px;
    padding: 9px 12px;
    font-size: .82rem;
    color: #16743d;
    font-weight: 800;
    margin-bottom: 7px;
}
.head-missing {
    background: rgba(255,107,43,.10);
    border: 1px solid rgba(255,107,43,.22);
    border-radius: 16px;
    padding: 9px 12px;
    font-size: .82rem;
    color: #b53d11;
    font-weight: 800;
    margin-bottom: 7px;
}
.section-title {
    font-size: .74rem;
    text-transform: uppercase;
    letter-spacing: .13em;
    color: var(--plum);
    font-weight: 900;
    margin: 1.1rem 0 .65rem;
}

/* Login: image #2 phone-screen mood */
.login-wrap { max-width: 470px; margin: 4vh auto 0; }
.login-logo {
    text-align: center;
    background: linear-gradient(155deg, #4a173d 0%, #331126 100%);
    border-radius: 34px 34px 22px 22px;
    padding: 2rem 1.4rem 4rem;
    box-shadow: var(--shadow);
    position: relative;
}
.login-logo::before {
    content: "";
    width: 78px;
    height: 78px;
    border-radius: 24px;
    display: block;
    margin: 0 auto 1rem;
    background: linear-gradient(135deg, #ffbf65, #ff6b2b 55%, #7b3ff2);
    box-shadow: 0 18px 34px rgba(255,107,43,.30);
}
.login-logo h1 {
    color: #fff !important;
    font-size: 1.85rem !important;
    font-weight: 900;
    margin: 0;
}
.login-logo .urdu-title {
    color: rgba(255,247,251,.82);
    font-family: 'Noto Nastaliq Urdu', serif;
    font-size: 1.2rem;
    direction: rtl;
}
.login-logo .sub {
    color: rgba(255,247,251,.55);
    font-size: .76rem;
    margin-top: .45rem;
}
.login-card {
    background: rgba(255,255,255,0.94);
    border-radius: 28px;
    padding: 1.35rem;
    margin-top: -2.55rem;
    box-shadow: var(--shadow);
    border: 1px solid rgba(255,255,255,.90);
    position: relative;
    z-index: 3;
}

div[data-testid="stAlert"] {
    border-radius: 18px !important;
    border: 1px solid rgba(74,23,61,.08) !important;
}

[data-testid="stVegaLiteChart"],
[data-testid="stArrowVegaLiteChart"],
[data-testid="stPlotlyChart"] {
    background: rgba(255,255,255,.90);
    border: 1px solid rgba(255,255,255,.78);
    border-radius: 28px;
    padding: 1rem;
    box-shadow: var(--soft-shadow);
}
.stTabs [data-baseweb="tab-list"] {
    gap: .55rem;
    background: rgba(255,255,255,.62);
    border: 1px solid rgba(255,255,255,.75);
    padding: .45rem;
    border-radius: 22px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 16px;
    color: var(--muted);
    font-weight: 900;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, var(--plum), var(--orange));
    color: white !important;
}
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,.10);
    border-radius: 18px;
    padding: .35rem;
}

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: rgba(74,23,61,0.06); }
::-webkit-scrollbar-thumb { background: rgba(74,23,61,0.28); border-radius: 999px; }

@media (max-width: 860px) {
    .kpi-grid { grid-template-columns: 1fr; }
    .page-header { border-radius: 24px; }
}
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
        <div class="page-kicker">Madrasa Finance Dashboard</div>
        <h1>{title}</h1>
        {'<p>' + subtitle + '</p>' if subtitle else ''}
    </div>""", unsafe_allow_html=True)

def kpi_row(income, expense, balance, entries):
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card green">
            <div class="kpi-icon">💰</div>
            <div class="kpi-label">{t('total_income')}</div>
            <div class="kpi-value">Rs. {income:,.0f}</div>
            <div class="kpi-sub">{entries} {t('total_entries')}</div>
        </div>
        <div class="kpi-card orange">
            <div class="kpi-icon">💸</div>
            <div class="kpi-label">{t('total_expense')}</div>
            <div class="kpi-value">Rs. {expense:,.0f}</div>
        </div>
        <div class="kpi-card blue">
            <div class="kpi-icon">⚖️</div>
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
            <div class="page-kicker" style="color:#ffb25d;text-align:center;">Welcome</div>
            <h1>Madrasa Accounting</h1>
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
        <div class="side-brand">
            <div class="brand-mark">📚</div>
            <div class="brand-title">{BRAND_URDU}</div>
            <div class="brand-sub">👤 {st.session_state.get('display_name','')} · Finance App</div>
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
