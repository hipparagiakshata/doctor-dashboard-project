import os
import sqlite3
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Doctor Directory | MediCare", page_icon="👨‍⚕️", layout="wide")

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


def init_doctors_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            shift_timing TEXT NOT NULL,
            contact TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    existing_count = cur.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
    if existing_count == 0:
        initial_doctors = [
            ("Dr. Rajesh Sharma", "Cardiologist", "Morning (08:00 AM - 02:00 PM)", "9811223344", "Available"),
            ("Dr. Priya Deshmukh", "Pediatrician", "Evening (02:00 PM - 08:00 PM)", "9811223345", "In Surgery"),
            ("Dr. Amit Kothari", "Orthopedic", "Morning (08:00 AM - 02:00 PM)", "9811223346", "Available"),
            ("Dr. Sneha Joshi", "Dermatologist", "Night (08:00 PM - 08:00 AM)", "9811223347", "On Leave"),
            ("Dr. Vikramaditya", "Neurologist", "Morning (08:00 AM - 02:00 PM)", "9811223348", "Available"),
        ]
        cur.executemany(
            """
            INSERT INTO doctors (
                doctor_name, specialty, shift_timing, contact, status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            initial_doctors,
        )

    conn.commit()
    conn.close()


def fetch_doctors_df():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            id AS "ID",
            doctor_name AS "Doctor Name",
            specialty AS "Specialty",
            shift_timing AS "Shift Timing",
            contact AS "Phone",
            status AS "Status"
        FROM doctors
        ORDER BY id DESC
        """,
        conn,
    )
    conn.close()
    return df


def add_doctor(doctor_name: str, specialty: str, shift_timing: str, contact: str, status: str = "Available"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO doctors (doctor_name, specialty, shift_timing, contact, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (doctor_name.strip(), specialty, shift_timing, contact.strip(), status),
    )
    conn.commit()
    conn.close()


def update_doctor_status(doctor_id: int, new_status: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE doctors
        SET status = ?
        WHERE id = ?
        """,
        (new_status, int(doctor_id)),
    )
    conn.commit()
    conn.close()


init_doctors_db()

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
st.title("👨‍⚕️ Doctor Directory & Specialists")
st.caption("Manage Hospital Specialists, On-Duty Rosters & Consultation Timings")

if st.session_state.get("doctor_msg"):
    st.success(st.session_state.pop("doctor_msg"))

st.divider()

# ----------------- LIVE DOCTOR METRICS -----------------
doc_df = fetch_doctors_df()
total_docs = len(doc_df)
on_duty_count = (
    int((doc_df["Status"].isin(["Available", "In Surgery"])).sum()) if not doc_df.empty else 0
)
specialties_count = (
    int(doc_df["Specialty"].nunique()) if not doc_df.empty else 0
)
on_leave_count = (
    int((doc_df["Status"] == "On Leave").sum()) if not doc_df.empty else 0
)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Total Doctors</div><div class="kpi-val">👨‍⚕️ {total_docs:02d}</div></div>',
        unsafe_allow_html=True,
    )
with m2:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">On Duty Today</div><div class="kpi-val">🟢 {on_duty_count:02d}</div></div>',
        unsafe_allow_html=True,
    )
with m3:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Active Specialties</div><div class="kpi-val">⭐ {specialties_count:02d}</div></div>',
        unsafe_allow_html=True,
    )
with m4:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">On Leave</div><div class="kpi-val">🌴 {on_leave_count:02d}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ----------------- DOCTOR FORM & TABLE -----------------
col_form, col_table = st.columns([1, 1.3])

with col_form:
    st.subheader("➕ Add New Doctor")
    with st.form("doctor_form", clear_on_submit=True):
        doc_name = st.text_input("Doctor Name", placeholder="e.g. Dr. Rajesh Sharma")
        doc_spec = st.selectbox(
            "Specialization",
            [
                "Cardiologist",
                "Pediatrician",
                "Orthopedic",
                "Neurologist",
                "Dermatologist",
                "General Surgeon",
            ],
        )
        doc_shift = st.selectbox(
            "Shift Timing",
            [
                "Morning (08:00 AM - 02:00 PM)",
                "Evening (02:00 PM - 08:00 PM)",
                "Night (08:00 PM - 08:00 AM)",
            ],
        )
        doc_contact = st.text_input("Phone Number", placeholder="e.g. 9811223344")
        doc_status = st.selectbox("Initial Status", ["Available", "In Surgery", "On Leave"])

        btn_doc = st.form_submit_button("Add Doctor", type="primary", use_container_width=True)
        if btn_doc:
            if doc_name.strip():
                add_doctor(doc_name, doc_spec, doc_shift, doc_contact, doc_status)
                st.session_state["doctor_msg"] = f"{doc_name.strip()} added successfully to directory!"
                st.rerun()
            else:
                st.warning("Please enter doctor name.")

    if not doc_df.empty:
        st.write("")
        st.subheader("🔄 Update Doctor Status")
        with st.form("update_doctor_status_form"):
            selected_doc_id = st.selectbox(
                "Select Doctor",
                options=doc_df["ID"].tolist(),
                format_func=lambda x: f"#{x} - {doc_df.loc[doc_df['ID'] == x, 'Doctor Name'].values[0]}",
            )
            new_doc_status = st.selectbox("New Status", ["Available", "In Surgery", "On Leave"])
            btn_upd_doc = st.form_submit_button("Update Status", use_container_width=True)
            if btn_upd_doc:
                update_doctor_status(selected_doc_id, new_doc_status)
                st.session_state["doctor_msg"] = f"Doctor status updated to {new_doc_status}."
                st.rerun()

with col_table:
    st.subheader("📋 On-Duty Doctor Roster")
    st.dataframe(doc_df, use_container_width=True, hide_index=True)