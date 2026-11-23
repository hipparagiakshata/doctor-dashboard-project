import os
import sqlite3
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Pharmacy Inventory | MediCare", page_icon="💊", layout="wide")

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


def compute_status(stock_count: int, expiry_status: str) -> str:
    if expiry_status == "Expired":
        return "Expired"
    if stock_count <= 0:
        return "Out of Stock"
    if stock_count < 100:
        return "Low Stock"
    return "In Stock"


def init_pharma_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pharmacy_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            stock_count INTEGER NOT NULL DEFAULT 0,
            unit_price REAL NOT NULL DEFAULT 0.0,
            status TEXT NOT NULL DEFAULT 'In Stock',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    existing_count = cur.execute("SELECT COUNT(*) FROM pharmacy_inventory").fetchone()[0]
    if existing_count == 0:
        initial_medicines = [
            ("Paracetamol 650mg", "Analgesic", 450, 15.0, "In Stock"),
            ("Amoxicillin 500mg", "Antibiotic", 85, 45.0, "Low Stock"),
            ("Ibuprofen 400mg", "Anti-inflammatory", 230, 25.0, "In Stock"),
            ("Cetirizine 10mg", "Antihistamine", 600, 10.0, "In Stock"),
            ("Azithromycin 500mg", "Antibiotic", 42, 120.0, "Low Stock"),
        ]
        cur.executemany(
            """
            INSERT INTO pharmacy_inventory (medicine_name, category, stock_count, unit_price, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            initial_medicines,
        )

    conn.commit()
    conn.close()


def fetch_pharma_df():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            id AS "ID",
            medicine_name AS "Medicine Name",
            category AS "Category",
            stock_count AS "Stock Count",
            unit_price AS "Unit Price (₹)",
            status AS "Status",
            updated_at AS "Updated At"
        FROM pharmacy_inventory
        ORDER BY id ASC
        """,
        conn,
    )
    conn.close()
    return df


def add_or_update_medicine(
    medicine_name: str,
    category: str,
    stock_count: int,
    unit_price: float,
    mark_expired: bool = False,
):
    conn = get_connection()
    cur = conn.cursor()

    clean_name = medicine_name.strip()
    status = compute_status(int(stock_count), "Expired" if mark_expired else "Valid")

    existing = cur.execute(
        "SELECT id FROM pharmacy_inventory WHERE LOWER(medicine_name) = LOWER(?)",
        (clean_name,),
    ).fetchone()

    if existing:
        cur.execute(
            """
            UPDATE pharmacy_inventory
            SET category = ?,
                stock_count = ?,
                unit_price = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (category, int(stock_count), float(unit_price), status, existing["id"]),
        )
    else:
        cur.execute(
            """
            INSERT INTO pharmacy_inventory (medicine_name, category, stock_count, unit_price, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (clean_name, category, int(stock_count), float(unit_price), status),
        )

    conn.commit()
    conn.close()


def adjust_medicine_stock(medicine_name: str, delta_qty: int):
    conn = get_connection()
    cur = conn.cursor()

    row = cur.execute(
        "SELECT id, stock_count, status FROM pharmacy_inventory WHERE medicine_name = ?",
        (medicine_name,),
    ).fetchone()

    if row:
        new_stock = max(0, int(row["stock_count"]) + int(delta_qty))
        new_status = compute_status(new_stock, row["status"])
        cur.execute(
            """
            UPDATE pharmacy_inventory
            SET stock_count = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_stock, new_status, row["id"]),
        )

    conn.commit()
    conn.close()


init_pharma_db()

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
st.title("💊 Pharmacy Inventory")
st.caption("Medicine Stock, Prescriptions & Pharma Supply Logistics")

if st.session_state.get("pharma_msg"):
    st.success(st.session_state.pop("pharma_msg"))

st.divider()

# ----------------- LIVE PHARMA METRICS -----------------
pharma_data = fetch_pharma_df()
total_stock_units = int(pharma_data["Stock Count"].sum()) if not pharma_data.empty else 0
low_stock_count = (
    int((pharma_data["Status"] == "Low Stock").sum()) if not pharma_data.empty else 0
)
expired_count = (
    int((pharma_data["Status"] == "Expired").sum()) if not pharma_data.empty else 0
)
total_medicines_types = len(pharma_data)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Total Stock Units</div><div class="kpi-val">💊 {total_stock_units:,}</div></div>',
        unsafe_allow_html=True,
    )
with m2:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Low Stock Items</div><div class="kpi-val">⚠️ {low_stock_count:02d}</div></div>',
        unsafe_allow_html=True,
    )
with m3:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Expired Medicine</div><div class="kpi-val">🚨 {expired_count:02d}</div></div>',
        unsafe_allow_html=True,
    )
with m4:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Medicine Varieties</div><div class="kpi-val">🧾 {total_medicines_types:02d}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ----------------- ADD / UPDATE STOCK & TABLE -----------------
col_form, col_table = st.columns([1, 1.3])

with col_form:
    st.subheader("➕ Add / Update Medicine")
    with st.form("add_medicine_form", clear_on_submit=True):
        med_name = st.text_input("Medicine Name", placeholder="e.g. Pantoprazole 40mg")
        category = st.selectbox(
            "Category",
            [
                "Analgesic",
                "Antibiotic",
                "Anti-inflammatory",
                "Antihistamine",
                "Antacid",
                "Cardiac",
                "Other",
            ],
        )
        stock_qty = st.number_input("Stock Count", min_value=0, max_value=100000, value=100, step=10)
        unit_price = st.number_input("Unit Price (₹)", min_value=0.0, value=20.0, step=5.0)
        mark_expired = st.checkbox("Mark as Expired")

        btn_save_med = st.form_submit_button("Save Medicine", type="primary", use_container_width=True)
        if btn_save_med:
            if med_name.strip():
                add_or_update_medicine(med_name, category, stock_qty, unit_price, mark_expired)
                st.session_state["pharma_msg"] = f"Saved '{med_name.strip()}' to pharmacy inventory."
                st.rerun()
            else:
                st.warning("Please enter Medicine Name.")

    if not pharma_data.empty:
        st.write("")
        st.subheader("🔄 Quick Stock Restock / Dispense")
        with st.form("adjust_stock_form"):
            selected_med = st.selectbox("Select Medicine", options=pharma_data["Medicine Name"].tolist())
            action = st.radio("Action", ["Add Stock (+)", "Dispense / Issue (-)"], horizontal=True)
            qty_change = st.number_input("Quantity", min_value=1, max_value=10000, value=10)
            btn_adj = st.form_submit_button("Update Stock", use_container_width=True)
            if btn_adj:
                delta = qty_change if action == "Add Stock (+)" else -qty_change
                adjust_medicine_stock(selected_med, delta)
                st.session_state["pharma_msg"] = f"Updated stock for '{selected_med}'."
                st.rerun()

with col_table:
    st.subheader("📋 Medicine Stock Table")
    st.dataframe(pharma_data, use_container_width=True, hide_index=True)