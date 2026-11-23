import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# जर हा कोड models/ फोल्डरमध्ये असेल तर रूट फोल्डरसाठी:
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..")) if os.path.basename(BASE_DIR) == "models" else BASE_DIR
DB_FILE = os.path.join(PROJECT_ROOT, "hospital.db")


def get_connection():
    """Establishes and returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_schedule_table():
    """Initializes the schedules table if it does not already exist."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_name TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                department TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                status TEXT DEFAULT 'Pending'
            )
        """)
        conn.commit()
    finally:
        conn.close()


init_schedule_table()


def get_total_schedules():
    """Returns the total number of scheduled appointments."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM schedules")
        row = cursor.fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def get_all_schedules():
    """Fetches all schedules as a Pandas DataFrame."""
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM schedules ORDER BY id DESC", conn)
        return df
    finally:
        conn.close()


def add_schedule(doctor_name, patient_name, department, appointment_date, appointment_time, status="Confirmed"):
    """Inserts a new appointment record into the database."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO schedules (
                doctor_name, patient_name, department,
                appointment_date, appointment_time, status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(doctor_name).strip(),
                str(patient_name).strip(),
                str(department).strip(),
                str(appointment_date),
                str(appointment_time),
                str(status).strip() if status else "Confirmed",
            ),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def delete_schedule(schedule_id):
    """Deletes an appointment record by ID."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM schedules WHERE id = ?", (int(schedule_id),))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()