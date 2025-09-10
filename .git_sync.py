#!/usr/bin/env python3
"""
Git sync script for CML to pull latest changes from the repository.
This script runs as a CML job to update the project code.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a shell command and return the output."""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True,
            check=True
        )
        if result.stdout:
            print(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        sys.exit(1)


def main():
    """Main function to sync git repository."""
    print("=" * 50)
    print("Starting Git Repository Sync")
    print("=" * 50)
    
    # Get the project directory (current working directory in CML)
    project_dir = Path.cwd()
    print(f"Project directory: {project_dir}")
    
    # Check if .git directory exists
    git_dir = project_dir / ".git"
    if not git_dir.exists():
        print("❌ No git repository found. Initializing...")
        
        # Get GitHub token from environment
        github_token = os.environ.get("GITHUB_TOKEN", "")
        if not github_token:
            print("❌ No GitHub token found in environment")
            print("💡 Set GITHUB_TOKEN in the job environment variables")
            sys.exit(1)
        
        # Get repository URL (should be set in environment or hardcoded)
        github_repo = os.environ.get("GITHUB_REPOSITORY", "adfr/ai-screening")
        
        # Clone the repository
        git_url = f"https://{github_token}@github.com/{github_repo}.git"
        print(f"Cloning repository: {github_repo}")
        
        # Clone into temp directory and move files
        run_command(f"git clone {git_url} /tmp/repo_temp")
        run_command("cp -r /tmp/repo_temp/.git .")
        run_command("rm -rf /tmp/repo_temp")
        
        # Reset to get all files
        run_command("git reset --hard HEAD")
    else:
        print("✅ Git repository found")
    
    # Fetch latest changes
    print("\n📥 Fetching latest changes...")
    run_command("git fetch origin")
    
    # Get current branch
    current_branch = run_command("git rev-parse --abbrev-ref HEAD").strip()
    print(f"Current branch: {current_branch}")
    
    # Pull latest changes
    print("\n📦 Pulling latest changes...")
    run_command(f"git pull origin {current_branch}")
    
    # Show latest commit
    print("\n📝 Latest commit:")
    run_command("git log -1 --oneline")
    
    # Show changed files
    print("\n📄 Recently changed files:")
    run_command("git diff --name-status HEAD~1..HEAD")
    
    print("\n" + "=" * 50)
    print("✅ Git sync completed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    main()