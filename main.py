import streamlit as st
import sqlite3
import bcrypt
from pathlib import Path
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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

# ----------------------- Perfect Modern Design -----------------------
def apply_perfect_design():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
    
    /* ========= ROOT VARIABLES ========= */
    :root {
        --primary: #6366f1;
        --primary-dark: #4f46e5;
        --success: #10b981;
        --danger: #ef4444;
        --warning: #f59e0b;
        --info: #3b82f6;
        --bg-light: #f8fafc;
        --bg-white: #ffffff;
        --text-dark: #0f172a;
        --text-gray: #64748b;
        --border: #e2e8f0;
        --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
        --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
        --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1);
    }
    
    /* ========= GLOBAL RESET ========= */
    * {
        font-family: 'Inter', 'Noto Nastaliq Urdu', -apple-system, BlinkMacSystemFont, sans-serif !important;
        letter-spacing: -0.01em;
    }
    
    /* ========= APP BACKGROUND ========= */
    .stApp {
        background: var(--bg-light);
    }
    
    .main {
        padding: 1.5rem !important;
    }
    
    /* ========= SIDEBAR ========= */
    [data-testid="stSidebar"] {
        background: var(--bg-white) !important;
        border-right: 1px solid var(--border) !important;
        box-shadow: var(--shadow) !important;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        padding: 2rem 1.5rem !important;
    }
    
    /* ========= BUTTONS ========= */
    .stButton > button {
        width: 100%;
        background: var(--bg-white) !important;
        color: var(--text-dark) !important;
        border: 1.5px solid var(--border) !important;
        border-radius: 12px !important;
        padding: 14px 20px !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
        box-shadow: var(--shadow-sm) !important;
        text-align: left !important;
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
    }
    
    .stButton > button:hover {
        background: var(--primary) !important;
        color: white !important;
        border-color: var(--primary) !important;
        box-shadow: var(--shadow) !important;
        transform: translateY(-1px) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* ========= PRIMARY BUTTON ========= */
    .stButton > button[kind="primary"],
    div[data-testid="stForm"] .stButton > button {
        background: var(--primary) !important;
        color: white !important;
        border-color: var(--primary) !important;
        box-shadow: var(--shadow) !important;
    }
    
    .stButton > button[kind="primary"]:hover,
    div[data-testid="stForm"] .stButton > button:hover {
        background: var(--primary-dark) !important;
        border-color: var(--primary-dark) !important;
        box-shadow: var(--shadow-lg) !important;
    }
    
    /* ========= INPUT FIELDS ========= */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select,
    .stDateInput > div > div > input {
        background: var(--bg-white) !important;
        border: 1.5px solid var(--border) !important;
        border-radius: 10px !important;
        color: var(--text-dark) !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        box-shadow: var(--shadow-sm) !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stDateInput > div > div > input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
        outline: none !important;
    }
    
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {
        color: var(--text-gray) !important;
        opacity: 0.6;
    }
    
    /* ========= LABELS ========= */
    label {
        color: var(--text-dark) !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        margin-bottom: 6px !important;
        display: block !important;
    }
    
    /* ========= FORMS ========= */
    [data-testid="stForm"] {
        background: var(--bg-white) !important;
        border: 1px solid var(--border) !important;
        border-radius: 16px !important;
        padding: 28px !important;
        box-shadow: var(--shadow) !important;
    }
    
    /* ========= METRICS ========= */
    [data-testid="stMetric"] {
        background: var(--bg-white) !important;
        border: 1px solid var(--border) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        box-shadow: var(--shadow) !important;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 32px !important;
        font-weight: 800 !important;
        color: var(--text-dark) !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: var(--text-gray) !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 14px !important;
    }
    
    /* ========= ALERTS ========= */
    .stSuccess {
        background: #ecfdf5 !important;
        border: 1px solid #86efac !important;
        border-radius: 12px !important;
        color: #166534 !important;
        padding: 14px 18px !important;
        font-weight: 500 !important;
    }
    
    .stError {
        background: #fef2f2 !important;
        border: 1px solid #fca5a5 !important;
        border-radius: 12px !important;
        color: #991b1b !important;
        padding: 14px 18px !important;
        font-weight: 500 !important;
    }
    
    .stInfo {
        background: #eff6ff !important;
        border: 1px solid #93c5fd !important;
        border-radius: 12px !important;
        color: #1e40af !important;
        padding: 14px 18px !important;
        font-weight: 500 !important;
    }
    
    .stWarning {
        background: #fffbeb !important;
        border: 1px solid #fcd34d !important;
        border-radius: 12px !important;
        color: #92400e !important;
        padding: 14px 18px !important;
        font-weight: 500 !important;
    }
    
    /* ========= DATAFRAMES ========= */
    .stDataFrame {
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        overflow: hidden;
        box-shadow: var(--shadow-sm) !important;
    }
    
    .stDataFrame [data-testid="stDataFrameResizeHandle"] {
        display: none;
    }
    
    /* ========= HEADERS ========= */
    h1 {
        color: var(--text-dark) !important;
        font-weight: 800 !important;
        font-size: 28px !important;
        margin-bottom: 8px !important;
    }
    
    h2 {
        color: var(--text-dark) !important;
        font-weight: 700 !important;
        font-size: 22px !important;
        margin-bottom: 6px !important;
    }
    
    h3 {
        color: var(--text-dark) !important;
        font-weight: 600 !important;
        font-size: 18px !important;
        margin-bottom: 12px !important;
    }
    
    /* ========= CARDS ========= */
    .card {
        background: var(--bg-white);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 20px;
        box-shadow: var(--shadow-sm);
        transition: all 0.2s ease;
    }
    
    .card:hover {
        box-shadow: var(--shadow);
        transform: translateY(-2px);
    }
    
    /* ========= ENTRY CARD ========= */
    .entry-card {
        background: var(--bg-white);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 12px;
        box-shadow: var(--shadow-sm);
        transition: all 0.2s ease;
        border-left: 3px solid var(--primary);
    }
    
    .entry-card:hover {
        box-shadow: var(--shadow);
        border-left-color: var(--primary-dark);
    }
    
    .entry-card.expense {
        border-left-color: var(--danger);
    }
    
    .entry-card.expense:hover {
        border-left-color: #dc2626;
    }
    
    /* ========= STAT CARD ========= */
    .stat-card {
        background: var(--bg-white);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 24px;
        box-shadow: var(--shadow);
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .stat-card:hover {
        box-shadow: var(--shadow-lg);
        transform: translateY(-4px);
    }
    
    .stat-card-icon {
        font-size: 40px;
        margin-bottom: 12px;
    }
    
    .stat-card-value {
        font-size: 36px;
        font-weight: 800;
        margin: 8px 0;
        color: var(--text-dark);
    }
    
    .stat-card-label {
        color: var(--text-gray);
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
    }
    
    /* ========= COLORS ========= */
    .text-primary { color: var(--primary) !important; }
    .text-success { color: var(--success) !important; }
    .text-danger { color: var(--danger) !important; }
    .text-warning { color: var(--warning) !important; }
    .text-info { color: var(--info) !important; }
    
    .bg-primary { background: var(--primary) !important; }
    .bg-success { background: var(--success) !important; }
    .bg-danger { background: var(--danger) !important; }
    .bg-warning { background: var(--warning) !important; }
    .bg-info { background: var(--info) !important; }
    
    /* ========= UTILITIES ========= */
    .rounded { border-radius: 12px; }
    .shadow { box-shadow: var(--shadow); }
    .shadow-lg { box-shadow: var(--shadow-lg); }
    
    /* ========= SCROLLBAR ========= */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-light);
    }
    
    ::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #94a3b8;
    }
    
    /* ========= DIVIDER ========= */
    hr {
        border: none;
        height: 1px;
        background: var(--border);
        margin: 24px 0;
    }
    
    /* ========= HIDE STREAMLIT BRANDING ========= */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

def page_header(title, subtitle=""):
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        padding: 32px 28px;
        border-radius: 16px;
        margin-bottom: 28px;
        box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.3);
    ">
        <h1 style="
            color: white;
            font-size: 32px;
            font-weight: 800;
            margin: 0 0 4px 0;
        ">{title}</h1>
        <p style="
            color: rgba(255, 255, 255, 0.9);
            font-size: 15px;
            margin: 0;
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
    
    return {
        "summary": dict(summ),
        "monthly": [dict(r) for r in monthly]
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
    apply_perfect_design()
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="
            background: white;
            padding: 48px 40px;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            border: 1px solid #e2e8f0;
        ">
            <div style="text-align: center; margin-bottom: 32px;">
                <div style="font-size: 56px; margin-bottom: 16px;">📚</div>
                <h1 style="font-size: 28px; font-weight: 800; color: #0f172a; margin: 0 0 8px 0;">مدرسہ اکاؤنٹنگ</h1>
                <p style="color: #64748b; font-size: 14px; margin: 0;">Jamia Millia Islamia & Masjid Madrasa Wali</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("👤 یوزر نیم", value="admin", placeholder="یوزر نیم درج کریں")
            password = st.text_input("🔒 پاس ورڈ", type="password", value="admin123", placeholder="پاس ورڈ درج کریں")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.form_submit_button("لاگ ان کریں →", use_container_width=True):
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
    
    apply_perfect_design()
    
    # Sidebar
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 24px 0; margin-bottom: 24px; border-bottom: 1px solid #e2e8f0;">
            <div style="font-size: 48px; margin-bottom: 12px;">📚</div>
            <h2 style="font-size: 20px; margin: 0; font-weight: 800; color: #0f172a;">مدرسہ اکاؤنٹس</h2>
            <p style="color: #64748b; margin: 6px 0 0 0; font-size: 13px; font-weight: 600;">{}</p>
        </div>
        """.format(st.session_state.get('display_name', '')), unsafe_allow_html=True)
        
        years = get_years()
        year = st.selectbox("📅 سال منتخب کریں", years, index=0)
        st.session_state.year = year
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("<p style='font-size: 11px; font-weight: 700; text-transform: uppercase; color: #64748b; margin-bottom: 12px;'>مینو</p>", unsafe_allow_html=True)
        
        if st.button("💰 انکم انٹری"):
            st.session_state.view = "income"
        
        if st.button("💸 خرچ انٹری"):
            st.session_state.view = "expense"
        
        if st.button("📊 ڈیش بورڈ"):
            st.session_state.view = "overview"
        
        if st.button("📒 لیجر"):
            st.session_state.view = "ledger"
        
        if st.button("🗂️ اکاؤنٹس"):
            st.session_state.view = "accounts"
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        if st.button("🚪 لاگ آؤٹ"):
            st.session_state.clear()
            st.rerun()
    
    # Main Content
    conn = get_connection()
    year = st.session_state.year
    
    if "view" not in st.session_state:
        st.session_state.view = "overview"
    
    view = st.session_state.view
    
    # Income Entry
    if view == "income":
        page_header("💰 انکم انٹری", "روزانہ کی آمدنی درج کریں")
        
        with st.form("income_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                date = st.date_input("📆 تاریخ", value=datetime.now())
                code = st.text_input("🔢 اکاؤنٹ کوڈ", max_chars=3, placeholder="001")
            
            with col2:
                account_name = ""
                if code:
                    acc = conn.execute("SELECT name FROM accounts WHERE code=?", (code.zfill(3),)).fetchone()
                    account_name = acc["name"] if acc else ""
                
                st.text_input("🏦 اکاؤنٹ کا نام", value=account_name, disabled=True)
                amount = st.number_input("💵 رقم (PKR)", min_value=0.0, step=100.0, format="%.2f")
            
            description = st.text_area("📝 تفصیل", placeholder="تفصیل یہاں لکھیں...", height=100)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col2:
                submitted = st.form_submit_button("✓ محفوظ کریں", use_container_width=True)
            
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
                    st.error("⚠️ کوڈ اور رقم ضروری ہیں")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📋 حالیہ انٹریز")
        st.markdown("<br>", unsafe_allow_html=True)
        
        recent = fetch_entries(conn, year, mode="income", limit=10)
        if recent:
            for entry in recent:
                st.markdown(f"""
                <div class="entry-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1;">
                            <div style="font-size: 12px; color: #64748b; margin-bottom: 4px; font-weight: 600;">📅 {entry['entry_date']}</div>
                            <div style="font-size: 15px; font-weight: 700; color: #0f172a;">🔢 {entry['code']} • {entry['account_name']}</div>
                            <div style="font-size: 13px; color: #475569; margin-top: 4px;">📝 {entry['description'][:80]}</div>
                        </div>
                        <div style="text-align: right; min-width: 140px;">
                            <div style="font-size: 24px; font-weight: 800; color: #6366f1;">₨ {entry['income']:,.0f}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("ℹ️ ابھی تک کوئی انکم درج نہیں ہوئی")
    
    # Expense Entry
    elif view == "expense":
        page_header("💸 خرچ انٹری", "روزانہ کے اخراجات درج کریں")
        
        with st.form("expense_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                date = st.date_input("📆 تاریخ", value=datetime.now())
                code = st.text_input("🔢 اکاؤنٹ کوڈ", max_chars=3, placeholder="007")
            
            with col2:
                account_name = ""
                if code:
                    acc = conn.execute("SELECT name FROM accounts WHERE code=?", (code.zfill(3),)).fetchone()
                    account_name = acc["name"] if acc else ""
                
                st.text_input("🏦 اکاؤنٹ کا نام", value=account_name, disabled=True)
                amount = st.number_input("💵 رقم (PKR)", min_value=0.0, step=100.0, format="%.2f")
            
            description = st.text_area("📝 تفصیل", placeholder="تفصیل یہاں لکھیں...", height=100)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col2:
                submitted = st.form_submit_button("✓ محفوظ کریں", use_container_width=True)
            
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
                    st.error("⚠️ کوڈ اور رقم ضروری ہیں")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📋 حالیہ انٹریز")
        st.markdown("<br>", unsafe_allow_html=True)
        
        recent = fetch_entries(conn, year, mode="expense", limit=10)
        if recent:
            for entry in recent:
                st.markdown(f"""
                <div class="entry-card expense">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1;">
                            <div style="font-size: 12px; color: #64748b; margin-bottom: 4px; font-weight: 600;">📅 {entry['entry_date']}</div>
                            <div style="font-size: 15px; font-weight: 700; color: #0f172a;">🔢 {entry['code']} • {entry['account_name']}</div>
                            <div style="font-size: 13px; color: #475569; margin-top: 4px;">📝 {entry['description'][:80]}</div>
                        </div>
                        <div style="text-align: right; min-width: 140px;">
                            <div style="font-size: 24px; font-weight: 800; color: #ef4444;">₨ {entry['payment']:,.0f}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("ℹ️ ابھی تک کوئی خرچ درج نہیں ہوا")
    
    # Overview
    elif view == "overview":
        page_header("📊 ڈیش بورڈ", f"سال {year} کا مالی جائزہ")
        
        dash = get_dashboard(conn, year)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-card-icon">💰</div>
                <div class="stat-card-label">کل آمدنی</div>
                <div class="stat-card-value text-primary">₨ {dash['summary']['total_income']:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-card-icon">💸</div>
                <div class="stat-card-label">کل اخراجات</div>
                <div class="stat-card-value text-danger">₨ {dash['summary']['total_payment']:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            balance = dash['summary']['balance']
            balance_color = "text-success" if balance > 0 else "text-danger"
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-card-icon">⚖️</div>
                <div class="stat-card-label">خالص بیلنس</div>
                <div class="stat-card-value {balance_color}">₨ {balance:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        if dash['monthly']:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("### 📈 ماہانہ رپورٹ")
            
            df = pd.DataFrame(dash['monthly'])
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df['month'],
                y=df['income'],
                name='آمدنی',
                marker_color='#6366f1'
            ))
            fig.add_trace(go.Bar(
                x=df['month'],
                y=df['payment'],
                name='اخراجات',
                marker_color='#ef4444'
            ))
            
            fig.update_layout(
                barmode='group',
                height=400,
                margin=dict(l=0, r=0, t=0, b=0),
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(family='Inter', size=12),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='#f1f5f9')
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Ledger
    elif view == "ledger":
        page_header("📒 لیجر", "تمام لین دین")
        
        entries = fetch_entries(conn, year, limit=100)
        
        if entries:
            data = []
            for e in entries:
                data.append({
                    "📅 تاریخ": e['entry_date'],
                    "🔢 کوڈ": e['code'],
                    "🏦 اکاؤنٹ": e['account_name'],
                    "📝 تفصیل": e['description'][:60],
                    "💰 آمدنی": f"₨ {e['income']:,.0f}" if e['income'] > 0 else "-",
                    "💸 اخراجات": f"₨ {e['payment']:,.0f}" if e['payment'] > 0 else "-"
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, height=600)
        else:
            st.info("ℹ️ کوئی ڈیٹا نہیں ملا")
    
    # Accounts
    elif view == "accounts":
        page_header("🗂️ اکاؤنٹس", "تمام اکاؤنٹ ہیڈز")
        
        accounts = conn.execute("SELECT code, name, atype FROM accounts ORDER BY code").fetchall()
        
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
            st.info("ℹ️ کوئی اکاؤنٹ نہیں ملا")
    
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
