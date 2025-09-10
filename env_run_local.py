#!/usr/bin/env python3
import subprocess
import sys
import os

def run():
    # Already in root directory
    current_dir = os.getcwd()
    
    # Check if uv virtual environment exists
    venv_python = os.path.join('.venv', 'bin', 'python')
    
    if not os.path.exists(venv_python):
        print("Virtual environment not found. Creating it...")
        subprocess.run(['uv', 'venv'], check=True)
        print("Installing dependencies...")
        subprocess.run(['uv', 'sync'], check=True)
    
    print(f"Starting merged SDN application from {current_dir}")
    print(f"Using Python: {venv_python}")
    subprocess.run(['uv', 'sync'], check=True)
    # Run merged Flask app with virtual environment
    subprocess.run([venv_python, 'run_merged_app.py'])

if __name__ == "__main__":
    run()