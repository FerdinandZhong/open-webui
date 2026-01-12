# Local CML Testing Guide

This guide explains how to test CML connectivity and job creation locally before running the full deployment.

## Prerequisites

- Python 3.11+
- `requests` library installed
- Conda environment: `vllm-playground-env` (or any environment with Python 3.11)
- CML credentials (API key)

## Setup

### 1. Install Dependencies

```bash
# Using the vllm-playground-env
conda activate vllm-playground-env
pip install requests pyyaml
```

### 2. Set Environment Variables

```bash
export CML_HOST="https://ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site/"
export CML_API_KEY="your_actual_api_key_here"
```

## Running Tests

### Method 1: Direct Python Script (Recommended)

```bash
# Set environment variables first
export CML_HOST="https://ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site/"
export CML_API_KEY="$YOUR_ACTUAL_API_KEY"

# Run the test
python test_cml_connection.py
```

### Method 2: Using Bash Wrapper Script

```bash
export CML_API_KEY="your_actual_api_key_here"
bash run_test.sh
```

## What the Test Script Does

The `test_cml_connection.py` script performs 5 tests:

### 1. **Authentication Test** ✅
- Verifies CML API credentials are valid
- Tests basic API connectivity

### 2. **Project Search** ✅
- Searches for the "open-webui" project
- Returns the Project ID if found
- Lists all available projects if not found

### 3. **Project Details** ✅
- Retrieves detailed project information
- Shows status, creation date, owner

### 4. **File Listing** ✅
- Lists all files in the project
- Helps verify git clone completed (should see `.git_sync.py`, `cai_integration/` files)
- This is crucial for debugging the "script not found" error

### 5. **Job Listing** ✅
- Shows all jobs currently in the project
- Helps verify job creation worked

## Expected Output

```
======================================================================
🧪 CML Connection Test
======================================================================

📋 Configuration:
   CML Host: https://ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site/
   API Key: ***xxxx
   Project Name: open-webui
   API URL: https://ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site/api/v2

✅ CML Tester initialized successfully.

======================================================================
1️⃣  Testing Authentication
======================================================================

➡️  GET https://ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site/api/v2/projects
   Params: {'page_size': 1}
⬅️  Response: 200
✅ Authentication successful!

======================================================================
2️⃣  Searching for Project
======================================================================

🔍 Searching for project: open-webui
➡️  GET https://ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site/api/v2/projects
   Params: {'search_filter': '{"name":"open-webui"}', 'page_size': 50}
⬅️  Response: 200
✅ Found project: open-webui
   Project ID: 4u5o-hjm5-h635-k7u2
   Status: success
   Created: 2026-01-12T08:54:10.688760Z
   Owner: Qishuai Zhong

======================================================================
3️⃣  Getting Project Details
======================================================================

✅ Project Details:
   Name: open-webui
   ID: 4u5o-hjm5-h635-k7u2
   Status: success
   Visibility: private
   Created: 2026-01-12T08:54:10.688760Z
   Owner: Qishuai Zhong

======================================================================
4️⃣  Listing Project Files
======================================================================

✅ Found 247 files in project:
   - .git
   - .git_sync.py ✅ (This should exist!)
   - cai_integration/ ✅
   - ... and 244 more files

======================================================================
5️⃣  Listing Project Jobs
======================================================================

✅ Found 0 jobs in project:
   (No jobs created yet - this is expected for first run)

======================================================================
✅ All tests completed!
======================================================================

📝 Summary:
   Project ID: 4u5o-hjm5-h635-k7u2
   Project Status: success
   Files in Project: 247
   Jobs in Project: 0
```

## Debugging the "Script Not Found" Error

If you see "script not found" errors, run the file listing test to check:

```python
# Look for these files in the output:
.git_sync.py                           # Should exist ✅
cai_integration/setup_environment.py   # Should exist ✅
cai_integration/build_frontend.py      # Should exist ✅
```

**If files are missing:**
1. Git clone may not have completed yet
2. Wait 60 seconds and run test again
3. Check project status (should be "success", not "creating")

**If files exist but job creation still fails:**
1. The script path may need adjustment
2. CML may require different path format
3. Check the error response from job creation API

## Next Steps

After confirming:
1. ✅ Project exists
2. ✅ Files are present (including .git_sync.py)
3. ✅ Project status is "success"

You can proceed with the full deployment using:

```bash
python cai_integration/deploy_to_cml.py
```

## Troubleshooting

### "Authentication failed"
- Verify CML_API_KEY is correct
- Check CML_HOST URL is accessible
- Check for network connectivity issues

### "Project 'open-webui' not found"
- Project may not exist yet (create it first)
- Project name is case-sensitive
- Use project ID directly if known

### "Failed to get project details"
- Project may have been deleted
- Check project ID is correct

### "Files not listed"
- Git clone may still be in progress
- Wait longer and try again
- Check project status directly

## Files Created

- `test_cml_connection.py` - Main test script
- `run_test.sh` - Bash wrapper for conda environment
- `TEST_CML_LOCAL.md` - This documentation

