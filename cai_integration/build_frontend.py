import os
import subprocess
import sys

def run_command(command, cwd=None, env=None, shell=True):
    print(f"Running command: {command}")
    try:
        # shell=True allows using shell features like variables if needed, 
        # but here we pass environment variables explicitly via env parameter for PATH
        subprocess.run(command, cwd=cwd, env=env, shell=shell, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        sys.exit(1)

def main():
    # --- Install Node.js and npm ---
    NODE_VERSION = "v22.4.1"
    NODE_DIST = f"node-{NODE_VERSION}-linux-x64"
    NODE_ARCHIVE = f"{NODE_DIST}.tar.xz"
    INSTALL_DIR = "/home/cdsw/npm"

    run_command(f"mkdir -p {INSTALL_DIR}")
    
    # Download Node.js binary
    print(f"Downloading Node.js {NODE_VERSION}...")
    run_command(f"curl -fsSL https://nodejs.org/dist/{NODE_VERSION}/{NODE_ARCHIVE} -o {INSTALL_DIR}/{NODE_ARCHIVE}")

    print("Extracting Node.js...")
    run_command(f"tar -xf {INSTALL_DIR}/{NODE_ARCHIVE} -C {INSTALL_DIR}")

    # Set up environment variables
    node_bin_path = f"{INSTALL_DIR}/{NODE_DIST}/bin"
    current_env = os.environ.copy()
    current_env["PATH"] = f"{node_bin_path}:{current_env.get('PATH', '')}"
    
    print(f"Node.js added to PATH: {node_bin_path}")
    print("Node.js installation complete.")

    print("Install frontend dependencies and build")
    # --- Install frontend dependencies and build ---
    # /home/cdsw is the standard project root in CML
    project_root = "/home/cdsw"
    
    run_command("npm install --force", cwd=project_root, env=current_env)
    run_command("npm run build", cwd=project_root, env=current_env)

if __name__ == "__main__":
    main()
