#!/usr/bin/env python3
"""Wrapper to run SDN API with venv Python that has all required packages."""

import os
import subprocess
import sys


def main():
    # Change to CML working directory
    os.chdir("/home/cdsw")
    current_dir = os.getcwd()

    # Use venv Python (which should have all our packages)
    venv_python = "/home/cdsw/.venv/bin/python"

    print(f"Starting SDN API from {current_dir}")
    print(f"Using Python: {venv_python}")
    
    # Set environment variables for the API
    os.environ["API_HOST"] = os.environ.get("API_HOST", "0.0.0.0")
    os.environ["API_PORT"] = os.environ.get("API_PORT", "8000")
    
    print(f"API will run on {os.environ['API_HOST']}:{os.environ['API_PORT']}")

    # Run SDN API script with venv Python
    result = subprocess.run([venv_python, "run_api.py"])
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()