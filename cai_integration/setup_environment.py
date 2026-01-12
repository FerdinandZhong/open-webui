#!/usr/bin/env python3
"""Simple environment setup script that only uses uv to install dependencies."""

import os
import subprocess
import sys


def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            check=True,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False


def is_venv_ready(venv_dir):
    """Check if virtual environment exists and is properly configured."""
    if not os.path.exists(venv_dir):
        return False

    # Check if python executable exists in venv
    python_exe = os.path.join(venv_dir, "bin", "python")
    if not os.path.exists(python_exe):
        return False

    # Check if pyvenv.cfg exists (indicator of valid venv)
    pyvenv_cfg = os.path.join(venv_dir, "pyvenv.cfg")
    if not os.path.exists(pyvenv_cfg):
        return False

    return True


def main():
    """Setup Python environment using uv."""
    print("=" * 50)
    print("Setting up Python Environment with UV")
    print("=" * 50)

    # List files in the project directory for debugging
    print("\n📂 Listing files in the project directory...")
    run_command("ls -lR /home/cdsw")

    # Change to project directory
    os.chdir("/home/cdsw")
    print(f"Working directory: {os.getcwd()}")

    venv_dir = "/home/cdsw/.venv"
    backend_dir = os.path.join(os.getcwd(), "backend")

    # Check if environment is already properly configured
    if is_venv_ready(venv_dir):
        print(f"\n✅ Virtual environment already exists and is configured at: {venv_dir}")
        print("   Skipping venv creation. Verifying dependencies are still installed...")

        # Still verify dependencies to ensure they're usable
        if not run_command("uv pip list"):
            print("⚠️  Could not verify dependencies, will reinstall...")
        else:
            print("✅ Dependencies verified successfully!")
            print("\n" + "=" * 50)
            print("✅ Environment already ready - skipped setup!")
            print("=" * 50)
            return

    # Install uv first
    print("\n⬇️  Installing uv...")
    if not run_command("pip install uv"):
        print("❌ Failed to install uv")
        sys.exit(1)

    # Verify uv installation
    print("\n🔍 Verifying uv installation...")
    if not run_command("uv --version"):
        print("❌ Failed to verify uv installation")
        sys.exit(1)

    # Create virtual environment with uv
    print("\n🐍 Creating virtual environment...")
    if os.path.exists(venv_dir):
        print(f"Virtual environment exists but not fully configured. Removing and recreating...")
        run_command(f"rm -rf {venv_dir}")

    if not run_command(f"uv venv {venv_dir}"):
        print("❌ Failed to create virtual environment")
        sys.exit(1)

    # Install dependencies
    print("\n📦 Installing dependencies...")
    if not run_command("uv pip install -r requirements.txt", cwd=backend_dir):
        print("❌ Failed to install dependencies")
        sys.exit(1)

    # Verify installation
    print("\n✅ Verifying installation...")
    if not run_command("uv pip list"):
        print("❌ Failed to verify installation")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("✅ Environment setup completed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    main()