import os
import tempfile

import pytest

# Import the Flask app (not the test client) so we can create our own client per test
from portals.app import app  # noqa: F401


@pytest.fixture(scope="function")
def flask_app():
    """Provide a fresh Flask app with an isolated test database."""
    import portals.app as app_mod

    # Use a temporary database file so tests don't interfere with the demo DB
    TEST_DB = os.path.join(tempfile.gettempdir(), "opsbridge_test_demo.db")
    app_mod.DB_PATH = TEST_DB
    # Re‑initialise with fresh schema
    app_mod.init_db()

    # Yield the Flask app instance; tests will create their own test client
    yield app_mod.app

    # Clean‑up: remove the temp DB after the test
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def portal_a_post(client, data):
    """Helper to POST to portal A."""
    return client.post("/portal_a", data=data)


def test_portal_a_submission(flask_app):
    """Portal A should accept valid data and store a job record."""
    with flask_app.test_client() as client:
        response = portal_a_post(client, {
            "job_id": "JA1001",
            "customer": "Acme Corp",
            "address": "123 Maple St",
            "work_description": "Roof repair",
            "priority": "High",
            "due_date": "2025-12-01",
        })
        assert response.status_code == 302  # redirect to dashboard

        # Follow redirect and check dashboard
        resp = client.get("/dashboard", follow_redirects=True)
        assert resp.status_code == 200
        text = resp.get_data(as_text=True)
        assert "JA1001" in text
        assert "Acme Corp" in text


def test_portal_b_submission_without_file(flask_app):
    """Portal B should accept the basic form fields (file upload optional)."""
    with flask_app.test_client() as client:
        response = client.post(
            "/portal_b",
            data={
                "job_id": "JB2002",
                "company": "Beta Ltd",
                "contact": "Jane Doe",
                "phone": "555-1234",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302  # redirect

        # Follow redirect and check dashboard
        resp = client.get("/dashboard", follow_redirects=True)
        assert resp.status_code == 200
        text = resp.get_data(as_text=True)
        assert "JB2002" in text
        assert "Beta Ltd" in text


def test_dashboard_lists_all_jobs(flask_app):
    """Dashboard should display jobs from both portals."""
    with flask_app.test_client() as client:
        # First submit a job via portal A
        response = portal_a_post(client, {
            "job_id": "JA3003",
            "customer": "Gamma LLC",
            "address": "456 Oak Ave",
            "work_description": "HVAC service",
            "priority": "Medium",
            "due_date": "2025-11-15",
        })
        assert response.status_code == 302

        # Follow redirects to see the dashboard
        resp = client.get("/dashboard", follow_redirects=True)
        assert resp.status_code == 200
        text = resp.get_data(as_text=True)
        assert "JA3003" in text
        assert "Gamma LLC" in text