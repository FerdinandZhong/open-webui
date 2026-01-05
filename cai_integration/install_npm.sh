#!/bin/bash
set -e

# Define Node.js version and paths
NODE_VERSION="v22.4.1"
NODE_DIST="node-${NODE_VERSION}-linux-x64"
NODE_ARCHIVE="${NODE_DIST}.tar.xz"
INSTALL_DIR="/home/cdsw/npm"

# Create installation directory if it doesn't exist
mkdir -p "${INSTALL_DIR}"

# Download Node.js binary
echo "Downloading Node.js ${NODE_VERSION}..."
curl -fsSL "https://nodejs.org/dist/${NODE_VERSION}/${NODE_ARCHIVE}" -o "${INSTALL_DIR}/${NODE_ARCHIVE}"

# Extract the archive
echo "Extracting Node.js..."
tar -xf "${INSTALL_DIR}/${NODE_ARCHIVE}" -C "${INSTALL_DIR}"

# Add Node.js to PATH
echo "Adding Node.js to PATH..."
export PATH="${INSTALL_DIR}/${NODE_DIST}/bin:${PATH}"

# Verify installation
echo "Verifying Node.js installation..."
node -v
npm -v

echo "Node.js installation complete."
