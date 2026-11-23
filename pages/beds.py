import os
import sqlite3
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Bed Allocation | MediCare", page_icon="🛏️", layout="wide")

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


def init_beds_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS beds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bed_no TEXT UNIQUE NOT NULL,
            ward_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Available',
            patient_name TEXT NOT NULL DEFAULT 'Vacant',
            doctor_assigned TEXT NOT NULL DEFAULT '-',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    existing_count = cur.execute("SELECT COUNT(*) FROM beds").fetchone()[0]
    if existing_count == 0:
        initial_beds = [
            ("ICU-01", "ICU Ward", "Occupied", "Rahul S.", "Dr. Kulkarni"),
            ("ICU-02", "ICU Ward", "Occupied", "Priya M.", "Dr. Sharma"),
            ("B-101", "General Male Ward", "Available", "Vacant", "-"),
            ("B-102", "General Male Ward", "Occupied", "Suresh P.", "Dr. Deshmukh"),
            ("S-201", "Special Private Suite", "Available", "Vacant", "-"),
            ("S-202", "Special Private Suite", "Occupied", "Anil R.", "Dr. Joshi"),
        ]
        cur.executemany(
            """
            INSERT INTO beds (bed_no, ward_type, status, patient_name, doctor_assigned)
            VALUES (?, ?, ?, ?, ?)
            """,
            initial_beds,
        )

    conn.commit()
    conn.close()


def fetch_beds_df():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            bed_no AS "Bed No",
            ward_type AS "Ward",
            status AS "Status",
            patient_name AS "Patient",
            doctor_assigned AS "Doctor",
            updated_at AS "Updated At"
        FROM beds
        ORDER BY id ASC
        """,
        conn,
    )
    conn.close()
    return df


def allocate_bed(patient_name: str, ward_type: str, bed_no: str, doctor_assigned: str):
    conn = get_connection()
    cur = conn.cursor()

    clean_bed = bed_no.strip().upper()
    clean_patient = patient_name.strip()
    clean_doctor = doctor_assigned.strip() if doctor_assigned.strip() else "Assigned"

    existing = cur.execute(
        "SELECT id FROM beds WHERE UPPER(bed_no) = ?",
        (clean_bed,),
    ).fetchone()

    if existing:
        cur.execute(
            """
            UPDATE beds
            SET ward_type = ?,
                status = 'Occupied',
                patient_name = ?,
                doctor_assigned = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (ward_type, clean_patient, clean_doctor, existing["id"]),
        )
    else:
        cur.execute(
            """
            INSERT INTO beds (bed_no, ward_type, status, patient_name, doctor_assigned)
            VALUES (?, ?, 'Occupied', ?, ?)
            """,
            (clean_bed, ward_type, clean_patient, clean_doctor),
        )

    conn.commit()
    conn.close()


def release_bed(bed_no: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE beds
        SET status = 'Available',
            patient_name = 'Vacant',
            doctor_assigned = '-',
            updated_at = CURRENT_TIMESTAMP
        WHERE bed_no = ?
        """,
        (bed_no,),
    )
    conn.commit()
    conn.close()


init_beds_db()

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

        [data-testid="stMetric"] {
            background: #ffffff;
            border-radius: 16px;
            padding: 18px;
            border: 1px solid #d1fae5;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
        }
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
st.title("🛏️ Bed Allocation & Ward Occupancy")
st.caption("ICU, General Wards, Special Rooms & Bed Availability Tracker")

st.divider()

# ----------------- LIVE BED METRICS -----------------
beds_data = fetch_beds_df()
total_beds = len(beds_data)
occupied_beds = int((beds_data["Status"] == "Occupied").sum()) if not beds_data.empty else 0
available_beds = int((beds_data["Status"] == "Available").sum()) if not beds_data.empty else 0

icu_df = beds_data[beds_data["Ward"] == "ICU Ward"] if not beds_data.empty else pd.DataFrame()
icu_total = len(icu_df)
icu_occupied = int((icu_df["Status"] == "Occupied").sum()) if not icu_df.empty else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("🛏️ Total Beds", f"{total_beds}")
m2.metric("🔴 Occupied Beds", f"{occupied_beds}")
m3.metric("🟢 Available Beds", f"{available_beds}")
m4.metric("🚨 ICU Occupancy", f"{icu_occupied} / {icu_total}")

st.write("")

# ----------------- BED ALLOCATION & TABLE -----------------
col_form, col_table = st.columns([1, 1.2])

with col_form:
    st.subheader("➕ Allocate Bed to Patient")
    with st.form("allocate_bed_form", clear_on_submit=True):
        patient_name = st.text_input("Patient ID / Name", placeholder="e.g. PAT-901 or Amit K.")
        ward_type = st.selectbox(
            "Ward Type",
            [
                "ICU Ward",
                "General Male Ward",
                "General Female Ward",
                "Special Private Suite",
                "Emergency ER",
            ],
        )
        bed_no = st.text_input("Bed Number", placeholder="e.g. ICU-05 or B-12")
        doctor_assigned = st.text_input("Attending Doctor", placeholder="e.g. Dr. Sharma")

        btn_allocate = st.form_submit_button("Allocate Bed", type="primary", use_container_width=True)
        if btn_allocate:
            if patient_name.strip() and bed_no.strip():
                allocate_bed(patient_name, ward_type, bed_no, doctor_assigned)
                st.success(f"Bed {bed_no.strip().upper()} ({ward_type}) allocated to {patient_name.strip()}.")
                st.rerun()
            else:
                st.warning("Please enter Patient Name and Bed Number.")

    st.write("")
    st.subheader("🔓 Vacate / Release Bed")
    occupied_list = (
        beds_data[beds_data["Status"] == "Occupied"]["Bed No"].tolist()
        if not beds_data.empty
        else []
    )
    if occupied_list:
        with st.form("release_bed_form"):
            bed_to_release = st.selectbox("Select Occupied Bed", options=occupied_list)
            btn_release = st.form_submit_button("Mark Bed Available", use_container_width=True)
            if btn_release:
                release_bed(bed_to_release)
                st.success(f"Bed {bed_to_release} is now Available.")
                st.rerun()

with col_table:
    st.subheader("📋 Current Bed Status")
    st.dataframe(beds_data, use_container_width=True, hide_index=True)