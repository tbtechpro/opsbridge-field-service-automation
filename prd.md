# OpsBridge – Field Service Automation Demo (PRD)

## Problem statement
Field‑service companies using AroFlo need job records transferred into client portals that have no API. The current manual process is about 100 entries per day, error‑prone, and consumes staff time. A local demo must prove the ability to read CSV job data, populate web‑form UIs, upload supporting documents, update job status, and surface diagnostics – all without writing to a production system.

## Target users
- Hiring managers assessing an AI Automation Specialist candidate.
- Teammates who want to see the automation logic.
- Ops staff who will later maintain the production version.

## User stories
1. As a user I can place a CSV of job records into a known folder and the system reads them.
2. As a user I see each job validated (required fields, data types).
3. As a user I click “Run” and the system automates form fills in two local portal simulators.
4. As a user I receive a screenshot and log if a submission fails.
5. As a user I can restart the program and it skips already‑submitted job IDs.
6. As a user I can toggle a dry‑run flag that records intentions without touching the browser.
7. As a user I visit an operations dashboard that shows job status, retries, and failures.
8. As a user I see a secondary prototype that books an appointment using local voice‑input (no paid API).

## Functional requirements
- FR‑1: Import CSV and map columns to job fields (customer, address, asset, description, due date).
- FR‑2: Validate each record – required fields present, date formats, postcode length.
- FR‑3: Submit each valid job to **Portal A** (simple form: name, address, postcode, submit).
- FR‑4: Submit each valid job to **Portal B** (different schema: company name, contact, phone, upload field).
- FR‑5: Upload a sample PDF/IMG to Portal B’s upload field.
- FR‑6: After each submission, update the job’s status in SQLite (Pending → Submitted → Verified/Failed).
- FR‑7: Prevent duplicate submissions using the job’s unique ID; persist this state across restarts.
- FR‑8: Implement per‑job timeouts (default 30 s) and limited retries (max 3).
- FR‑9: On failure, capture a PNG screenshot and write a structured log entry.
- FR‑10: Provide a dry‑run mode (`--dry-run`) that logs intentions but never launches the browser.
- FR‑11: Include safe fault‑injection tests that can simulate a slow portal or a missing field without real web traffic.
- FR‑12: Offer an operations dashboard (Flask at `http://localhost:5000`) showing job queue, status counts, retry attempts, and recent logs.
- FR‑13: Provide a secondary “appointment‑booking” prototype that uses local speech‑to‑text (Python `speech_recognition` offline) to fill a simple form – no external API cost.
- FR‑14: Architecture must allow adding Portal C–E without rewriting the core engine (portal‑config driven).

## Non‑functional requirements
- Runs on Windows 10/11 with Python 3.11+.
- No external paid services (free local simulators only).
- Deterministic test outcomes (screenshots/logs deterministic for given input).
- Test coverage ≥ 80 % of branches (pytest).
- Memory footprint < 200 MB for 100 jobs.
- All secrets externalised via environment variables or a `.env` file not committed.

## Out‑of‑scope
- Real AroFlo API integration.
- Production deployment (Docker, CI/CD, hosting).
- Real voice‑API (Twilio, AWS Polly).
- Multi‑user authentication or role‑based access.
- Visual UI polish – the dashboard is functional, not pixel‑perfect.
- Concurrent multi‑threaded browser instances (single‑threaded demo).

## Risks & assumptions
- **Risk:** Portal UI changes break selectors.
  - *Mitigation:* Use Playwright `wait_for_selector` + text‑based fallback; document selector strategy.
- **Assumption:** The two simulated portals will remain static for the demo duration.
- **Assumption:** CSV files will have a header row and consistent column names.

## Security considerations
- No passwords or tokens stored in code – use `.env` (git‑ignored).
- No external network traffic except to `localhost` simulators.
- All file paths are relative to the project folder; no access to system‑wide directories.
- SQLite database file is local and not exposed over the network.

## Success metrics
- 100 % of valid CSV records are processed without manual intervention.
- Duplicate‑prevention works across restarts (0 duplicate submissions in test runs).
- > 95 % of submissions complete within the timeout + retry budget.
- Dashboard shows correct status for each job (Submitted/Verified/Failed).
- Test suite passes ≥ 80 % of the defined test cases.

## Acceptance criteria
Each FR‑1‒FR‑14 is “Done” when the associated pytest test passes, the demo can be run from a fresh Windows command prompt, and a short video (≤ 5 min) demonstrates the end‑to‑end flow.