#!/bin/bash
# Test job creation in CML with conda environment support

set -e

# Configure these values
CONDA_ENV_NAME="${CONDA_ENV_NAME:-your-env-name}"  # Change to your conda environment name
CML_HOST="https://ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site/"

echo "CML Job Creation Test Runner"
echo "============================"
echo ""

# Optionally activate conda environment
if [ "$USE_CONDA" = "true" ]; then
    echo "Activating conda environment: $CONDA_ENV_NAME"
    source ~/miniconda3/etc/profile.d/conda.sh 2>/dev/null || source /opt/miniconda3/etc/profile.d/conda.sh 2>/dev/null || source $(conda info --base)/etc/profile.d/conda.sh
    conda activate "$CONDA_ENV_NAME"
    echo ""
fi

# Check if PROJECT_ID is provided
if [ -z "$PROJECT_ID" ]; then
    if [ -z "$1" ]; then
        echo "❌ Error: PROJECT_ID not provided"
        echo ""
        echo "Usage:"
        echo "  ./run_job_test.sh <PROJECT_ID>"
        echo ""
        echo "Example:"
        echo "  ./run_job_test.sh 4u5o-hjm5-h635-k7u2"
        echo ""
        echo "Or set environment variable:"
        echo "  export PROJECT_ID=4u5o-hjm5-h635-k7u2"
        echo "  ./run_job_test.sh"
        exit 1
    else
        PROJECT_ID="$1"
    fi
fi

echo "Testing job creation for project: $PROJECT_ID"
echo ""

# Check if CML_API_KEY is set
if [ -z "$CML_API_KEY" ]; then
    echo "❌ Error: CML_API_KEY not set"
    echo "Set it with: export CML_API_KEY=your_key"
    exit 1
fi

# Export variables for Python script
export CML_HOST="$CML_HOST"
export PROJECT_ID="$PROJECT_ID"

# Run the test
python test_job_creation.py "$PROJECT_ID"

# Deactivate conda if activated
if [ "$USE_CONDA" = "true" ]; then
    conda deactivate
fi
