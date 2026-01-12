# CML Testing Summary

The `cai_integration/local_test` directory contains comprehensive local testing scripts to debug and validate CML deployment before running full deployment.

## Test Scripts Available

### 1. **test_cml_connection.py** - Basic Connectivity
Tests:
- API authentication
- Project discovery
- Project details
- File listing (git clone status)
- Job listing

**Run:**
```bash
export CML_API_KEY="your_key"
python test_cml_connection.py
```

### 2. **test_job_creation.py** - Job Creation
Tests:
- Project verification
- Git clone completion (by listing files)
- 4 different script path formats
- Reports which format works

**Run:**
```bash
export CML_API_KEY="your_key"
python test_job_creation.py <project_id>
```

## Quick Testing Workflow

```bash
# Step 1: Set credentials
export CML_HOST="https://ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site/"
export CML_API_KEY="your_actual_api_key"

# Step 2: Test basic connectivity
python test_cml_connection.py

# Step 3: From output, get the project ID

# Step 4: Test job creation
python test_job_creation.py <project_id>

# Step 5: Check results and update jobs_config.yaml with working script path
```

## Key Debugging Insights

### "Script not found" Error?
Check with job creation test:
1. ✅ Files exist in project (listed in test)
2. ✅ Git clone is complete (files present)
3. ✅ Correct script path format (test finds which works)

### Project Status Issues?
- `creating` = Still initializing (wait and retry)
- `success` = Ready to use
- `error` = Something went wrong (delete and recreate)

### Missing Files?
- `.git_sync.py` not found = Git clone not complete yet
- `cai_integration/` not found = Git clone in progress
- Wait 60+ seconds and retry

## Documentation Files

- `TEST_CML_LOCAL.md` - Detailed connection testing guide
- `JOB_CREATION_TEST.md` - Detailed job creation testing guide
- `TESTING_SUMMARY.md` - This file

## Next Steps

After successful testing:

1. Confirm project exists and is ready
2. Confirm all files are present
3. Confirm at least one script path format works for job creation
4. Update `cai_integration/jobs_config.yaml` with working script paths
5. Run full deployment: `python cai_integration/deploy_to_cml.py`

## Troubleshooting Quick Reference

| Issue | Cause | Solution |
|-------|-------|----------|
| "Authentication failed" | Invalid API key | Check CML_API_KEY |
| "Project not found" | Project ID incorrect | Run test_cml_connection.py to find ID |
| "script not found" | Git clone incomplete | Wait 60s, then retry test |
| "Project creating" | Still initializing | Wait and retry in 30s |
| Job creation works but won't run | Job dependency issue | Check parent_job_key in config |

## Support

If tests still fail:
1. Check CML API key is valid
2. Verify CML host is accessible
3. Ensure project was created with git template
4. Check git repository URL is accessible
5. Review error messages in test output carefully

