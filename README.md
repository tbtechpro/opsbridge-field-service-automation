# OpsBridge – Field Service Automation Demo

## Overview
A local demonstration of transferring fictional AroFlo-style job records into two simulated client portals using Python, Playwright, Flask, and SQLite. No real client accounts or paid services are used. The portals are local simulations and the project demonstrates automation techniques rather than a live integration with a real client's field-service system.

## Quick‑start (after Python is installed)
1. **Install Python 3.11+** from <https://www.python.org/downloads/windows/> and ensure `python` is on your PATH.
2. **Create a virtual environment** (run in PowerShell):
   ```powershell
   cd C:\path\to\opsbridge_demo
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. **Install free dependencies** (once the venv is active):
   ```powershell
   pip install -r requirements.txt
   python -m playwright install chromium
   ```
4. **Run a dry‑run** (no browser launched):
   ```powershell
   python main.py --dry-run
   ```
5. **Start the Flask portals and dashboard**:
   ```powershell
   python main.py
   ```
   then open <http://localhost:5000> in a browser to access the operations dashboard.

## Project structure
```
opsbridge_demo/
├─ .gitignore            # env, venv, logs, screenshots, db
├─ README.md             # you are reading it
├─ prd.md                # product requirement document
├─ implementation_plan.md# milestone roadmap
├─ config.yaml           # portal URLs, timeouts, retry limits, sample-document path
├─ data/
│   └─ sample.pdf        # dummy upload file
├─ portals/
│   ├─ app.py            # Flask dashboard + portal simulators
│   ├─ portal_a/
│   │   └─ portal_a.html
│   └─ portal_b/
│       └─ portal_b.html
├─ engine/
│   └─ submitter.py     # Playwright automation loop
├─ tests/
│   └─ test_*.py         # pytest suite
└─ main.py               # entry point (cli)
```

## Installation
```powershell
# 1. Create a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browser (Chromium)
python -m playwright install chromium
```

## Test suite
The pytest test suite consists of several categories:

- **Portal‑client tests** (`tests/test_portals.py`): 3 tests using the Flask test client; verify form submission and dashboard display.
- **Reliability / fault‑injection tests** (`tests/test_reliability.py`): 4 tests that exercise retry logic, flag states, and duplicate‑prevention using deterministic fault‑injection flags.
- **Submitter tests** (`tests/test_submitter.py`): 3 tests using `pytest‑asyncio`; verify field mapping, duplicate‑prevention, and successful submission with mock Playwright objects.
- **End‑to‑end browser tests** (`tests/test_e2e_browser.py`): 3 tests that launch the Flask portals in a background thread and use Playwright to drive a real Chromium instance against the local portals. These tests are automatically skipped unless the environment variable `RUN_E2E=1` is set.

Running the core test suite (without `RUN_E2E=1`):
```
$env:RUN_E2E = ""
python -m pytest tests/ -v
# 10 passed, 3 skipped
```

Running the full test suite with `RUN_E2E=1` (PowerShell):
```
$env:RUN_E2E = "1"
python -m pytest tests/ -v
# 13 passed, 0 failed, 0 skipped
```

## Scope and limitations
- **Local simulations only**: The two portals (A and B) are simulated Flask web applications with static HTML forms. They do not connect to any external client system or real AroFlo account.
- **No production readiness**: This demo shows automation techniques using free, locally‑hosted tools. Production deployment, restart recovery, and full missing‑upload failure handling have not been verified.
- **Single‑threaded automation**: The engine processes one job at a time; concurrent workers are not implemented.
- **Test coverage**: The existing tests cover the implemented scenarios (form submission, retry exhaustion, duplicate‑prevention, fault‑injection) but do not cover every possible failure mode or a full missing‑upload end‑to‑end path.
- **No authentication or session handling**: Simulated portals log in instantly; real integrations would need credential management and CSRF token handling.

Future improvements may include: concurrent job processing, persistent selector configuration, enhanced error‑recovery workflows, and CI/CD integration.

## Requirements
- Python 3.11+
- `requirements.txt` (Flask, pytest, pytest-asyncio, playwright, PyYAML)
- Playwright Chromium browser installed via `python -m playwright install chromium`

## Credits
Generated as part of the OpsBridge Field Service Automation Demo project.