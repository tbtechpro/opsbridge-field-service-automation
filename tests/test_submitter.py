"""
Submitter tests for OpsBridge Milestone 7.

Uses pytest‑asyncio to run the async ``submit_job`` function and
properly‑mocked Playwright objects to verify a successful submission.
"""
from __future__ import annotations

import asyncio
import os
import sys

import sqlite3
import os
import sys

import pytest
from unittest import mock

# Ensure the project root is on sys.path so that ``engine.*`` modules are importable.
_project = os.path.join(os.path.dirname(__file__), "..")
if _project not in sys.path:
    sys.path.insert(0, _project)

from engine.submitter import submit_job, map_fields
from db import upsert_job, get_pending_jobs, update_job_status

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
# Helper: build a minimal mock Playwright hierarchy that submit_job can use.
# ---------------------------------------------------------------------------
def _build_mock_playwright():
    """Return an async‑context‑manager mock that submit_job can use successfully."""
    # async_playwright() is an async context manager; its __aenter__ returns the
    # Playwright instance that submit_job will use.
    mock_pw = mock.MagicMock()

    # --- Playwright instance ---
    pw_instance = mock.MagicMock()

    # pw.chromium.launch returns a browser mock
    browser_mock = mock.MagicMock()
    pw_instance.chromium.launch = mock.AsyncMock(return_value=browser_mock)

    # browser.new_context returns a context mock
    context_mock = mock.MagicMock()
    browser_mock.new_context = mock.AsyncMock(return_value=context_mock)

    # context.new_page returns a page mock
    page_mock = mock.MagicMock()
    page_mock.fill = mock.AsyncMock()
    page_mock.click = mock.AsyncMock()
    page_mock.wait_for_selector = mock.AsyncMock(return_value=None)  # success
    context_mock.new_page = mock.AsyncMock(return_value=page_mock)

    # -----------------------------------------------------------------
    # page.goto is also called by submit_job; make it a no‑op coroutine.
    # -----------------------------------------------------------------
    page_mock.go_to = mock.AsyncMock(return_value=None)

    # Attach the hierarchy
    pw_instance.chromium.launch = mock.AsyncMock(return_value=browser_mock)  # redundant but safe
    # Ensure the hierarchy is consistent:
    # pw_instance -> chromium.launch -> browser_mock
    # browser_mock.new_context -> context_mock
    # context_mock.new_page -> page_mock

    # Attach the whole hierarchy to the magic mock so that
    # ``async with async_playwright() as p`` yields pw_instance.
    mock_pw.__aenter__.return_value = pw_instance
    mock_pw.__aexit__ = mock.MagicMock(return_value=None)

    return mock_pw


# ---------------------------------------------------------------------------
# 1️⃣  Successful submission test
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_submit_job_successful():
    """When the page reports success, submit_job must return status ``ok``."""
    job = {
        "job_id": "SJ1",
        "customer": "Test Customer",
        "address": "42 Test Ave",
        "work_description": "Fix leak",
        "priority": "Medium",
        "due_date": "2025-11-20",
    }

    # -----------------------------------------------------------------
    # Mock Playwright – the real submit_job will use these objects.
    # -----------------------------------------------------------------
    mock_pw = _build_mock_playwright()

    # Patch the module‑level symbol that submit_job imports.
    # submit_job does:  from playwright.async_api import async_playwright
    # (the import is at module level, so we replace the attribute on the module).
    import engine.submitter
    original = engine.submitter.async_playwright
    engine.submitter.async_playwright = mock_pw

    try:
        result = await submit_job(job, PORTAL_A_CFG)
        assert result["status"] == "ok", f"Expected ok, got {result['status']}"
    finally:
        # Restore the original symbol so other tests are not affected.
        engine.submitter.async_playwright = original


# ---------------------------------------------------------------------------
# 2️⃣  Map fields test (unchanged from earlier version)
# ---------------------------------------------------------------------------
def test_map_fields():
    """map_fields should translate job dict keys to form field names."""
    job = {
        "job_id": "TEST-001",
        "customer": "Acme Corp",
        "address": "123 Street",
        "work_description": "Roof repair",
        "priority": "High",
        "due_date": "2025-12-01",
    }
    result = map_fields(job, {"name": "A", "url": "http://x", "fields": {
        "job_id": "job_id", "customer": "customer", "address": "address",
        "work_description": "work_description", "priority": "priority", "due_date": "due_date"
    }})
    assert "job_id" in result
    assert result["customer"] == "Acme Corp"
    assert result["address"] == "123 Street"


# ---------------------------------------------------------------------------
# 3️⃣  Duplicate‑prevention test (uses the real DB but an isolated path)
# ---------------------------------------------------------------------------
def test_duplicate_prevention_skips_verified():
    """If a job already has status ``Verified`` it should be skipped."""
    from db import init_db, upsert_job, get_pending_jobs

    import os, sqlite3 as _sq

    import db as _db_mod
    original_db_path = _db_mod.DB_PATH
    tmp_path = os.path.join(os.path.dirname(__file__), "..", "jobs_dup_test.db")
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    _db_mod.DB_PATH = tmp_path
    init_db()

    upsert_job(
        job_id="DP-001",
        customer="Dup Corp",
        address="3 Dup St",
        work_description="Dup work",
        priority="Low",
        due_date="2025-12-01",
        portal="A",
    )
    conn = sqlite3.connect(tmp_path)
    cur = conn.cursor()
    cur.execute("UPDATE jobs SET status = 'Verified' WHERE job_id = ?", ("DP-001",))
    conn.commit()
    conn.close()

    pending = get_pending_jobs()
    pending_ids = [r["job_id"] for r in pending]
    assert "DP-001" not in pending_ids, "Verified job should not be pending"

    _db_mod.DB_PATH = original_db_path
    if os.path.exists(tmp_path):
        os.remove(tmp_path)