#!/usr/bin/env python
"""Wrapper script to capture pip install errors with detailed logging."""
import json
import os
import subprocess
import sys
from pathlib import Path

# Try multiple log paths for different build environments
LOG_PATHS = [
    Path("/Users/skupr/src/aggregate/ewah-bool-utils-feedstock/.cursor/debug.log"),
    Path(os.path.join(os.path.dirname(__file__), "..", "..", ".cursor", "debug.log")),
    Path(os.path.expanduser("~/.cursor/debug.log")),
    Path(os.path.join(os.getcwd(), "debug.log")),
]

LOG_PATH = None
for path in LOG_PATHS:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Test write
        with open(path, "a") as f:
            f.write("")
        LOG_PATH = path
        break
    except (OSError, PermissionError):
        continue

def log_entry(data):
    """Write a log entry in NDJSON format."""
    entry = {
        "sessionId": "debug-session",
        "runId": os.environ.get("RUN_ID", "run1"),
        "timestamp": int(__import__("time").time() * 1000),
        **data
    }
    if LOG_PATH:
        try:
            with open(LOG_PATH, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except (OSError, PermissionError):
            pass
    # Also print critical errors to stderr for visibility
    if data.get("message") in ["pip install completed", "Exception during pip install", "stderr_full", "stdout_full"]:
        sys.stderr.write(f"\n[DEBUG] {data.get('message')}: {json.dumps(data.get('data', {}), indent=2)}\n")

# Print startup message to confirm script is running
sys.stderr.write("\n[DEBUG] Build wrapper script started\n")
sys.stderr.write(f"[DEBUG] Python: {sys.executable}\n")
sys.stderr.write(f"[DEBUG] CWD: {os.getcwd()}\n")
sys.stderr.write(f"[DEBUG] Log path: {LOG_PATH}\n\n")

# #region agent log
log_entry({
    "location": "build_with_logging.py:entry",
    "message": "Build wrapper started",
    "data": {
        "python_version": sys.version,
        "python_executable": sys.executable,
        "cwd": os.getcwd(),
        "args": sys.argv,
        "env_python": os.environ.get("PYTHON", "not set"),
        "log_path": str(LOG_PATH) if LOG_PATH else "none",
        "hypothesisId": "A,B,C,D,E"
    }
})
# #endregion

# Check if source directory exists
src_dir = os.getcwd()
# #region agent log
log_entry({
    "location": "build_with_logging.py:check_source",
    "message": "Checking source directory",
    "data": {
        "src_dir": src_dir,
        "exists": os.path.exists(src_dir),
        "files": os.listdir(src_dir) if os.path.exists(src_dir) else [],
        "has_pyproject": os.path.exists(os.path.join(src_dir, "pyproject.toml")),
        "hypothesisId": "C,D"
    }
})
# #endregion

# Check pyproject.toml if it exists
pyproject_path = os.path.join(src_dir, "pyproject.toml")
if os.path.exists(pyproject_path):
    # #region agent log
    with open(pyproject_path, "r") as f:
        pyproject_content = f.read()
    log_entry({
        "location": "build_with_logging.py:read_pyproject",
        "message": "Read pyproject.toml",
        "data": {
            "content": pyproject_content[:1000],  # First 1000 chars
            "length": len(pyproject_content),
            "hypothesisId": "C"
        }
    })
    # #endregion

# Get Python executable
python_exe = os.environ.get("PYTHON", sys.executable)
# #region agent log
log_entry({
    "location": "build_with_logging.py:before_pip",
    "message": "About to run pip install",
    "data": {
        "python_exe": python_exe,
        "command": [python_exe, "-m", "pip", "install", ".", "-vv", "--no-deps", "--no-build-isolation"],
        "hypothesisId": "A,B,D"
    }
})
# #endregion

# Run pip install and capture all output
try:
    result = subprocess.run(
        [python_exe, "-m", "pip", "install", ".", "-vv", "--no-deps", "--no-build-isolation"],
        cwd=src_dir,
        capture_output=True,
        text=True,
        check=False
    )
    
    # #region agent log
    log_entry({
        "location": "build_with_logging.py:after_pip",
        "message": "pip install completed",
        "data": {
            "returncode": result.returncode,
            "stdout_length": len(result.stdout),
            "stderr_length": len(result.stderr),
            "stdout_preview": result.stdout[-2000:] if result.stdout else "",  # Last 2000 chars
            "stderr_preview": result.stderr[-2000:] if result.stderr else "",  # Last 2000 chars
            "hypothesisId": "A,B,C,D,E"
        }
    })
    # #endregion
    
    # Also log full stderr if it exists (this is where the real error usually is)
    if result.stderr:
        # #region agent log
        log_entry({
            "location": "build_with_logging.py:stderr_full",
            "message": "Full stderr output",
            "data": {
                "stderr": result.stderr,
                "hypothesisId": "A,B,C,D,E"
            }
        })
        # #endregion
    
    # Log full stdout as well (sometimes errors are in stdout)
    if result.stdout:
        # #region agent log
        log_entry({
            "location": "build_with_logging.py:stdout_full",
            "message": "Full stdout output",
            "data": {
                "stdout": result.stdout,
                "hypothesisId": "A,B,C,D,E"
            }
        })
        # #endregion
    
    # Print output to maintain normal behavior
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    
    sys.exit(result.returncode)
    
except Exception as e:
    # #region agent log
    log_entry({
        "location": "build_with_logging.py:exception",
        "message": "Exception during pip install",
        "data": {
            "exception_type": type(e).__name__,
            "exception_message": str(e),
            "hypothesisId": "D,E"
        }
    })
    # #endregion
    raise

