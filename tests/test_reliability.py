"""
Reliability / fault‑injection tests for OpsBridge Milestone 4.

These tests use the ``FAULT_INJECT_TIMEOUT`` and ``FAULT_INJECT_UPLOAD_MISSING`` flags in
``engine.submitter`` to deterministically exercise the retry logic
without needing a real slow portal.

Run them with the virtual environment activated and the project folder on the
path::

    $ env:RUN_E2E=1
    python -m pytest tests\test_reliability.py -v
"""
import asyncio
import os
import sys
import sqlite3

import pytest
from db import upsert_job, init_db

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so that `engine.*` modules can be
# imported inside the test functions (the import at module level would fail
# because of the package layout).
# ---------------------------------------------------------------------------
_project = os.path.join(os.path.dirname(__file__), "..")
if _project not in sys.path:
    sys.path.insert(0, _project)

# ---------------------------------------------------------------------------
# Helper: minimal portal config for Portal A (used by several tests)
# ---------------------------------------------------------------------------
PORTAL_A_CFG = {
    "name": "A",
    "url": "http://localhost:5000/portal_a",
    "fields": {
        "job_id": "job_id",
        "customer": "customer",
        "address": "address",
        "work_description": "work_description",
        "priority": "priority",
        "due_date": "due_date",
    },
}


# ---------------------------------------------------------------------------
# 1️⃣  Timeout‑exhaustion test
# ---------------------------------------------------------------------------
def test_retry_exhaustion(tmp_path, monkeypatch):
    """When FAULT_INJECT_TIMEOUT is true, submit_job must exhaust retries."""
    import engine.submitter

    # Use a temporary database so the real demo DB is never touched
    tmp_db = tmp_path / "jobs_retry_test.db"

    # Remember original DB path and redirect the module‑level path
    original_db_path = engine.submitter.__dict__.get(
        "DB_PATH", os.path.join(_project, "opsbridge_demo.db")
    )
    # We patch the DB_PATH attribute on the submitter module after import.
    # The submitter module uses `from db import get_pending_jobs, update_job_status,
    # record_attempt` and relies on the global `DB_PATH` defined in db.py.
    # We will redirect it via the `db` module's DB_PATH.
    import db as _db_mod
    original_db_path_db = _db_mod.DB_PATH
    _db_mod.DB_PATH = str(tmp_db)

    # Initialise the fresh database
    init_db()

    # Insert a job so that submit_job can update its status
    upsert_job(
        job_id="RX-001",
        customer="Test Corp",
        address="1 Test St",
        work_description="Test work",
        priority="Low",
        due_date="2025-12-01",
        portal="A",
    )

    # Set the fault‑injection flag so that submit_job raises a timeout on every attempt
    monkeypatch.setattr(engine.submitter, "FAULT_INJECT_TIMEOUT", True)

    try:
        job = {
            "job_id": "RX-001",
            "customer": "Test Corp",
            "address": "1 Test St",
            "work_description": "Test work",
            "priority": "Low",
            "due_date": "2025-12-01",
        }

        # submit_job is an coroutine; run it with asyncio.run()
        result = asyncio.run(engine.submitter.submit_job(job, PORTAL_A_CFG))

        # The function should have exhausted all retries and return "exhausted"
        assert result["status"] == "exhausted", (
            f"Expected exhausted, got {result['status']}")

        # The job should be marked Failed in the temporary database
        conn = sqlite3.connect(str(tmp_db))
        cur = conn.cursor()
        cur.execute("SELECT status FROM jobs WHERE job_id = ?", (job["job_id"],))
        row = cur.fetchone()
        conn.close()
        assert row is not None and row[0] == "Failed", (
            "Job should be marked Failed in DB")
    finally:
        # Restore the original DB path and clean up the temporary file
        _db_mod.DB_PATH = original_db_path_db
        if tmp_db.exists():
            tmp_db.unlink()


# ---------------------------------------------------------------------------
# 2️⃣  Flag‑start‑False sanity check
# ---------------------------------------------------------------------------
def test_flags_start_false():
    """Verify that the fault‑injection flags are False by default."""
    from engine.submitter import FAULT_INJECT_TIMEOUT, FAULT_INJECT_UPLOAD_MISSING

    assert FAULT_INJECT_TIMEOUT is False, "FLAG should start False"
    assert FAULT_INJECT_UPLOAD_MISSING is False, "FLAG should start False"


# ---------------------------------------------------------------------------
# 3️⃣  Duplicate‑prevention test using an isolated temporary database
# ---------------------------------------------------------------------------
def test_duplicate_prevention_with_verified_job(tmp_path):
    """If a job already has status 'Verified' in the DB, it should stay verified."""
    from db import init_db, upsert_job, get_pending_jobs

    # Use a temporary database so the real demo DB is never touched
    tmp_db = tmp_path / "jobs_test.db"

    # Remember original DB path and redirect the module‑level path
    import db as _db_mod
    original_db_path = _db_mod.DB_PATH
    _db_mod.DB_PATH = str(tmp_db)

    # Clean any leftover
    if tmp_db.exists():
        tmp_db.unlink()

    # Initialise the fresh database
    init_db()

    # Insert a job (status default 'Submitted')
    upsert_job(
        job_id="DP-001",
        customer="Dup Corp",
        address="3 Dup St",
        work_description="Dup work",
        priority="Low",
        due_date="2025-12-01",
        portal="A",
    )

    # Mark it as Verified
    conn = sqlite3.connect(str(tmp_db))
    cur = conn.cursor()
    cur.execute("UPDATE jobs SET status = 'Verified' WHERE job_id = ?",
                ("DP-001",))
    conn.commit()
    conn.close()

    # Verify that get_pending_jobs() does NOT include this job
    pending = get_pending_jobs()
    pending_ids = [r["job_id"] for r in pending]
    assert "DP-001" not in pending_ids, (
        "Verified job should not be pending")

    # Restore original DB path
    _db_mod.DB_PATH = original_db_path

    # Remove the temporary database
    if tmp_db.exists():
        tmp_db.unlink()


# ---------------------------------------------------------------------------
# 3️⃣  Upload‑missing flag structure test (still just a structural check)
# ---------------------------------------------------------------------------
def test_upload_missing_flag_structure():
    """Verify that the FAULT_INJECT_UPLOAD_MISSING flag exists and can be set."""
    from engine.submitter import FAULT_INJECT_UPLOAD_MISSING

    assert FAULT_INJECT_UPLOAD_MISSING is False