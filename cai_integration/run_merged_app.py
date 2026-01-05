#!/usr/bin/env python3
"""
Run the merged application by installing dependencies for both frontend and backend,
and then starting the backend server which serves the frontend.
"""

import subprocess
import os
import sys

def run_command(command, working_dir):
    """Runs a command in a specified directory and streams the output."""
    print(f"Running command: '{command}' in '{working_dir}'")
    try:
        process = subprocess.Popen(
            command,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            text=True,
            bufsize=1
        )
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        rc = process.poll()
        if rc != 0:
            print(f"Command failed with exit code {rc}")
            sys.exit(rc)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

def main():
    """Main function to setup and run the application."""
    backend_dir = "./backend"
    frontend_dir = "."  # Assuming frontend is at the root

    # Install backend dependencies
    print("--- Installing backend dependencies ---")
    run_command("pip install -r requirements.txt", backend_dir)

    # Install frontend dependencies
    print("\n--- Installing frontend dependencies ---")
    run_command("npm install", frontend_dir)

    # Build frontend
    print("\n--- Building frontend ---")
    run_command("npm run build", frontend_dir)

    # Start the backend server
    print("\n--- Starting backend server ---")
    run_command("python -m open_webui.main", backend_dir)

if __name__ == "__main__":
    main()
