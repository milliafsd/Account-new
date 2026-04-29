import streamlit as st
import sqlite3
import bcrypt
import re
import struct
from pathlib import Path
from datetime import datetime
from io import BytesIO
import pandas as pd

# ----------------------- ڈیٹا بیس کنفیگریشن -----------------------
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
    seed_accounts_from_pdf(conn)   # کوڈ.پی ڈی ایف سے اکاؤنٹس داخل کریں
    conn.commit()
    conn.close()

def seed_default_user(conn):
    exists = conn.execute("SELECT username FROM app_users WHERE username = 'admin'").fetchone()
    if not exists:
        hashed = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        conn.execute("INSERT INTO app_users (username, password_hash, display_name) VALUES (?, ?, ?)",
                     ("admin", hashed, "Administrator"))

def seed_accounts_from_pdf(conn):
    """code.pdf میں دیے گئے تمام اکاؤنٹس کو ڈیٹا بیس میں ڈالیں"""
    accounts = [
        ("001","SADQAT",""),
        ("002","ZAKAT",""),
        ("003","GENERAL DONATION",""),
        ("004","CONSTRUCTION DONATION",""),
        ("005","FOOD EXPENSES",""),
        ("006","QARZ-E-HASSNA",""),
        ("007","ELECTICITY",""),
        ("008","PHONE & POSTAGE",""),
        ("009","SUI GAS",""),
        ("010","MISC. EXP.",""),
        ("011","MASJID DONATION",""),
        ("012","MISC. RENT EXP",""),
        ("013","ELECTRIC GOODS",""),
        ("014","REPAIR & MAINTINANCE",""),
        ("015","TRANSPORTATION",""),
        ("016","FURNITURE & FIXTURE",""),
        ("017","MEDICEN EXP.",""),
        ("018","PRINTING & STATIONARY",""),
        ("019","NEWS PAPERS",""),
        ("020","LANDRY",""),
        ("021","CLOTH & SHOES EXP.",""),
        ("022","CROCKY",""),
        ("023","AUDIT FEE",""),
        ("024","BOOKS",""),
        ("025","SALARIES",""),
        ("026","SENETARY EXP.",""),
        ("027","OTHER INCOME",""),
        ("028","HABIB BANK A/C NO. 17271-6",""),
        ("029","BANK CHARGES",""),
        ("030","SALES OF HIDE",""),
        ("031","CARPETS",""),
        ("032","OFFICE EQUIPMENTS",""),
        ("033","BUILDING",""),
        ("034","PRAYER MATS (SAFAIN)",""),
        ("035","CLEANLINESS ETC",""),
        ("036","WATER PUMP",""),
        ("037","RECEIVABLE A/C",""),
        ("038","ACCOUMULATED FUND",""),
        ("039","EXPENSES PAYABLE","BS"),
        ("040","WAGES ETC","PA"),
        ("041","COMPUTER","BS"),
        ("042","LAIBRARY BOOKS",""),
        ("043","SECURITY DEPOSIT","BS"),
        ("044","PRISES TO STUDENT",""),
        ("045","STEPENDS",""),
        ("046","SOLAR SYSTEM","BS"),
        ("047","TUFF TILES","BS"),
    ]
    for code, name, atype in accounts:
        conn.execute("INSERT OR IGNORE INTO accounts (code, name, atype) VALUES (?, ?, ?)", (code, name, atype.strip()))
    conn.commit()

# ----------------------- زبان کی معاونت -----------------------
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
        "upload_legacy": "📁 Upload Old Data",
        "upload_files": "📤 Upload Files",
        "save_income": "💾 Save Income",
        "save_expense": "💾 Save Expense",
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
        "report_type": "📑 Report Type",
        "from_date": "📅 From Date",
        "to_date": "📅 To Date",
        "view_report": "👁 View Report",
        "download_csv": "📥 Download CSV",
        "total_income": "💰 Total Income",
        "total_expense": "💸 Total Expense",
        "net_balance": "⚖ Net Balance",
        "opening_balance": "🔓 Opening Balance",
        "cash_in_hand": "💵 Cash In Hand",
        "monthly_flow": "📊 Monthly Flow",
        "top_accounts": "🏆 Top Accounts",
        "save_settings": "💾 Save Settings",
        "search": "🔍 Search",
        "refresh_ledger": "🔄 Refresh Ledger",
        "no_data": "ℹ No data found",
        "save_account_head": "💾 Save Account Head",
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
        "upload_legacy": "📁 پرانا ڈیٹا اپلوڈ",
        "upload_files": "📤 فائلیں اپلوڈ",
        "save_income": "💾 انکم محفوظ",
        "save_expense": "💾 پیمنٹ محفوظ",
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
        "report_type": "📑 رپورٹ کی قسم",
        "from_date": "📅 شروع تاریخ",
        "to_date": "📅 آخری تاریخ",
        "view_report": "👁 رپورٹ دیکھیں",
        "download_csv": "📥 CSV ڈاؤن لوڈ",
        "total_income": "💰 کل انکم",
        "total_expense": "💸 کل پیمنٹ",
        "net_balance": "⚖ خالص بیلنس",
        "opening_balance": "🔓 اوپننگ بیلنس",
        "cash_in_hand": "💵 کیش ان ہینڈ",
        "monthly_flow": "📊 ماہانہ بہاؤ",
        "top_accounts": "🏆 اہم اکاؤنٹس",
        "save_settings": "💾 سیٹنگز محفوظ",
        "search": "🔍 تلاش",
        "refresh_ledger": "🔄 لیجر ریفریش",
        "no_data": "ℹ کوئی ڈیٹا نہیں",
        "save_account_head": "💾 اکاؤنٹ ہیڈ محفوظ",
    },
}

def t(key):
    lang = st.session_state.get("lang", "en")
    return I18N.get(lang, I18N["en"]).get(key, key)

# ----------------------- خوبصورت CSS -----------------------
def local_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    html, body, [class*="css"] {{
        font-family: 'Poppins', sans-serif;
    }}
    .main-header {{
        background: linear-gradient(135deg, #0e695c 0%, #1db89a 100%);
        padding: 1.8rem 2rem;
        border-radius: 24px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 12px 30px rgba(14,105,92,0.25);
    }}
    .main-header h1 {{
        font-weight: 700;
        font-size: 2rem;
        margin: 0;
    }}
    .card {{
        background: white;
        border-radius: 20px;
        padding: 1.5rem;
        box-shadow: 0 6px 20px rgba(0,0,0,0.04);
        margin-bottom: 1rem;
        border: 1px solid #f0f2f6;
    }}
    .metric-card {{
        background: white;
        border-radius: 16px;
        padding: 1.2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.06);
        text-align: center;
        transition: transform 0.2s;
    }}
    .metric-card:hover {{
        transform: translateY(-3px);
    }}
    .metric-card.income {{ border-top: 5px solid #0e695c; }}
    .metric-card.expense {{ border-top: 5px solid #e87a20; }}
    .metric-card.balance {{ border-top: 5px solid #1e88e5; }}
    .stButton>button {{
        border-radius: 12px;
        font-weight: 600;
        background: linear-gradient(135deg, #0e695c, #0a5548);
        color: white;
        border: none;
        transition: all 0.3s;
    }}
    .stButton>button:hover {{
        background: linear-gradient(135deg, #1db89a, #0e695c);
        box-shadow: 0 8px 20px rgba(14,105,92,0.4);
        transform: translateY(-2px);
    }}
    .sidebar .stButton>button {{
        background: #f8fafd;
        color: #162033;
        border: 1px solid #e0e6ed;
    }}
    .sidebar .stButton>button:hover {{
        background: #eef3fa;
        color: #0e695c;
        border-color: #0e695c;
    }}
    [data-testid="stForm"] {{
        background: white;
        padding: 1.5rem;
        border-radius: 20px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.04);
    }}
    </style>
    """, unsafe_allow_html=True)

def colored_header(title, subtitle=""):
    st.markdown(f"""
    <div class="main-header">
        <h1>{title}</h1>
        <p style="font-size:1.1rem; opacity:0.9; margin-top:0.4rem;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

# ----------------------- ڈی بی ایف اپ لوڈنگ کے فنکشن (پہلے جیسے) -----------------------
# (scan_legacy_years, parse_dbf_date, iterate_dbf, وغیرہ)
def scan_legacy_years(legacy_dir: Path):
    if not legacy_dir.exists(): return []
    years = []
    for item in legacy_dir.iterdir():
        match = re.compile(r"^JIID(\d{4})\.DBF$", re.IGNORECASE).match(item.name)
        if match: years.append(match.group(1))
    return sorted(set(years))

def parse_dbf_date(value):
    clean = value.strip()
    if not clean or clean == "00000000": return None
    try: return datetime.strptime(clean, "%Y%m%d").date().isoformat()
    except ValueError: return None

def parse_dbf_number(value, decimals):
    clean = value.strip()
    if not clean: return None
    try: num = float(clean)
    except ValueError: return None
    if decimals == 0: return int(num)
    return round(num, decimals)

def parse_dbf_bool(value):
    return value.strip().upper() in {"Y", "T"}

def iterate_dbf(path_or_bytes, is_file=True):
    if is_file: handle = open(path_or_bytes, "rb")
    else: handle = BytesIO(path_or_bytes)
    try:
        header = handle.read(32)
        if len(header) < 32: return
        record_count = struct.unpack("<I", header[4:8])[0]
        header_length = struct.unpack("<H", header[8:10])[0]
        record_length = struct.unpack("<H", header[10:12])[0]
        fields = []
        while True:
            descriptor = handle.read(32)
            if not descriptor or descriptor[0] == 0x0D: break
            name = descriptor[:11].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
            field_type = chr(descriptor[11])
            length = descriptor[16]
            decimals = descriptor[17]
            fields.append((name, field_type, length, decimals))
        handle.seek(header_length)
        for row_index in range(1, record_count + 1):
            raw_record = handle.read(record_length)
            if not raw_record: break
            if raw_record[0:1] == b"*": continue
            position = 1
            row = {}
            for name, field_type, length, decimals in fields:
                chunk = raw_record[position:position+length]
                position += length
                text = chunk.decode("cp1252", errors="ignore")
                if field_type == "D": row[name] = parse_dbf_date(text)
                elif field_type == "N": row[name] = parse_dbf_number(text, decimals)
                elif field_type == "L": row[name] = parse_dbf_bool(text)
                else: row[name] = text.rstrip()
            yield row_index, row
    finally: handle.close()

def import_accounts_from_dbf(conn, legacy_dir):
    path = legacy_dir / "JIICODED.DBF"
    if not path.exists(): return 0
    deduped = {}
    for _, row in iterate_dbf(path):
        code = str(row.get("CODE") or "").strip()
        if not code: continue
        candidate = {"code": code.zfill(3), "name": str(row.get("NAME") or "").strip(), "atype": str(row.get("ATYPE") or "").strip()}
        deduped[candidate["code"]] = candidate
    for rec in deduped.values():
        conn.execute("""INSERT OR IGNORE INTO accounts (code, name, atype) VALUES (?, ?, ?)
                        ON CONFLICT(code) DO UPDATE SET name=excluded.name, atype=excluded.atype""",
                     (rec["code"], rec["name"], rec["atype"]))
    conn.commit()
    return len(deduped)

def import_entries_from_dbf(conn, legacy_dir, year):
    path = legacy_dir / f"JIID{year}.DBF"
    if not path.exists(): return 0
    conn.execute("DELETE FROM entries WHERE year = ? AND source_file <> 'MODERN'", (year,))
    count = 0
    source = path.name.upper()
    for row_index, row in iterate_dbf(path):
        code = str(row.get("CODE") or "").strip().zfill(3)
        conn.execute("INSERT OR IGNORE INTO accounts (code, name, atype) VALUES (?, '', '')", (code,))
        conn.execute("""INSERT INTO entries (year, entry_date, jv_no, jv_ext, branch, category, code, description,
                        receipt_no, voucher_no, entry_kind, income, payment, checked_flag, group_no, source_file, source_row)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                     (year, row.get("DATE"), row.get("JVNO"), row.get("JVEXT"), str(row.get("BRANCH") or "").strip(),
                      str(row.get("CATEGORY") or "").strip(), code, str(row.get("DESC1") or "").strip(),
                      row.get("R_NO"), row.get("V_NO"), str(row.get("CJ") or "").strip(),
                      float(row.get("INCOME") or 0), float(row.get("PAYMENT") or 0),
                      1 if row.get("CHECKED") else 0, row.get("GROUP"), source, row_index))
        count += 1
    conn.commit()
    return count

def import_year_dbf(conn, legacy_dir, year):
    import_control_settings_from_dbf(conn, legacy_dir, year)  # assuming similar function
    return import_entries_from_dbf(conn, legacy_dir, year)

def import_control_settings_from_dbf(conn, legacy_dir, year):
    path = legacy_dir / f"JIIC{year}.DBF"
    if not path.exists(): return
    chosen = None
    for _, row in iterate_dbf(path):
        if row.get("SDATE") or row.get("EDATE") or row.get("CIH") is not None:
            chosen = row; break
    if chosen:
        conn.execute("""INSERT OR IGNORE INTO control_settings (year, start_date, end_date, cash_in_hand, min_cash, max_cash, last_jvno)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(year) DO UPDATE SET start_date=excluded.start_date, end_date=excluded.end_date,
                        cash_in_hand=excluded.cash_in_hand, min_cash=excluded.min_cash, max_cash=excluded.max_cash,
                        last_jvno=excluded.last_jvno""",
                     (year, chosen.get("SDATE"), chosen.get("EDATE"), float(chosen.get("CIH") or 0),
                      float(chosen.get("MINCIN") or 0), float(chosen.get("MAXCIN") or 0), int(chosen.get("JVNO") or 0)))
        conn.commit()

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

def upsert_entry(conn, payload, entry_id=None):
    year = payload.pop("year")
    code = payload.pop("code").zfill(3)
    conn.execute("INSERT OR IGNORE INTO accounts (code) VALUES (?)", (code,))
    vals = (year, payload.get("entry_date"), payload.get("jv_no"), payload.get("jv_ext"),
            payload.get("branch","G"), payload.get("category","GENERAL"), code, payload.get("description"),
            payload.get("receipt_no"), payload.get("voucher_no"), payload.get("entry_kind","C"),
            payload.get("income",0), payload.get("payment",0), 1 if payload.get("checked_flag") else 0,
            payload.get("group_no"))
    if entry_id is None:
        cur = conn.execute("""INSERT INTO entries (year, entry_date, jv_no, jv_ext, branch, category, code, description,
                              receipt_no, voucher_no, entry_kind, income, payment, checked_flag, group_no, source_file)
                              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'MODERN')""", vals)
        conn.commit()
        return cur.lastrowid
    else:
        conn.execute("""UPDATE entries SET year=?, entry_date=?, jv_no=?, jv_ext=?, branch=?, category=?, code=?,
                        description=?, receipt_no=?, voucher_no=?, entry_kind=?, income=?, payment=?, checked_flag=?,
                        group_no=? WHERE id=?""", vals + (entry_id,))
        conn.commit()
        return entry_id

def upsert_account(conn, code, name, atype):
    conn.execute("INSERT OR IGNORE INTO accounts (code, name, atype) VALUES (?, ?, ?) ON CONFLICT(code) DO UPDATE SET name=excluded.name, atype=excluded.atype",
                 (code.zfill(3), name, atype.upper()))
    conn.commit()

# ----------------------- رپورٹ جنریشن -----------------------
def build_report(conn, rtype, year, dfrom, dto):
    if rtype == "ledger":
        rows = fetch_entries(conn, year, date_from=dfrom, date_to=dto, sort_ascending=True)
        df = pd.DataFrame([dict(r) for r in rows])[["entry_date","code","account_name","description","receipt_no","voucher_no","income","payment"]]
    elif rtype == "cashbook":
        rows = fetch_entries(conn, year, date_from=dfrom, date_to=dto, sort_ascending=True)
        bal = 0
        data = []
        for r in rows:
            bal += r["income"] - r["payment"]
            data.append([r["entry_date"], r["code"], r["account_name"], r["description"], r["income"], r["payment"], bal])
        df = pd.DataFrame(data, columns=["Date","Code","Account","Description","Receipt","Payment","Balance"])
    elif rtype == "trial-balance":
        rows = conn.execute("""SELECT e.code, COALESCE(a.name,'') as name, SUM(e.income) as income, SUM(e.payment) as payment
                              FROM entries e LEFT JOIN accounts a ON a.code=e.code WHERE e.year=? GROUP BY e.code""", (year,)).fetchall()
        data = [[r["code"], r["name"], r["income"], r["payment"], r["income"]-r["payment"]] for r in rows]
        df = pd.DataFrame(data, columns=["Code","Account","Income","Expense","Balance"])
    elif rtype == "opening-balance":
        cutoff = dfrom or (conn.execute("SELECT start_date FROM control_settings WHERE year=?", (year,)).fetchone() or {"start_date":""})["start_date"]
        rows = conn.execute("""SELECT e.code, COALESCE(a.name,'') as name, SUM(e.income) as income, SUM(e.payment) as payment
                              FROM entries e LEFT JOIN accounts a ON a.code=e.code
                              WHERE e.year=? AND COALESCE(e.entry_date,'') <= ? GROUP BY e.code""", (year, cutoff)).fetchall()
        data = [[r["code"], r["name"], r["income"], r["payment"], r["income"]-r["payment"]] for r in rows]
        df = pd.DataFrame(data, columns=["Code","Account","Income","Expense","Balance"])
    elif rtype == "income-expense":
        rows = conn.execute("""SELECT e.code, COALESCE(a.name,'') as name, SUM(e.income) as income, SUM(e.payment) as payment
                              FROM entries e LEFT JOIN accounts a ON a.code=e.code WHERE e.year=? GROUP BY e.code""", (year,)).fetchall()
        data = [[r["code"], r["name"], r["income"], r["payment"], r["income"]-r["payment"]] for r in rows]
        df = pd.DataFrame(data, columns=["Code","Account","Income","Expense","Net"])
    return df

# ----------------------- لاگ ان پیج -----------------------
def login_page():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h1 style='text-align:center; color:#0e695c;'>📚 " + t("login_title") + "</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#5e6e87;'>JAMIA MILLIA ISLAMIA AND MSJID MADRASA WALI</p>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input(t("username"), value="admin")
            password = st.text_input(t("password"), type="password", value="admin123")
            if st.form_submit_button(t("login_btn")):
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
    else:
        st.markdown('<body dir="ltr">', unsafe_allow_html=True)

    # سائڈبار
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center; padding:1rem;">
            <h2 style="color:#0e695c;">📚 مدرسہ اکاؤنٹس</h2>
            <p>👤 {st.session_state.get('display_name','')}</p>
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
            t("tab_income"): "income",
            t("tab_expense"): "expense",
            t("tab_reports"): "reports",
            t("tab_ledger"): "ledger",
            t("tab_accounts"): "accounts",
            t("tab_overview"): "overview",
            t("tab_settings"): "settings",
        }
        for label, vid in views.items():
            if st.button(label, use_container_width=True):
                st.session_state.view = vid

        st.markdown("---")
        st.subheader(t("upload_legacy"))
        uploaded = st.file_uploader("DBF فائلیں", accept_multiple_files=True, type=["dbf","acb","cdx","fpt"])
        if uploaded and st.button(t("upload_files")):
            save_dir = Path("uploaded_legacy") / datetime.now().strftime("%Y%m%d_%H%M%S")
            save_dir.mkdir(parents=True, exist_ok=True)
            for f in uploaded:
                with open(save_dir / f.name, "wb") as out:
                    out.write(f.getbuffer())
            conn = get_connection()
            import_accounts_from_dbf(conn, save_dir)
            for y in scan_legacy_years(save_dir):
                import_year_dbf(conn, save_dir, y)
            conn.close()
            st.success("✅ ڈیٹا امپورٹ ہو گیا")
            st.rerun()

        if st.button(t("logout")):
            st.session_state.authenticated = False
            st.rerun()

    # مواد
    if "view" not in st.session_state:
        st.session_state.view = "income"
    view = st.session_state.view
    conn = get_connection()
    year = st.session_state.year

    if view == "income":
        colored_header("💰 " + t("tab_income"), "روزانہ انکم انٹری")
        c1, c2 = st.columns(2)
        with c1:
            with st.form("inc_form"):
                date = st.date_input(t("date"))
                code = st.text_input(t("code"), max_chars=3, key="ic")
                # auto head
                head = ""
                if code:
                    acc = conn.execute("SELECT name, atype FROM accounts WHERE code=?", (code.zfill(3),)).fetchone()
                    head = f"{acc['name']} ({acc['atype']})" if acc and acc['atype'] else (acc['name'] if acc else "")
                st.text_input(t("account_head"), value=head, disabled=True)
                branch = st.text_input(t("branch"), value="G")
                category = st.text_input(t("category"), value="GENERAL")
                receipt = st.number_input(t("receipt_no"), value=0, step=1)
                jv = st.number_input(t("jv_no"), value=0, step=1)
                desc = st.text_area(t("description"))
                amount = st.number_input(t("amount"), min_value=0.0, format="%.2f")
                if st.form_submit_button(t("save_income")):
                    if not code or not date:
                        st.error("کوڈ اور تاریخ ضروری ہیں")
                    else:
                        payload = {"year": year, "entry_date": date.isoformat(), "code": code.zfill(3),
                                   "branch": branch, "category": category, "receipt_no": receipt, "jv_no": jv,
                                   "description": desc, "income": amount, "payment": 0, "entry_kind": "C"}
                        try:
                            upsert_entry(conn, payload)
                            st.success("✅ انکم محفوظ ہو گئی")
                        except Exception as e:
                            st.error(str(e))
        with c2:
            st.subheader("📋 حالیہ انکم")
            recent = fetch_entries(conn, year, mode="income", limit=10)
            if recent:
                df = pd.DataFrame([dict(r) for r in recent])[["entry_date","code","account_name","description","income"]]
                st.dataframe(df.style.format({"income":"{:.2f}"}), use_container_width=True)
            else:
                st.info(t("no_data"))

    elif view == "expense":
        colored_header("💸 " + t("tab_expense"), "روزانہ اخراجات")
        c1, c2 = st.columns(2)
        with c1:
            with st.form("exp_form"):
                date = st.date_input(t("date"))
                code = st.text_input(t("code"), max_chars=3, key="ec")
                head = ""
                if code:
                    acc = conn.execute("SELECT name, atype FROM accounts WHERE code=?", (code.zfill(3),)).fetchone()
                    head = f"{acc['name']} ({acc['atype']})" if acc and acc['atype'] else (acc['name'] if acc else "")
                st.text_input(t("account_head"), value=head, disabled=True)
                branch = st.text_input(t("branch"), value="G")
                category = st.text_input(t("category"), value="GENERAL")
                voucher = st.number_input(t("voucher_no"), value=0, step=1)
                jv = st.number_input(t("jv_no"), value=0, step=1)
                desc = st.text_area(t("description"))
                amount = st.number_input(t("amount"), min_value=0.0, format="%.2f")
                if st.form_submit_button(t("save_expense")):
                    if not code or not date:
                        st.error("کوڈ اور تاریخ ضروری ہیں")
                    else:
                        payload = {"year": year, "entry_date": date.isoformat(), "code": code.zfill(3),
                                   "branch": branch, "category": category, "voucher_no": voucher, "jv_no": jv,
                                   "description": desc, "income": 0, "payment": amount, "entry_kind": "C"}
                        try:
                            upsert_entry(conn, payload)
                            st.success("✅ اخراجات محفوظ ہو گئے")
                        except Exception as e:
                            st.error(str(e))
        with c2:
            st.subheader("📋 حالیہ اخراجات")
            recent = fetch_entries(conn, year, mode="expense", limit=10)
            if recent:
                df = pd.DataFrame([dict(r) for r in recent])[["entry_date","code","account_name","description","payment"]]
                st.dataframe(df.style.format({"payment":"{:.2f}"}), use_container_width=True)
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
                df = pd.DataFrame([dict(r) for r in entries])[["entry_date","code","account_name","description","income","payment","source_file","id"]]
                st.dataframe(df, use_container_width=True)
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
                if st.form_submit_button(t("save_account_head")):
                    if nc:
                        upsert_account(conn, nc, nn, nt)
                        st.success("اکاؤنٹ محفوظ ہو گیا")
                        st.rerun()

    elif view == "overview":
        colored_header("📈 " + t("tab_ledger"))
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
            cih = c1.number_input(t("cash_in_hand"), value=float(sets["cash_in_hand"]))
            minc = c2.number_input("کم از کم کیش", value=float(sets["min_cash"]))
            maxc = c1.number_input("زیادہ سے زیادہ کیش", value=float(sets["max_cash"]))
            jvno = c2.number_input("آخری جے وی نمبر", value=int(sets["last_jvno"]))
            if st.form_submit_button(t("save_settings")):
                conn.execute("""INSERT OR IGNORE INTO control_settings (year, start_date, end_date, cash_in_hand, min_cash, max_cash, last_jvno)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT(year) DO UPDATE SET start_date=excluded.start_date, end_date=excluded.end_date,
                                cash_in_hand=excluded.cash_in_hand, min_cash=excluded.min_cash, max_cash=excluded.max_cash,
                                last_jvno=excluded.last_jvno""",
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
