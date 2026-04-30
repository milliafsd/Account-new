import streamlit as st
import sqlite3
import bcrypt
import re
import struct
from pathlib import Path
from datetime import datetime
from io import BytesIO
import pandas as pd
import os
from PIL import Image
import pytesseract  # for OCR

# ----------------------- ڈیٹا بیس کنفیگریشن -----------------------
DB_PATH = Path(__file__).parent / "madrasa_modern.sqlite3"
UPLOAD_DIR = Path(__file__).parent / "uploaded_bills"
UPLOAD_DIR.mkdir(exist_ok=True)

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
            bill_image TEXT,
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
    seed_accounts_from_pdf(conn)
    conn.commit()
    conn.close()

def seed_default_user(conn):
    exists = conn.execute("SELECT username FROM app_users WHERE username = 'admin'").fetchone()
    if not exists:
        hashed = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        conn.execute("INSERT INTO app_users (username, password_hash, display_name) VALUES (?, ?, ?)",
                     ("admin", hashed, "Administrator"))

def seed_accounts_from_pdf(conn):
    accounts = [
        ("001","SADQAT",""),("002","ZAKAT",""),("003","GENERAL DONATION",""),("004","CONSTRUCTION DONATION",""),
        ("005","FOOD EXPENSES",""),("006","QARZ-E-HASSNA",""),("007","ELECTICITY",""),("008","PHONE & POSTAGE",""),
        ("009","SUI GAS",""),("010","MISC. EXP.",""),("011","MASJID DONATION",""),("012","MISC. RENT EXP",""),
        ("013","ELECTRIC GOODS",""),("014","REPAIR & MAINTINANCE",""),("015","TRANSPORTATION",""),
        ("016","FURNITURE & FIXTURE",""),("017","MEDICEN EXP.",""),("018","PRINTING & STATIONARY",""),
        ("019","NEWS PAPERS",""),("020","LANDRY",""),("021","CLOTH & SHOES EXP.",""),("022","CROCKY",""),
        ("023","AUDIT FEE",""),("024","BOOKS",""),("025","SALARIES",""),("026","SENETARY EXP.",""),
        ("027","OTHER INCOME",""),("028","HABIB BANK A/C NO. 17271-6",""),("029","BANK CHARGES",""),
        ("030","SALES OF HIDE",""),("031","CARPETS",""),("032","OFFICE EQUIPMENTS",""),("033","BUILDING",""),
        ("034","PRAYER MATS (SAFAIN)",""),("035","CLEANLINESS ETC",""),("036","WATER PUMP",""),
        ("037","RECEIVABLE A/C",""),("038","ACCOUMULATED FUND",""),("039","EXPENSES PAYABLE","BS"),
        ("040","WAGES ETC","PA"),("041","COMPUTER","BS"),("042","LAIBRARY BOOKS",""),
        ("043","SECURITY DEPOSIT","BS"),("044","PRISES TO STUDENT",""),("045","STEPENDS",""),
        ("046","SOLAR SYSTEM","BS"),("047","TUFF TILES","BS"),
    ]
    for code, name, atype in accounts:
        conn.execute("INSERT OR IGNORE INTO accounts (code, name, atype) VALUES (?, ?, ?)", (code, name, atype.strip()))
    conn.commit()

# ----------------------- زبان -----------------------
I18N = {
    "en": {
        "login_title": "Madrasa Accounting", "username": "Username", "password": "Password",
        "login_btn": "🔐 Login", "logout": "🚪 Logout", "tab_income": "💰 Income Entry",
        "tab_expense": "💸 Expense Entry", "tab_reports": "📊 Reports", "tab_ledger": "📒 Ledger",
        "tab_accounts": "🗂 Accounts", "tab_overview": "📈 Overview", "tab_settings": "⚙ Settings",
        "year": "📅 Year", "language": "🌐 Language", "upload_legacy": "📁 Upload Old Data",
        "upload_files": "📤 Upload Files", "save_income": "💾 Save Income", "save_expense": "💾 Save Expense",
        "date": "📆 Date", "code": "🔢 Code", "account_head": "🏦 Account Head",
        "amount": "💵 Amount", "description": "📄 Description", "bill": "🧾 Bill Image (optional)",
        "auto_entry": "🧠 Auto-Read Bill (OCR)", "advanced": "⚙ Advanced Settings (Branch/Category)",
        "branch": "🏢 Branch", "category": "🏷 Category", "receipt_no": "🧾 Receipt No",
        "voucher_no": "🎫 Voucher No", "jv_no": "📝 JV No",
        "report_type": "📑 Report Type", "from_date": "📅 From", "to_date": "📅 To",
        "view_report": "👁 View", "download_csv": "📥 CSV", "no_data": "ℹ No data",
        "total_income": "💰 Total Income", "total_expense": "💸 Total Expense",
        "net_balance": "⚖ Net Balance", "monthly_flow": "📊 Monthly Flow",
        "top_accounts": "🏆 Top Accounts", "save_settings": "💾 Save Settings",
        "search": "🔍 Search", "refresh_ledger": "🔄 Refresh",
    },
    "ur": {
        "login_title": "مدرسہ اکاؤنٹنگ", "username": "یوزر نیم", "password": "پاس ورڈ",
        "login_btn": "🔐 لاگ ان", "logout": "🚪 لاگ آؤٹ", "tab_income": "💰 انکم انٹری",
        "tab_expense": "💸 پیمنٹس انٹری", "tab_reports": "📊 رپورٹس", "tab_ledger": "📒 لیجر",
        "tab_accounts": "🗂 اکاؤنٹس", "tab_overview": "📈 جائزہ", "tab_settings": "⚙ سیٹنگز",
        "year": "📅 سال", "language": "🌐 زبان", "upload_legacy": "📁 پرانا ڈیٹا",
        "upload_files": "📤 اپلوڈ", "save_income": "💾 انکم محفوظ", "save_expense": "💾 پیمنٹ محفوظ",
        "date": "📆 تاریخ", "code": "🔢 کوڈ", "account_head": "🏦 اکاؤنٹ ہیڈ",
        "amount": "💵 رقم", "description": "📄 تفصیل", "bill": "🧾 بل کی تصویر (اختیاری)",
        "auto_entry": "🧠 بل خودکار پڑھیں", "advanced": "⚙ ایڈوانسڈ (برانچ/کیٹیگری)",
        "branch": "🏢 برانچ", "category": "🏷 کیٹیگری", "receipt_no": "🧾 رسید",
        "voucher_no": "🎫 واؤچر", "jv_no": "📝 جے وی", "report_type": "📑 رپورٹ",
        "from_date": "📅 سے", "to_date": "📅 تک", "view_report": "👁 دیکھیں",
        "download_csv": "📥 CSV", "no_data": "ℹ کوئی ڈیٹا نہیں",
        "total_income": "💰 کل انکم", "total_expense": "💸 کل پیمنٹ",
        "net_balance": "⚖ خالص بیلنس", "monthly_flow": "📊 ماہانہ",
        "top_accounts": "🏆 اہم اکاؤنٹس", "save_settings": "💾 محفوظ",
        "search": "🔍 تلاش", "refresh_ledger": "🔄 ریفریش",
    },
}

def t(key):
    return I18N.get(st.session_state.get("lang", "en"), I18N["en"]).get(key, key)

# ----------------------- خوبصورت CSS -----------------------
def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600;700;800&family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
    
    /* Global Styles */
    html, body, [class*="css"] { 
        font-family: 'Rubik', 'Noto Nastaliq Urdu', sans-serif;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    }
    
    /* Main Container */
    .main {
        background: transparent;
    }
    
    /* Animated Background */
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-20px); }
    }
    
    /* Header Styles */
    .main-header {
        background: linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(59, 130, 246, 0.1) 100%);
        backdrop-filter: blur(10px);
        padding: 2.5rem 2rem;
        border-radius: 24px;
        color: white;
        margin-bottom: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, transparent 100%);
        pointer-events: none;
    }
    
    .main-header h1 { 
        font-weight: 800;
        font-size: 3rem;
        margin: 0;
        background: linear-gradient(135deg, #fff 0%, #cbd5e1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .main-header p {
        font-size: 1.2rem;
        opacity: 0.9;
        margin-top: 0.5rem;
        color: #94a3b8;
    }
    
    /* Sidebar Styles */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    [data-testid="stSidebar"] h2 {
        color: #fff;
        font-weight: 800;
        font-size: 1.5rem;
    }
    
    /* Button Styles */
    .stButton>button {
        border-radius: 16px;
        font-weight: 600;
        background: linear-gradient(135deg, rgba(168, 85, 247, 0.8) 0%, rgba(124, 58, 237, 0.8) 100%);
        color: white;
        border: 1px solid rgba(168, 85, 247, 0.3);
        transition: all 0.3s ease;
        padding: 0.75rem 1.5rem;
        font-size: 1rem;
        box-shadow: 0 4px 15px rgba(168, 85, 247, 0.3);
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, rgba(168, 85, 247, 1) 0%, rgba(124, 58, 237, 1) 100%);
        box-shadow: 0 8px 25px rgba(168, 85, 247, 0.5);
        transform: translateY(-2px);
        border-color: rgba(168, 85, 247, 0.5);
    }
    
    /* Sidebar Button Styles */
    .sidebar .stButton>button {
        background: rgba(30, 41, 59, 0.5);
        color: #e2e8f0;
        border: 1px solid rgba(148, 163, 184, 0.3);
        backdrop-filter: blur(10px);
    }
    
    .sidebar .stButton>button:hover {
        background: rgba(168, 85, 247, 0.2);
        color: #fff;
        border-color: rgba(168, 85, 247, 0.5);
        box-shadow: 0 4px 15px rgba(168, 85, 247, 0.2);
    }
    
    /* Input Styles */
    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea,
    .stNumberInput>div>div>input,
    .stSelectbox>div>div>select,
    .stDateInput>div>div>input {
        background: rgba(30, 41, 59, 0.5) !important;
        border: 1px solid rgba(148, 163, 184, 0.3) !important;
        border-radius: 12px !important;
        color: #fff !important;
        backdrop-filter: blur(10px);
        padding: 0.75rem 1rem !important;
        font-size: 0.95rem !important;
    }
    
    .stTextInput>div>div>input:focus,
    .stTextArea>div>div>textarea:focus,
    .stNumberInput>div>div>input:focus,
    .stSelectbox>div>div>select:focus,
    .stDateInput>div>div>input:focus {
        border-color: rgba(168, 85, 247, 0.5) !important;
        box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.1) !important;
    }
    
    /* Card Styles */
    .glass-card {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 20px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        border-color: rgba(168, 85, 247, 0.3);
        box-shadow: 0 12px 40px rgba(168, 85, 247, 0.2);
        transform: translateY(-2px);
    }
    
    /* Metric Cards */
    [data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        background-clip: text !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 0.9rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600 !important;
    }
    
    /* DataFrame Styles */
    .stDataFrame {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 16px;
        overflow: hidden;
    }
    
    /* Expander Styles */
    .streamlit-expanderHeader {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(148, 163, 184, 0.3);
        border-radius: 12px;
        color: #e2e8f0 !important;
        font-weight: 600;
    }
    
    .streamlit-expanderHeader:hover {
        background: rgba(168, 85, 247, 0.1);
        border-color: rgba(168, 85, 247, 0.3);
    }
    
    /* File Uploader */
    [data-testid="stFileUploader"] {
        background: rgba(30, 41, 59, 0.5);
        border: 2px dashed rgba(148, 163, 184, 0.3);
        border-radius: 16px;
        padding: 2rem;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: rgba(168, 85, 247, 0.5);
        background: rgba(168, 85, 247, 0.05);
    }
    
    /* Success/Error/Info Messages */
    .stSuccess {
        background: rgba(16, 185, 129, 0.1) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        border-radius: 12px !important;
        color: #10b981 !important;
    }
    
    .stError {
        background: rgba(239, 68, 68, 0.1) !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
        border-radius: 12px !important;
        color: #ef4444 !important;
    }
    
    .stInfo {
        background: rgba(59, 130, 246, 0.1) !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
        border-radius: 12px !important;
        color: #3b82f6 !important;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(30, 41, 59, 0.5);
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(168, 85, 247, 0.5);
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(168, 85, 247, 0.7);
    }
    
    /* Tab Styles */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(30, 41, 59, 0.5);
        border-radius: 12px;
        padding: 0.5rem;
        gap: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(168, 85, 247, 0.8), rgba(124, 58, 237, 0.8));
        color: white !important;
    }
    
    /* Form Styles */
    [data-testid="stForm"] {
        background: rgba(30, 41, 59, 0.3);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 20px;
        padding: 2rem;
        backdrop-filter: blur(10px);
    }
    
    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(148, 163, 184, 0.3), transparent);
        margin: 2rem 0;
    }
    
    /* Login Page */
    .login-container {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 24px;
        padding: 3rem;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    }
    </style>
    """, unsafe_allow_html=True)

def colored_header(title, subtitle=""):
    st.markdown(f"""
    <div class="main-header">
        <h1>{title}</h1>
        <p style="font-size:1.1rem; opacity:0.9; margin-top:0.4rem;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

# ----------------------- OCR بل پڑھنا -----------------------
def ocr_bill(image_bytes):
    """تصویر سے متن نکال کر ممکنہ تاریخ اور رقم تلاش کرنا"""
    try:
        img = Image.open(BytesIO(image_bytes))
        text = pytesseract.image_to_string(img, lang='eng+urd')  # if Urdu support needed
    except Exception:
        return None, None, None
    amount = None
    amount_pattern = re.findall(r'(\d{1,3}(?:,\d{2,3})*(?:\.\d{2}))', text)
    if not amount_pattern:
        amount_pattern = re.findall(r'(\d+(?:\.\d{2}))', text)
    if amount_pattern:
        amounts = [float(x.replace(',','')) for x in amount_pattern]
        amount = max(amounts)
    date = None
    date_pattern = re.findall(r'(\d{2}/\d{2}/\d{4})', text) or re.findall(r'(\d{4}-\d{2}-\d{2})', text)
    if date_pattern:
        date = date_pattern[0]
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    description = ' '.join(lines[:3]) if lines else text[:100]
    return date, amount, description

# ----------------------- بزنس لاجک -----------------------
def get_years():
    conn = get_connection()
    rows = conn.execute("SELECT year, COUNT(*) as cnt FROM entries GROUP BY year ORDER BY year").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_dashboard(conn, year):
    summ = conn.execute("""SELECT COUNT(*) AS entries_count, ROUND(COALESCE(SUM(income),0),2) AS total_income,
                           ROUND(COALESCE(SUM(payment),0),2) AS total_payment,
                           ROUND(COALESCE(SUM(income-payment),0),2) AS balance,
                           ROUND(COALESCE(SUM(CASE WHEN entry_kind='B' THEN income-payment ELSE 0 END),0),2) AS opening_balance
                           FROM entries WHERE year=?""", (year,)).fetchone()
    monthly = conn.execute("""SELECT substr(entry_date,1,7) as month, ROUND(SUM(income),2) as income, ROUND(SUM(payment),2) as payment
                              FROM entries WHERE year=? AND entry_date IS NOT NULL GROUP BY month ORDER BY month""", (year,)).fetchall()
    top = conn.execute("""SELECT e.code, COALESCE(a.name,'') as name, ROUND(SUM(e.income-e.payment),2) as balance
                          FROM entries e LEFT JOIN accounts a ON a.code=e.code
                          WHERE e.year=? GROUP BY e.code ORDER BY ABS(SUM(e.income-e.payment)) DESC LIMIT 10""", (year,)).fetchall()
    sets = conn.execute("SELECT * FROM control_settings WHERE year=?", (year,)).fetchone()
    return {"summary": dict(summ), "monthly": [dict(r) for r in monthly],
            "top_accounts": [dict(r) for r in top], "settings": dict(sets) if sets else None}

def fetch_entries(conn, year, **kwargs):
    sql = ["SELECT e.*, COALESCE(a.name,'') as account_name FROM entries e LEFT JOIN accounts a ON a.code=e.code WHERE e.year=?"]
    params = [year]
    if kwargs.get("date_from"):
        sql.append("AND COALESCE(e.entry_date,'') >= ?"); params.append(kwargs["date_from"])
    if kwargs.get("date_to"):
        sql.append("AND COALESCE(e.entry_date,'') <= ?"); params.append(kwargs["date_to"])
    if kwargs.get("code"):
        sql.append("AND e.code = ?"); params.append(kwargs["code"].zfill(3))
    if kwargs.get("search"):
        w = f"%{kwargs['search']}%"
        sql.append("AND (e.description LIKE ? OR e.category LIKE ? OR e.code LIKE ? OR a.name LIKE ?)")
        params.extend([w,w,w,w])
    mode = kwargs.get("mode")
    if mode == "income": sql.append("AND e.income > 0")
    elif mode == "expense": sql.append("AND e.payment > 0")
    order = "ASC" if kwargs.get("sort_ascending") else "DESC"
    sql.append(f"ORDER BY COALESCE(e.entry_date,'') {order}, e.id {order}")
    if limit := kwargs.get("limit"): sql.append("LIMIT ?"); params.append(limit)
    return conn.execute("\n".join(sql), params).fetchall()

def get_accounts(conn, year):
    rows = conn.execute("""SELECT a.code, a.name, a.atype, COUNT(e.id) as entries_count,
                          ROUND(COALESCE(SUM(e.income-e.payment),0),2) as balance
                          FROM accounts a LEFT JOIN entries e ON e.code=a.code AND e.year=?
                          GROUP BY a.code ORDER BY a.code""", (year,)).fetchall()
    return [dict(r) for r in rows]

def save_bill_image(image_bytes, entry_id, old_path=None):
    if old_path and os.path.exists(old_path):
        os.remove(old_path)
    ext = ".jpg"
    filename = f"bill_{entry_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    filepath = UPLOAD_DIR / filename
    with open(filepath, "wb") as f:
        f.write(image_bytes)
    return str(filepath)

def upsert_entry(conn, payload, entry_id=None, bill_image_bytes=None):
    year = payload.pop("year")
    code = payload.pop("code").zfill(3)
    conn.execute("INSERT OR IGNORE INTO accounts (code) VALUES (?)", (code,))
    branch = payload.get("branch", "G")
    category = payload.get("category", "GENERAL")
    vals = (year, payload.get("entry_date"), payload.get("jv_no"), payload.get("jv_ext"),
            branch, category, code, payload.get("description"),
            payload.get("receipt_no"), payload.get("voucher_no"), payload.get("entry_kind","C"),
            payload.get("income",0), payload.get("payment",0), 1 if payload.get("checked_flag") else 0,
            payload.get("group_no"))
    if entry_id is None:
        cur = conn.execute("""INSERT INTO entries (year, entry_date, jv_no, jv_ext, branch, category, code, description,
                              receipt_no, voucher_no, entry_kind, income, payment, checked_flag, group_no, source_file)
                              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'MODERN')""", vals)
        conn.commit()
        new_id = cur.lastrowid
    else:
        conn.execute("""UPDATE entries SET year=?, entry_date=?, jv_no=?, jv_ext=?, branch=?, category=?, code=?,
                        description=?, receipt_no=?, voucher_no=?, entry_kind=?, income=?, payment=?, checked_flag=?,
                        group_no=? WHERE id=?""", vals + (entry_id,))
        conn.commit()
        new_id = entry_id
    if bill_image_bytes is not None:
        old = conn.execute("SELECT bill_image FROM entries WHERE id=?", (new_id,)).fetchone()
        old_path = old["bill_image"] if old else None
        new_path = save_bill_image(bill_image_bytes, new_id, old_path)
        conn.execute("UPDATE entries SET bill_image = ? WHERE id = ?", (new_path, new_id))
        conn.commit()
    return new_id

def upsert_account(conn, code, name, atype):
    conn.execute("INSERT OR IGNORE INTO accounts (code, name, atype) VALUES (?, ?, ?) ON CONFLICT(code) DO UPDATE SET name=excluded.name, atype=excluded.atype",
                 (code.zfill(3), name, atype.upper()))
    conn.commit()

# ----------------------- رپورٹ -----------------------
def build_report(conn, rtype, year, dfrom, dto):
    if rtype == "ledger":
        rows = fetch_entries(conn, year, date_from=dfrom, date_to=dto, sort_ascending=True)
        df = pd.DataFrame([dict(r) for r in rows])[["entry_date","code","account_name","description","receipt_no","voucher_no","income","payment"]]
    elif rtype == "cashbook":
        rows = fetch_entries(conn, year, date_from=dfrom, date_to=dto, sort_ascending=True)
        bal = 0; data = []
        for r in rows:
            bal += r["income"] - r["payment"]
            data.append([r["entry_date"], r["code"], r["account_name"], r["description"], r["income"], r["payment"], bal])
        df = pd.DataFrame(data, columns=["Date","Code","Account","Description","Receipt","Payment","Balance"])
    elif rtype == "trial-balance":
        rows = conn.execute("""SELECT e.code, COALESCE(a.name,'') as name, SUM(e.income) as income, SUM(e.payment) as payment
                              FROM entries e LEFT JOIN accounts a ON a.code=e.code WHERE e.year=? GROUP BY e.code""", (year,)).fetchall()
        df = pd.DataFrame([[r["code"], r["name"], r["income"], r["payment"], r["income"]-r["payment"]] for r in rows],
                          columns=["Code","Account","Income","Expense","Balance"])
    elif rtype == "opening-balance":
        cutoff = dfrom or (conn.execute("SELECT start_date FROM control_settings WHERE year=?", (year,)).fetchone() or {"start_date":""})["start_date"]
        rows = conn.execute("""SELECT e.code, COALESCE(a.name,'') as name, SUM(e.income) as income, SUM(e.payment) as payment
                              FROM entries e LEFT JOIN accounts a ON a.code=e.code
                              WHERE e.year=? AND COALESCE(e.entry_date,'') <= ? GROUP BY e.code""", (year, cutoff)).fetchall()
        df = pd.DataFrame([[r["code"], r["name"], r["income"], r["payment"], r["income"]-r["payment"]] for r in rows],
                          columns=["Code","Account","Income","Expense","Balance"])
    elif rtype == "income-expense":
        rows = conn.execute("""SELECT e.code, COALESCE(a.name,'') as name, SUM(e.income) as income, SUM(e.payment) as payment
                              FROM entries e LEFT JOIN accounts a ON a.code=e.code WHERE e.year=? GROUP BY e.code""", (year,)).fetchall()
        df = pd.DataFrame([[r["code"], r["name"], r["income"], r["payment"], r["income"]-r["payment"]] for r in rows],
                          columns=["Code","Account","Income","Expense","Net"])
    return df

# ----------------------- لاگ ان -----------------------
def login_page():
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <div style="display: inline-block; padding: 60px 80px; background: rgba(30, 41, 59, 0.4); backdrop-filter: blur(10px); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 24px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);">
            <h1 style='color: #fff; font-size: 2.5rem; font-weight: 800; margin-bottom: 0.5rem;'>📚 مدرسہ اکاؤنٹنگ</h1>
            <p style='color: #94a3b8; font-size: 1rem;'>JAMIA MILLIA ISLAMIA AND MSJID MADRASA WALI</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input(t("username"), value="admin")
            password = st.text_input(t("password"), type="password", value="admin123")
            if st.form_submit_button(t("login_btn"), use_container_width=True):
                conn = get_connection()
                user = conn.execute("SELECT * FROM app_users WHERE username=?", (username,)).fetchone()
                if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
                    st.session_state.authenticated = True
                    st.session_state.user = user["username"]
                    st.session_state.display_name = user["display_name"]
                    st.session_state.lang = "en"
                    conn.close()
                    st.rerun()
                else:
                    st.error("غلط صارف نام یا پاس ورڈ")
                conn.close()

# ----------------------- مین ایپ -----------------------
def main_app():
    st.set_page_config(page_title="Madrasa Accounting", layout="wide", initial_sidebar_state="expanded")
    local_css()
    
    if st.session_state.get("lang") == "ur":
        st.markdown('<body dir="rtl">', unsafe_allow_html=True)

    # سائڈبار
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center; padding:1rem;">
            <h2 style="color:#fff; font-weight: 800;">📚 مدرسہ اکاؤنٹس</h2>
            <p style="color: #94a3b8;">👤 {st.session_state.get('display_name','')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        years = get_years()
        yr_list = [y["year"] for y in years]
        if yr_list:
            yr = st.selectbox(t("year"), yr_list, index=len(yr_list)-1)
        else:
            yr = st.text_input("سال درج کریں", value=str(datetime.now().year))
            if st.button("سال بنائیں"):
                conn = get_connection()
                conn.execute("INSERT OR IGNORE INTO control_settings (year) VALUES (?)", (yr,))
                conn.commit(); conn.close()
                st.rerun()
        st.session_state.year = yr

        lang_names = ["🇬🇧 English", "🇵🇰 اردو"]
        lang_idx = 0 if st.session_state.get("lang","en")=="en" else 1
        lang = st.radio(t("language"), lang_names, index=lang_idx)
        st.session_state.lang = "en" if lang.startswith("🇬🇧") else "ur"

        st.markdown("---")
        views = {
            t("tab_income"): "income", t("tab_expense"): "expense", t("tab_reports"): "reports",
            t("tab_ledger"): "ledger", t("tab_accounts"): "accounts", t("tab_overview"): "overview",
            t("tab_settings"): "settings",
        }
        for label, vid in views.items():
            if st.button(label, use_container_width=True):
                st.session_state.view = vid

        st.markdown("---")
        if st.button(t("logout"), use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    # مواد
    conn = get_connection()
    year = st.session_state.year
    if "view" not in st.session_state:
        st.session_state.view = "income"
    view = st.session_state.view

    if view == "income":
        colored_header("💰 " + t("tab_income"), "روزانہ انکم (بل اپ لوڈ کے ساتھ)")
        with st.form("inc_form"):
            col1, col2 = st.columns(2)
            date = col1.date_input(t("date"))
            code = col2.text_input(t("code"), max_chars=3, key="ic")
            head = ""
            if code:
                acc = conn.execute("SELECT name, atype FROM accounts WHERE code=?", (code.zfill(3),)).fetchone()
                head = f"{acc['name']} ({acc['atype']})" if acc and acc['atype'] else (acc['name'] if acc else "")
            st.text_input(t("account_head"), value=head, disabled=True)
            desc = st.text_area(t("description"))
            amount = st.number_input(t("amount"), min_value=0.0, format="%.2f", key="inc_amt")
            bill_file = st.file_uploader(t("bill"), type=["jpg","jpeg","png","pdf"], key="inc_bill")
            
            with st.expander(t("advanced")):
                branch = st.text_input(t("branch"), value="G")
                category = st.text_input(t("category"), value="GENERAL")
                receipt_no = st.number_input(t("receipt_no"), value=0, step=1)
                jv_no = st.number_input(t("jv_no"), value=0, step=1)
            
            submitted = st.form_submit_button(t("save_income"))
            if submitted:
                if not code or not date:
                    st.error("کوڈ اور تاریخ ضروری ہیں")
                else:
                    payload = {"year": year, "entry_date": date.isoformat(), "code": code.zfill(3),
                               "description": desc, "income": amount, "payment": 0, "entry_kind": "C",
                               "branch": branch, "category": category,
                               "receipt_no": receipt_no, "jv_no": jv_no}
                    bill_bytes = bill_file.getvalue() if bill_file else None
                    try:
                        upsert_entry(conn, payload, bill_image_bytes=bill_bytes)
                        st.success("✅ انکم محفوظ ہو گئی")
                    except Exception as e:
                        st.error(str(e))
        
        st.subheader("📋 حالیہ انکم")
        recent = fetch_entries(conn, year, mode="income", limit=10)
        if recent:
            for r in recent:
                cols = st.columns([2,2,2,2,1])
                cols[0].write(r["entry_date"])
                cols[1].write(r["code"] + " - " + r["account_name"])
                cols[2].write(r["description"])
                cols[3].write(f"{r['income']:,.2f}")
                if r["bill_image"] and os.path.exists(r["bill_image"]):
                    cols[4].image(r["bill_image"], width=60)
        else:
            st.info(t("no_data"))

    elif view == "expense":
        colored_header("💸 " + t("tab_expense"), "روزانہ اخراجات (بل اپ لوڈ)")
        with st.form("exp_form"):
            col1, col2 = st.columns(2)
            date = col1.date_input(t("date"))
            code = col2.text_input(t("code"), max_chars=3, key="ec")
            head = ""
            if code:
                acc = conn.execute("SELECT name, atype FROM accounts WHERE code=?", (code.zfill(3),)).fetchone()
                head = f"{acc['name']} ({acc['atype']})" if acc and acc['atype'] else (acc['name'] if acc else "")
            st.text_input(t("account_head"), value=head, disabled=True)
            desc = st.text_area(t("description"))
            amount = st.number_input(t("amount"), min_value=0.0, format="%.2f", key="exp_amt")
            bill_file = st.file_uploader(t("bill"), type=["jpg","jpeg","png","pdf"], key="exp_bill")
            
            with st.expander(t("advanced")):
                branch = st.text_input(t("branch"), value="G")
                category = st.text_input(t("category"), value="GENERAL")
                voucher_no = st.number_input(t("voucher_no"), value=0, step=1)
                jv_no = st.number_input(t("jv_no"), value=0, step=1)
            
            submitted = st.form_submit_button(t("save_expense"))
            if submitted:
                if not code or not date:
                    st.error("کوڈ اور تاریخ ضروری ہیں")
                else:
                    payload = {"year": year, "entry_date": date.isoformat(), "code": code.zfill(3),
                               "description": desc, "income": 0, "payment": amount, "entry_kind": "C",
                               "branch": branch, "category": category,
                               "voucher_no": voucher_no, "jv_no": jv_no}
                    bill_bytes = bill_file.getvalue() if bill_file else None
                    try:
                        upsert_entry(conn, payload, bill_image_bytes=bill_bytes)
                        st.success("✅ اخراجات محفوظ ہو گئے")
                    except Exception as e:
                        st.error(str(e))
        
        st.subheader("📋 حالیہ اخراجات")
        recent = fetch_entries(conn, year, mode="expense", limit=10)
        if recent:
            for r in recent:
                cols = st.columns([2,2,2,2,1])
                cols[0].write(r["entry_date"])
                cols[1].write(r["code"] + " - " + r["account_name"])
                cols[2].write(r["description"])
                cols[3].write(f"{r['payment']:,.2f}")
                if r["bill_image"] and os.path.exists(r["bill_image"]):
                    cols[4].image(r["bill_image"], width=60)
        else:
            st.info(t("no_data"))

    elif view == "reports":
        colored_header("📊 " + t("tab_reports"))
        rtype = st.selectbox(t("report_type"), ["ledger","cashbook","trial-balance","opening-balance","income-expense"])
        c1, c2 = st.columns(2)
        dfrom = c1.date_input(t("from_date"))
        dto = c2.date_input(t("to_date"))
        if st.button(t("view_report")):
            df = build_report(conn, rtype, year, dfrom.isoformat() if dfrom else None, dto.isoformat() if dto else None)
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(t("download_csv"), csv, f"{rtype}_{year}.csv", "text/csv")

    elif view == "ledger":
        colored_header("📒 " + t("tab_ledger"))
        col1, col2, col3 = st.columns(3)
        search = col1.text_input(t("search"))
        code = col2.text_input(t("code"))
        mode = col3.selectbox("قسم", ["تمام","انکم","اخراجات"])
        c4, c5 = st.columns(2)
        dfrom = c4.date_input(t("from_date"))
        dto = c5.date_input(t("to_date"))
        mode_map = {"تمام": None, "انکم": "income", "اخراجات": "expense"}
        if st.button(t("refresh_ledger")):
            entries = fetch_entries(conn, year, date_from=dfrom.isoformat() if dfrom else None, date_to=dto.isoformat() if dto else None,
                                    search=search or None, code=code or None, mode=mode_map[mode], limit=500)
            if entries:
                for e in entries:
                    cols = st.columns([1.5,1,2,2,1,1,1])
                    cols[0].write(e["entry_date"] or "-")
                    cols[1].write(e["code"])
                    cols[2].write(e["account_name"])
                    cols[3].write(e["description"])
                    if e["income"]:
                        cols[4].write(f"⬆ {e['income']:,.2f}")
                    if e["payment"]:
                        cols[5].write(f"⬇ {e['payment']:,.2f}")
                    if e["bill_image"] and os.path.exists(e["bill_image"]):
                        cols[6].image(e["bill_image"], width=50)
            else:
                st.info(t("no_data"))

    elif view == "accounts":
        colored_header("🗂 " + t("tab_accounts"))
        accounts = get_accounts(conn, year)
        if accounts:
            df = pd.DataFrame(accounts)[["code","name","atype","entries_count","balance"]]
            st.dataframe(df.style.format({"balance":"{:.2f}"}), use_container_width=True)
        else:
            st.info(t("no_data"))
        with st.expander("➕ نیا اکاؤنٹ شامل کریں"):
            with st.form("add_acc"):
                nc = st.text_input(t("code"), max_chars=3)
                nn = st.text_input("نام")
                nt = st.selectbox("ٹائپ", ["","BS","TA","PA"])
                if st.form_submit_button("محفوظ کریں"):
                    if nc:
                        upsert_account(conn, nc, nn, nt)
                        st.success("اکاؤنٹ محفوظ ہو گیا")
                        st.rerun()

    elif view == "overview":
        colored_header("📈 " + t("tab_overview"))
        dash = get_dashboard(conn, year)
        if dash["summary"]["entries_count"]:
            c1, c2, c3 = st.columns(3)
            c1.metric(t("total_income"), f"{dash['summary']['total_income']:,.2f}")
            c2.metric(t("total_expense"), f"{dash['summary']['total_payment']:,.2f}")
            c3.metric(t("net_balance"), f"{dash['summary']['balance']:,.2f}")
            if dash["monthly"]:
                dfm = pd.DataFrame(dash["monthly"]).set_index("month")[["income","payment"]]
                st.subheader(t("monthly_flow"))
                st.bar_chart(dfm, use_container_width=True)
            if dash["top_accounts"]:
                st.subheader(t("top_accounts"))
                dft = pd.DataFrame(dash["top_accounts"])[["code","name","balance"]]
                st.dataframe(dft.style.format({"balance":"{:.2f}"}), use_container_width=True)
        else:
            st.info(t("no_data"))

    elif view == "settings":
        colored_header("⚙ " + t("tab_settings"))
        sets = conn.execute("SELECT * FROM control_settings WHERE year=?", (year,)).fetchone()
        if not sets:
            sets = {"start_date":"", "end_date":"", "cash_in_hand":0, "min_cash":0, "max_cash":0, "last_jvno":0}
        with st.form("sets_form"):
            c1, c2 = st.columns(2)
            start = c1.text_input("شروع تاریخ", value=sets["start_date"] or "")
            end = c2.text_input("اختتام تاریخ", value=sets["end_date"] or "")
            cih = c1.number_input("کیش ان ہینڈ", value=float(sets["cash_in_hand"]))
            minc = c2.number_input("کم از کم کیش", value=float(sets["min_cash"]))
            maxc = c1.number_input("زیادہ سے زیادہ کیش", value=float(sets["max_cash"]))
            jvno = c2.number_input("آخری جے وی نمبر", value=int(sets["last_jvno"]))
            if st.form_submit_button(t("save_settings")):
                conn.execute("""INSERT OR IGNORE INTO control_settings (year, start_date, end_date, cash_in_hand, min_cash, max_cash, last_jvno)
                                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                             (year, start, end, cih, minc, maxc, jvno))
                conn.commit()
                st.success("سیٹنگز محفوظ ہو گئیں")
    conn.close()

# ----------------------- ایپ چلائیں -----------------------
init_db()
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.lang = "en"

if st.session_state.authenticated:
    main_app()
else:
    login_page()
