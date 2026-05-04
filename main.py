import html
import os
import sqlite3
import uuid
from datetime import date, datetime
from pathlib import Path

import bcrypt
import pandas as pd
import streamlit as st


# ----------------------- Configuration -----------------------
APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "madrasa_modern.sqlite3"
UPLOAD_DIR = APP_DIR / "uploaded_bills"
UPLOAD_DIR.mkdir(exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(
        """
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
        CREATE INDEX IF NOT EXISTS idx_entries_year_kind ON entries(year, income, payment);
        """
    )
    seed_default_user(conn)
    seed_accounts_from_pdf(conn)
    ensure_control_year(conn, str(datetime.now().year))
    conn.commit()
    conn.close()


def seed_default_user(conn):
    exists = conn.execute("SELECT username FROM app_users WHERE username = 'admin'").fetchone()
    if not exists:
        hashed = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        conn.execute(
            "INSERT INTO app_users (username, password_hash, display_name) VALUES (?, ?, ?)",
            ("admin", hashed, "Administrator"),
        )


def seed_accounts_from_pdf(conn):
    accounts = [
        ("001", "SADQAT", ""),
        ("002", "ZAKAT", ""),
        ("003", "GENERAL DONATION", ""),
        ("004", "CONSTRUCTION DONATION", ""),
        ("005", "FOOD EXPENSES", ""),
        ("006", "QARZ-E-HASSNA", ""),
        ("007", "ELECTICITY", ""),
        ("008", "PHONE & POSTAGE", ""),
        ("009", "SUI GAS", ""),
        ("010", "MISC. EXP.", ""),
        ("011", "MASJID DONATION", ""),
        ("012", "MISC. RENT EXP", ""),
        ("013", "ELECTRIC GOODS", ""),
        ("014", "REPAIR & MAINTINANCE", ""),
        ("015", "TRANSPORTATION", ""),
        ("016", "FURNITURE & FIXTURE", ""),
        ("017", "MEDICEN EXP.", ""),
        ("018", "PRINTING & STATIONARY", ""),
        ("019", "NEWS PAPERS", ""),
        ("020", "LANDRY", ""),
        ("021", "CLOTH & SHOES EXP.", ""),
        ("022", "CROCKY", ""),
        ("023", "AUDIT FEE", ""),
        ("024", "BOOKS", ""),
        ("025", "SALARIES", ""),
        ("026", "SENETARY EXP.", ""),
        ("027", "OTHER INCOME", ""),
        ("028", "HABIB BANK A/C NO. 17271-6", ""),
        ("029", "BANK CHARGES", ""),
        ("030", "SALES OF HIDE", ""),
        ("031", "CARPETS", ""),
        ("032", "OFFICE EQUIPMENTS", ""),
        ("033", "BUILDING", ""),
        ("034", "PRAYER MATS (SAFAIN)", ""),
        ("035", "CLEANLINESS ETC", ""),
        ("036", "WATER PUMP", ""),
        ("037", "RECEIVABLE A/C", ""),
        ("038", "ACCOUMULATED FUND", ""),
        ("039", "EXPENSES PAYABLE", "BS"),
        ("040", "WAGES ETC", "PA"),
        ("041", "COMPUTER", "BS"),
        ("042", "LAIBRARY BOOKS", ""),
        ("043", "SECURITY DEPOSIT", "BS"),
        ("044", "PRISES TO STUDENT", ""),
        ("045", "STEPENDS", ""),
        ("046", "SOLAR SYSTEM", "BS"),
        ("047", "TUFF TILES", "BS"),
    ]
    for code, name, atype in accounts:
        conn.execute(
            "INSERT OR IGNORE INTO accounts (code, name, atype) VALUES (?, ?, ?)",
            (code, name, atype.strip()),
        )


# ----------------------- Translations -----------------------
I18N = {
    "en": {
        "app_title": "Madrasa Accounting",
        "login_title": "Madrasa Accounting System",
        "login_subtitle": "Jamia Millia Islamia & Masjid Madrasa Wali",
        "username": "Username",
        "password": "Password",
        "login_btn": "Login",
        "logout": "Logout",
        "income": "Income Entry",
        "expense": "Expense Entry",
        "overview": "Overview",
        "ledger": "Ledger",
        "accounts": "Accounts",
        "settings": "Settings",
        "year": "Financial Year",
        "language": "Language",
        "save": "Save",
        "date": "Date",
        "account": "Account",
        "description": "Description",
        "amount": "Amount",
        "receipt_no": "Receipt No.",
        "voucher_no": "Voucher No.",
        "bill": "Bill Image",
        "recent_income": "Recent Income",
        "recent_expense": "Recent Expenses",
        "total_income": "Total Income",
        "total_expense": "Total Expenses",
        "net_balance": "Net Balance",
        "cash_in_hand": "Cash in Hand",
        "monthly_report": "Monthly Report",
        "top_accounts": "Top Accounts",
        "no_data": "No records found",
        "success_income": "Income saved successfully.",
        "success_expense": "Expense saved successfully.",
        "required": "Account and amount are required.",
    },
    "ur": {
        "app_title": "مدرسہ اکاؤنٹنگ",
        "login_title": "مدرسہ اکاؤنٹنگ سسٹم",
        "login_subtitle": "جامعہ ملیہ اسلامیہ و مسجد مدرسہ والی",
        "username": "یوزر نیم",
        "password": "پاس ورڈ",
        "login_btn": "لاگ ان",
        "logout": "لاگ آؤٹ",
        "income": "انکم انٹری",
        "expense": "خرچ انٹری",
        "overview": "مالی جائزہ",
        "ledger": "لیجر",
        "accounts": "اکاؤنٹس",
        "settings": "سیٹنگز",
        "year": "مالی سال",
        "language": "زبان",
        "save": "محفوظ کریں",
        "date": "تاریخ",
        "account": "اکاؤنٹ",
        "description": "تفصیل",
        "amount": "رقم",
        "receipt_no": "رسید نمبر",
        "voucher_no": "واؤچر نمبر",
        "bill": "بل تصویر",
        "recent_income": "حالیہ انکم",
        "recent_expense": "حالیہ اخراجات",
        "total_income": "کل آمدنی",
        "total_expense": "کل اخراجات",
        "net_balance": "خالص بیلنس",
        "cash_in_hand": "کیش ان ہینڈ",
        "monthly_report": "ماہانہ رپورٹ",
        "top_accounts": "اہم اکاؤنٹس",
        "no_data": "کوئی ریکارڈ نہیں ملا",
        "success_income": "انکم کامیابی سے محفوظ ہو گئی۔",
        "success_expense": "خرچ کامیابی سے محفوظ ہو گیا۔",
        "required": "اکاؤنٹ اور رقم ضروری ہیں۔",
    },
}


def t(key):
    return I18N.get(st.session_state.get("lang", "ur"), I18N["ur"]).get(key, key)


def rtl():
    return st.session_state.get("lang", "ur") == "ur"


# ----------------------- Styling -----------------------
def apply_modern_css():
    direction = "rtl" if rtl() else "ltr"
    text_align = "right" if rtl() else "left"
    st.markdown(
        f"""
        <style>
        :root {{
            --bg: #f6f8fb;
            --panel: rgba(255, 255, 255, 0.94);
            --panel-solid: #ffffff;
            --text: #14213d;
            --muted: #64748b;
            --primary: #0f766e;
            --primary-strong: #0b5f59;
            --secondary: #2563eb;
            --accent: #f59e0b;
            --danger: #dc2626;
            --success: #16a34a;
            --border: #dde6ef;
            --shadow: 0 16px 40px rgba(15, 23, 42, 0.10);
            --shadow-soft: 0 8px 24px rgba(15, 23, 42, 0.08);
        }}

        * {{
            font-family: "Segoe UI", "Noto Nastaliq Urdu", Tahoma, Arial, sans-serif !important;
            letter-spacing: 0 !important;
        }}

        .stApp {{
            direction: {direction};
            background:
                radial-gradient(circle at top left, rgba(14, 165, 233, 0.14), transparent 28rem),
                radial-gradient(circle at bottom right, rgba(245, 158, 11, 0.16), transparent 24rem),
                linear-gradient(180deg, #f8fafc 0%, #eef5f1 100%);
            color: var(--text);
        }}

        .main .block-container {{
            max-width: 1280px;
            padding-top: 1.25rem;
            padding-bottom: 2.5rem;
        }}

        [data-testid="stSidebar"] {{
            background: rgba(255, 255, 255, 0.92) !important;
            border-{ "left" if rtl() else "right" }: 1px solid var(--border);
            box-shadow: var(--shadow-soft);
        }}

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span {{
            color: var(--text) !important;
        }}

        h1, h2, h3 {{
            color: var(--text) !important;
            font-weight: 800 !important;
            text-shadow: none !important;
        }}

        p, label, span, div {{
            text-align: {text_align};
        }}

        label {{
            color: var(--text) !important;
            font-size: 0.84rem !important;
            font-weight: 750 !important;
        }}

        .stButton > button,
        .stDownloadButton > button,
        div[data-testid="stFormSubmitButton"] button {{
            width: 100%;
            min-height: 3rem;
            border: 0 !important;
            border-radius: 12px !important;
            color: #ffffff !important;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%) !important;
            font-weight: 800 !important;
            box-shadow: 0 10px 24px rgba(15, 118, 110, 0.22) !important;
            transition: transform 0.16s ease, box-shadow 0.16s ease, filter 0.16s ease !important;
        }}

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        div[data-testid="stFormSubmitButton"] button:hover {{
            transform: translateY(-2px);
            filter: brightness(1.03);
            box-shadow: 0 14px 30px rgba(37, 99, 235, 0.24) !important;
        }}

        .stButton > button:active,
        .stDownloadButton > button:active,
        div[data-testid="stFormSubmitButton"] button:active {{
            transform: translateY(0);
        }}

        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        .stDateInput input,
        .stSelectbox div[data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] > div {{
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            background: #ffffff !important;
            color: var(--text) !important;
            box-shadow: 0 1px 0 rgba(15, 23, 42, 0.03);
        }}

        .stTextInput input:focus,
        .stTextArea textarea:focus,
        .stNumberInput input:focus,
        .stDateInput input:focus {{
            border-color: var(--primary) !important;
            box-shadow: 0 0 0 4px rgba(15, 118, 110, 0.12) !important;
        }}

        [data-testid="stForm"],
        .soft-panel {{
            background: var(--panel) !important;
            border: 1px solid rgba(221, 230, 239, 0.9) !important;
            border-radius: 16px !important;
            padding: 1.35rem !important;
            box-shadow: var(--shadow-soft) !important;
        }}

        [data-testid="stMetric"] {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1rem 1.1rem;
            box-shadow: var(--shadow-soft);
        }}

        [data-testid="stMetricValue"] {{
            color: var(--text) !important;
            font-size: 1.9rem !important;
            font-weight: 850 !important;
        }}

        [data-testid="stMetricLabel"] {{
            color: var(--muted) !important;
            font-weight: 750 !important;
        }}

        .hero {{
            background:
                linear-gradient(135deg, rgba(15, 118, 110, 0.97), rgba(37, 99, 235, 0.92)),
                linear-gradient(45deg, rgba(245, 158, 11, 0.18), transparent);
            border-radius: 18px;
            padding: 1.35rem 1.5rem;
            margin-bottom: 1.25rem;
            color: white;
            box-shadow: var(--shadow);
        }}

        .hero h1 {{
            color: white !important;
            margin: 0 0 0.35rem 0;
            font-size: 2rem;
        }}

        .hero p {{
            color: rgba(255, 255, 255, 0.88);
            margin: 0;
            font-weight: 600;
        }}

        .brand-card {{
            background: linear-gradient(135deg, #0f766e, #2563eb);
            color: white;
            border-radius: 18px;
            padding: 1.25rem;
            box-shadow: var(--shadow-soft);
        }}

        .brand-card * {{
            color: white !important;
            text-align: center !important;
        }}

        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.9rem;
            margin-bottom: 1rem;
        }}

        .kpi-card {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.05rem;
            box-shadow: var(--shadow-soft);
        }}

        .kpi-label {{
            color: var(--muted);
            font-size: 0.82rem;
            font-weight: 800;
            margin-bottom: 0.4rem;
        }}

        .kpi-value {{
            color: var(--text);
            font-size: 1.7rem;
            font-weight: 900;
            line-height: 1.15;
        }}

        .kpi-foot {{
            color: var(--muted);
            font-size: 0.78rem;
            margin-top: 0.35rem;
        }}

        .entry-card {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-{ "right" if rtl() else "left" }: 5px solid var(--primary);
            border-radius: 14px;
            padding: 1rem;
            margin-bottom: 0.75rem;
            box-shadow: var(--shadow-soft);
        }}

        .entry-card.expense {{
            border-{ "right" if rtl() else "left" }-color: var(--danger);
        }}

        .entry-title {{
            color: var(--text);
            font-weight: 850;
            font-size: 1rem;
        }}

        .entry-meta {{
            color: var(--muted);
            font-size: 0.82rem;
            font-weight: 650;
        }}

        .entry-amount {{
            color: var(--primary);
            font-size: 1.45rem;
            font-weight: 900;
            white-space: nowrap;
        }}

        .entry-card.expense .entry-amount {{
            color: var(--danger);
        }}

        .status-pill {{
            display: inline-block;
            padding: 0.25rem 0.65rem;
            border-radius: 999px;
            font-weight: 850;
            font-size: 0.78rem;
            background: rgba(15, 118, 110, 0.12);
            color: var(--primary);
        }}

        .status-pill.warn {{
            background: rgba(245, 158, 11, 0.16);
            color: #92400e;
        }}

        .status-pill.danger {{
            background: rgba(220, 38, 38, 0.12);
            color: var(--danger);
        }}

        .stDataFrame {{
            border: 1px solid var(--border);
            border-radius: 14px;
            overflow: hidden;
            box-shadow: var(--shadow-soft);
        }}

        div[data-testid="stAlert"] {{
            border-radius: 14px !important;
            border: 1px solid var(--border);
        }}

        @media (max-width: 900px) {{
            .kpi-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
            .hero h1 {{
                font-size: 1.55rem;
            }}
        }}

        @media (max-width: 600px) {{
            .kpi-grid {{
                grid-template-columns: 1fr;
            }}
            .main .block-container {{
                padding-left: 0.8rem;
                padding-right: 0.8rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def safe_text(value):
    return html.escape("" if value is None else str(value))


def money(value):
    return f"{float(value or 0):,.0f}"


def page_header(title, subtitle="", icon="📚"):
    st.markdown(
        f"""
        <section class="hero">
            <div style="display:flex; gap:1rem; align-items:center; justify-content:space-between; flex-wrap:wrap;">
                <div>
                    <h1>{safe_text(icon)} {safe_text(title)}</h1>
                    <p>{safe_text(subtitle)}</p>
                </div>
                <span class="status-pill" style="background:rgba(255,255,255,0.18); color:white;">
                    {safe_text(st.session_state.get("year", ""))}
                </span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def kpi_grid(items):
    cards = []
    for item in items:
        cards.append(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">{safe_text(item["label"])}</div>
                <div class="kpi-value" style="color:{safe_text(item.get("color", "#14213d"))};">
                    {safe_text(item["value"])}
                </div>
                <div class="kpi-foot">{safe_text(item.get("foot", ""))}</div>
            </div>
            """
        )
    st.markdown(f'<div class="kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def entry_card(entry):
    is_expense = float(entry["payment"] or 0) > 0
    amount = entry["payment"] if is_expense else entry["income"]
    card_class = "entry-card expense" if is_expense else "entry-card"
    label = t("expense") if is_expense else t("income")
    description = safe_text(entry["description"])[:120]
    account = f'{entry["code"]} - {entry["account_name"] or ""}'
    st.markdown(
        f"""
        <div class="{card_class}">
            <div style="display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; flex-wrap:wrap;">
                <div>
                    <div class="entry-meta">{safe_text(entry["entry_date"])} · {safe_text(label)}</div>
                    <div class="entry-title">{safe_text(account)}</div>
                    <div class="entry-meta" style="margin-top:0.35rem;">{description}</div>
                </div>
                <div class="entry-amount">PKR {money(amount)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------------- Data Helpers -----------------------
def get_years():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT year FROM entries
        UNION
        SELECT year FROM control_settings
        ORDER BY year DESC
        """
    ).fetchall()
    conn.close()
    years = [r["year"] for r in rows if r["year"]]
    current_year = str(datetime.now().year)
    if current_year not in years:
        years.insert(0, current_year)
    return years or [current_year]


def ensure_control_year(conn, year):
    exists = conn.execute("SELECT year FROM control_settings WHERE year=?", (year,)).fetchone()
    if not exists:
        conn.execute(
            """
            INSERT INTO control_settings (year, start_date, end_date)
            VALUES (?, ?, ?)
            """,
            (year, f"{year}-01-01", f"{year}-12-31"),
        )


def get_accounts(conn):
    return conn.execute("SELECT code, name, atype FROM accounts ORDER BY code").fetchall()


def account_options(conn):
    rows = get_accounts(conn)
    options = [f'{r["code"]} - {r["name"]}' for r in rows]
    return options


def code_from_option(option):
    return (option or "").split(" - ", 1)[0].strip().zfill(3)


def get_dashboard(conn, year):
    ensure_control_year(conn, year)
    summ = conn.execute(
        """
        SELECT
            COUNT(*) AS entries_count,
            ROUND(COALESCE(SUM(income),0),2) AS total_income,
            ROUND(COALESCE(SUM(payment),0),2) AS total_payment,
            ROUND(COALESCE(SUM(income-payment),0),2) AS balance
        FROM entries
        WHERE year=?
        """,
        (year,),
    ).fetchone()

    settings = conn.execute(
        "SELECT * FROM control_settings WHERE year=?",
        (year,),
    ).fetchone()

    monthly = conn.execute(
        """
        SELECT
            substr(entry_date,1,7) AS month,
            ROUND(SUM(income),2) AS income,
            ROUND(SUM(payment),2) AS payment,
            ROUND(SUM(income-payment),2) AS balance
        FROM entries
        WHERE year=? AND entry_date IS NOT NULL
        GROUP BY month
        ORDER BY month
        """,
        (year,),
    ).fetchall()

    top = conn.execute(
        """
        SELECT
            e.code,
            COALESCE(a.name,'') AS name,
            ROUND(SUM(e.income),2) AS income,
            ROUND(SUM(e.payment),2) AS payment,
            ROUND(SUM(e.income-e.payment),2) AS balance
        FROM entries e
        LEFT JOIN accounts a ON a.code=e.code
        WHERE e.year=?
        GROUP BY e.code
        ORDER BY ABS(SUM(e.income-e.payment)) DESC
        LIMIT 10
        """,
        (year,),
    ).fetchall()

    return {
        "summary": dict(summ),
        "settings": dict(settings) if settings else {},
        "monthly": [dict(r) for r in monthly],
        "top_accounts": [dict(r) for r in top],
    }


def fetch_entries(
    conn,
    year,
    mode="all",
    limit=100,
    account_code=None,
    search="",
    start_date=None,
    end_date=None,
):
    sql = """
        SELECT e.*, COALESCE(a.name,'') AS account_name
        FROM entries e
        LEFT JOIN accounts a ON a.code=e.code
        WHERE e.year=?
    """
    params = [year]

    if mode == "income":
        sql += " AND e.income > 0"
    elif mode == "expense":
        sql += " AND e.payment > 0"

    if account_code and account_code != "all":
        sql += " AND e.code=?"
        params.append(account_code)

    if search:
        sql += " AND (e.description LIKE ? OR e.code LIKE ? OR a.name LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])

    if start_date:
        sql += " AND e.entry_date >= ?"
        params.append(start_date)

    if end_date:
        sql += " AND e.entry_date <= ?"
        params.append(end_date)

    sql += " ORDER BY e.entry_date DESC, e.id DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"

    return conn.execute(sql, params).fetchall()


def save_uploaded_bill(uploaded_file):
    if uploaded_file is None:
        return None

    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".pdf"}:
        suffix = ".bin"

    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{suffix}"
    destination = UPLOAD_DIR / filename
    destination.write_bytes(uploaded_file.getbuffer())
    return str(destination)


def save_entry(
    conn,
    year,
    entry_date,
    code,
    description,
    amount,
    entry_type,
    receipt_no=None,
    voucher_no=None,
    bill_image=None,
):
    code = code.zfill(3)
    conn.execute("INSERT OR IGNORE INTO accounts (code) VALUES (?)", (code,))
    income, payment = (float(amount), 0.0) if entry_type == "income" else (0.0, float(amount))
    entry_kind = "R" if entry_type == "income" else "P"
    conn.execute(
        """
        INSERT INTO entries (
            year, entry_date, code, description, income, payment,
            receipt_no, voucher_no, entry_kind, source_file, bill_image
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'MODERN', ?)
        """,
        (
            year,
            entry_date,
            code,
            description.strip(),
            income,
            payment,
            receipt_no,
            voucher_no,
            entry_kind,
            bill_image,
        ),
    )
    conn.commit()


def entries_to_frame(entries):
    data = []
    for e in entries:
        data.append(
            {
                "ID": e["id"],
                "Date": e["entry_date"],
                "Code": e["code"],
                "Account": e["account_name"],
                "Description": e["description"],
                "Receipt": e["receipt_no"],
                "Voucher": e["voucher_no"],
                "Income": float(e["income"] or 0),
                "Payment": float(e["payment"] or 0),
                "Balance": float(e["income"] or 0) - float(e["payment"] or 0),
                "Bill": e["bill_image"] or "",
            }
        )
    return pd.DataFrame(data)


def upsert_account(conn, code, name, atype):
    code = code.zfill(3)
    conn.execute(
        """
        INSERT INTO accounts (code, name, atype, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(code) DO UPDATE SET
            name=excluded.name,
            atype=excluded.atype,
            updated_at=CURRENT_TIMESTAMP
        """,
        (code, name.strip(), atype.strip()),
    )
    conn.commit()


def delete_entry(conn, entry_id):
    conn.execute("DELETE FROM entries WHERE id=?", (entry_id,))
    conn.commit()


# ----------------------- Auth -----------------------
def login_page():
    apply_modern_css()
    st.markdown(
        f"""
        <div style="max-width:560px; margin:6vh auto 1.5rem auto;">
            <div class="brand-card">
                <div style="font-size:3.4rem; margin-bottom:0.4rem;">📚</div>
                <h1 style="margin:0; font-size:2rem;">{safe_text(t("login_title"))}</h1>
                <p style="margin:0.5rem 0 0 0; opacity:0.9;">{safe_text(t("login_subtitle"))}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1.25, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("👤 " + t("username"), value="admin")
            password = st.text_input("🔒 " + t("password"), type="password", value="admin123")
            submitted = st.form_submit_button("🔐 " + t("login_btn"), use_container_width=True)

            if submitted:
                conn = get_connection()
                user = conn.execute("SELECT * FROM app_users WHERE username=?", (username,)).fetchone()
                if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
                    st.session_state.authenticated = True
                    st.session_state.user = user["username"]
                    st.session_state.display_name = user["display_name"] or user["username"]
                    conn.close()
                    st.rerun()
                conn.close()
                st.error("غلط یوزر نیم یا پاس ورڈ")


def sidebar(conn):
    with st.sidebar:
        st.markdown(
            f"""
            <div class="brand-card" style="margin-bottom:1rem;">
                <div style="font-size:2.4rem;">📚</div>
                <h2 style="font-size:1.3rem; margin:0.35rem 0 0 0;">{safe_text(t("app_title"))}</h2>
                <p style="font-size:0.9rem;">{safe_text(st.session_state.get("display_name", ""))}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        years = get_years()
        current_year = st.session_state.get("year", years[0])
        if current_year not in years:
            current_year = years[0]
        st.session_state.year = st.selectbox(
            "📅 " + t("year"),
            years,
            index=years.index(current_year),
        )
        ensure_control_year(conn, st.session_state.year)

        selected_lang = st.radio(
            "🌐 " + t("language"),
            ["اردو", "English"],
            index=0 if st.session_state.get("lang", "ur") == "ur" else 1,
            horizontal=True,
        )
        st.session_state.lang = "ur" if selected_lang == "اردو" else "en"

        nav_items = {
            "overview": "📈 " + t("overview"),
            "income": "💰 " + t("income"),
            "expense": "💸 " + t("expense"),
            "ledger": "📒 " + t("ledger"),
            "accounts": "🗂 " + t("accounts"),
            "settings": "⚙ " + t("settings"),
        }
        current_view = st.session_state.get("view", "overview")
        selected_label = nav_items.get(current_view, nav_items["overview"])
        selected = st.radio(
            "",
            list(nav_items.values()),
            index=list(nav_items.values()).index(selected_label),
            label_visibility="collapsed",
        )
        st.session_state.view = next(key for key, value in nav_items.items() if value == selected)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 " + t("logout"), use_container_width=True):
            st.session_state.clear()
            st.session_state.lang = "ur"
            st.rerun()


# ----------------------- Pages -----------------------
def entry_form(conn, year, entry_type):
    is_income = entry_type == "income"
    title = t("income") if is_income else t("expense")
    subtitle = "روزانہ کی آمدنی درج کریں" if is_income else "روزانہ کے اخراجات درج کریں"
    icon = "💰" if is_income else "💸"
    page_header(title, subtitle, icon)

    accounts = account_options(conn)
    if not accounts:
        st.warning("پہلے اکاؤنٹ بنائیں۔")
        return

    with st.form(f"{entry_type}_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([1, 1.5, 1])
        entry_date = col1.date_input("📆 " + t("date"), value=date.today())
        account = col2.selectbox("🏦 " + t("account"), accounts)
        amount = col3.number_input("💵 " + t("amount") + " (PKR)", min_value=0.0, step=100.0, format="%.2f")

        col4, col5 = st.columns(2)
        receipt_no = None
        voucher_no = None
        if is_income:
            receipt_no = col4.number_input("🧾 " + t("receipt_no"), min_value=0, step=1, value=0)
        else:
            voucher_no = col4.number_input("🧾 " + t("voucher_no"), min_value=0, step=1, value=0)
        bill_file = col5.file_uploader("📎 " + t("bill"), type=["jpg", "jpeg", "png", "webp", "pdf"])

        description = st.text_area(
            "📄 " + t("description"),
            height=110,
            placeholder="تفصیل لکھیں...",
        )

        submitted = st.form_submit_button("💾 " + t("save"), use_container_width=True)

    if submitted:
        code = code_from_option(account)
        if not code or amount <= 0:
            st.error(t("required"))
            return

        try:
            bill_path = save_uploaded_bill(bill_file)
            save_entry(
                conn,
                year,
                entry_date.isoformat(),
                code,
                description,
                amount,
                entry_type,
                receipt_no=receipt_no or None,
                voucher_no=voucher_no or None,
                bill_image=bill_path,
            )
            st.success(t("success_income") if is_income else t("success_expense"))
            st.rerun()
        except Exception as exc:
            st.error(f"خرابی: {exc}")

    st.markdown("### " + ("📋 " + t("recent_income") if is_income else "📋 " + t("recent_expense")))
    recent = fetch_entries(conn, year, mode=entry_type, limit=8)
    if recent:
        for entry in recent:
            entry_card(entry)
    else:
        st.info(t("no_data"))


def overview_page(conn, year):
    page_header(t("overview"), f"سال {year} کا خلاصہ", "📈")
    dash = get_dashboard(conn, year)
    summary = dash["summary"]
    settings = dash["settings"]
    cash_in_hand = float(settings.get("cash_in_hand") or 0)
    min_cash = float(settings.get("min_cash") or 0)
    max_cash = float(settings.get("max_cash") or 0)

    kpi_grid(
        [
            {
                "label": t("total_income"),
                "value": "PKR " + money(summary["total_income"]),
                "foot": f'{summary["entries_count"]} entries',
                "color": "#0f766e",
            },
            {
                "label": t("total_expense"),
                "value": "PKR " + money(summary["total_payment"]),
                "foot": "Payments",
                "color": "#dc2626",
            },
            {
                "label": t("net_balance"),
                "value": "PKR " + money(summary["balance"]),
                "foot": "Income minus expenses",
                "color": "#2563eb" if summary["balance"] >= 0 else "#dc2626",
            },
            {
                "label": t("cash_in_hand"),
                "value": "PKR " + money(cash_in_hand),
                "foot": "Control settings",
                "color": "#f59e0b",
            },
        ]
    )

    if min_cash and cash_in_hand < min_cash:
        st.warning(f"کیش کم ہے: موجودہ کیش {money(cash_in_hand)}، کم از کم حد {money(min_cash)}")
    elif max_cash and cash_in_hand > max_cash:
        st.info(f"کیش حد سے زیادہ ہے: موجودہ کیش {money(cash_in_hand)}، زیادہ سے زیادہ حد {money(max_cash)}")

    left, right = st.columns([1.25, 1])
    with left:
        st.markdown("### 📊 " + t("monthly_report"))
        if dash["monthly"]:
            monthly_df = pd.DataFrame(dash["monthly"]).set_index("month")
            st.bar_chart(monthly_df[["income", "payment"]], use_container_width=True)
            st.line_chart(monthly_df[["balance"]], use_container_width=True)
        else:
            st.info(t("no_data"))

    with right:
        st.markdown("### 🏆 " + t("top_accounts"))
        if dash["top_accounts"]:
            st.dataframe(pd.DataFrame(dash["top_accounts"]), use_container_width=True, height=360)
        else:
            st.info(t("no_data"))

    st.markdown("### 🧾 حالیہ لین دین")
    recent = fetch_entries(conn, year, mode="all", limit=6)
    if recent:
        for entry in recent:
            entry_card(entry)
    else:
        st.info(t("no_data"))


def ledger_page(conn, year):
    page_header(t("ledger"), "فلٹر، تلاش، ایکسپورٹ اور ڈیلیٹ", "📒")

    accounts = ["all - تمام اکاؤنٹس"] + account_options(conn)
    with st.container():
        col1, col2, col3, col4 = st.columns([1, 1, 1.2, 0.8])
        mode_label = col1.selectbox("قسم", ["all", "income", "expense"], format_func=lambda x: {"all": "تمام", "income": "انکم", "expense": "خرچ"}[x])
        account = col2.selectbox("اکاؤنٹ", accounts)
        search = col3.text_input("تلاش", placeholder="کوڈ، اکاؤنٹ یا تفصیل")
        limit = col4.number_input("حد", min_value=25, max_value=1000, value=200, step=25)

        col5, col6 = st.columns(2)
        start = col5.date_input("شروع تاریخ", value=None)
        end = col6.date_input("آخر تاریخ", value=None)

    account_code = "all" if account.startswith("all") else code_from_option(account)
    entries = fetch_entries(
        conn,
        year,
        mode=mode_label,
        limit=limit,
        account_code=account_code,
        search=search.strip(),
        start_date=start.isoformat() if start else None,
        end_date=end.isoformat() if end else None,
    )

    if not entries:
        st.info(t("no_data"))
        return

    df = entries_to_frame(entries)
    total_income = df["Income"].sum()
    total_payment = df["Payment"].sum()
    kpi_grid(
        [
            {"label": "Records", "value": str(len(df)), "foot": "Filtered", "color": "#14213d"},
            {"label": t("total_income"), "value": "PKR " + money(total_income), "foot": "", "color": "#0f766e"},
            {"label": t("total_expense"), "value": "PKR " + money(total_payment), "foot": "", "color": "#dc2626"},
            {"label": t("net_balance"), "value": "PKR " + money(total_income - total_payment), "foot": "", "color": "#2563eb"},
        ]
    )

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇ CSV Export",
        data=csv,
        file_name=f"madrasa_ledger_{year}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.dataframe(df, use_container_width=True, height=520)

    with st.expander("🗑 ریکارڈ ڈیلیٹ"):
        entry_id = st.number_input("Entry ID", min_value=1, step=1)
        confirm = st.checkbox("میں اس ریکارڈ کو ڈیلیٹ کرنا چاہتا ہوں")
        if st.button("Delete Entry", disabled=not confirm):
            delete_entry(conn, int(entry_id))
            st.success("ریکارڈ ڈیلیٹ ہو گیا۔")
            st.rerun()


def accounts_page(conn):
    page_header(t("accounts"), "اکاؤنٹ ہیڈز شامل یا اپڈیٹ کریں", "🗂")

    with st.form("account_form"):
        col1, col2, col3 = st.columns([0.7, 2, 0.8])
        code = col1.text_input("کوڈ", max_chars=3, placeholder="048")
        name = col2.text_input("نام", placeholder="Account name")
        atype = col3.text_input("قسم", placeholder="BS / PA")
        submitted = st.form_submit_button("💾 محفوظ / اپڈیٹ", use_container_width=True)

    if submitted:
        if not code.strip() or not name.strip():
            st.error("کوڈ اور نام ضروری ہیں۔")
        else:
            upsert_account(conn, code.strip(), name, atype)
            st.success("اکاؤنٹ محفوظ ہو گیا۔")
            st.rerun()

    accounts = get_accounts(conn)
    if accounts:
        df = pd.DataFrame([dict(r) for r in accounts])
        st.dataframe(df, use_container_width=True, height=560)
    else:
        st.info(t("no_data"))


def settings_page(conn, year):
    page_header(t("settings"), "سال، کیش حدود، پاس ورڈ اور بیک اپ", "⚙")
    ensure_control_year(conn, year)
    settings = conn.execute("SELECT * FROM control_settings WHERE year=?", (year,)).fetchone()

    tab1, tab2, tab3 = st.tabs(["مالی سال", "پاس ورڈ", "بیک اپ"])
    with tab1:
        with st.form("control_settings_form"):
            col1, col2 = st.columns(2)
            start_default = datetime.fromisoformat(settings["start_date"]).date() if settings["start_date"] else date(int(year), 1, 1)
            end_default = datetime.fromisoformat(settings["end_date"]).date() if settings["end_date"] else date(int(year), 12, 31)
            start_date = col1.date_input("Start Date", value=start_default)
            end_date = col2.date_input("End Date", value=end_default)

            col3, col4, col5, col6 = st.columns(4)
            cash = col3.number_input("Cash in Hand", min_value=0.0, value=float(settings["cash_in_hand"] or 0), step=100.0)
            min_cash = col4.number_input("Min Cash", min_value=0.0, value=float(settings["min_cash"] or 0), step=100.0)
            max_cash = col5.number_input("Max Cash", min_value=0.0, value=float(settings["max_cash"] or 0), step=100.0)
            last_jvno = col6.number_input("Last JV No", min_value=0, value=int(settings["last_jvno"] or 0), step=1)
            submitted = st.form_submit_button("💾 Settings Save", use_container_width=True)

        if submitted:
            conn.execute(
                """
                UPDATE control_settings
                SET start_date=?, end_date=?, cash_in_hand=?, min_cash=?, max_cash=?, last_jvno=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE year=?
                """,
                (start_date.isoformat(), end_date.isoformat(), cash, min_cash, max_cash, last_jvno, year),
            )
            conn.commit()
            st.success("سیٹنگز محفوظ ہو گئیں۔")
            st.rerun()

    with tab2:
        with st.form("password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("🔐 Password Update", use_container_width=True)

        if submitted:
            user = conn.execute("SELECT * FROM app_users WHERE username=?", (st.session_state.user,)).fetchone()
            if not user or not bcrypt.checkpw(current_password.encode(), user["password_hash"].encode()):
                st.error("موجودہ پاس ورڈ درست نہیں۔")
            elif len(new_password) < 6:
                st.error("نیا پاس ورڈ کم از کم 6 حروف کا ہونا چاہیے۔")
            elif new_password != confirm_password:
                st.error("نیا پاس ورڈ اور تصدیق برابر نہیں۔")
            else:
                hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                conn.execute(
                    "UPDATE app_users SET password_hash=?, updated_at=CURRENT_TIMESTAMP WHERE username=?",
                    (hashed, st.session_state.user),
                )
                conn.commit()
                st.success("پاس ورڈ اپڈیٹ ہو گیا۔")

    with tab3:
        if DB_PATH.exists():
            st.download_button(
                "⬇ Database Backup",
                data=DB_PATH.read_bytes(),
                file_name=f"madrasa_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.sqlite3",
                mime="application/octet-stream",
                use_container_width=True,
            )
        st.caption(f"Database: {DB_PATH}")
        st.caption(f"Bill uploads: {UPLOAD_DIR}")


def main_app():
    conn = get_connection()
    sidebar(conn)
    apply_modern_css()

    year = st.session_state.get("year", str(datetime.now().year))
    view = st.session_state.get("view", "overview")

    if view == "overview":
        overview_page(conn, year)
    elif view == "income":
        entry_form(conn, year, "income")
    elif view == "expense":
        entry_form(conn, year, "expense")
    elif view == "ledger":
        ledger_page(conn, year)
    elif view == "accounts":
        accounts_page(conn)
    elif view == "settings":
        settings_page(conn, year)

    conn.close()


def main():
    st.set_page_config(
        page_title="Madrasa Accounting",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_db()
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("lang", "ur")

    if st.session_state.authenticated:
        main_app()
    else:
        login_page()


if __name__ == "__main__":
    main()
