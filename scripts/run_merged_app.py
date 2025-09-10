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

# Pass through all environment variables including OPENAI_API_KEY
env = os.environ.copy()
env['SDN_FILE_PATH'] = '/home/cdsw/data_list/sdn_final.csv'

print(f"DEBUG WRAPPER: OPENAI_API_KEY: {'*' * 10 if env.get('OPENAI_API_KEY') else 'NOT SET'}")
print(f"DEBUG WRAPPER: USE_LLM: {env.get('USE_LLM', 'NOT SET')}")
print(f"DEBUG WRAPPER: SDN_FILE_PATH: {env.get('SDN_FILE_PATH', 'NOT SET')}")

result = subprocess.run([venv_python, "run_merged_app.py"], env=env)
sys.exit(result.returncode)