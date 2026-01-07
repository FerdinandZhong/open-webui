#!/bin/bash
set -e

# --- Install Node.js and npm ---
NODE_VERSION="v22.4.1"
NODE_DIST="node-${NODE_VERSION}-linux-x64"
NODE_ARCHIVE="${NODE_DIST}.tar.xz"
INSTALL_DIR="/home/cdsw/npm"

mkdir -p "${INSTALL_DIR}"
# Download Node.js binary
echo "Downloading Node.js ${NODE_VERSION}..."
curl -fsSL "https://nodejs.org/dist/${NODE_VERSION}/${NODE_ARCHIVE}" -o "${INSTALL_DIR}/${NODE_ARCHIVE}"

echo "Extracting Node.js..."
tar -xf "${INSTALL_DIR}/${NODE_ARCHIVE}" -C "${INSTALL_DIR}"

echo "Adding Node.js to PATH..."
export PATH="${INSTALL_DIR}/${NODE_DIST}/bin:${PATH}"
echo "Node.js installation complete."

echo "Install frontend dependencies and build"
# --- Install frontend dependencies and build ---
cd /home/cdsw
npm install --force
npm run build
