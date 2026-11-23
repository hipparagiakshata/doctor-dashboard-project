import json
import os
import sqlite3
from datetime import datetime
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="MediCare | Executive Portal",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------- DATABASE SETUP (hospital.db) -----------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(PROJECT_ROOT, "hospital.db")


def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(cur, table_name: str) -> bool:
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def get_columns(cur, table_name: str) -> list:
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table_name})").fetchall()]


def get_live_overview_data():
    conn = get_connection()
    cur = conn.cursor()

    metrics = {
        "active_doctors": 0,
        "total_doctors": 0,
        "total_patients": 0,
        "occupied_beds": 0,
        "total_beds": 0,
        "available_beds": 0,
        "available_ambulances": 0,
        "total_ambulances": 0,
    }

    if table_exists(cur, "doctors"):
        cols = get_columns(cur, "doctors")
        metrics["total_doctors"] = cur.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
        if "status" in cols:
            metrics["active_doctors"] = cur.execute(
                "SELECT COUNT(*) FROM doctors WHERE status IN ('Available', 'In Surgery')"
            ).fetchone()[0]
        else:
            metrics["active_doctors"] = metrics["total_doctors"]

    if table_exists(cur, "patients"):
        metrics["total_patients"] = cur.execute("SELECT COUNT(*) FROM patients").fetchone()[0]

    if table_exists(cur, "beds"):
        cols = get_columns(cur, "beds")
        metrics["total_beds"] = cur.execute("SELECT COUNT(*) FROM beds").fetchone()[0]
        if "status" in cols:
            metrics["occupied_beds"] = cur.execute(
                "SELECT COUNT(*) FROM beds WHERE status = 'Occupied'"
            ).fetchone()[0]
            metrics["available_beds"] = cur.execute(
                "SELECT COUNT(*) FROM beds WHERE status = 'Available'"
            ).fetchone()[0]

    if table_exists(cur, "ambulances"):
        cols = get_columns(cur, "ambulances")
        metrics["total_ambulances"] = cur.execute("SELECT COUNT(*) FROM ambulances").fetchone()[0]
        if "status" in cols:
            metrics["available_ambulances"] = cur.execute(
                "SELECT COUNT(*) FROM ambulances WHERE status = 'Available'"
            ).fetchone()[0]

    # Recent Activity Log
    activities = []

    if table_exists(cur, "patients"):
        cols = get_columns(cur, "patients")
        code_col = "patient_code" if "patient_code" in cols else "id"
        rows = cur.execute(
            f"SELECT {code_col} AS pcode, name, created_at FROM patients ORDER BY id DESC LIMIT 2"
        ).fetchall()
        for r in rows:
            activities.append(
                (f"📝 Patient Record: {r['name']} ({r['pcode']})", str(r["created_at"] or "Recent"))
            )

    if table_exists(cur, "ambulance_dispatches"):
        rows = cur.execute(
            "SELECT patient_name, vehicle_no, dispatched_at FROM ambulance_dispatches ORDER BY id DESC LIMIT 2"
        ).fetchall()
        for r in rows:
            activities.append(
                (f"🚑 Ambulance {r['vehicle_no']} → {r['patient_name']}", str(r["dispatched_at"] or "Recent"))
            )

    if table_exists(cur, "bills"):
        cols = get_columns(cur, "bills")
        amt_col = "total_amount" if "total_amount" in cols else ("amount" if "amount" in cols else "0")
        rows = cur.execute(
            f"SELECT bill_id, patient_name, {amt_col} AS amt, created_at FROM bills ORDER BY id DESC LIMIT 2"
        ).fetchall()
        for r in rows:
            activities.append(
                (f"💳 Bill {r['bill_id']} ({r['patient_name']}) - ₹{float(r['amt'] or 0):,.0f}", str(r["created_at"] or "Recent"))
            )

    # Today's Priority Schedule
    schedules = []
    sched_table = "schedules" if table_exists(cur, "schedules") else ("appointments" if table_exists(cur, "appointments") else None)
    if sched_table:
        s_cols = get_columns(cur, sched_table)
        time_col = "appointment_time" if "appointment_time" in s_cols else ("time_slot" if "time_slot" in s_cols else "''")
        doc_col = "doctor_name" if "doctor_name" in s_cols else ("doctor" if "doctor" in s_cols else "''")
        dept_col = "department" if "department" in s_cols else "''"
        pat_col = "patient_name" if "patient_name" in s_cols else "''"
        st_col = "status" if "status" in s_cols else "'Confirmed'"

        rows = cur.execute(
            f"""
            SELECT {time_col} AS slot, {doc_col} AS doc, {dept_col} AS dept, {pat_col} AS pat, {st_col} AS st
            FROM {sched_table}
            ORDER BY id DESC
            LIMIT 5
            """
        ).fetchall()
        for r in rows:
            schedules.append(
                (
                    f"⏰ {r['slot']} - {r['doc']} ({r['dept']}) · {r['pat']}",
                    str(r["st"] or "Confirmed"),
                )
            )

    conn.close()
    return metrics, activities[:4], schedules


# ----------------- PERMANENT JSON USER DATABASE -----------------
USER_FILE = os.path.join(PROJECT_ROOT, "users_db.json")


def load_users():
    if not os.path.exists(USER_FILE):
        default_users = {"admin": "admin123"}
        with open(USER_FILE, "w") as f:
            json.dump(default_users, f, indent=4)
        return default_users

    try:
        with open(USER_FILE, "r") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {"admin": "admin123"}
    except (json.JSONDecodeError, Exception):
        return {"admin": "admin123"}


def save_user(username, password):
    users = load_users()
    users[username] = password
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=4)


# ----------------- URL QUERY PARAMETERS AUTH CHECK -----------------
query_params = st.query_params
logged_in_user = query_params.get("user", None)

if "logged_in" not in st.session_state:
    if logged_in_user:
        st.session_state.logged_in = True
        st.session_state.current_user = logged_in_user
    else:
        st.session_state.logged_in = False
        st.session_state.current_user = "Admin"

# ----------------- EMERALD & TEAL CLEAN THEME (CSS) -----------------
st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(135deg, #f0fdf4 0%, #e2fbe8 100%) !important;
        }

        header { visibility: hidden; }

        [data-testid="stSidebar"] {
            background-color: #064e3b !important;
            display: var(--sidebar-display, block);
        }
        [data-testid="stSidebar"] * { color: #ecfdf5 !important; }

        .stTextInput > div > div > input {
            border-radius: 10px !important;
            border: 1px solid #a7f3d0 !important;
            padding: 10px 14px !important;
            background-color: #f8fafc !important;
            color: #064e3b !important;
        }

        .stTextInput > div > div > input:focus {
            border-color: #059669 !important;
            box-shadow: 0 0 0 2px rgba(5, 150, 105, 0.15) !important;
        }

        .stButton > button {
            width: 100% !important;
            background-color: #059669 !important;
            color: white !important;
            border-radius: 10px !important;
            height: 42px !important;
            font-weight: 600 !important;
            border: none !important;
            box-shadow: 0 4px 12px rgba(5, 150, 105, 0.2);
            transition: all 0.3s ease;
        }

        .stButton > button:hover {
            background-color: #047857 !important;
            color: white !important;
        }

        /* Top Right Logout Button (Only on Overview) */
        div[data-testid="stColumn"]:has(button[key="top_logout_btn"]) button {
            background-color: #dc2626 !important;
            color: #ffffff !important;
            width: auto !important;
        }

        .kpi-card {
            background: #ffffff;
            border-radius: 16px;
            padding: 20px;
            border: 1px solid #d1fae5;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
        }
        .kpi-title { font-size: 13px; color: #047857; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
        .kpi-val { font-size: 26px; font-weight: 800; color: #064e3b; margin: 6px 0; }
        .kpi-sub { font-size: 12px; color: #64748b; }
        .badge-green { background-color: #d1fae5; color: #047857; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; }
        .badge-orange { background-color: #ffedd5; color: #c2410c; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; }
        .content-box { background: #ffffff; border-radius: 16px; padding: 22px; border: 1px solid #d1fae5; margin-top: 10px; }
        .act-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #f0fdf4; font-size: 13px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# LOGIN SECTION
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<style>:root { --sidebar-display: none; }</style>", unsafe_allow_html=True)

    _, center_col, _ = st.columns([1, 1.2, 1])

    with center_col:
        st.write("")
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 20px;">
                <span style="font-size: 45px;">🩺</span>
                <h2 style="color: #064e3b; font-weight: 800; margin: 5px 0 0 0;">MediCare Portal</h2>
                <p style="color: #047857; font-size: 13px; margin: 0;">Advanced Medical & Hospital Operations</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_reg = st.tabs(["🔑 Sign In", "📝 Register"])

        with tab_login:
            st.write("")
            with st.form("login_form"):
                u_name = st.text_input("Username", placeholder="Enter username").strip()
                u_pass = st.text_input("Password", type="password", placeholder="Enter password").strip()
                st.write("")
                btn_login = st.form_submit_button("Sign In")

                if btn_login:
                    users_db = load_users()
                    if u_name in users_db and users_db[u_name] == u_pass:
                        st.session_state.logged_in = True
                        st.session_state.current_user = u_name
                        st.query_params["user"] = u_name
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password!")

        with tab_reg:
            st.write("")
            with st.form("register_form"):
                new_user = st.text_input("Choose Username").strip()
                new_pass = st.text_input("Choose Password", type="password").strip()
                confirm_pass = st.text_input("Confirm Password", type="password").strip()
                st.write("")
                btn_reg = st.form_submit_button("Create Account")

                if btn_reg:
                    users_db = load_users()
                    if not new_user or not new_pass:
                        st.warning("All fields are required!")
                    elif new_user in users_db:
                        st.error("Username already exists!")
                    elif new_pass != confirm_pass:
                        st.error("Passwords do not match!")
                    else:
                        save_user(new_user, new_pass)
                        st.success("Account created successfully! Go to 'Sign In'.")

# ==========================================
# DASHBOARD (OVERVIEW)
# ==========================================
else:
    st.markdown("<style>:root { --sidebar-display: block; }</style>", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### 🩺 MediCare")
        st.caption(f"Active Session: **{st.session_state.get('current_user', 'Admin')}**")
        st.write("")
        st.caption("NAVIGATION MENU")

        st.page_link("app.py", label="Overview", icon="📊")
        st.page_link("pages/Analytics.py", label="Analytics", icon="📈")
        st.page_link("pages/doctors.py", label="Doctor Directory", icon="👨‍⚕️")
        st.page_link("pages/patient.py", label="Patient Records", icon="👨‍👩‍👧‍👦")
        st.page_link("pages/beds.py", label="Bed Allocation", icon="🛏️")
        st.page_link("pages/pharma.py", label="Pharmacy Inventory", icon="💊")
        st.page_link("pages/products.py", label="Assign Product", icon="📋")
        st.page_link("pages/ambulances.py", label="Ambulance Fleet", icon="🚑")
        st.page_link("pages/appointments.py", label="Schedule & Appointments", icon="📅")
        st.page_link("pages/bills.py", label="Billing System", icon="💳")

    current_hour = datetime.now().hour
    greeting_text = "Good Morning" if current_hour < 12 else ("Good Afternoon" if current_hour < 17 else "Good Evening")
    today_str = datetime.now().strftime("%d %b %Y, %A")

    h_col1, h_col2, h_col3 = st.columns([3, 1.2, 0.8])
    with h_col1:
        st.markdown(f"## {greeting_text}, {st.session_state.get('current_user', 'Admin')} 👋")
        st.caption("Welcome to MediCare Executive Overview.")
    with h_col2:
        st.markdown(
            f"<p style='text-align: right; color: #047857; font-size: 13px; font-weight: 600; margin-top: 15px;'>{today_str}</p>",
            unsafe_allow_html=True,
        )
    with h_col3:
        st.write("")
        if st.button("🚪 Logout", key="top_logout_btn", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.query_params.clear()
            st.rerun()

    st.write("")

    metrics, activities, schedules = get_live_overview_data()

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-title">Active Doctors</div><div class="kpi-val">🧑‍⚕️ {metrics["active_doctors"]}</div><div class="kpi-sub">Out of {metrics["total_doctors"]} registered</div></div>',
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-title">Total Patients</div><div class="kpi-val">👤 {metrics["total_patients"]}</div><div class="kpi-sub">In hospital.db</div></div>',
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-title">Bed Occupancy</div><div class="kpi-val">🛏️ {metrics["occupied_beds"]} / {metrics["total_beds"]}</div><div class="kpi-sub">{metrics["available_beds"]} Beds Free</div></div>',
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-title">Emergency Fleet</div><div class="kpi-val">🚑 {metrics["available_ambulances"]} / {metrics["total_ambulances"]}</div><div class="kpi-sub">Ambulances Available</div></div>',
            unsafe_allow_html=True,
        )

    st.write("")

    col_left, col_right = st.columns(2)
    with col_left:
        if activities:
            act_html = "".join(
                f'<div class="act-item"><span>{label}</span><span style="color:#047857;">{ts}</span></div>'
                for label, ts in activities
            )
        else:
            act_html = '<div class="act-item"><span>No recent database activity yet.</span><span style="color:#047857;">—</span></div>'

        st.markdown(
            f"""
            <div class="content-box">
                <b style="font-size: 16px; color: #064e3b;">Recent Activity Log</b>
                <hr style="margin: 10px 0; border-top: 1px solid #d1fae5;">
                {act_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_right:
        if schedules:
            sched_html = ""
            for item_text, st_val in schedules:
                badge_cls = "badge-green" if str(st_val).lower() == "confirmed" else "badge-orange"
                sched_html += f'<div class="act-item"><span>{item_text}</span><span class="{badge_cls}">{st_val}</span></div>'
        else:
            sched_html = '<div class="act-item"><span>No scheduled appointments yet.</span><span class="badge-orange">Empty</span></div>'

        st.markdown(
            f"""
            <div class="content-box">
                <b style="font-size: 16px; color: #064e3b;">Today's Priority Schedule</b>
                <hr style="margin: 10px 0; border-top: 1px solid #d1fae5;">
                {sched_html}
            </div>
            """,
            unsafe_allow_html=True,
        )