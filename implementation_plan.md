# OpsBridge – Implementation Roadmap (Milestones)

## Milestone 1 – Project foundation
- Create the repository structure.
- Save the approved PRD, implementation plan and `AGENTS.md`.
- Create the virtual environment and install only the necessary free dependencies.
- Document the exact Windows PowerShell commands required to run the project.
- Confirm that the environment works before proceeding.

**Deliverables**
- `opsbridge_demo/` folder with `.gitignore`, `README.md`, `prd.md`, `implementation_plan.md`, `AGENTS.md`.
- `config.yaml` placeholder (empty or skeleton).
- `data/` folder (empty, will hold `jobs.csv` later).
- Verify Python version and `pip` after installation.

**Definition of Done**
- Repo folder exists, required markdown files present.
- PowerShell command `python -c "import sys; print(sys.version)"` returns a version ≥ 3.11.
- `venv` can be created and activated.
- `pip list` shows no errors (packages not yet installed).

---

## Milestone 2 – Simulated portals
- Build Portal A and Portal B.
- Add SQLite persistence and a page for viewing submitted jobs.
- Test each portal manually before writing browser automation.

**Deliverables**
- `portals/app.py` Flask app with two routes `/portal_a` and `/portal_b`.
- Simple HTML forms reflecting the schemas described in the PRD.
- In‑memory SQLite DB (or file‑based) storing submitted job records.
- Manual test: submit a job via each portal and see data echoed back.

**Definition of Done**
- Flask app starts without errors (`python portals/app.py`).
- Navigating to `http://localhost:5001/portal_a` shows a form; submitting posts data and returns success.
- Same for Portal B, including a file upload field that accepts a dummy file.

---

## Milestone 3 – First working browser automation
- Build the Playwright bot for Portal A.
- Process one sample job and verify its submission.
- Add CSV input validation, clear logging and dry-run mode.
- Write and run the initial tests.

**Deliverables**
- `engine/importer.py` reads `data/jobs.csv`, normalises column names, validates required fields.
- `engine/submitter.py` launches Playwright, navigates to `http://localhost:5001/portal_a`, fills fields, clicks Submit, captures screenshot on failure.
- `main.py` CLI entry point with `--dry-run` flag.
- `tests/test_importer.py` covering valid row, missing field, bad postcode.
- Running `python main.py --dry-run` logs each job intention without launching a browser.

**Definition of Done**
- `pytest -q` runs all importer tests and they pass.
- `python main.py --dry-run` produces console output listing each job and does NOT open a browser window.
- Manual run (without flag) on a single job results in browser opening, form fields populated, and a “Submitted” log entry.

---

## Milestone 4 – Reliability and duplicate prevention
- Persist job‑processing state.
- Prevent duplicate submissions, including after a program restart.
- Add explicit timeouts, bounded retries, failure screenshots and safe recovery.
- Test uncertain outcomes and partial failures.

**Deliverables**
- `db.py` with functions `init_db()`, `upsert_job(job)`, `get_pending_jobs()`, `mark_submitted(job_id)`.
- UNIQUE constraint on `jobs.job_id`.
- `engine/submitter.py` incorporates timeout (30 s), max_retries (3), exponential back‑off, screenshot on failure (`screenshots/jobid_portalX.png`).
- Fault‑injection helper (`fault_injection.py`) that can add a configurable delay before success.
- Tests for duplicate detection across runs.

**Definition of Done**
- `upsert_job` inserts a new job or silently ignores a duplicate.
- Running the engine twice on the same CSV results in no extra `submissions` rows.
- When a portal does not respond within 30 s, the job is retried up to 3 times then marked **Failed**; a screenshot exists in `screenshots/`.
- Fault‑injection test (T4) passes: after 3 retries job fails, log records timeout.

---

## Milestone 5 – Portal B and document uploads
- Add a reusable portal‑adapter design.
- Map the input data to Portal B's different form fields.
- Upload the sample document and verify the result.
- Confirm that successful jobs are not duplicated when the bot is rerun.

**Deliverables**
- `portals/portal_b/routes.py` HTML form with fields *company, contact, phone* + `<input type="file">`.
- POST endpoint stores uploaded filename in a temp folder and returns `{ success: true, saved_name: "..." }`.
- `engine/submitter.py` includes portal‑specific field mapping (read from `config.yaml` or a mapping dict).
- Sample PDF `data/sample.pdf` placed in the repo.
- Test confirming upload success and that subsequent runs skip the job.

**Definition of Done**
- Playwright can fill Portal B fields and upload `data/sample.pdf`; the simulator returns success.
- Engine updates DB status to **Verified** for Portal B submissions.
- Re‑running the engine does not create duplicate submission rows for the same job.

---

## Milestone 6 – Monitoring and fault testing
- Add a simple operations dashboard showing successful, failed and pending jobs.
- Test invalid data, portal unavailability, upload failures, timeouts, retry exhaustion and partial success.
- Run the full automated test suite.

**Deliverables**
- `app.py` Flask dashboard at `http://localhost:5000` showing job queue, status counts, recent logs, thumbnail links to screenshots.
- pytest suite covering all acceptance criteria (T1‑T11).
- CI‑style local test run: `pytest -q --cov=engine`.

**Definition of Done**
- Dashboard reflects the current DB state (counts of Pending, Submitted, Verified, Failed).
- All test cases T1‑T11 pass (or are marked as known limitations).
- `pytest -q --cov=engine` reports ≥ 80 % line coverage for the engine module.

---

## Milestone 7 – Portfolio preparation
- Complete the README, architecture diagram and test documentation.
- Include setup instructions, screenshots and demonstration steps.
- Prepare a short screen‑recording outline and honest production‑readiness limitations.

**Deliverables**
- Updated `README.md` with full installation, running demos, and known limitations.
- `docs/ARCHITECTURE.md` containing the Mermaid component diagram and data‑flow description.
- Short video (≤ 5 min) walkthrough of the end‑to‑end flow.
- GitHub repository with a clean `main` branch and all milestone folders committed.

**Definition of Done**
- README, architecture diagram, and test docs are present and accurate.
- Video uploaded to an unlisted Loom/YouTube link and referenced in README.
- Repository passes `git status` clean (no untracked sensitive files).

---
*Each milestone builds on the previous one. The appointment‑booking and voice‑agent features are deferred until after Milestone 6, when the core browser automation is reliable.*