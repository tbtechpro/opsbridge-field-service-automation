import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT UNIQUE NOT NULL,
            customer TEXT NOT NULL,
            address TEXT NOT NULL,
            work_description TEXT,
            priority TEXT,
            due_date TEXT,
            status TEXT NOT NULL DEFAULT 'Pending',
            portal TEXT
        )
    """)
    conn.commit()
    conn.close()

def upsert_job(job_id, customer, address, work_description, priority, due_date, portal):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO jobs (job_id, customer, address, work_description, priority, due_date, status, portal)
        VALUES (?, ?, ?, ?, ?, ?, 'Submitted', ?)
        ON CONFLICT(job_id) DO UPDATE SET
            customer = excluded.customer,
            address = excluded.address,
            work_description = excluded.work_description,
            priority = excluded.priority,
            due_date = excluded.due_date,
            status = 'Submitted',
            portal = excluded.portal
    """, (job_id, customer, address, work_description, priority, due_date, portal))
    conn.commit()
    conn.close()

def get_all_jobs():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs ORDER BY job_id")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_job(job_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
    row = cur.fetchone()
    conn.close()
    return row