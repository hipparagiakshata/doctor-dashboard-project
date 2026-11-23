import os
import sys
import streamlit as st
import pandas as pd

# प्रोजेक्ट रूट पाथ जोडून models फोल्डर इम्पोर्ट करणे
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

try:
    from models.schedule_model import (
        add_schedule,
        get_all_schedules,
        get_total_schedules,
        delete_schedule,
    )
except ImportError:
    from schedule_model import (
        add_schedule,
        get_all_schedules,
        get_total_schedules,
        delete_schedule,
    )

st.set_page_config(page_title="Schedule & Appointments | MediCare", page_icon="📅", layout="wide")

# ----------------- LOGIN GUARD & SESSION CHECK -----------------
if not st.session_state.get("logged_in", False):
    st.switch_page("app.py")

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
st.title("📅 Schedule & OPD Appointments")
st.caption("Patient Tokens, Doctor Consultation Booking & Schedule Management")

st.divider()

# डेटाबेसमधून रेकॉर्ड्स आणणे
df_schedules = get_all_schedules()
total_count = get_total_schedules()

# ----------------- APPOINTMENT METRICS -----------------
confirmed_cnt = (
    int((df_schedules["status"] == "Confirmed").sum())
    if not df_schedules.empty and "status" in df_schedules.columns
    else 0
)
pending_cnt = (
    int((df_schedules["status"] == "Pending").sum())
    if not df_schedules.empty and "status" in df_schedules.columns
    else 0
)
cancelled_cnt = (
    int((df_schedules["status"] == "Cancelled").sum())
    if not df_schedules.empty and "status" in df_schedules.columns
    else 0
)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Total Scheduled</div><div class="kpi-val">📅 {total_count}</div></div>',
        unsafe_allow_html=True,
    )
with m2:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Confirmed</div><div class="kpi-val">🟢 {confirmed_cnt}</div></div>',
        unsafe_allow_html=True,
    )
with m3:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Pending / Waiting</div><div class="kpi-val">⏳ {pending_cnt}</div></div>',
        unsafe_allow_html=True,
    )
with m4:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">Cancelled</div><div class="kpi-val">❌ {cancelled_cnt}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ----------------- BOOKING FORM & TABLE -----------------
col_form, col_table = st.columns([1, 1.3])

DOCTOR_OPTIONS = {
    "Dr. Rajesh Sharma": "Cardiology",
    "Dr. Priya Deshmukh": "Pediatrics",
    "Dr. Amit Kothari": "Orthopedics",
    "Dr. Sneha Joshi": "Dermatology",
}

with col_form:
    st.subheader("➕ Book New Appointment")
    with st.form("appointment_form", clear_on_submit=True):
        p_name = st.text_input("Patient Name", placeholder="e.g. Mahesh Kulkarni")
        doctor = st.selectbox("Select Specialist Doctor", list(DOCTOR_OPTIONS.keys()))
        department = DOCTOR_OPTIONS[doctor]
        st.caption(f"Department: **{department}**")
        appt_date = st.date_input("Appointment Date")
        time_slot = st.selectbox(
            "Time Slot",
            [
                "10:00 AM - 10:30 AM",
                "11:00 AM - 11:30 AM",
                "02:00 PM - 02:30 PM",
                "04:30 PM - 05:00 PM",
            ],
        )
        status = st.selectbox("Status", ["Confirmed", "Pending", "Cancelled"])

        btn_book = st.form_submit_button("Confirm Booking", type="primary", use_container_width=True)
        if btn_book:
            if p_name.strip():
                saved = add_schedule(
                    doctor_name=doctor,
                    patient_name=p_name.strip(),
                    department=department,
                    appointment_date=str(appt_date),
                    appointment_time=time_slot,
                    status=status,
                )
                if saved:
                    st.success(f"Appointment saved for {p_name.strip()} with {doctor}!")
                    st.rerun()
                else:
                    st.error("Failed to save appointment in database.")
            else:
                st.warning("Please enter patient name.")

with col_table:
    st.subheader("📋 Scheduled Appointments")
    df_display = get_all_schedules()

    if df_display.empty:
        st.info("No appointments scheduled yet. Use the form on the left to book one.")
    else:
        display_df = df_display.rename(
            columns={
                "id": "Token / ID",
                "patient_name": "Patient Name",
                "doctor_name": "Doctor",
                "department": "Department",
                "appointment_date": "Date",
                "appointment_time": "Time Slot",
                "status": "Status",
            }
        )
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.markdown("##### 🗑️ Cancel / Remove Appointment")
        del_col1, del_col2 = st.columns([2, 1])
        with del_col1:
            selected_id = st.selectbox(
                "Select Appointment ID to remove",
                options=df_display["id"].tolist(),
                format_func=lambda x: f"ID #{x} - {df_display.loc[df_display['id'] == x, 'patient_name'].values[0]}",
                label_visibility="collapsed",
            )
        with del_col2:
            if st.button("Remove", use_container_width=True):
                if delete_schedule(selected_id):
                    st.success(f"Removed appointment #{selected_id}")
                    st.rerun()