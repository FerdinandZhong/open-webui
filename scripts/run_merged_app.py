#!/usr/bin/env python3

import os
import subprocess
import sys

os.chdir("/home/cdsw")

# Use the local .venv that has the packages installed
venv_python = os.path.join('.venv', 'bin', 'python')

# Check if venv exists
if not os.path.exists(venv_python):
    print("Virtual environment not found. Creating it...")
    subprocess.run(['uv', 'venv'], check=True)
    print("Installing dependencies...")
    subprocess.run(['uv', 'sync'], check=True)
subprocess.run(['uv', 'sync'], check=True)

result = subprocess.run([venv_python, "run_merged_app.py"])
sys.exit(result.returncode)