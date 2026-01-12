import os
import subprocess
import sys
from pathlib import Path

def run_command(command, cwd=None, env=None, shell=True):
    print(f"Running command: {command}")
    try:
        # shell=True allows using shell features like variables if needed,
        # but here we pass environment variables explicitly via env parameter for PATH
        subprocess.run(command, cwd=cwd, env=env, shell=shell, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        sys.exit(1)

def check_build_artifacts_exist(project_root: str) -> bool:
    """
    Check if frontend build artifacts already exist.

    Checks for common build output directories that indicate a successful build.
    Returns True if build artifacts are found, False otherwise.
    """
    # Common build output directories for different build tools
    possible_build_dirs = [
        "dist",           # Vite, esbuild
        "build",          # Create React App, standard
        ".next",          # Next.js
        "out",            # Another common build output
        "public/build",   # Some configurations put build here
    ]

    print(f"\n🔍 Checking for existing build artifacts in {project_root}...")

    for build_dir in possible_build_dirs:
        artifact_path = Path(project_root) / build_dir
        if artifact_path.exists():
            # Check if directory has content (not just empty)
            if list(artifact_path.iterdir()):
                print(f"   ✅ Found build artifacts: {build_dir}/")
                print(f"   📊 Directory size: {sum(f.stat().st_size for f in artifact_path.rglob('*') if f.is_file()) / 1024 / 1024:.1f} MB")
                return True

    print(f"   ❌ No build artifacts found")
    return False

def main():
    project_root = "/home/cdsw"

    print("=" * 60)
    print("🏗️  Frontend Build Process")
    print("=" * 60)

    # Check if build already exists and should be skipped
    force_rebuild = os.environ.get("FORCE_BUILD", "false").lower() == "true"

    if not force_rebuild and check_build_artifacts_exist(project_root):
        print("\n✅ Build artifacts already exist!")
        print("   Skipping npm install and build (FORCE_BUILD not set)")
        print("\n   To force rebuild, set: export FORCE_BUILD=true")
        print("=" * 60)
        return

    if force_rebuild:
        print("\n⚙️  FORCE_BUILD=true detected, rebuilding anyway...")
    else:
        print("\n🚀 No existing build found, proceeding with build...")

    # --- Install Node.js and npm ---
    print("\n--- Installing Node.js ---")
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
    print("✅ Node.js installation complete.")

    print("\n--- Installing Dependencies and Building Frontend ---")

    run_command("npm install --force", cwd=project_root, env=current_env)
    run_command("npm run build", cwd=project_root, env=current_env)

    # Verify build artifacts were created
    print("\n--- Verifying Build ---")
    if check_build_artifacts_exist(project_root):
        print("✅ Build verification successful!")
    else:
        print("⚠️  Warning: No build artifacts found after build completed")
        print("   This might indicate the build failed or artifacts are in unexpected location")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ Frontend build completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()
