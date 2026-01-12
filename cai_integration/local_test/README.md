# Local CML Testing Suite

This directory contains scripts and documentation for local testing of CML connectivity and job creation before running the full deployment.

## Quick Start

```bash
# 1. Navigate to this directory
cd cai_integration/local_test

# 2. Set your credentials
export CML_API_KEY="your_actual_api_key"

# 3. Run the connection test
python test_cml_connection.py

# 4. From the output, get your PROJECT_ID

# 5. Test job creation
python test_job_creation.py <PROJECT_ID>
```

## What's Included

### Python Test Scripts

- **`test_cml_connection.py`** - Tests basic CML connectivity
  - Verifies API authentication
  - Searches for projects
  - Lists files (checks git clone status)
  - Lists jobs

- **`test_job_creation.py`** - Tests job creation with different script paths
  - Verifies project exists
  - Lists files to confirm git clone
  - Tests 4 different script path formats
  - Reports which format works

### Shell Wrappers

- **`run_test.sh`** - Wrapper for running connection test with conda
  - Customize `CONDA_ENV_NAME` inside the script
  - Requires `CML_API_KEY` environment variable

- **`run_job_test.sh`** - Wrapper for running job creation test
  - Optional conda support (set `USE_CONDA=true` to enable)
  - Customize `CONDA_ENV_NAME` inside the script
  - Requires `PROJECT_ID` as argument or environment variable

### Documentation

- **`TESTING_SUMMARY.md`** - Quick reference guide
- **`TEST_CML_LOCAL.md`** - Detailed connection testing guide
- **`JOB_CREATION_TEST.md`** - Detailed job creation guide
- **`README.md`** - This file

## Configuration

### Setting Up Conda Environment

Edit the shell scripts and replace:
```bash
CONDA_ENV_NAME="${CONDA_ENV_NAME:-your-env-name}"
```

With your actual environment name, e.g.:
```bash
CONDA_ENV_NAME="${CONDA_ENV_NAME:-vllm-playground-env}"
```

Or set the environment variable before running:
```bash
export CONDA_ENV_NAME="your-env-name"
bash run_test.sh
```

## Usage Examples

### Test 1: Basic Connectivity

```bash
export CML_API_KEY="your_key"
python test_cml_connection.py
```

**Output includes:**
- Project ID (if found)
- Project status
- Number of files (indicates git clone completion)
- Existing jobs

### Test 2: Job Creation

```bash
export CML_API_KEY="your_key"
python test_job_creation.py 4u5o-hjm5-h635-k7u2
```

**Output includes:**
- Project verification
- File listing
- 4 script path format tests
- Recommended script path

### Test 3: With Conda (Optional)

```bash
export CML_API_KEY="your_key"
export CONDA_ENV_NAME="your-env-name"
bash run_test.sh
```

## Key Findings

Based on testing with adfr/ai-screening reference and your CML instance:

✅ **WORKING script paths (RELATIVE):**
- `.git_sync.py`
- `cai_integration/setup_environment.py`
- `cai_integration/build_frontend.py`

❌ **NOT WORKING (ABSOLUTE):**
- `/home/cdsw/.git_sync.py`
- `/home/cdsw/cai_integration/setup_environment.py`

**Conclusion:** CML expects RELATIVE paths, not absolute `/home/cdsw/` paths.

## Troubleshooting

### "Script not found" Error

1. Run `test_cml_connection.py` to verify files exist
2. Run `test_job_creation.py` to test path formats
3. Check which format works
4. Update `cai_integration/jobs_config.yaml` with working path

### Project Status Issues

- `creating` - Wait 30-60 seconds, then retry
- `success` - Ready to use
- `error` - Delete and recreate project

### Missing Files

- If files don't appear in listing, git clone is still in progress
- Wait 60+ seconds after project creation
- Retry the test

## Next Steps

After successful testing:

1. ✅ Confirm project exists and is ready
2. ✅ Confirm all files are present
3. ✅ Confirm job creation works
4. ✅ Note the working script path format
5. Run full deployment:
   ```bash
   python cai_integration/deploy_to_cml.py
   ```

## Important Notes

- Test jobs are prefixed with "Test Job -" for easy identification in CML
- You can safely delete test jobs from the CML UI
- All test jobs use minimal resources (1 CPU, 2GB memory, 5 min timeout)
- Tests use the same API calls as the real deployment

## Environment Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `CML_API_KEY` | ✅ Yes | - | Your CML API authentication key |
| `CML_HOST` | ❌ No | https://ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site/ | CML instance URL |
| `PROJECT_ID` | ❌ No (for job test) | - | Project ID to test with |
| `CONDA_ENV_NAME` | ❌ No | your-env-name | Conda environment to activate |
| `USE_CONDA` | ❌ No | false | Set to "true" to activate conda |

## Documentation

For detailed information, see:
- `TESTING_SUMMARY.md` - Quick reference
- `TEST_CML_LOCAL.md` - Connection testing details
- `JOB_CREATION_TEST.md` - Job creation details

