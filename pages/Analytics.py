import os
import sqlite3
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Analytics & Reports | MediCare", page_icon="📈", layout="wide")

# ----------------- LOGIN GUARD & SESSION CHECK -----------------
if not st.session_state.get("logged_in", False):
    st.switch_page("app.py")

# ----------------- DATABASE SETUP (hospital.db) -----------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_FILE = os.path.join(PROJECT_ROOT, "hospital.db")


def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_analytics_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS analytics_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monthly_revenue REAL NOT NULL DEFAULT 4580000.0,
            bed_occupancy_pct REAL NOT NULL DEFAULT 78.5,
            avg_recovery_days REAL NOT NULL DEFAULT 4.2,
            satisfaction_pct REAL NOT NULL DEFAULT 94.2,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS department_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_label TEXT NOT NULL,
            cardiology INTEGER NOT NULL DEFAULT 0,
            pediatrics INTEGER NOT NULL DEFAULT 0,
            orthopedics INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    if cur.execute("SELECT COUNT(*) FROM analytics_summary").fetchone()[0] == 0:
        cur.execute(
            """
            INSERT INTO analytics_summary (
                monthly_revenue, bed_occupancy_pct, avg_recovery_days, satisfaction_pct
            )
            VALUES (4580000.0, 78.5, 4.2, 94.2)
            """
        )

    if cur.execute("SELECT COUNT(*) FROM department_trends").fetchone()[0] == 0:
        seed_trends = [
            ("Jan", 40, 55, 75),
            ("Feb", 65, 30, 48),
            ("Mar", 45, 50, 52),
            ("Apr", 80, 42, 20),
            ("May", 50, 48, 60),
            ("Jun", 75, 46, 60),
        ]
        cur.executemany(
            """
            INSERT INTO department_trends (
                period_label, cardiology, pediatrics, orthopedics
            )
            VALUES (?, ?, ?, ?)
            """,
            seed_trends,
        )

    conn.commit()
    conn.close()


def get_live_metrics():
    conn = get_connection()
    cur = conn.cursor()

    summary = cur.execute(
        """
        SELECT monthly_revenue, bed_occupancy_pct, avg_recovery_days, satisfaction_pct
        FROM analytics_summary
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    revenue = float(summary["monthly_revenue"]) if summary else 4580000.0
    recovery = float(summary["avg_recovery_days"]) if summary else 4.2
    satisfaction = float(summary["satisfaction_pct"]) if summary else 94.2
    occupancy = float(summary["bed_occupancy_pct"]) if summary else 78.5

    # जर beds टेबल अस्तित्वात असेल तर प्रत्यक्ष बेड ऑक्युपन्सी मोजणे
    beds_table = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='beds'"
    ).fetchone()
    if beds_table:
        bed_cols = [r[1] for r in cur.execute("PRAGMA table_info(beds)").fetchall()]
        if "status" in bed_cols:
            total_b = cur.execute("SELECT COUNT(*) FROM beds").fetchone()[0]
            occ_b = cur.execute("SELECT COUNT(*) FROM beds WHERE status = 'Occupied'").fetchone()[0]
            if total_b > 0:
                occupancy = round((occ_b / total_b) * 100.0, 1)

    # जर bills टेबल अस्तित्वात असेल तर Paid बिले revenue मध्ये जोडणे
    bills_table = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='bills'"
    ).fetchone()
    if bills_table:
        bill_cols = [r[1] for r in cur.execute("PRAGMA table_info(bills)").fetchall()]
        if "total_amount" in bill_cols and "status" in bill_cols:
            paid_sum = cur.execute(
                "SELECT COALESCE(SUM(total_amount), 0) FROM bills WHERE status = 'Paid'"
            ).fetchone()[0]
            revenue = revenue + float(paid_sum or 0)

    conn.close()
    return revenue, occupancy, recovery, satisfaction


def update_summary_metrics(revenue: float, occupancy: float, recovery: float, satisfaction: float):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO analytics_summary (
            monthly_revenue, bed_occupancy_pct, avg_recovery_days, satisfaction_pct
        )
        VALUES (?, ?, ?, ?)
        """,
        (float(revenue), float(occupancy), float(recovery), float(satisfaction)),
    )
    conn.commit()
    conn.close()


def add_department_trend(period_label: str, cardiology: int, pediatrics: int, orthopedics: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO department_trends (
            period_label, cardiology, pediatrics, orthopedics
        )
        VALUES (?, ?, ?, ?)
        """,
        (period_label.strip(), int(cardiology), int(pediatrics), int(orthopedics)),
    )
    conn.commit()
    conn.close()


def fetch_trends_df():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            id AS "ID",
            period_label AS "Month",
            cardiology AS "Cardiology",
            pediatrics AS "Pediatrics",
            orthopedics AS "Orthopedics"
        FROM department_trends
        ORDER BY id ASC
        """,
        conn,
    )
    conn.close()
    return df


init_analytics_db()

# ----------------- THEME & STYLING -----------------
st.markdown(
    """
    <style>
        .stApp { background: #f0fdf4 !important; }
        header { visibility: hidden; }

        [data-testid="stSidebar"] {
            background-color: #064e3b !important;
            display: block !important;
        }
        [data-testid="stSidebar"] * { color: #ecfdf5 !important; }

        .kpi-card {
            background: #ffffff;
            border-radius: 16px;
            padding: 20px;
            border: 1px solid #d1fae5;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
        }
        .kpi-title { font-size: 13px; color: #047857; font-weight: 700; text-transform: uppercase; }
        .kpi-val { font-size: 26px; font-weight: 800; color: #064e3b; margin: 6px 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------- SIDEBAR NAVIGATION -----------------
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

# ----------------- HEADER -----------------
st.title("📈 Analytics & Hospital Performance")
st.caption("Insights, Revenue Trends, Departmental Load & Patient Statistics")

if st.session_state.get("analytics_msg"):
    st.success(st.session_state.pop("analytics_msg"))

st.divider()

# ----------------- LIVE ANALYTICS METRICS -----------------
revenue_val, occupancy_val, recovery_val, satisfaction_val = get_live_metrics()
revenue_lakhs = revenue_val / 100000.0

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Monthly Revenue</div><div class="kpi-val">💰 ₹{revenue_lakhs:.1f}L</div></div>',
        unsafe_allow_html=True,
    )
with m2:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Bed Occupancy Rate</div><div class="kpi-val">🛏️ {occupancy_val:.1f}%</div></div>',
        unsafe_allow_html=True,
    )
with m3:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Avg Recovery Time</div><div class="kpi-val">⏱️ {recovery_val:.1f} Days</div></div>',
        unsafe_allow_html=True,
    )
with m4:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Patient Satisfaction</div><div class="kpi-val">⭐ {satisfaction_val:.1f}%</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ----------------- MULTI-LINE TRENDS GRAPH -----------------
st.subheader("📊 Monthly Patient Admission Trends & Department Performance")
trends_df = fetch_trends_df()

if not trends_df.empty:
    chart_input = trends_df[["Month", "Cardiology", "Pediatrics", "Orthopedics"]].set_index("Month")
    st.line_chart(chart_input)
    st.dataframe(trends_df, use_container_width=True, hide_index=True)
else:
    st.info("No department trend data available yet.")

st.write("")

# ----------------- REAL-TIME ADD / UPDATE FORMS -----------------
f_col1, f_col2 = st.columns(2)

with f_col1:
    st.subheader("➕ Add Department Trend Data")
    with st.form("add_trend_form", clear_on_submit=True):
        period_lbl = st.text_input("Month / Period Label", placeholder="e.g. Jul or Week 1")
        card_val = st.number_input("Cardiology Admissions", min_value=0, max_value=10000, value=60)
        ped_val = st.number_input("Pediatrics Admissions", min_value=0, max_value=10000, value=45)
        ortho_val = st.number_input("Orthopedics Admissions", min_value=0, max_value=10000, value=55)

        btn_add_trend = st.form_submit_button("Add Trend Record", type="primary", use_container_width=True)
        if btn_add_trend:
            if period_lbl.strip():
                add_department_trend(period_lbl, card_val, ped_val, ortho_val)
                st.session_state["analytics_msg"] = f"Added trend record for '{period_lbl.strip()}'."
                st.rerun()
            else:
                st.warning("Please enter a Month / Period label.")

with f_col2:
    st.subheader("🔄 Update Performance Metrics")
    with st.form("update_metrics_form"):
        rev_input = st.number_input("Base Monthly Revenue (₹)", min_value=0.0, value=float(revenue_val), step=50000.0)
        occ_input = st.number_input("Bed Occupancy (%)", min_value=0.0, max_value=100.0, value=float(occupancy_val), step=0.5)
        rec_input = st.number_input("Avg Recovery Time (Days)", min_value=0.1, max_value=365.0, value=float(recovery_val), step=0.1)
        sat_input = st.number_input("Patient Satisfaction (%)", min_value=0.0, max_value=100.0, value=float(satisfaction_val), step=0.5)

        btn_upd_metrics = st.form_submit_button("Save Metrics", use_container_width=True)
        if btn_upd_metrics:
            update_summary_metrics(rev_input, occ_input, rec_input, sat_input)
            st.session_state["analytics_msg"] = "Analytics metrics updated in hospital.db!"
            st.rerun()