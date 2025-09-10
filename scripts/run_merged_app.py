#!/usr/bin/env python3

import os
import subprocess
import sys

os.chdir("/home/cdsw")
result = subprocess.run(["/home/cdsw/.venv/bin/python", "run_merged_app.py"])
sys.exit(result.returncode)