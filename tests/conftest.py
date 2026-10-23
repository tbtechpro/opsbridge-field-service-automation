import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path so that `engine.*` modules are importable
_project = Path(__file__).parent.parent
if str(_project) not in sys.path:
    sys.path.insert(0, str(_project))

# Ensure the logs directory exists so that submitter’s FileHandler can open it
os.makedirs(os.path.join(_project, "logs"), exist_ok=True)