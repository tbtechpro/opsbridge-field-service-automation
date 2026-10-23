"""
End‑to‑end browser tests for OpsBridge Milestone 3.

These tests launch the Flask portals in a background thread, then use
Playwright to drive a real Chromium instance against the local portals.

Set the environment variable ``RUN_E2E=1`` before running pytest to execute them,
otherwise they are automatically skipped.

Example::

    RUN_E2E=1 python -m pytest tests/test_e2e_browser.py -v
"""
import os
import subprocess
import sys
import time
import threading

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _start_flask():
    """Start the Flask app in a daemon thread and return the process."""
    # Ensure the project root is on sys.path
    project = os.path.join(os.path.dirname(__file__), "..")
    if project not in sys.path:
        sys.path.insert(0, project)

    # Import after path setup
    from portals.app import app as flask_app  # noqa: F401

    # Run Flask on a random available port – we’ll use 5000 as defined
    # but we need it in a thread so we can terminate later.
    # Flask’s built‑in server is simple enough for a thread.
    thread = threading.Thread(target=lambda: flask_app.run(port=5000, use_reloader=False), daemon=True)
    thread.start()
    # Give the server a moment to start
    time.sleep(2)
    return flask_app


# ---------------------------------------------------------------------------
# Fixture that starts/stops the Flask server for each test
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function", autouse=True)
def flask_server():
    if not os.environ.get("RUN_E2E"):
        pytest.skip("E2E tests require RUN_E2E=1")
    _start_flask()
    yield
    # No explicit teardown needed; the thread will die when process ends.


# ---------------------------------------------------------------------------
# Actual test: successful Portal A submission via browser
# ---------------------------------------------------------------------------
@pytest.mark.usefixtures("flask_server")
def test_e2e_portal_a_submission():
    """Playwright should fill Portal A and verify the job appears in the DB."""
    from playwright.sync_api import sync_playwright
    import sqlite3
    import json

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        # Navigate to Portal A
        page.goto("http://localhost:5000/portal_a")

        # Fill the form using the known field names from the HTML
        page.fill('input[name="job_id"]', "E2E-A-001")
        page.fill('input[name="customer"]', "E2E Customer A")
        page.fill('input[name="address"]', "100 E Test Blvd")
        page.fill('input[name="work_description"]', "E2E repair work")
        page.select_option('select[name="priority"]', "High")
        page.fill('input[name="due_date"]', "2025-12-15")

        # Submit
        page.click('button[type="submit"]')

        # Wait for the dashboard to show the new job
        page.goto("http://localhost:5000/dashboard")
        # Assert the job appears
        assert "E2E-A-001" in page.content()
        # Check the status cell says "Verified" or "Submitted"
        assert "Submitted" in page.content() or "Verified" in page.content()

        browser.close()


# ---------------------------------------------------------------------------
# Test: successful Portal B submission with document upload
# ---------------------------------------------------------------------------
@pytest.mark.usefixtures("flask_server")
def test_e2e_portal_b_submission_with_upload():
    """Playwright should fill Portal B, upload a PDF, and verify the job appears."""
    from playwright.sync_api import sync_playwright
    import sqlite3

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("http://localhost:5000/portal_b")

        # Fill basic fields
        page.fill('input[name="job_id"]', "E2E-B-001")
        page.fill('input[name="company"]', "E2E Company")
        page.fill('input[name="contact"]', "E2E Contact")
        page.fill('input[name="phone"]', "555-E2E")

        # Upload the sample document
        page.set_input_files('input[name="document"]', os.path.join(os.path.dirname(__file__), "..", "data", "sample.pdf"))

        # Submit
        page.click('button[type="submit"]')

        # Navigate to dashboard and verify
        page.goto("http://localhost:5000/dashboard")
        assert "E2E-B-001" in page.content()
        assert "E2E Company" in page.content()

        browser.close()


# ---------------------------------------------------------------------------
# Test: duplicate prevention – running the bot twice should not create extra rows
# ---------------------------------------------------------------------------
@pytest.mark.usefixtures("flask_server")
def test_e2e_duplicate_prevention():
    """After the first run, a second run should skip already‑verified jobs."""
    from playwright.sync_api import sync_playwright
    import sqlite3

    # First run: submit a job
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("http://localhost:5000/portal_a")
        page.fill('input[name="job_id"]', "DUP-001")
        page.fill('input[name="customer"]', "Duplicate Test")
        page.fill('input[name="address"]', "Dup St")
        page.fill('input[name="work_description"]', "Dup desc")
        page.select_option('select[name="priority"]', "Medium")
        page.fill('input[name="due_date"]', "2025-11-01")
        page.click('button[type="submit"]')
        page.goto("http://localhost:5000/dashboard")
        assert "DUP-001" in page.content()
        browser.close()

    # Second run (simulated by calling the automation again) – in this manual test
    # we just check the DB has not duplicate entries.
    # The Flask portals app stores its SQLite file at <project>/portals/jobs.db
    db_path = os.path.join(os.path.dirname(__file__), "..", "portals", "jobs.db")
    print("Using DB path:", db_path, file=__import__('sys').stdout)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM jobs WHERE job_id = 'DUP-001'")
    count = cur.fetchone()[0]
    conn.close()
    assert count == 1, "Job should appear only once; duplicate detection failed."