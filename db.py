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
            portal TEXT,
            attempt_count INTEGER DEFAULT 0,
            last_attempt_timestamp TEXT,
            submitted_at TEXT
        )
    """)
    # Ensure the submitted_at column exists (migration for old databases)
    try:
        cur.execute("ALTER TABLE jobs ADD COLUMN submitted_at TEXT")
    except sqlite3.OperationalError:
        # Column already exists; ignore
        pass
    conn.commit()
    conn.close()

def upsert_job(job_id, customer, address, work_description, priority, due_date, portal):
    conn = get_connection()
    cur = conn.cursor()
    now = __import__('datetime').datetime.utcnow().isoformat()
    cur.execute("""
        INSERT INTO jobs (job_id, customer, address, work_description, priority, due_date, status, portal, attempt_count, last_attempt_timestamp)
        VALUES (?, ?, ?, ?, ?, ?, 'Submitted', ?, 1, ?)
        ON CONFLICT(job_id) DO UPDATE SET
            customer = excluded.customer,
            address = excluded.address,
            work_description = excluded.work_description,
            priority = excluded.priority,
            due_date = excluded.due_date,
            status = 'Submitted',
            portal = excluded.portal,
            attempt_count = attempt_count + 1,
            last_attempt_timestamp = ?
    """, (job_id, customer, address, work_description, priority, due_date, portal, now, now))
    conn.commit()
    conn.close()

def get_all_jobs():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs ORDER BY job_id")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_pending_jobs():
    """Return all jobs whose status is not 'Verified' (i.e. still need processing)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs WHERE status != 'Verified' ORDER BY job_id")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_job_status(job_id, status, portal=None, submitted_at=None):
    """Update a job's status and optionally its portal and submission timestamp."""
    conn = get_connection()
    cur = conn.cursor()
    if submitted_at is None:
        submitted_at = __import__('datetime').datetime.utcnow().isoformat()
    cur.execute(
        "UPDATE jobs SET status = ?, portal = ?, submitted_at = ? WHERE job_id = ?",
        (status, portal, submitted_at, job_id),
    )
    conn.commit()
    conn.close()


def record_attempt(job_id, portal=None):
    """Increment the attempt counter and record the timestamp for a given job."""
    conn = get_connection()
    cur = conn.cursor()
    now = __import__('datetime').datetime.utcnow().isoformat()
    cur.execute(
        "UPDATE jobs SET attempt_count = attempt_count + 1, last_attempt_timestamp = ? WHERE job_id = ?",
        (now, job_id),
    )
    conn.commit()
    conn.close()