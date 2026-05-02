import streamlit as st
import sqlite3
import bcrypt
from pathlib import Path
from datetime import datetime
import pandas as pd
import os

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

# ----------------------- Ultra Modern Styling -----------------------
def apply_ultra_modern_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
    
    /* ========= RESET & BASE ========= */
    * {
        font-family: 'Poppins', 'Noto Nastaliq Urdu', sans-serif !important;
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    /* ========= APP BACKGROUND ========= */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    .main {
        background: transparent;
        padding: 2rem;
    }
    
    /* ========= SIDEBAR - WHITE & CLEAN ========= */
    [data-testid="stSidebar"] {
        background: #ffffff !important;
        box-shadow: 4px 0 20px rgba(0, 0, 0, 0.08);
        border-right: 1px solid #e8ecf4 !important;
    }
    
    [data-testid="stSidebar"] * {
        color: #2d3748 !important;
    }
    
    /* ========= MODERN CARD BUTTONS ========= */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 16px !important;
        padding: 16px 28px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        letter-spacing: 0.3px !important;
        box-shadow: 0 10px 25px -5px rgba(102, 126, 234, 0.4) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        width: 100%;
        text-align: left !important;
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 15px 35px -5px rgba(102, 126, 234, 0.5) !important;
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%) !important;
    }
    
    .stButton > button:active {
        transform: translateY(-1px) !important;
    }
    
    /* ========= CLEAN INPUT FIELDS ========= */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select,
    .stDateInput > div > div > input {
        background: #ffffff !important;
        border: 2px solid #e8ecf4 !important;
        border-radius: 12px !important;
        color: #2d3748 !important;
        padding: 14px 18px !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        transition: all 0.25s ease !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stDateInput > div > div > input:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1), 0 4px 12px rgba(0, 0, 0, 0.08) !important;
        outline: none !important;
    }
    
    /* ========= LABELS ========= */
    label {
        color: #4a5568 !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px !important;
    }
    
    /* ========= WHITE CARD CONTAINERS ========= */
    [data-testid="stForm"] {
        background: #ffffff !important;
        border: 1px solid #e8ecf4 !important;
        border-radius: 20px !important;
        padding: 32px !important;
        box-shadow: 0 10px 40px -10px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* ========= STATS CARDS ========= */
    [data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        color: #2d3748 !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #718096 !important;
        font-size: 13px !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 600 !important;
    }
    
    /* ========= COLORFUL ALERTS ========= */
    .stSuccess {
        background: linear-gradient(135deg, #56ab2f 0%, #a8e063 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 16px 24px !important;
        font-weight: 600 !important;
        box-shadow: 0 8px 20px rgba(86, 171, 47, 0.3) !important;
    }
    
    .stError {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 16px 24px !important;
        font-weight: 600 !important;
        box-shadow: 0 8px 20px rgba(235, 51, 73, 0.3) !important;
    }
    
    .stInfo {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 16px 24px !important;
        font-weight: 600 !important;
        box-shadow: 0 8px 20px rgba(79, 172, 254, 0.3) !important;
    }
    
    /* ========= DATAFRAMES ========= */
    .stDataFrame {
        background: #ffffff !important;
        border: 1px solid #e8ecf4 !important;
        border-radius: 16px !important;
        overflow: hidden;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08) !important;
    }
    
    /* ========= HEADERS ========= */
    h1 {
        color: #2d3748 !important;
        font-weight: 800 !important;
        font-size: 2.5rem !important;
        letter-spacing: -0.5px;
    }
    
    h2 {
        color: #2d3748 !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
    }
    
    h3 {
        color: #4a5568 !important;
        font-weight: 600 !important;
        font-size: 1.3rem !important;
    }
    
    /* ========= MODERN ENTRY CARDS ========= */
    .modern-entry-card {
        background: #ffffff;
        border: 1px solid #e8ecf4;
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 14px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        transition: all 0.25s ease;
        position: relative;
        overflow: hidden;
    }
    
    .modern-entry-card::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .modern-entry-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        border-color: #667eea;
    }
    
    /* ========= STAT CARD CONTAINERS ========= */
    .stat-card {
        background: #ffffff;
        border: 1px solid #e8ecf4;
        border-radius: 20px;
        padding: 28px;
        text-align: center;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
        transition: all 0.3s ease;
    }
    
    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 45px rgba(0, 0, 0, 0.12);
    }
    
    .stat-icon {
        font-size: 3rem;
        margin-bottom: 12px;
    }
    
    .stat-value {
        font-size: 2.2rem;
        font-weight: 800;
        margin: 8px 0;
    }
    
    .stat-label {
        color: #718096;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    
    /* ========= SCROLLBAR ========= */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f7fafc;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea, #764ba2);
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #764ba2, #667eea);
    }
    
    /* ========= DIVIDERS ========= */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #e8ecf4, transparent);
        margin: 28px 0;
    }
    </style>
    """, unsafe_allow_html=True)

def page_header(title, subtitle="", emoji="📚"):
    st.markdown(f"""
    <div style="
        background: #ffffff;
        border: 1px solid #e8ecf4;
        padding: 40px;
        border-radius: 24px;
        margin-bottom: 32px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
        text-align: center;
    ">
        <div style="font-size: 4rem; margin-bottom: 16px;">{emoji}</div>
        <h1 style="
            font-size: 2.5rem;
            font-weight: 800;
            margin: 0;
            color: #2d3748;
            letter-spacing: -0.5px;
        ">{title}</h1>
        <p style="
            font-size: 1rem;
            color: #718096;
            margin: 12px 0 0 0;
            font-weight: 500;
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
    apply_ultra_modern_css()
    
    st.markdown("""
    <div style="
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 85vh;
    ">
        <div style="
            background: #ffffff;
            padding: 60px 50px;
            border-radius: 28px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
            max-width: 450px;
            width: 100%;
            text-align: center;
            border: 1px solid #e8ecf4;
        ">
            <div style="font-size: 5rem; margin-bottom: 24px;">📚</div>
            <h1 style="
                font-size: 2.2rem;
                font-weight: 800;
                color: #2d3748;
                margin-bottom: 8px;
                letter-spacing: -0.5px;
            ">مدرسہ اکاؤنٹنگ</h1>
            <p style="
                font-size: 0.95rem;
                color: #718096;
                margin-bottom: 40px;
                font-weight: 500;
            ">JAMIA MILLIA ISLAMIA & MASJID MADRASA WALI</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("👤 یوزر نیم", value="admin", placeholder="یوزر نیم درج کریں")
            password = st.text_input("🔒 پاس ورڈ", type="password", value="admin123", placeholder="پاس ورڈ درج کریں")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.form_submit_button("🔐 لاگ ان کریں", use_container_width=True):
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
    
    apply_ultra_modern_css()
    
    # Sidebar
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 32px 0 28px 0;">
            <div style="font-size: 3.5rem; margin-bottom: 16px;">📚</div>
            <h2 style="font-size: 1.6rem; margin: 0; font-weight: 800; color: #2d3748;">مدرسہ اکاؤنٹس</h2>
            <p style="color: #718096; margin: 8px 0 0 0; font-weight: 600; font-size: 0.9rem;">👤 {}</p>
        </div>
        """.format(st.session_state.get('display_name', '')), unsafe_allow_html=True)
        
        years = get_years()
        year = st.selectbox("📅 سال", years, index=0)
        st.session_state.year = year
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        lang_options = ["🇬🇧 English", "🇵🇰 اردو"]
        lang_idx = 0 if st.session_state.get("lang", "en") == "en" else 1
        selected_lang = st.radio("🌐 زبان", lang_options, index=lang_idx)
        st.session_state.lang = "en" if selected_lang.startswith("🇬🇧") else "ur"
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("💰 انکم انٹری"):
            st.session_state.view = "income"
        
        if st.button("💸 خرچ انٹری"):
            st.session_state.view = "expense"
        
        if st.button("📈 مالی جائزہ"):
            st.session_state.view = "overview"
        
        if st.button("📒 لیجر"):
            st.session_state.view = "ledger"
        
        if st.button("🗂 اکاؤنٹس"):
            st.session_state.view = "accounts"
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        if st.button("🚪 لاگ آؤٹ"):
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
        page_header("انکم انٹری", "روزانہ کی آمدنی درج کریں", "💰")
        
        with st.form("income_form"):
            col1, col2 = st.columns(2)
            
            date = col1.date_input("📆 تاریخ", value=datetime.now())
            code = col2.text_input("🔢 اکاؤنٹ کوڈ", max_chars=3, placeholder="001")
            
            account_name = ""
            if code:
                acc = conn.execute("SELECT name FROM accounts WHERE code=?", (code.zfill(3),)).fetchone()
                account_name = acc["name"] if acc else ""
            
            st.text_input("🏦 اکاؤنٹ کا نام", value=account_name, disabled=True)
            
            description = st.text_area("📄 تفصیل", placeholder="مکمل تفصیل یہاں لکھیں...", height=100)
            amount = st.number_input("💵 رقم (PKR)", min_value=0.0, step=100.0, format="%.2f")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            submitted = st.form_submit_button("💾 محفوظ کریں", use_container_width=True)
            
            if submitted:
                if code and amount > 0:
                    try:
                        save_entry(conn, year, date.isoformat(), code, description, amount, "income")
                        st.success("✅ انکم کامیابی سے محفوظ ہو گئی!")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خرابی: {str(e)}")
                else:
                    st.error("⚠ کوڈ اور رقم ضروری ہیں")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h3 style='color: #2d3748; font-weight: 700;'>📋 حالیہ انکم انٹریز</h3>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        recent = fetch_entries(conn, year, mode="income", limit=10)
        if recent:
            for entry in recent:
                st.markdown(f"""
                <div class="modern-entry-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1;">
                            <div style="font-size: 0.85rem; color: #718096; margin-bottom: 6px; font-weight: 600;">📅 {entry['entry_date']}</div>
                            <div style="font-size: 1.05rem; font-weight: 700; color: #2d3748; margin-bottom: 6px;">🔢 {entry['code']} • {entry['account_name']}</div>
                            <div style="font-size: 0.9rem; color: #4a5568;">📄 {entry['description'][:70]}</div>
                        </div>
                        <div style="text-align: right; min-width: 140px;">
                            <div style="font-size: 1.8rem; font-weight: 800; color: #667eea;">₨ {entry['income']:,.0f}</div>
                            <div style="font-size: 0.85rem; color: #718096; font-weight: 600;">PKR</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("ℹ ابھی تک کوئی انکم درج نہیں ہوئی")
    
    # Expense Entry
    elif view == "expense":
        page_header("خرچ انٹری", "روزانہ کے اخراجات درج کریں", "💸")
        
        with st.form("expense_form"):
            col1, col2 = st.columns(2)
            
            date = col1.date_input("📆 تاریخ", value=datetime.now())
            code = col2.text_input("🔢 اکاؤنٹ کوڈ", max_chars=3, placeholder="007")
            
            account_name = ""
            if code:
                acc = conn.execute("SELECT name FROM accounts WHERE code=?", (code.zfill(3),)).fetchone()
                account_name = acc["name"] if acc else ""
            
            st.text_input("🏦 اکاؤنٹ کا نام", value=account_name, disabled=True)
            
            description = st.text_area("📄 تفصیل", placeholder="مکمل تفصیل یہاں لکھیں...", height=100)
            amount = st.number_input("💵 رقم (PKR)", min_value=0.0, step=100.0, format="%.2f")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            submitted = st.form_submit_button("💾 محفوظ کریں", use_container_width=True)
            
            if submitted:
                if code and amount > 0:
                    try:
                        save_entry(conn, year, date.isoformat(), code, description, amount, "expense")
                        st.success("✅ خرچ کامیابی سے محفوظ ہو گیا!")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خرابی: {str(e)}")
                else:
                    st.error("⚠ کوڈ اور رقم ضروری ہیں")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h3 style='color: #2d3748; font-weight: 700;'>📋 حالیہ خرچ انٹریز</h3>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        recent = fetch_entries(conn, year, mode="expense", limit=10)
        if recent:
            for entry in recent:
                st.markdown(f"""
                <div class="modern-entry-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1;">
                            <div style="font-size: 0.85rem; color: #718096; margin-bottom: 6px; font-weight: 600;">📅 {entry['entry_date']}</div>
                            <div style="font-size: 1.05rem; font-weight: 700; color: #2d3748; margin-bottom: 6px;">🔢 {entry['code']} • {entry['account_name']}</div>
                            <div style="font-size: 0.9rem; color: #4a5568;">📄 {entry['description'][:70]}</div>
                        </div>
                        <div style="text-align: right; min-width: 140px;">
                            <div style="font-size: 1.8rem; font-weight: 800; color: #eb3349;">₨ {entry['payment']:,.0f}</div>
                            <div style="font-size: 0.85rem; color: #718096; font-weight: 600;">PKR</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("ℹ ابھی تک کوئی خرچ درج نہیں ہوا")
    
    # Overview
    elif view == "overview":
        page_header("مالی جائزہ", f"سال {year} کا مکمل خلاصہ", "📈")
        
        dash = get_dashboard(conn, year)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-icon">💰</div>
                <div class="stat-label">کل آمدنی</div>
                <div class="stat-value" style="color: #667eea;">₨ {dash['summary']['total_income']:,.0f}</div>
                <div style="font-size: 0.9rem; color: #718096; margin-top: 4px;">PKR</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-icon">💸</div>
                <div class="stat-label">کل اخراجات</div>
                <div class="stat-value" style="color: #eb3349;">₨ {dash['summary']['total_payment']:,.0f}</div>
                <div style="font-size: 0.9rem; color: #718096; margin-top: 4px;">PKR</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            balance = dash['summary']['balance']
            balance_color = "#56ab2f" if balance > 0 else "#eb3349"
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-icon">⚖️</div>
                <div class="stat-label">خالص بیلنس</div>
                <div class="stat-value" style="color: {balance_color};">₨ {balance:,.0f}</div>
                <div style="font-size: 0.9rem; color: #718096; margin-top: 4px;">PKR</div>
            </div>
            """, unsafe_allow_html=True)
        
        if dash['monthly']:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<h3 style='color: #2d3748; font-weight: 700;'>📊 ماہانہ رپورٹ</h3>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            df = pd.DataFrame(dash['monthly'])
            st.bar_chart(df.set_index('month')[['income', 'payment']])
        
        if dash['top_accounts']:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<h3 style='color: #2d3748; font-weight: 700;'>🏆 اہم اکاؤنٹس</h3>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            df = pd.DataFrame(dash['top_accounts'])
            st.dataframe(df, use_container_width=True, height=400)
    
    # Ledger
    elif view == "ledger":
        page_header("لیجر", "تمام لین دین دیکھیں", "📒")
        
        entries = fetch_entries(conn, year, limit=100)
        
        if entries:
            data = []
            for e in entries:
                data.append({
                    "📅 تاریخ": e['entry_date'],
                    "🔢 کوڈ": e['code'],
                    "🏦 اکاؤنٹ": e['account_name'],
                    "📄 تفصیل": e['description'][:60],
                    "💰 آمدنی": f"₨ {e['income']:,.0f}" if e['income'] > 0 else "-",
                    "💸 اخراجات": f"₨ {e['payment']:,.0f}" if e['payment'] > 0 else "-"
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, height=600)
        else:
            st.info("ℹ کوئی ڈیٹا نہیں ملا")
    
    # Accounts
    elif view == "accounts":
        page_header("اکاؤنٹس کی فہرست", "تمام اکاؤنٹ ہیڈز", "🗂")
        
        accounts = conn.execute("""
            SELECT code, name, atype
            FROM accounts
            ORDER BY code
        """).fetchall()
        
        if accounts:
            data = []
            for acc in accounts:
                data.append({
                    "🔢 کوڈ": acc['code'],
                    "🏦 نام": acc['name'],
                    "📁 قسم": acc['atype']
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
