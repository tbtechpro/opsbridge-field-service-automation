#!/usr/bin/env python
"""OpsBridge – Field Service Automation Demo (Milestone 3)

Usage (from the project root):
    python main.py                  # start the Flask portals & dashboard
    python main.py --run            # run the Playwright automation once
    python main.py --dry-run        # log jobs without touching the browser

The script will activate the virtual‑env (if present) and use the
free dependencies listed in requirements.txt.
"""

import sys
import os

# Ensure the project root is on the path so that `engine`, `portals`, `db` etc. are importable
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

def _ensure_venv():
    """If a venv folder exists, add its site‑packages to the path."""
    venv_path = os.path.join(_PROJECT_ROOT, "venv")
    if os.path.isdir(venv_path):
        site_packages = os.path.join(venv_path, "Lib", "site-packages")
        if site_packages not in sys.path:
            sys.path.insert(0, site_packages)

_ensure_venv()

def run_automation():
    """Run the Playwright submitter once."""
    from engine.submitter import run_automation as _run
    import asyncio
    asyncio.run(_run())

def run_flask():
    """Start the Flask portals & dashboard (blocking)."""
    os.chdir(_PROJECT_ROOT)
    from portals.app import app
    app.run(debug=True, port=5000)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OpsBridge demo controller")
    parser.add_argument("--run", action="store_true", help="Run the Playwright automation once")
    parser.add_argument("--dry-run", action="store_true", help="Log jobs without launching a browser")
    parser.add_argument("--flask", action="store_true", help="Start the Flask portals and dashboard")
    args = parser.parse_args()

    if args.flask or not any([args.run, args.dry_run]):
        # Default behaviour: start Flask (so the portals are available for manual testing)
        run_flask()
    elif args.run:
        run_automation()
    elif args.dry_run:
        logger = __import__("logging").getLogger("opsbridge")
        logger.info("Dry‑run mode – no browser will be launched.")
        # still list pending jobs for visibility
        from engine.submitter import get_pending_jobs as _get
        jobs = _get()
        if jobs:
            for j in jobs:
                logger.info("Pending job: %s (customer=%s portal=%s)", j["job_id"], j["customer"], j.get("portal"))
        else:
            logger.info("No pending jobs found.")