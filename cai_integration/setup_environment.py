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


def main():
    """Setup Python environment using uv."""
    print("=" * 50)
    print("Setting up Python Environment with UV")
    print("=" * 50)
    
    # Change to project directory
    os.chdir("/home/cdsw")
    print(f"Working directory: {os.getcwd()}")
    
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
    if not run_command("uv venv"):
        print("❌ Failed to create virtual environment")
        sys.exit(1)
    
    # Install dependencies
    print("\n📦 Installing dependencies...")
    backend_dir = os.path.join(os.getcwd(), "backend")
    if not run_command("uv pip install -e .", cwd=backend_dir):
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