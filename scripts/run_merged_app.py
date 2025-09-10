#!/usr/bin/env python3
"""Wrapper to run merged SDN application with venv Python that has all required packages."""

import os
import subprocess
import sys


def main():
    # Change to CML working directory
    os.chdir("/home/cdsw")
    
    # Use venv Python (which should have all our packages)
    venv_python = "/home/cdsw/.venv/bin/python"
    
    # Check if venv exists, if not try regular python
    if not os.path.exists(venv_python):
        print("Virtual environment not found at /home/cdsw/.venv")
        venv_python = "python3"
    
    print(f"Starting merged SDN application")
    print(f"Using Python: {venv_python}")
    
    # Set environment variables for the application
    os.environ["SDN_FILE_PATH"] = os.environ.get("SDN_FILE_PATH", "data_list/sdn_final.csv")
    
    # Pass through OpenAI API key if available
    if "OPENAI_API_KEY" not in os.environ or not os.environ["OPENAI_API_KEY"]:
        print("⚠️  OpenAI API key not set - disabling LLM features")
        os.environ["USE_LLM"] = "false"
    
    # Run merged application directly without subprocess
    # This keeps the process running as the main process
    print("Executing run_merged_app.py...")
    sys.stdout.flush()
    
    # Execute the script directly in the same process
    exec(open("run_merged_app.py").read(), {'__name__': '__main__'})


if __name__ == "__main__":
    main()