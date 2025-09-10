#!/usr/bin/env python3
"""Wrapper to run merged SDN application with venv Python that has all required packages."""

import os
import subprocess
import sys


def main():
    # Change to CML working directory
    os.chdir("/home/cdsw")
    current_dir = os.getcwd()

    # Use venv Python (which should have all our packages)
    venv_python = "/home/cdsw/.venv/bin/python"

    print(f"Starting merged SDN application from {current_dir}")
    print(f"Using Python: {venv_python}")
    
    # Set environment variables for the application
    os.environ["FLASK_ENV"] = os.environ.get("FLASK_ENV", "production")
    os.environ["USE_LLM"] = os.environ.get("USE_LLM", "true")
    os.environ["CDSW_READONLY_PORT"] = os.environ.get("CDSW_READONLY_PORT", "8090")
    os.environ["SDN_FILE_PATH"] = os.environ.get("SDN_FILE_PATH", "data_list/sdn_final.csv")
    
    print(f"Flask env: {os.environ['FLASK_ENV']}")
    print(f"LLM enabled: {os.environ['USE_LLM']}")
    print(f"Port: {os.environ['CDSW_READONLY_PORT']}")
    print(f"SDN file: {os.environ['SDN_FILE_PATH']}")

    # Run merged application with venv Python
    result = subprocess.run([venv_python, "run_merged_app.py"])
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()