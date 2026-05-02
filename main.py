import streamlit as st
import sqlite3
import bcrypt
from pathlib import Path
from datetime import datetime
import pandas as pd
import os
from PIL import Image
from io import BytesIO

# ----------------------- Configuration -----------------------
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

# ----------------------- Translations -----------------------
I18N = {
    "en": {
        "login_title": "Madrasa Accounting System",
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
    },
    "ur": {
        "login_title": "مدرسہ اکاؤنٹنگ سسٹم",
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
    },
}

def t(key):
    return I18N.get(st.session_state.get("lang", "en"), I18N["en"]).get(key, key)

# ----------------------- Styling -----------------------
def apply_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600;700;800&family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
    
    /* Main Background */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    }
    
    /* Typography */
    * {
        font-family: 'Rubik', 'Noto Nastaliq Urdu', sans-serif !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #a855f7 0%, #7c3aed 100%) !important;
        color: white !important;
        border: 1px solid rgba(168, 85, 247, 0.3) !important;
        border-radius: 16px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 15px rgba(168, 85, 247, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        box-shadow: 0 8px 25px rgba(168, 85, 247, 0.5) !important;
        transform: translateY(-2px) !important;
    }
    
    /* Input Fields */
    input, textarea, select {
        background: rgba(30, 41, 59, 0.5) !important;
        border: 1px solid rgba(148, 163, 184, 0.3) !important;
        border-radius: 12px !important;
        color: white !important;
        padding: 0.75rem 1rem !important;
    }
    
    input:focus, textarea:focus, select:focus {
        border-color: rgba(168, 85, 247, 0.5) !important;
        box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.1) !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 800 !important;
        color: #10b981 !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    
    /* DataFrames */
    .stDataFrame {
        background: rgba(30, 41, 59, 0.4) !important;
        border: 1px solid rgba(148, 163, 184, 0.2) !important;
        border-radius: 16px !important;
    }
    
    /* Messages */
    .stSuccess {
        background: rgba(16, 185, 129, 0.1) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        color: #10b981 !important;
        border-radius: 12px !important;
    }
    
    .stError {
        background: rgba(239, 68, 68, 0.1) !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
        color: #ef4444 !important;
        border-radius: 12px !important;
    }
    
    .stInfo {
        background: rgba(59, 130, 246, 0.1) !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
        color: #3b82f6 !important;
        border-radius: 12px !important;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: white !important;
    }
    
    /* Labels */
    label {
        color: #cbd5e1 !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)

def page_header(title, subtitle=""):
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(59, 130, 246, 0.1) 100%);
        backdrop-filter: blur(10px);
        padding: 2rem;
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        margin-bottom: 2rem;
    ">
        <h1 style="
            font-size: 2.5rem;
            font-weight: 800;
            margin: 0;
            background: linear-gradient(135deg, #fff 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        ">{title}</h1>
        <p style="
            font-size: 1.1rem;
            color: #94a3b8;
            margin: 0.5rem 0 0 0;
        ">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

# ----------------------- Business Logic -----------------------
def get_years():
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT year FROM entries ORDER BY year DESC").fetchall()
    conn.close()
    years = [r["year"] for r in rows]
    if not years:
        years = [str(datetime.now().year)]
    return years

def get_dashboard(conn, year):
    summ = conn.execute("""
        SELECT 
            COUNT(*) AS entries_count,
            ROUND(COALESCE(SUM(income),0),2) AS total_income,
            ROUND(COALESCE(SUM(payment),0),2) AS total_payment,
            ROUND(COALESCE(SUM(income-payment),0),2) AS balance
        FROM entries WHERE year=?
    """, (year,)).fetchone()
    
    monthly = conn.execute("""
        SELECT 
            substr(entry_date,1,7) as month,
            ROUND(SUM(income),2) as income,
            ROUND(SUM(payment),2) as payment
        FROM entries 
        WHERE year=? AND entry_date IS NOT NULL 
        GROUP BY month 
        ORDER BY month
    """, (year,)).fetchall()
    
    top = conn.execute("""
        SELECT 
            e.code,
            COALESCE(a.name,'') as name,
            ROUND(SUM(e.income-e.payment),2) as balance
        FROM entries e 
        LEFT JOIN accounts a ON a.code=e.code
        WHERE e.year=? 
        GROUP BY e.code 
        ORDER BY ABS(SUM(e.income-e.payment)) DESC 
        LIMIT 10
    """, (year,)).fetchall()
    
    return {
        "summary": dict(summ),
        "monthly": [dict(r) for r in monthly],
        "top_accounts": [dict(r) for r in top]
    }

def fetch_entries(conn, year, mode=None, limit=None):
    sql = "SELECT e.*, COALESCE(a.name,'') as account_name FROM entries e LEFT JOIN accounts a ON a.code=e.code WHERE e.year=?"
    params = [year]
    
    if mode == "income":
        sql += " AND e.income > 0"
    elif mode == "expense":
        sql += " AND e.payment > 0"
    
    sql += " ORDER BY e.entry_date DESC, e.id DESC"
    
    if limit:
        sql += f" LIMIT {limit}"
    
    return conn.execute(sql, params).fetchall()

def save_entry(conn, year, date, code, description, amount, entry_type):
    code = code.zfill(3)
    conn.execute("INSERT OR IGNORE INTO accounts (code) VALUES (?)", (code,))
    
    if entry_type == "income":
        income, payment = amount, 0
    else:
        income, payment = 0, amount
    
    conn.execute("""
        INSERT INTO entries (year, entry_date, code, description, income, payment, entry_kind, source_file)
        VALUES (?, ?, ?, ?, ?, ?, 'C', 'MODERN')
    """, (year, date, code, description, income, payment))
    
    conn.commit()

# ----------------------- Login Page -----------------------
def login_page():
    apply_custom_css()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; margin: 3rem 0;">
            <h1 style="
                font-size: 3rem;
                font-weight: 800;
                color: white;
                margin-bottom: 0.5rem;
            ">📚 مدرسہ اکاؤنٹنگ</h1>
            <p style="
                font-size: 1.2rem;
                color: #94a3b8;
            ">JAMIA MILLIA ISLAMIA & MASJID MADRASA WALI</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("👤 " + t("username"), value="admin")
            password = st.text_input("🔒 " + t("password"), type="password", value="admin123")
            
            if st.form_submit_button(t("login_btn"), use_container_width=True):
                conn = get_connection()
                user = conn.execute("SELECT * FROM app_users WHERE username=?", (username,)).fetchone()
                
                if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
                    st.session_state.authenticated = True
                    st.session_state.user = user["username"]
                    st.session_state.display_name = user["display_name"]
                    st.session_state.lang = "ur"
                    conn.close()
                    st.rerun()
                else:
                    st.error("❌ غلط یوزر نیم یا پاس ورڈ")
                    conn.close()

# ----------------------- Main App -----------------------
def main_app():
    st.set_page_config(
        page_title="Madrasa Accounting",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    apply_custom_css()
    
    # Sidebar
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1.5rem 0; margin-bottom: 1rem;">
            <h2 style="font-size: 1.8rem; margin: 0;">📚 مدرسہ اکاؤنٹس</h2>
            <p style="color: #94a3b8; margin: 0.5rem 0 0 0;">👤 {}</p>
        </div>
        """.format(st.session_state.get('display_name', '')), unsafe_allow_html=True)
        
        years = get_years()
        year = st.selectbox("📅 سال", years, index=0)
        st.session_state.year = year
        
        st.markdown("---")
        
        lang_options = ["🇬🇧 English", "🇵🇰 اردو"]
        lang_idx = 0 if st.session_state.get("lang", "en") == "en" else 1
        selected_lang = st.radio("🌐 زبان", lang_options, index=lang_idx)
        st.session_state.lang = "en" if selected_lang.startswith("🇬🇧") else "ur"
        
        st.markdown("---")
        
        if st.button("💰 " + t("tab_income"), use_container_width=True):
            st.session_state.view = "income"
        
        if st.button("💸 " + t("tab_expense"), use_container_width=True):
            st.session_state.view = "expense"
        
        if st.button("📈 " + t("tab_overview"), use_container_width=True):
            st.session_state.view = "overview"
        
        if st.button("📒 " + t("tab_ledger"), use_container_width=True):
            st.session_state.view = "ledger"
        
        if st.button("🗂 " + t("tab_accounts"), use_container_width=True):
            st.session_state.view = "accounts"
        
        st.markdown("---")
        
        if st.button("🚪 " + t("logout"), use_container_width=True):
            st.session_state.clear()
            st.rerun()
    
    # Main Content
    conn = get_connection()
    year = st.session_state.year
    
    if "view" not in st.session_state:
        st.session_state.view = "income"
    
    view = st.session_state.view
    
    # Income Entry
    if view == "income":
        page_header("💰 انکم انٹری", "روزانہ کی آمدنی درج کریں")
        
        with st.form("income_form"):
            col1, col2 = st.columns(2)
            
            date = col1.date_input("📆 تاریخ", value=datetime.now())
            code = col2.text_input("🔢 کوڈ", max_chars=3, placeholder="007")
            
            # Auto-populate account name
            account_name = ""
            if code:
                acc = conn.execute("SELECT name FROM accounts WHERE code=?", (code.zfill(3),)).fetchone()
                account_name = acc["name"] if acc else ""
            
            st.text_input("🏦 اکاؤنٹ نام", value=account_name, disabled=True)
            
            description = st.text_area("📄 تفصیل", placeholder="تفصیل یہاں لکھیں...")
            amount = st.number_input("💵 رقم", min_value=0.0, step=100.0, format="%.2f")
            
            submitted = st.form_submit_button("💾 محفوظ کریں", use_container_width=True)
            
            if submitted:
                if code and amount > 0:
                    try:
                        save_entry(conn, year, date.isoformat(), code, description, amount, "income")
                        st.success("✅ انکم کامیابی سے محفوظ ہو گئی!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خرابی: {str(e)}")
                else:
                    st.error("⚠ کوڈ اور رقم ضروری ہیں")
        
        st.markdown("---")
        st.subheader("📋 حالیہ انکم انٹریز")
        
        recent = fetch_entries(conn, year, mode="income", limit=10)
        if recent:
            for entry in recent:
                cols = st.columns([2, 1, 3, 2])
                cols[0].write(f"📅 {entry['entry_date']}")
                cols[1].write(f"🔢 {entry['code']}")
                cols[2].write(f"📄 {entry['description'][:50]}")
                cols[3].write(f"💰 {entry['income']:,.2f} PKR")
        else:
            st.info("ℹ ابھی تک کوئی انکم درج نہیں ہوئی")
    
    # Expense Entry
    elif view == "expense":
        page_header("💸 خرچ انٹری", "روزانہ کے اخراجات درج کریں")
        
        with st.form("expense_form"):
            col1, col2 = st.columns(2)
            
            date = col1.date_input("📆 تاریخ", value=datetime.now())
            code = col2.text_input("🔢 کوڈ", max_chars=3, placeholder="007")
            
            account_name = ""
            if code:
                acc = conn.execute("SELECT name FROM accounts WHERE code=?", (code.zfill(3),)).fetchone()
                account_name = acc["name"] if acc else ""
            
            st.text_input("🏦 اکاؤنٹ نام", value=account_name, disabled=True)
            
            description = st.text_area("📄 تفصیل", placeholder="تفصیل یہاں لکھیں...")
            amount = st.number_input("💵 رقم", min_value=0.0, step=100.0, format="%.2f")
            
            submitted = st.form_submit_button("💾 محفوظ کریں", use_container_width=True)
            
            if submitted:
                if code and amount > 0:
                    try:
                        save_entry(conn, year, date.isoformat(), code, description, amount, "expense")
                        st.success("✅ خرچ کامیابی سے محفوظ ہو گیا!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خرابی: {str(e)}")
                else:
                    st.error("⚠ کوڈ اور رقم ضروری ہیں")
        
        st.markdown("---")
        st.subheader("📋 حالیہ خرچ انٹریز")
        
        recent = fetch_entries(conn, year, mode="expense", limit=10)
        if recent:
            for entry in recent:
                cols = st.columns([2, 1, 3, 2])
                cols[0].write(f"📅 {entry['entry_date']}")
                cols[1].write(f"🔢 {entry['code']}")
                cols[2].write(f"📄 {entry['description'][:50]}")
                cols[3].write(f"💸 {entry['payment']:,.2f} PKR")
        else:
            st.info("ℹ ابھی تک کوئی خرچ درج نہیں ہوا")
    
    # Overview
    elif view == "overview":
        page_header("📈 مالی جائزہ", f"سال {year} کا خلاصہ")
        
        dash = get_dashboard(conn, year)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "💰 کل آمدنی",
                f"{dash['summary']['total_income']:,.2f} PKR"
            )
        
        with col2:
            st.metric(
                "💸 کل اخراجات",
                f"{dash['summary']['total_payment']:,.2f} PKR"
            )
        
        with col3:
            balance = dash['summary']['balance']
            st.metric(
                "⚖ خالص بیلنس",
                f"{balance:,.2f} PKR",
                delta="فائدہ" if balance > 0 else "نقصان"
            )
        
        if dash['monthly']:
            st.markdown("---")
            st.subheader("📊 ماہانہ رپورٹ")
            df = pd.DataFrame(dash['monthly'])
            st.bar_chart(df.set_index('month')[['income', 'payment']])
        
        if dash['top_accounts']:
            st.markdown("---")
            st.subheader("🏆 اہم اکاؤنٹس")
            df = pd.DataFrame(dash['top_accounts'])
            st.dataframe(df, use_container_width=True)
    
    # Ledger
    elif view == "ledger":
        page_header("📒 لیجر", "تمام لین دین دیکھیں")
        
        entries = fetch_entries(conn, year, limit=100)
        
        if entries:
            data = []
            for e in entries:
                data.append({
                    "تاریخ": e['entry_date'],
                    "کوڈ": e['code'],
                    "اکاؤنٹ": e['account_name'],
                    "تفصیل": e['description'][:50],
                    "آمدنی": f"{e['income']:,.2f}" if e['income'] > 0 else "-",
                    "اخراجات": f"{e['payment']:,.2f}" if e['payment'] > 0 else "-"
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, height=600)
        else:
            st.info("ℹ کوئی ڈیٹا نہیں ملا")
    
    # Accounts
    elif view == "accounts":
        page_header("🗂 اکاؤنٹس کی فہرست", "تمام اکاؤنٹ ہیڈز")
        
        accounts = conn.execute("""
            SELECT code, name, atype
            FROM accounts
            ORDER BY code
        """).fetchall()
        
        if accounts:
            data = []
            for acc in accounts:
                data.append({
                    "کوڈ": acc['code'],
                    "نام": acc['name'],
                    "قسم": acc['atype']
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, height=600)
        else:
            st.info("ℹ کوئی اکاؤنٹ نہیں ملا")
    
    conn.close()

# ----------------------- Run App -----------------------
if __name__ == "__main__":
    init_db()
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.lang = "ur"
    
    if st.session_state.authenticated:
        main_app()
    else:
        login_page()
