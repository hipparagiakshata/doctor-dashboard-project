import os
import sqlite3
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Ambulance Fleet | MediCare", page_icon="🚑", layout="wide")

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


def init_ambulance_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ambulances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_no TEXT UNIQUE NOT NULL,
            amb_type TEXT NOT NULL,
            driver_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Available',
            location TEXT NOT NULL DEFAULT 'Standby Zone'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ambulance_dispatches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            pickup_location TEXT NOT NULL,
            amb_type TEXT NOT NULL,
            vehicle_no TEXT NOT NULL,
            dispatched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    existing_count = cur.execute("SELECT COUNT(*) FROM ambulances").fetchone()[0]
    if existing_count == 0:
        initial_fleet = [
            ("MH-10-AB-1111", "ALS", "Santosh K.", "On Dispatch", "City Hospital"),
            ("MH-10-AB-2222", "BLS", "Vijay M.", "Available", "Standby Zone"),
            ("MH-10-AB-3333", "ICU", "Anil D.", "On Dispatch", "Highway 4"),
            ("MH-10-AB-4444", "BLS", "Prakash S.", "Available", "Standby Zone"),
            ("MH-10-AB-5555", "ALS", "Kiran P.", "Maintenance", "Workshop"),
        ]
        cur.executemany(
            """
            INSERT INTO ambulances (vehicle_no, amb_type, driver_name, status, location)
            VALUES (?, ?, ?, ?, ?)
            """,
            initial_fleet,
        )

    conn.commit()
    conn.close()


def fetch_fleet_df():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            vehicle_no AS "Vehicle No",
            amb_type AS "Type",
            driver_name AS "Driver",
            status AS "Status",
            location AS "Location"
        FROM ambulances
        ORDER BY id ASC
        """,
        conn,
    )
    conn.close()
    return df


def fetch_recent_dispatches_df():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            id AS "ID",
            patient_name AS "Patient / Caller",
            pickup_location AS "Pickup Location",
            amb_type AS "Type",
            vehicle_no AS "Vehicle No",
            dispatched_at AS "Dispatched At"
        FROM ambulance_dispatches
        ORDER BY id DESC
        LIMIT 15
        """,
        conn,
    )
    conn.close()
    return df


def dispatch_ambulance(patient_name: str, location: str, amb_type: str, vehicle_no: str):
    conn = get_connection()
    cur = conn.cursor()

    chosen_vehicle = vehicle_no.strip().upper()
    if not chosen_vehicle:
        row = cur.execute(
            "SELECT vehicle_no FROM ambulances WHERE status = 'Available' ORDER BY id ASC LIMIT 1"
        ).fetchone()
        chosen_vehicle = row["vehicle_no"] if row else "UNASSIGNED"

    cur.execute(
        """
        INSERT INTO ambulance_dispatches (patient_name, pickup_location, amb_type, vehicle_no)
        VALUES (?, ?, ?, ?)
        """,
        (patient_name.strip(), location.strip(), amb_type, chosen_vehicle),
    )

    if chosen_vehicle != "UNASSIGNED":
        cur.execute(
            """
            UPDATE ambulances
            SET status = 'On Dispatch', location = ?
            WHERE UPPER(vehicle_no) = ?
            """,
            (location.strip(), chosen_vehicle),
        )

    conn.commit()
    conn.close()


def update_ambulance_status(vehicle_no: str, new_status: str, new_location: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE ambulances
        SET status = ?, location = ?
        WHERE vehicle_no = ?
        """,
        (new_status, new_location.strip(), vehicle_no),
    )
    conn.commit()
    conn.close()


init_ambulance_db()

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
st.title("🚑 Ambulance Fleet & Emergency Dispatch")
st.caption("Real-time Tracking, Driver Allocation & Emergency Response")

st.divider()

# ----------------- LIVE AMBULANCE METRICS -----------------
amb_data = fetch_fleet_df()
total_count = len(amb_data)
dispatch_count = int((amb_data["Status"] == "On Dispatch").sum()) if not amb_data.empty else 0
available_count = int((amb_data["Status"] == "Available").sum()) if not amb_data.empty else 0
maintenance_count = int((amb_data["Status"] == "Maintenance").sum()) if not amb_data.empty else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("🚑 Total Ambulances", f"{total_count:02d}")
m2.metric("🚨 On Dispatch", f"{dispatch_count:02d}")
m3.metric("🟢 Available", f"{available_count:02d}")
m4.metric("⚠️ Maintenance", f"{maintenance_count:02d}")

st.write("")

# ----------------- DISPATCH FORM & TABLE -----------------
col_form, col_table = st.columns([1, 1.2])

with col_form:
    st.subheader("🚨 Emergency Dispatch Request")
    with st.form("ambulance_form", clear_on_submit=True):
        p_name = st.text_input("Patient / Caller Name", placeholder="e.g. Ramesh Patil")
        location = st.text_input("Pickup Location", placeholder="e.g. Station Road, Near Bus Stand")
        ambulance_type = st.selectbox(
            "Ambulance Type",
            ["Advanced Life Support (ALS)", "Basic Life Support (BLS)", "ICU Ambulance"],
        )
        vehicle_options = [""] + amb_data["Vehicle No"].tolist() if not amb_data.empty else [""]
        driver_pref = st.selectbox("Assign Vehicle No (Optional)", options=vehicle_options)

        btn_dispatch = st.form_submit_button("Dispatch Ambulance", type="primary", use_container_width=True)
        if btn_dispatch:
            if p_name.strip() and location.strip():
                dispatch_ambulance(p_name, location, ambulance_type, driver_pref)
                st.success(f"Ambulance dispatched and saved for {p_name.strip()} at {location.strip()}!")
                st.rerun()
            else:
                st.warning("Please enter Patient Name and Location.")

    st.write("")
    st.subheader("🔄 Update Vehicle Status")
    if not amb_data.empty:
        with st.form("status_update_form"):
            selected_veh = st.selectbox("Select Vehicle", options=amb_data["Vehicle No"].tolist())
            current_row = amb_data[amb_data["Vehicle No"] == selected_veh].iloc[0]
            status_opts = ["Available", "On Dispatch", "Maintenance"]
            default_idx = status_opts.index(current_row["Status"]) if current_row["Status"] in status_opts else 0
            new_status = st.selectbox("New Status", options=status_opts, index=default_idx)
            new_loc = st.text_input("Current Location", value=str(current_row["Location"]))
            btn_update = st.form_submit_button("Update Status", use_container_width=True)
            if btn_update and new_loc.strip():
                update_ambulance_status(selected_veh, new_status, new_loc)
                st.success(f"{selected_veh} status updated to {new_status}.")
                st.rerun()

with col_table:
    st.subheader("📋 Fleet Status & Live Tracking")
    st.dataframe(amb_data, use_container_width=True, hide_index=True)

    st.write("")
    st.subheader("🕒 Recent Dispatches Log")
    dispatches_df = fetch_recent_dispatches_df()
    st.dataframe(dispatches_df, use_container_width=True, hide_index=True)