#!/bin/bash
# Test script runner with conda environment activation

# Configure these values
CONDA_ENV_NAME="${CONDA_ENV_NAME:-your-env-name}"  # Change to your conda environment name
CML_HOST="https://ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site/"

# Source conda
source ~/miniconda3/etc/profile.d/conda.sh 2>/dev/null || source /opt/miniconda3/etc/profile.d/conda.sh 2>/dev/null || source $(conda info --base)/etc/profile.d/conda.sh

# Activate the conda environment
echo "Activating conda environment: $CONDA_ENV_NAME"
conda activate "$CONDA_ENV_NAME"

# Set CML credentials
export CML_HOST="$CML_HOST"
# CML_API_KEY should be set from environment or pass as parameter

# Show configuration
echo ""
echo "Configuration:"
echo "  Environment: $CONDA_ENV_NAME"
echo "  CML_HOST: $CML_HOST"
echo "  CML_API_KEY: ${CML_API_KEY:0:10}..."
echo ""

if [ -z "$CML_API_KEY" ]; then
    echo "❌ Error: CML_API_KEY not set"
    echo "Set it with: export CML_API_KEY=your_key"
    conda deactivate
    exit 1
fi

# Run the test script
python test_cml_connection.py

# Deactivate conda environment
conda deactivate
