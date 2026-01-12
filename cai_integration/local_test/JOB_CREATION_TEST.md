# CML Job Creation Test Guide

This guide explains how to test job creation in CML to debug script path issues.

## Quick Start

```bash
# 1. Set your API key
export CML_API_KEY="your_actual_api_key_here"

# 2. Set your project ID (from previous deployment or use test_cml_connection.py to find it)
export PROJECT_ID="4u5o-hjm5-h635-k7u2"

# 3. Run the job creation test
python test_job_creation.py $PROJECT_ID
```

Or using the shell script:
```bash
export CML_API_KEY="your_actual_api_key_here"
bash run_job_test.sh 4u5o-hjm5-h635-k7u2
```

## What the Script Tests

The `test_job_creation.py` script performs 3 main tests:

### 1. **Verify Project** ✅
- Confirms project exists in CML
- Checks project status (should be "success" or "ready")
- Returns project ID if valid

### 2. **List Project Files** ✅
- Lists all files currently in the project
- Verifies git clone completed by checking for:
  - `.git_sync.py`
  - `cai_integration/setup_environment.py`
  - `cai_integration/build_frontend.py`
- This is crucial for debugging "script not found" errors

### 3. **Test Script Path Formats** ✅
Tests 4 different script path formats:

| Format | Path | Description |
|--------|------|-------------|
| Test 1 | `/home/cdsw/.git_sync.py` | Absolute path |
| Test 2 | `.git_sync.py` | Relative path |
| Test 3 | `/home/cdsw/cai_integration/setup_environment.py` | Absolute nested |
| Test 4 | `cai_integration/setup_environment.py` | Relative nested |

For each format, the script:
- Attempts to create a test job
- Reports success/failure
- Provides the error message if it fails

## Expected Output

```
================================================================================
🧪 CML Job Creation Test
================================================================================

📋 Configuration:
   CML Host: https://ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site/
   API Key: ***xxxx
   Project ID: 4u5o-hjm5-h635-k7u2
   API URL: https://ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site/api/v2

✅ CML Job Tester initialized successfully.

🚀 Starting all tests...

================================================================================
1️⃣  Verifying Project
================================================================================

➡️  GET https://.../api/v2/projects/4u5o-hjm5-h635-k7u2
⬅️  Response: 200

✅ Project found
   Name: open-webui
   Status: success

================================================================================
2️⃣  Listing Project Files (Git Clone Status)
================================================================================

➡️  GET https://.../api/v2/projects/4u5o-hjm5-h635-k7u2/files
⬅️  Response: 200

✅ Found 247 files

📂 Key Files Status:
   ✅ .git_sync.py - FOUND
   ✅ cai_integration/setup_environment.py - FOUND
   ✅ cai_integration/build_frontend.py - FOUND

📋 Sample Files (first 20):
   - .git
   - .git_sync.py
   - .github/
   ... and 244 more files

================================================================================
3️⃣  Testing Script Path Formats
================================================================================

Testing: Absolute path: /home/cdsw/.git_sync.py

➡️  POST https://.../api/v2/projects/4u5o-hjm5-h635-k7u2/jobs
   Data: {...}
⬅️  Response: 201
   Response: {"id":"job-123","name":"Test Job - git_sync_absolute","script":"/home/cdsw/.git_sync.py"}

✅ SUCCESS! Job created with ID: job-123
   Name: Test Job - git_sync_absolute
   Script: /home/cdsw/.git_sync.py

...

================================================================================
✅ All tests completed!
================================================================================

📊 Summary:

   ✅ Successful (2):
      - git_sync_absolute: /home/cdsw/.git_sync.py
      - setup_env_relative: cai_integration/setup_environment.py

   ❌ Failed (2):
      - git_sync_relative: .git_sync.py
      - setup_env_absolute: /home/cdsw/cai_integration/setup_environment.py

🎯 RECOMMENDED SCRIPT PATH:
   Use: /home/cdsw/.git_sync.py
```

## Interpreting Results

### ✅ If ALL tests pass:
- Git clone is complete ✅
- Files are accessible ✅
- All script path formats work ✅

Use whichever format you prefer in `jobs_config.yaml`

### ✅ If SOME tests pass:
- Git clone is complete ✅
- Only specific path formats work ✅

Use the recommended script path from the summary

### ❌ If ALL tests fail with "script not found":
- Git clone may NOT be complete yet
- Wait longer and run test again
- Or delete and recreate the project

### ❌ If tests fail with other errors:
- Check the error message in the response
- Common issues:
  - Project doesn't exist (check project ID)
  - Project not ready (status is "creating")
  - Permission issues (check API key)

## Debugging Steps

### Step 1: Verify Connection
```bash
python test_cml_connection.py
```
This verifies basic connectivity before testing job creation.

### Step 2: Check Files
Look for these files in the file listing:
- `.git_sync.py` - Should exist ✅
- `cai_integration/setup_environment.py` - Should exist ✅
- `cai_integration/build_frontend.py` - Should exist ✅

If they don't exist:
1. Git clone may still be in progress
2. Wait 60 seconds and run test again
3. Check project status (should be "success", not "creating")

### Step 3: Try Job Creation
Once files are confirmed to exist, test job creation with the test script.

### Step 4: Use Recommended Path
Update `jobs_config.yaml` with the script path format that works.

## Troubleshooting

### "Project not found or unable to access"
- Verify project ID is correct
- Check API key is valid
- Ensure CML host is accessible

### "script '/home/cdsw/...' not found in project directory"
- This means files are NOT in the project yet
- Git clone is still in progress
- Wait longer and try again (at least 60 seconds after project creation)

### "Script path works but job won't trigger"
- Jobs may have dependencies set up
- Job won't run if parent job hasn't completed
- Check parent_job_key in jobs_config.yaml

### "Test job created but can't see it in CML UI"
- It might be there but not visible yet
- Refresh the UI
- Use `test_cml_connection.py` to list jobs
- Check job status with API

## Next Steps

After determining the correct script path format:

1. Update `cai_integration/jobs_config.yaml` with the working format
2. Run full deployment: `python cai_integration/deploy_to_cml.py`
3. Monitor the deployment logs
4. Check CML UI for running jobs

## Files Used

- `test_job_creation.py` - Main job creation test script
- `run_job_test.sh` - Shell wrapper script
- `JOB_CREATION_TEST.md` - This documentation

## Additional Notes

- Test jobs are prefixed with "Test Job -" for easy identification
- You can delete test jobs from the CML UI if cleanup is needed
- The script uses the same API calls as the real deployment
- All jobs are created with minimal resources (1 CPU, 2GB memory)

