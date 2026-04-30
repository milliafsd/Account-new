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
        ("001","صدقہ",""),("002","زکٰوۃ",""),("003","عام ڈونیشن",""),("004","تعمیر ڈونیشن",""),
        ("005","کھانے کی اشیاء",""),("006","قرض ِحسنہ",""),("007","بجلی",""),("008","فون و ڈاک",""),
        ("009","سوئی گیس",""),("010","مختلف اخراجات",""),("011","مسجد ڈونیشن",""),("012","کرائے کے اخراجات",""),
        ("013","الیکٹرک سامان",""),("014","مرمت و دیکھ بھال",""),("015","ٹرانسپورٹ",""),
        ("016","فرنیچر فکسچر",""),("017","دوائی اخراجات",""),("018","پرنٹنگ اسٹیشنری",""),
        ("019","اخبارات",""),("020","دھلائی",""),("021","کپڑے جوتے",""),("022","برتن",""),
        ("023","آڈٹ فیس",""),("024","کتابیں",""),("025","تنخواہیں",""),("026","سیکریٹری اخراجات",""),
        ("027","دوسری آمدنی",""),("028","ہبیب بینک",""),("029","بینک چارجز",""),
        ("030","چمڑے کی فروخت",""),("031","قالین",""),("032","آفس سازوسامان",""),("033","عمارت",""),
        ("034","نمازوں کی چادریں",""),("035","صفائی وغیرہ",""),("036","پانی کی پمپ",""),
        ("037","وصول کریڈٹ",""),("038","جمع شدہ فنڈ",""),("039","ادائیگی سے واجب","BS"),
        ("040","اجرت وغیرہ","PA"),("041","کمپیوٹر","BS"),("042","لائبریری کتابیں",""),
        ("043","سیکیورٹی ڈپوزٹ","BS"),("044","طلاب کو انعام",""),("045","وظائف",""),
        ("046","سولر سسٹم","BS"),("047","ٹائل","BS"),
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
        "login_btn": "🔐 لاگ ان", "logout": "🚪 لاگ آؤٹ", "tab_income": "💰 آمدنی انٹری",
        "tab_expense": "💸 اخراجات انٹری", "tab_reports": "📊 رپورٹس", "tab_ledger": "📒 لیجر",
        "tab_accounts": "🗂 اکاؤنٹس", "tab_overview": "📈 جائزہ", "tab_settings": "⚙ سیٹنگز",
        "year": "📅 سال", "language": "🌐 زبان", "upload_legacy": "📁 پرانا ڈیٹا",
        "upload_files": "📤 اپ لوڈ", "save_income": "💾 آمدنی محفوظ", "save_expense": "💾 اخراجات محفوظ",
        "date": "📆 تاریخ", "code": "🔢 کوڈ", "account_head": "🏦 اکاؤنٹ ہیڈ",
        "amount": "💵 رقم", "description": "📄 تفصیل", "bill": "🧾 بل کی تصویر",
        "auto_entry": "🧠 بل خودکار", "advanced": "⚙ ایڈوانسڈ",
        "branch": "🏢 برانچ", "category": "🏷 کیٹیگری", "receipt_no": "🧾 رسید",
        "voucher_no": "🎫 واؤچر", "jv_no": "📝 جے وی", "report_type": "📑 رپورٹ",
        "from_date": "📅 سے", "to_date": "📅 تک", "view_report": "👁 دیکھیں",
        "download_csv": "📥 CSV", "no_data": "ℹ کوئی ڈیٹا نہیں",
        "total_income": "💰 کل آمدنی", "total_expense": "💸 کل اخراجات",
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Poppins:wght@400;500;600;700;800&family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
    
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    /* Global Styles */
    html, body, [class*="css"] { 
        font-family: 'Inter', 'Poppins', 'Noto Nastaliq Urdu', sans-serif;
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1530 100%);
        color: #e2e8f0;
    }
    
    /* Main Container */
    .main {
        background: transparent;
    }
    
    /* Animations */
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-20px); }
    }
    
    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    @keyframes glow {
        0%, 100% { box-shadow: 0 0 20px rgba(102, 126, 234, 0.5); }
        50% { box-shadow: 0 0 40px rgba(240, 147, 251, 0.8); }
    }
    
    /* Header Styles - بہترین */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        background-size: 200% 200%;
        animation: gradient 6s ease infinite;
        backdrop-filter: blur(10px);
        padding: 3.5rem 3rem;
        border-radius: 24px;
        color: white;
        margin-bottom: 2.5rem;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 25px 50px rgba(102, 126, 234, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.2);
        position: relative;
        overflow: hidden;
        animation: slideDown 0.6s ease-out;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(255, 255, 255, 0.15) 0%, transparent 70%);
        border-radius: 50%;
        pointer-events: none;
        animation: float 8s ease-in-out infinite;
    }
    
    .main-header::after {
        content: '';
        position: absolute;
        bottom: -50%;
        left: -50%;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(255, 255, 255, 0.08) 0%, transparent 70%);
        border-radius: 50%;
        pointer-events: none;
    }
    
    .main-header h1 { 
        font-weight: 800;
        font-size: 2.8rem;
        margin: 0;
        color: #ffffff;
        text-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        letter-spacing: -0.5px;
        line-height: 1.2;
        position: relative;
        z-index: 1;
        word-wrap: break-word;
    }
    
    .main-header p {
        font-size: 1.1rem;
        opacity: 0.95;
        margin-top: 1rem;
        color: rgba(255, 255, 255, 0.95);
        font-weight: 500;
        letter-spacing: 0.3px;
        position: relative;
        z-index: 1;
    }
    
    /* Sidebar Styles */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1f3a 0%, #0f1530 100%);
        border-right: 1px solid rgba(102, 126, 234, 0.2);
    }
    
    [data-testid="stSidebar"] h2 {
        color: #fff;
        font-weight: 800;
        font-size: 1.8rem;
        background: linear-gradient(135deg, #667eea 0%, #f093fb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Button Styles */
    .stButton>button {
        border-radius: 12px;
        font-weight: 600;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        transition: all 0.3s ease;
        padding: 0.75rem 1.5rem;
        font-size: 1rem;
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        text-transform: none;
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #f093fb 100%);
        box-shadow: 0 12px 30px rgba(240, 147, 251, 0.5);
        transform: translateY(-2px);
    }
    
    .stButton>button:active {
        transform: translateY(0);
    }
    
    /* Sidebar Button */
    .sidebar .stButton>button {
        background: rgba(102, 126, 234, 0.2);
        color: #e2e8f0;
        border: 1px solid rgba(102, 126, 234, 0.3);
        backdrop-filter: blur(10px);
    }
    
    .sidebar .stButton>button:hover {
        background: rgba(102, 126, 234, 0.4);
        border-color: rgba(102, 126, 234, 0.6);
        color: #fff;
    }
    
    /* Input Styles */
    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea,
    .stNumberInput>div>div>input,
    .stSelectbox>div>div>select,
    .stDateInput>div>div>input {
        background: rgba(30, 41, 59, 0.6) !important;
        border: 1.5px solid rgba(102, 126, 234, 0.3) !important;
        border-radius: 12px !important;
        color: #fff !important;
        backdrop-filter: blur(10px);
        padding: 0.85rem 1.1rem !important;
        font-size: 0.95rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput>div>div>input:focus,
    .stTextArea>div>div>textarea:focus,
    .stNumberInput>div>div>input:focus,
    .stSelectbox>div>div>select:focus,
    .stDateInput>div>div>input:focus {
        border-color: rgba(102, 126, 234, 0.8) !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15) !important;
        background: rgba(30, 41, 59, 0.8) !important;
    }
    
    /* Card Styles */
    .glass-card {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        border-color: rgba(102, 126, 234, 0.4);
        box-shadow: 0 12px 40px rgba(102, 126, 234, 0.15);
        transform: translateY(-2px);
    }
    
    /* Metric Cards */
    [data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        color: #10b981 !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600 !important;
    }
    
    /* DataFrame Styles */
    .stDataFrame {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 12px;
        overflow: hidden;
    }
    
    /* Expander Styles */
    .streamlit-expanderHeader {
        background: rgba(30, 41, 59, 0.5) !important;
        border: 1px solid rgba(102, 126, 234, 0.2) !important;
        border-radius: 10px !important;
        color: #e2e8f0 !important;
        font-weight: 600 !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: rgba(102, 126, 234, 0.1) !important;
        border-color: rgba(102, 126, 234, 0.4) !important;
    }
    
    /* Success/Error/Info Messages */
    .stSuccess {
        background: rgba(16, 185, 129, 0.15) !important;
        border: 1px solid rgba(16, 185, 129, 0.4) !important;
        border-radius: 12px !important;
        color: #10b981 !important;
    }
    
    .stError {
        background: rgba(239, 68, 68, 0.15) !important;
        border: 1px solid rgba(239, 68, 68, 0.4) !important;
        border-radius: 12px !important;
        color: #f87171 !important;
    }
    
    .stInfo {
        background: rgba(59, 130, 246, 0.15) !important;
        border: 1px solid rgba(59, 130, 246, 0.4) !important;
        border-radius: 12px !important;
        color: #60a5fa !important;
    }
    
    /* Tab Styles */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(30, 41, 59, 0.5);
        border-radius: 12px;
        padding: 0.5rem;
        gap: 0.5rem;
        border-bottom: 1px solid rgba(102, 126, 234, 0.1);
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.8), rgba(240, 147, 251, 0.8));
        color: white !important;
    }
    
    /* Form Styles */
    [data-testid="stForm"] {
        background: rgba(30, 41, 59, 0.3);
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 16px;
        padding: 2.5rem;
        backdrop-filter: blur(10px);
    }
    
    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(102, 126, 234, 0.3), transparent);
        margin: 2rem 0;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(30, 41, 59, 0.5);
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(102, 126, 234, 0.5);
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(102, 126, 234, 0.7);
    }
    </style>
    """, unsafe_allow_html=True)

def colored_header(title, subtitle=""):
    st.markdown(f"""
    <div class="main-header">
        <h1>✨ {title}</h1>
        {f'<p>{subtitle}</p>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)

# ----------------------- بزنس لاجک -----------------------
def get_years():
    conn = get_connection()
    rows = conn.execute("SELECT year, COUNT(*) as cnt FROM entries GROUP BY year ORDER BY year").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_dashboard(conn, year):
    summ = conn.execute("""SELECT COUNT(*) AS entries_count, ROUND(COALESCE(SUM(income),0),2) AS total_income,
                           ROUND(COALESCE(SUM(payment),0),2) AS total_payment,
                           ROUND(COALESCE(SUM(income-payment),0),2) AS balance
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
        df = pd.DataFrame([dict(r) for r in rows])[["entry_date","code","account_name","description","income","payment"]]
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
    return df

# ----------------------- لاگ ان -----------------------
def login_page():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 3rem 0;">
            <div style="display: inline-block; padding: 4rem; background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(240, 147, 251, 0.1) 100%); backdrop-filter: blur(10px); border: 1px solid rgba(102, 126, 234, 0.2); border-radius: 24px; box-shadow: 0 25px 50px rgba(102, 126, 234, 0.2);">
                <h1 style='color: #fff; font-size: 2.5rem; font-weight: 800; margin-bottom: 0.5rem;'>📚 مدرسہ اکاؤنٹنگ</h1>
                <p style='color: #94a3b8; font-size: 1rem;'>JAMIA MILLIA ISLAMIA FAISALABAD</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
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
                    st.error("❌ غلط صارف نام یا پاس ورڈ")
                conn.close()

# ----------------------- مین ایپ -----------------------
def main_app():
    st.set_page_config(page_title="Madrasa Accounting", layout="wide", initial_sidebar_state="expanded")
    local_css()

    # سائڈبار
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center; padding:1.5rem 0;">
            <h2 style="color:#fff; font-weight: 800;">📚 اکاؤنٹنگ</h2>
            <p style="color: #94a3b8; margin-top: 0.5rem;">👤 {st.session_state.get('display_name','')}</p>
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
            if st.button(label, use_container_width=True, key=vid):
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
        colored_header("💰 " + t("tab_income"), "روزانہ کی آمدنی کو ریکارڈ کریں")
        with st.form("inc_form"):
            col1, col2 = st.columns(2)
            date = col1.date_input(t("date"))
            code = col2.text_input(t("code"), max_chars=3, key="ic")
            head = ""
            if code:
                acc = conn.execute("SELECT name, atype FROM accounts WHERE code=?", (code.zfill(3),)).fetchone()
                head = f"{acc['name']}" if acc else ""
            st.text_input(t("account_head"), value=head, disabled=True)
            desc = st.text_area(t("description"), height=80)
            amount = st.number_input(t("amount"), min_value=0.0, format="%.2f", key="inc_amt")
            bill_file = st.file_uploader(t("bill"), type=["jpg","jpeg","png"], key="inc_bill")
            
            with st.expander(t("advanced")):
                col1, col2 = st.columns(2)
                branch = col1.text_input(t("branch"), value="G")
                category = col2.text_input(t("category"), value="GENERAL")
                receipt_no = col1.number_input(t("receipt_no"), value=0, step=1)
                jv_no = col2.number_input(t("jv_no"), value=0, step=1)
            
            submitted = st.form_submit_button(t("save_income"), use_container_width=True)
            if submitted:
                if not code or not date:
                    st.error("❌ کوڈ اور تاریخ ضروری ہیں")
                else:
                    payload = {"year": year, "entry_date": date.isoformat(), "code": code.zfill(3),
                               "description": desc, "income": amount, "payment": 0, "entry_kind": "C",
                               "branch": branch, "category": category,
                               "receipt_no": receipt_no, "jv_no": jv_no}
                    bill_bytes = bill_file.getvalue() if bill_file else None
                    try:
                        upsert_entry(conn, payload, bill_image_bytes=bill_bytes)
                        st.success("✅ آمدنی محفوظ ہو گئی")
                    except Exception as e:
                        st.error(f"❌ خرابی: {str(e)}")
        
        st.subheader("📋 حالیہ آمدنی")
        recent = fetch_entries(conn, year, mode="income", limit=10)
        if recent:
            for r in recent:
                cols = st.columns([1.5,1.5,2.5,1.5,1])
                cols[0].write(f"📆 {r['entry_date'] or '-'}")
                cols[1].write(f"🔢 {r['code']}")
                cols[2].write(f"💬 {r['account_name']}")
                cols[3].write(f"💵 {r['income']:,.0f}")
                if r["bill_image"] and os.path.exists(r["bill_image"]):
                    with cols[4]:
                        st.image(r["bill_image"], width=60)
        else:
            st.info(t("no_data"))

    elif view == "expense":
        colored_header("💸 " + t("tab_expense"), "روزانہ کی اخراجات ریکارڈ کریں")
        with st.form("exp_form"):
            col1, col2 = st.columns(2)
            date = col1.date_input(t("date"))
            code = col2.text_input(t("code"), max_chars=3, key="ec")
            head = ""
            if code:
                acc = conn.execute("SELECT name, atype FROM accounts WHERE code=?", (code.zfill(3),)).fetchone()
                head = f"{acc['name']}" if acc else ""
            st.text_input(t("account_head"), value=head, disabled=True)
            desc = st.text_area(t("description"), height=80)
            amount = st.number_input(t("amount"), min_value=0.0, format="%.2f", key="exp_amt")
            bill_file = st.file_uploader(t("bill"), type=["jpg","jpeg","png"], key="exp_bill")
            
            with st.expander(t("advanced")):
                col1, col2 = st.columns(2)
                branch = col1.text_input(t("branch"), value="G")
                category = col2.text_input(t("category"), value="GENERAL")
                voucher_no = col1.number_input(t("voucher_no"), value=0, step=1)
                jv_no = col2.number_input(t("jv_no"), value=0, step=1)
            
            submitted = st.form_submit_button(t("save_expense"), use_container_width=True)
            if submitted:
                if not code or not date:
                    st.error("❌ کوڈ اور تاریخ ضروری ہیں")
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
                        st.error(f"❌ خرابی: {str(e)}")
        
        st.subheader("📋 حالیہ اخراجات")
        recent = fetch_entries(conn, year, mode="expense", limit=10)
        if recent:
            for r in recent:
                cols = st.columns([1.5,1.5,2.5,1.5,1])
                cols[0].write(f"📆 {r['entry_date'] or '-'}")
                cols[1].write(f"🔢 {r['code']}")
                cols[2].write(f"💬 {r['account_name']}")
                cols[3].write(f"💸 {r['payment']:,.0f}")
                if r["bill_image"] and os.path.exists(r["bill_image"]):
                    with cols[4]:
                        st.image(r["bill_image"], width=60)
        else:
            st.info(t("no_data"))

    elif view == "reports":
        colored_header("📊 " + t("tab_reports"), "تفصیلی رپورٹس دیکھیں")
        rtype = st.selectbox(t("report_type"), ["ledger","cashbook","trial-balance"], key="rtype")
        c1, c2 = st.columns(2)
        dfrom = c1.date_input(t("from_date"))
        dto = c2.date_input(t("to_date"))
        if st.button(t("view_report"), use_container_width=True):
            try:
                df = build_report(conn, rtype, year, dfrom.isoformat() if dfrom else None, dto.isoformat() if dto else None)
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(t("download_csv"), csv, f"{rtype}_{year}.csv", "text/csv", use_container_width=True)
            except Exception as e:
                st.error(f"❌ خرابی: {str(e)}")

    elif view == "ledger":
        colored_header("📒 " + t("tab_ledger"), "تمام داخلوں کا لیجر")
        col1, col2, col3 = st.columns(3)
        search = col1.text_input(t("search"))
        code = col2.text_input(t("code"))
        mode = col3.selectbox("قسم", ["تمام","آمدنی","اخراجات"])
        c4, c5 = st.columns(2)
        dfrom = c4.date_input(t("from_date"))
        dto = c5.date_input(t("to_date"))
        mode_map = {"تمام": None, "آمدنی": "income", "اخراجات": "expense"}
        if st.button(t("refresh_ledger"), use_container_width=True):
            entries = fetch_entries(conn, year, date_from=dfrom.isoformat() if dfrom else None, date_to=dto.isoformat() if dto else None,
                                    search=search or None, code=code or None, mode=mode_map[mode], limit=500)
            if entries:
                for e in entries:
                    cols = st.columns([1.2, 1, 2, 2.5, 1, 1, 0.8])
                    cols[0].write(f"📆 {e['entry_date'] or '-'}")
                    cols[1].write(f"🔢 {e['code']}")
                    cols[2].write(f"{e['account_name']}")
                    cols[3].write(f"{e['description'][:30]}...")
                    if e["income"]:
                        cols[4].write(f"⬆️ {e['income']:,.0f}")
                    if e["payment"]:
                        cols[5].write(f"⬇️ {e['payment']:,.0f}")
                    if e["bill_image"] and os.path.exists(e["bill_image"]):
                        with cols[6]:
                            st.image(e["bill_image"], width=50)
            else:
                st.info(t("no_data"))

    elif view == "accounts":
        colored_header("🗂 " + t("tab_accounts"), "تمام اکاؤنٹس")
        accounts = get_accounts(conn, year)
        if accounts:
            df = pd.DataFrame(accounts)[["code","name","atype","entries_count","balance"]]
            st.dataframe(df.style.format({"balance":"{:,.0f}"}), use_container_width=True)
        else:
            st.info(t("no_data"))
        with st.expander("➕ نیا اکاؤنٹ شامل کریں"):
            with st.form("add_acc"):
                col1, col2 = st.columns(2)
                nc = col1.text_input(t("code"), max_chars=3)
                nn = col2.text_input("نام")
                nt = st.selectbox("ٹائپ", ["","BS","TA","PA"])
                if st.form_submit_button("محفوظ کریں", use_container_width=True):
                    if nc:
                        upsert_account(conn, nc, nn, nt)
                        st.success("✅ اکاؤنٹ محفوظ ہو گیا")
                        st.rerun()

    elif view == "overview":
        colored_header("📈 " + t("tab_overview"), "جامع جائزہ")
        dash = get_dashboard(conn, year)
        if dash["summary"]["entries_count"]:
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 " + t("total_income"), f"{dash['summary']['total_income']:,.0f}")
            c2.metric("💸 " + t("total_expense"), f"{dash['summary']['total_payment']:,.0f}")
            c3.metric("⚖️ " + t("net_balance"), f"{dash['summary']['balance']:,.0f}")
            
            if dash["monthly"]:
                dfm = pd.DataFrame(dash["monthly"]).set_index("month")[["income","payment"]]
                st.subheader(t("monthly_flow"))
                st.bar_chart(dfm, use_container_width=True)
            
            if dash["top_accounts"]:
                st.subheader(t("top_accounts"))
                dft = pd.DataFrame(dash["top_accounts"])[["code","name","balance"]]
                st.dataframe(dft.style.format({"balance":"{:,.0f}"}), use_container_width=True)
        else:
            st.info(t("no_data"))

    elif view == "settings":
        colored_header("⚙ " + t("tab_settings"), "سسٹم سیٹنگز")
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
            if st.form_submit_button(t("save_settings"), use_container_width=True):
                conn.execute("""INSERT OR IGNORE INTO control_settings (year, start_date, end_date, cash_in_hand, min_cash, max_cash, last_jvno)
                                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                             (year, start, end, cih, minc, maxc, jvno))
                conn.commit()
                st.success("✅ سیٹنگز محفوظ ہو گئیں")
    
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
