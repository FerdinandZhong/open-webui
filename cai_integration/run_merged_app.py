#!/usr/bin/env python3
"""
Run the merged application by installing dependencies for both frontend and backend,
and then starting the backend server which serves the frontend.
"""

import subprocess
import os
import sys

VENV_DIR = "/home/cdsw/.venv"
BACKEND_DIR = "/home/cdsw/backend"


def run_command(command, working_dir, check=True):
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
        if rc != 0 and check:
            print(f"Command failed with exit code {rc}")
            sys.exit(rc)
        return rc == 0
    except Exception as e:
        print(f"An error occurred: {e}")
        if check:
            sys.exit(1)
        return False


def is_venv_ready():
    """Check if virtual environment exists and is properly configured."""
    python_exe = os.path.join(VENV_DIR, "bin", "python")
    return os.path.exists(python_exe)


def setup_environment():
    """Setup Python environment using uv if not already configured."""
    print("\n" + "=" * 50)
    print("🔧 Setting up Python Environment")
    print("=" * 50)

    os.chdir("/home/cdsw")

    # Install uv first
    print("\n⬇️  Installing uv...")
    if not run_command("pip install uv", "/home/cdsw", check=False):
        print("❌ Failed to install uv")
        sys.exit(1)

    # Create virtual environment with uv
    print("\n🐍 Creating virtual environment...")
    if os.path.exists(VENV_DIR):
        run_command(f"rm -rf {VENV_DIR}", "/home/cdsw", check=False)

    if not run_command(f"uv venv {VENV_DIR}", "/home/cdsw", check=False):
        print("❌ Failed to create virtual environment")
        sys.exit(1)

    # Install dependencies
    print("\n📦 Installing dependencies...")
    if not run_command("uv pip install -r requirements.txt", BACKEND_DIR, check=False):
        print("❌ Failed to install dependencies")
        sys.exit(1)

    print("\n✅ Environment setup completed!")


def main():
    """Main function to setup and run the application."""
    # Check if venv exists, create if not
    if not is_venv_ready():
        print("⚠️  Virtual environment not found, setting up...")
        setup_environment()
    else:
        print("✅ Virtual environment found")

    # Start the backend server
    print("\n--- Starting backend server ---")
    port = os.environ.get("CDSW_APP_PORT", "8090")
    command = f"{VENV_DIR}/bin/python -m uvicorn open_webui.main:app --host 127.0.0.1 --port {port}"
    run_command(command, BACKEND_DIR)

if __name__ == "__main__":
    main()
