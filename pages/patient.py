import os
import sqlite3
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Patient Records | MediCare", page_icon="👨‍👩‍👧‍👦", layout="wide")

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


def init_patients_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            age INTEGER NOT NULL DEFAULT 0,
            gender TEXT NOT NULL DEFAULT 'Other',
            contact TEXT NOT NULL DEFAULT '',
            diagnosis TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Admitted',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    existing_count = cur.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    if existing_count == 0:
        initial_patients = [
            ("PAT-101", "Rahul Sharma", 34, "Male", "9876543210", "Viral Fever", "Admitted"),
            ("PAT-102", "Priya More", 28, "Female", "9876543211", "Routine Checkup", "Discharged"),
            ("PAT-103", "Amit Kothari", 45, "Male", "9876543212", "Orthopedic Care", "Admitted"),
            ("PAT-104", "Sneha Joshi", 52, "Female", "9876543213", "Cardiac Observation", "Critical"),
            ("PAT-105", "Anil Patil", 39, "Male", "9876543214", "General Care", "Admitted"),
        ]
        cur.executemany(
            """
            INSERT INTO patients (
                patient_code, name, age, gender, contact, diagnosis, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            initial_patients,
        )

    conn.commit()
    conn.close()


def fetch_patients_df():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            patient_code AS "ID",
            name AS "Name",
            age AS "Age",
            gender AS "Gender",
            contact AS "Contact",
            diagnosis AS "Diagnosis",
            status AS "Status",
            created_at AS "Registered At"
        FROM patients
        ORDER BY id DESC
        """,
        conn,
    )
    conn.close()
    return df


def add_patient(
    name: str,
    age: int,
    gender: str,
    contact: str,
    diagnosis: str,
    status: str = "Admitted",
):
    conn = get_connection()
    cur = conn.cursor()

    next_num = cur.execute("SELECT COALESCE(MAX(id), 100) + 1 FROM patients").fetchone()[0]
    if next_num <= 100:
        next_num = 101
    pat_code = f"PAT-{next_num}"

    cur.execute(
        """
        INSERT INTO patients (
            patient_code, name, age, gender, contact, diagnosis, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pat_code,
            name.strip(),
            int(age),
            gender,
            contact.strip(),
            diagnosis.strip(),
            status,
        ),
    )

    conn.commit()
    conn.close()
    return pat_code


def update_patient_status(patient_code: str, new_status: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE patients
        SET status = ?
        WHERE patient_code = ?
        """,
        (new_status, patient_code),
    )
    conn.commit()
    conn.close()


init_patients_db()

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
st.title("👨‍👩‍👧‍👦 Patient Records & EHR")
st.caption("Electronic Health Records, Admissions & Patient Database")

if st.session_state.get("patient_msg"):
    st.success(st.session_state.pop("patient_msg"))

st.divider()

# ----------------- LIVE PATIENT METRICS -----------------
patient_df = fetch_patients_df()
total_patients = len(patient_df)
admitted_count = (
    int((patient_df["Status"] == "Admitted").sum()) if not patient_df.empty else 0
)
discharged_count = (
    int((patient_df["Status"] == "Discharged").sum()) if not patient_df.empty else 0
)
critical_count = (
    int((patient_df["Status"].isin(["Critical", "ICU"])).sum()) if not patient_df.empty else 0
)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Total Patients</div><div class="kpi-val">👥 {total_patients}</div></div>',
        unsafe_allow_html=True,
    )
with m2:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Currently Admitted</div><div class="kpi-val">🏥 {admitted_count}</div></div>',
        unsafe_allow_html=True,
    )
with m3:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Discharged</div><div class="kpi-val">🏡 {discharged_count}</div></div>',
        unsafe_allow_html=True,
    )
with m4:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Critical / ICU</div><div class="kpi-val">🚨 {critical_count:02d}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ----------------- PATIENT FORM & TABLE -----------------
col_form, col_table = st.columns([1, 1.3])

with col_form:
    st.subheader("➕ Register New Patient")
    with st.form("patient_form", clear_on_submit=True):
        p_name = st.text_input("Full Name", placeholder="e.g. Rahul Sharma")
        p_age = st.number_input("Age", min_value=0, max_value=120, value=30)
        p_gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        p_contact = st.text_input("Contact Number", placeholder="e.g. 9876543210")
        p_illness = st.text_input("Diagnosis / Symptom", placeholder="e.g. Viral Fever / Cardiac Check")
        p_status = st.selectbox("Admission Status", ["Admitted", "Critical", "Discharged"])

        btn_pat = st.form_submit_button("Save Patient Record", type="primary", use_container_width=True)
        if btn_pat:
            if p_name.strip():
                created_code = add_patient(
                    name=p_name,
                    age=p_age,
                    gender=p_gender,
                    contact=p_contact,
                    diagnosis=p_illness,
                    status=p_status,
                )
                st.session_state["patient_msg"] = f"Patient {p_name.strip()} ({created_code}) registered successfully!"
                st.rerun()
            else:
                st.warning("Please enter patient name.")

    if not patient_df.empty:
        st.write("")
        st.subheader("🔄 Update Patient Status")
        with st.form("update_patient_status_form"):
            selected_pat = st.selectbox("Select Patient ID", options=patient_df["ID"].tolist())
            new_pat_status = st.selectbox("New Status", ["Admitted", "Critical", "Discharged"])
            btn_upd_pat = st.form_submit_button("Update Status", use_container_width=True)
            if btn_upd_pat:
                update_patient_status(selected_pat, new_pat_status)
                st.session_state["patient_msg"] = f"Updated {selected_pat} status to {new_pat_status}."
                st.rerun()

with col_table:
    st.subheader("📋 Patient Database Directory")
    st.dataframe(patient_df, use_container_width=True, hide_index=True)