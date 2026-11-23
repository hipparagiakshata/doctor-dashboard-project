import os
import sqlite3
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Assign Product | MediCare", page_icon="📋", layout="wide")

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


def init_products_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS assigned_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_name TEXT NOT NULL,
            item_name TEXT NOT NULL,
            department TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'Assigned',
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    existing_count = cur.execute("SELECT COUNT(*) FROM assigned_products").fetchone()[0]
    if existing_count == 0:
        initial_items = [
            ("PAT-892 (Rahul S.)", "Oxygen Concentrator", "ICU Ward", 1, "Assigned"),
            ("ICU Room #04", "ECG Monitor", "ICU Ward", 2, "Active"),
            ("General Ward B", "IV Infusion Pump", "General Ward B", 1, "Active"),
            ("PAT-712 (Anita P.)", "Wheelchair", "General Ward A", 1, "Assigned"),
        ]
        cur.executemany(
            """
            INSERT INTO assigned_products (target_name, item_name, department, quantity, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            initial_items,
        )

    conn.commit()
    conn.close()


def fetch_assigned_df():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            id AS "ID",
            target_name AS "Patient/Ward",
            item_name AS "Item",
            department AS "Department",
            quantity AS "Qty",
            status AS "Status",
            assigned_at AS "Assigned At"
        FROM assigned_products
        ORDER BY id DESC
        """,
        conn,
    )
    conn.close()
    return df


def assign_product_to_db(target_name: str, item_name: str, department: str, quantity: int):
    conn = get_connection()
    cur = conn.cursor()

    clean_target = target_name.strip() if target_name.strip() else department
    cur.execute(
        """
        INSERT INTO assigned_products (target_name, item_name, department, quantity, status)
        VALUES (?, ?, ?, ?, 'Assigned')
        """,
        (clean_target, item_name, department, int(quantity)),
    )

    conn.commit()
    conn.close()


init_products_db()

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
st.title("📋 Assign Product & Equipment")
st.caption("Allocate Medical Equipment, Assets, & Surgical Products to Wards / Patients")

if st.session_state.pop("product_assigned_msg", None):
    st.success(st.session_state.pop("product_assigned_detail", "Product assigned and saved to hospital.db!"))

st.divider()

# ----------------- LIVE METRICS -----------------
assigned_df = fetch_assigned_df()
total_assignments = len(assigned_df)
total_units = int(assigned_df["Qty"].sum()) if not assigned_df.empty else 0
icu_units = (
    int(assigned_df[assigned_df["Department"] == "ICU Ward"]["Qty"].sum())
    if not assigned_df.empty
    else 0
)

m1, m2, m3 = st.columns(3)
with m1:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Total Allocations</div><div class="kpi-val">📋 {total_assignments}</div></div>',
        unsafe_allow_html=True,
    )
with m2:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Total Equipment Units</div><div class="kpi-val">🩺 {total_units}</div></div>',
        unsafe_allow_html=True,
    )
with m3:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">ICU Ward Units</div><div class="kpi-val">🚨 {icu_units}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ----------------- ASSIGN PRODUCT FORM & TABLE -----------------
col_form, col_assigned = st.columns([1, 1.2])

with col_form:
    st.subheader("➕ Assign Product / Equipment")
    with st.form("assign_product_form", clear_on_submit=True):
        p_name = st.text_input("Patient ID / Name", placeholder="e.g. PAT-892 or Rahul Sharma")
        equipment = st.selectbox(
            "Select Equipment / Product",
            [
                "Oxygen Concentrator 10L",
                "Patient Monitor (ECG/SpO2)",
                "Wheelchair (Standard)",
                "IV Infusion Pump",
                "Nebulizer Machine",
            ],
        )
        dept = st.selectbox(
            "Department / Ward",
            ["ICU Ward", "General Ward A", "General Ward B", "Emergency ER"],
        )
        quantity = st.number_input("Quantity", min_value=1, max_value=100, value=1)

        btn_assign = st.form_submit_button("Assign Product", type="primary", use_container_width=True)
        if btn_assign:
            target_display = p_name.strip() or dept
            assign_product_to_db(p_name, equipment, dept, quantity)
            st.session_state["product_assigned_msg"] = True
            st.session_state["product_assigned_detail"] = (
                f"Assigned {quantity} x {equipment} to {target_display} ({dept})."
            )
            st.toast("Saved to hospital.db!", icon="✅")
            st.rerun()

with col_assigned:
    st.subheader("📌 Recently Assigned Inventory")
    st.dataframe(assigned_df, use_container_width=True, hide_index=True)