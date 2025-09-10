#!/usr/bin/env python3
"""Wrapper to run Flask UI with venv Python that has all required packages."""

import os
import subprocess
import sys


def main():
    # Change to CML working directory
    os.chdir("/home/cdsw")
    current_dir = os.getcwd()

    # Use venv Python (which should have all our packages)
    venv_python = "/home/cdsw/.venv/bin/python"

    print(f"Starting Flask UI from {current_dir}")
    print(f"Using Python: {venv_python}")
    
    # Set environment variables for Flask
    os.environ["FLASK_APP"] = os.environ.get("FLASK_APP", "flask_ui.app.app")
    os.environ["FLASK_ENV"] = os.environ.get("FLASK_ENV", "production")
    
    print(f"Flask app: {os.environ['FLASK_APP']}")
    print(f"Flask env: {os.environ['FLASK_ENV']}")

    # Run Flask UI script with venv Python
    result = subprocess.run([venv_python, "flask_ui/run.py"])
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()