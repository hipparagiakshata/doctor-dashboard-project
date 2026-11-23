import os
import sqlite3
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Billing System | MediCare", page_icon="💳", layout="wide")

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


def init_bills_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id TEXT UNIQUE NOT NULL,
            patient_name TEXT NOT NULL,
            room_charges REAL NOT NULL DEFAULT 0.0,
            med_charges REAL NOT NULL DEFAULT 0.0,
            doc_fees REAL NOT NULL DEFAULT 0.0,
            total_amount REAL NOT NULL DEFAULT 0.0,
            payment_mode TEXT NOT NULL DEFAULT 'Cash',
            status TEXT NOT NULL DEFAULT 'Paid',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    existing_count = cur.execute("SELECT COUNT(*) FROM bills").fetchone()[0]
    if existing_count == 0:
        initial_bills = [
            ("INV-501", "Rahul S.", 8500.0, 6000.0, 4000.0, 18500.0, "Insurance", "Paid"),
            ("INV-502", "Anita P.", 22000.0, 12000.0, 8000.0, 42000.0, "UPI", "Paid"),
            ("INV-503", "Suresh K.", 4500.0, 3000.0, 2000.0, 9500.0, "Cash", "Pending"),
            ("INV-504", "Priya M.", 16000.0, 9000.0, 6000.0, 31000.0, "Credit Card", "Paid"),
        ]
        cur.executemany(
            """
            INSERT INTO bills (
                bill_id, patient_name, room_charges, med_charges,
                doc_fees, total_amount, payment_mode, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            initial_bills,
        )

    conn.commit()
    conn.close()


def fetch_bills_df():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            bill_id AS "Bill ID",
            patient_name AS "Patient",
            total_amount AS "Amount (₹)",
            payment_mode AS "Payment Mode",
            status AS "Status",
            created_at AS "Created At"
        FROM bills
        ORDER BY id DESC
        """,
        conn,
    )
    conn.close()
    return df


def create_bill(
    patient_name: str,
    room_charges: float,
    med_charges: float,
    doc_fees: float,
    payment_mode: str,
    status: str,
):
    conn = get_connection()
    cur = conn.cursor()

    next_num = cur.execute("SELECT COALESCE(MAX(id), 500) + 1 FROM bills").fetchone()[0]
    if next_num <= 500:
        next_num = 501
    bill_code = f"INV-{next_num}"

    total_amount = float(room_charges) + float(med_charges) + float(doc_fees)

    cur.execute(
        """
        INSERT INTO bills (
            bill_id, patient_name, room_charges, med_charges,
            doc_fees, total_amount, payment_mode, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            bill_code,
            patient_name.strip(),
            float(room_charges),
            float(med_charges),
            float(doc_fees),
            total_amount,
            payment_mode,
            status,
        ),
    )

    conn.commit()
    conn.close()
    return bill_code, total_amount


init_bills_db()

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
st.title("💳 Billing & Invoicing System")
st.caption("Patient Accounts, Payment Gateways & Discharge Invoicing")

st.divider()

# ----------------- LIVE BILLING METRICS -----------------
bills_data = fetch_bills_df()
total_bills_count = len(bills_data)

paid_df = bills_data[bills_data["Status"] == "Paid"] if not bills_data.empty else pd.DataFrame()
today_collection = float(paid_df["Amount (₹)"].sum()) if not paid_df.empty else 0.0

pending_invoices_count = (
    int((bills_data["Status"] == "Pending").sum()) if not bills_data.empty else 0
)
insurance_claims_count = (
    int((bills_data["Payment Mode"] == "Insurance").sum()) if not bills_data.empty else 0
)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Collected Amount</div><div class="kpi-val">💰 ₹{today_collection:,.0f}</div></div>',
        unsafe_allow_html=True,
    )
with m2:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Pending Invoices</div><div class="kpi-val">⏳ {pending_invoices_count:02d}</div></div>',
        unsafe_allow_html=True,
    )
with m3:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Insurance Claims</div><div class="kpi-val">🏥 {insurance_claims_count:02d}</div></div>',
        unsafe_allow_html=True,
    )
with m4:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Total Bills Generated</div><div class="kpi-val">🧾 {total_bills_count}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ----------------- BILLING FORM & TABLE -----------------
col_form, col_table = st.columns([1, 1.2])

with col_form:
    st.subheader("🧾 Generate Patient Bill")
    with st.form("billing_form", clear_on_submit=True):
        p_bill_name = st.text_input("Patient Name / ID", placeholder="e.g. Sachin Tendulkar")
        room_charges = st.number_input("Room & Ward Charges (₹)", min_value=0.0, value=5000.0, step=500.0)
        med_charges = st.number_input("Pharmacy & Medicines (₹)", min_value=0.0, value=2500.0, step=250.0)
        doc_fees = st.number_input("Doctor Consultation Fees (₹)", min_value=0.0, value=1500.0, step=200.0)
        payment_mode = st.selectbox("Payment Mode", ["Cash", "UPI", "Insurance", "Credit Card", "Debit Card"])
        status = st.selectbox("Payment Status", ["Paid", "Pending"])

        btn_gen = st.form_submit_button("Calculate & Generate Bill", type="primary", use_container_width=True)
        if btn_gen:
            if p_bill_name.strip():
                bill_code, total_amt = create_bill(
                    patient_name=p_bill_name,
                    room_charges=room_charges,
                    med_charges=med_charges,
                    doc_fees=doc_fees,
                    payment_mode=payment_mode,
                    status=status,
                )
                st.success(f"Bill {bill_code} generated! Total Amount: ₹{total_amt:,.2f}")
                st.rerun()
            else:
                st.warning("Please enter Patient Name / ID.")

with col_table:
    st.subheader("📋 Recent Invoices")
    st.dataframe(bills_data, use_container_width=True, hide_index=True)