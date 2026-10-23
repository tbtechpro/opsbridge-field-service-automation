import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import yaml
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from db import get_pending_jobs, update_job_status, record_attempt, record_attempt

# ---------------------------------------------------------------------------
# Fault‑injection flags (can be set by tests to simulate failures)
# ---------------------------------------------------------------------------
FAULT_INJECT_TIMEOUT = False
FAULT_INJECT_UPLOAD_MISSING = False

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logger = logging.getLogger("opsbridge.submitter")
handler = logging.FileHandler(os.path.join(os.path.dirname(__file__), "..", "logs", "opsbridge.log"))
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

PORTALS = CONFIG.get("portals", [])
TIMEOUT_SECONDS = CONFIG.get("timeout_seconds", 30)
MAX_RETRIES = CONFIG.get("max_retries", 3)

SAMPLE_DOCUMENT = CONFIG.get("sample_document", os.path.join(os.path.dirname(__file__), "..", "data", "sample.pdf"))

# ---------------------------------------------------------------------------
# Helper: map a job record to form fields for a given portal
# ---------------------------------------------------------------------------
def map_fields(job, portal_config):
    """Return a dict {field_name: value} ready for Playwright fill()."""
    fields = {}
    field_mapping = portal_config.get("fields", {})
    for job_field, form_field in field_mapping.items():
        if job_field in job:
            fields[form_field] = str(job[job_field])
    # Ensure required identifiers are present
    fields.setdefault("job_id", str(job["job_id"]))
    return fields


# ---------------------------------------------------------------------------
# Core automation for a single job on a single portal
# ---------------------------------------------------------------------------
async def submit_job(job, portal_config):
    """Attempt to submit *job* to the given *portal_config*.

    Returns a dict with keys:
      - "status": "ok" | "retryable" | "exhausted"
      - "message": human‑readable description
    """
    portal_name = portal_config.get("name", "unknown")
    url = portal_config["url"]
    field_mapping = map_fields(job, portal_config)
    upload_field = portal_config.get("upload_field")
    upload_path = portal_config.get("upload_path")

    retry_count = 0
    while retry_count <= MAX_RETRIES:
        record_attempt(job["job_id"], portal_name)
        browser = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.goto(url, wait_until="networkidle")

                # ----- Fault injection (testing only) -----
                if FAULT_INJECT_TIMEOUT:
                    raise PlaywrightTimeoutError("forced timeout for testing")

                # ----- Fill form fields -----
                for form_name, value in field_mapping.items():
                    if form_name == "job_id":
                        # job_id is usually a hidden or input field; fill it
                        await page.fill('input[name="job_id"]', value)
                    else:
                        await page.fill('input[name="' + form_name + '"]', value)

                # ----- Upload document for Portal B -----
                if upload_field and upload_path and os.path.exists(upload_path):
                    # Playwright's set_input_files accepts a file path
                    await page.set_input_files('input[name="' + upload_field + '"]', str(Path(upload_path).resolve()))

                # ----- Submit the form -----
                await page.click('button[type="submit"]')

                # ----- Wait for a success indicator -----
                try:
                    # Portal A: look for a success text or URL change
                    await page.wait_for_selector('text=Submitted', timeout=TIMEOUT_SECONDS * 1000)
                    success = True
                except PlaywrightTimeoutError:
                    # Portal B may show a different message; try generic success
                    try:
                        await page.wait_for_selector('text=Success', timeout=TIMEOUT_SECONDS * 1000)
                        success = True
                    except PlaywrightTimeoutError:
                        success = False

                if success:
                    # Persist verified status
                    update_job_status(job["job_id"], "Verified", portal=portal_name)
                    logger.info("Job %s submitted successfully to portal %s", job["job_id"], portal_name)
                    await context.close()
                    await browser.close()
                    return {"status": "ok", "message": f"Job {job['job_id']} submitted to {portal_name}"}
                else:
                    # Treat as failure – will retry
                    raise Exception("No success indicator observed")

        except PlaywrightTimeoutError as e:
            retry_count += 1
            logger.warning(
                "Timeout attempting job %s on portal %s (attempt %d/%d): %s",
                job["job_id"],
                portal_name,
                retry_count,
                MAX_RETRIES,
                e,
            )
            # Capture screenshot on timeout
            if browser:
                try:
                    ss_path = os.path.join(
                        os.path.dirname(__file__), "..", "screenshots", f"{job['job_id']}_{portal_name}_timeout.png"
                    )
                    await browser.contexts[0].screenshot(path=ss_path)
                    logger.info("Screenshot saved to %s", ss_path)
                except Exception:
                    pass
            if retry_count <= MAX_RETRIES:
                # exponential back‑off
                await asyncio.sleep(2 ** retry_count)
                continue
            else:
                update_job_status(job["job_id"], "Failed", portal=portal_name)
                return {
                    "status": "exhausted",
                    "message": f"Job {job['job_id']} failed after {MAX_RETRIES} retries on {portal_name}",
                }

        except Exception as e:
            retry_count += 1
            logger.error(
                "Error attempting job %s on portal %s (attempt %d/%d): %s",
                job["job_id"],
                portal_name,
                retry_count,
                MAX_RETRIES,
                e,
            )
            # Capture screenshot on unexpected error
            if browser:
                try:
                    ss_path = os.path.join(
                        os.path.dirname(__file__), "..", "screenshots", f"{job['job_id']}_{portal_name}_error.png"
                    )
                    await browser.contexts[0].screenshot(path=ss_path)
                    logger.info("Screenshot saved to %s", ss_path)
                except Exception:
                    pass
            if retry_count <= MAX_RETRIES:
                await asyncio.sleep(2 ** retry_count)
                continue
            else:
                update_job_status(job["job_id"], "Failed", portal=portal_name)
                return {
                    "status": "exhausted",
                    "message": f"Job {job['job_id']} failed after {MAX_RETRIES} retries on {portal_name}",
                }

    # Should not reach here, but just in case
    update_job_status(job["job_id"], "Failed", portal=portal_name)
    return {"status": "exhausted", "message": f"Job {job['job_id']} exhausted on {portal_name}"}


# ---------------------------------------------------------------------------
# Main entry point: process all pending jobs across all portals
# ---------------------------------------------------------------------------
async def run_automation():
    """Iterate over pending jobs and submit each to every configured portal."""
    # Ensure directories exist
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "screenshots"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "logs"), exist_ok=True)

    jobs = get_pending_jobs()
    if not jobs:
        logger.info("No pending jobs found – automation complete.")
        return

    logger.info("Found %d pending job(s); starting automation.", len(jobs))

    for job in jobs:
        job_id = job["job_id"]
        logger.info("Processing job %s ...", job_id)
        for portal_config in PORTALS:
            # Duplicate‑prevention: if the job already has a 'Verified' status for this portal, skip
            # (the DB query already excludes 'Verified', but we double‑check here)
            existing = next(
                (j for j in jobs if j["job_id"] == job_id and j.get("portal") == portal_config.get("name") and j["status"] == "Verified"),
                None,
            )
            if existing:
                logger.info("Job %s already verified for portal %s – skipping.", job_id, portal_config.get("name"))
                continue

            result = await submit_job(job, portal_config)
            logger.info("Result for %s → %s", job_id, result["message"])
            # Small pause between portals to avoid overwhelming the local server
            await asyncio.sleep(1)

    logger.info("Automation run finished.")


# ---------------------------------------------------------------------------
# Allow running as a script:  python -m engine.submitter
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="OpsBridge browser‑automation runner")
    parser.add_argument("--dry-run", action="store_true", help="Log intended jobs without launching browsers")
    args = parser.parse_args()

    if args.dry_run:
        jobs = __import__("opsbridge_demo.db").get_pending_jobs() if False else []
        logger.info("Dry‑run mode: would process %d pending jobs", len(jobs))
    else:
        asyncio.run(run_automation())