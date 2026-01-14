# Debugging Local CML Tests

## Problem Summary

You reported that project creation fails when running tests locally, but works successfully in GitHub Actions. This document explains the likely causes and provides quick debugging steps.

## Root Cause Analysis

When GitHub Actions succeeds but local tests fail, it's usually one of these issues:

### 1. Missing Environment Variables

**Why it fails locally:**
- Your shell session doesn't have `CML_HOST` or `CML_API_KEY` set
- GitHub Actions has these in repository secrets

**Check it:**
```bash
cd cai_integration/local_test
./check_env.sh
```

**Output shows:**
```
❌ CML_HOST not set
❌ CML_API_KEY not set
```

**Fix it:**
```bash
export CML_HOST="https://your-cml-instance.cloudera.site"
export CML_API_KEY="your-api-key"
```

### 2. Network/Firewall Issues

**Why it fails locally:**
- Your local machine can't reach CML host (firewall, VPN not connected)
- GitHub runner (cloud) has unrestricted access

**Check it:**
```bash
./check_env.sh
```

**Output shows:**
```
❌ Cannot reach your-host.cloudera.site (port 443)
  Check: firewall, VPN, CML_HOST value
```

**Fix it:**
- Connect to VPN if required
- Check firewall allows HTTPS (port 443)
- Verify CML_HOST is correct

### 3. API Key Issues

**Why it fails locally:**
- Your API key is expired or revoked
- GitHub Actions uses a fresh key from secrets

**Check it:**
```bash
VERBOSE=true python test_project_creation.py
```

**Output shows:**
```
[-] API Error 401: Unauthorized
```

**Fix it:**
1. Log in to CML UI
2. Go to Admin → API Keys
3. Generate a new API key
4. Update `CML_API_KEY`:
   ```bash
   export CML_API_KEY="new-key-here"
   ```

## Quick Debugging Workflow

Follow this workflow to find and fix the issue:

### Step 1: Check Environment

```bash
cd cai_integration/local_test
./check_env.sh
```

This shows:
- ✅ Which environment variables are set
- ✅ Network connectivity to CML
- ✅ What's missing and how to fix it

### Step 2: Run with Verbose Logging

If Step 1 shows environment is OK, run with debugging:

```bash
VERBOSE=true python test_project_creation.py
```

This shows:
- Full HTTP requests and responses
- API status codes
- Detailed error messages
- Environment variables being used (API key masked)

### Step 3: Compare with GitHub Actions

The test_project_creation.py works the same way in GitHub Actions. If it fails locally but succeeds in Actions:

1. Check environment (Step 1)
2. Check network connectivity (`./check_env.sh` tests this)
3. Check API key isn't expired
4. Look at GitHub Actions run logs to compare

## Environment Variables Needed

| Variable | Required | Example |
|----------|----------|---------|
| `CML_HOST` | ✅ Yes | `https://my-instance.cloudera.site` |
| `CML_API_KEY` | ✅ Yes | `<long-alphanumeric-string>` |
| `GITHUB_REPOSITORY` | ❌ Optional | `your-org/your-repo` |
| `GH_PAT` | ❌ Optional | `ghp_xxxxx...` |
| `VERBOSE` | ❌ Optional | `true` for debugging |

### Set All At Once

```bash
export CML_HOST="https://your-cml-instance.cloudera.site"
export CML_API_KEY="your-api-key"
export GITHUB_REPOSITORY="your-org/your-repo"  # Optional
export GH_PAT="your-github-token"               # Optional
```

## Files Modified/Created

### New Diagnostic Tools

1. **`cai_integration/local_test/check_env.sh`** (NEW)
   - Checks environment variables
   - Tests network connectivity
   - Shows setup instructions
   - Run this first when debugging

2. **`cai_integration/local_test/test_project_creation.py`** (ENHANCED)
   - Added `_test_connectivity()` to verify API access
   - Added verbose logging mode (`VERBOSE=true`)
   - Improved error messages
   - Now uses same search_filter format as deploy_to_cml.py
   - Shows setup instructions on startup

3. **`cai_integration/local_test/README.md`** (UPDATED)
   - Added "Local Test Fails But GitHub Actions Works" section
   - Added troubleshooting guide
   - Added check_env.sh documentation
   - Explains why tests might fail locally

## How to Use Updated Scripts

### Basic Test

```bash
python test_project_creation.py
```

**Shows:**
- Environment validation
- Connectivity test
- Project search/creation
- Project details

### Verbose Debugging

```bash
VERBOSE=true python test_project_creation.py
```

**Shows:**
- All of above, plus:
- Full HTTP requests/responses
- Parameter values
- Debug timestamps
- Environment variable masking

### Environment Diagnostics

```bash
./check_env.sh
```

**Shows:**
- Which env vars are set
- Network connectivity test
- Setup instructions
- Quick start guide

## Common Issues and Solutions

### Issue: "API Error 401: Unauthorized"

**Cause**: Invalid API key

**Solution**:
```bash
# Generate new key in CML UI
export CML_API_KEY="new-key-from-ui"
python test_project_creation.py
```

### Issue: "Connection error" or "Cannot reach host"

**Cause**: Network/firewall issue

**Solution**:
```bash
./check_env.sh  # See connectivity test
# Connect to VPN if needed, or check firewall
```

### Issue: "Missing environment variables"

**Cause**: CML_HOST or CML_API_KEY not set

**Solution**:
```bash
./check_env.sh  # Shows what's missing
# Then set missing variables
export CML_HOST="..."
export CML_API_KEY="..."
```

### Issue: "API Error 404: Not Found"

**Cause**: Wrong CML_HOST or API version issue

**Solution**:
```bash
# Verify CML_HOST format (no /api/v2 suffix)
echo $CML_HOST
# Should be: https://my-instance.cloudera.site
# NOT: https://my-instance.cloudera.site/api/v2
```

## Why GitHub Actions Works But Local Fails

GitHub Actions workflow has advantages:

1. **Secrets Management**: Credentials stored securely in GitHub
2. **Clean Environment**: Fresh runner with no interference
3. **Network**: Cloud runner has unrestricted network access
4. **Reproducibility**: Same workflow every time

Local development has challenges:

1. **Manual Setup**: You need to set env vars each session
2. **Network Issues**: Local network, VPN, firewall complications
3. **Stale Credentials**: API keys can expire
4. **Tool Versions**: Local Python/requests versions might differ

## Testing Strategy

1. **First**: Use `./check_env.sh` to diagnose environment
2. **Second**: Use `python test_project_creation.py` to test workflow
3. **Third**: Use `VERBOSE=true python test_project_creation.py` to debug failures
4. **Finally**: Compare logs with GitHub Actions run

## Example Debugging Session

```bash
# Step 1: Check environment
$ ./check_env.sh
❌ CML_HOST not set
❌ CML_API_KEY not set

# Step 2: Set variables (get from GitHub secrets or CML UI)
$ export CML_HOST="https://my-instance.go01-dem.ylcu-atmi.cloudera.site"
$ export CML_API_KEY="xxxxxxxxxxxx"

# Step 3: Run diagnostic again
$ ./check_env.sh
✅ CML_HOST: https://my-instance.go01-dem.ylcu-atmi.cloudera.site
✅ CML_API_KEY: (set, length: 32)
✅ Can reach my-instance... (port 443)

# Step 4: Test project creation
$ python test_project_creation.py
[+] API URL: https://my-instance.go01-dem.ylcu-atmi.cloudera.site/api/v2
[*] Searching for project: open-webui
[+] Found project: open-webui (ID: xxx, Status: running)
✅ All tests passed!
```

## Next Steps

After fixing the issue:

1. ✅ Verify `./check_env.sh` passes all checks
2. ✅ Verify `python test_project_creation.py` succeeds
3. ✅ Run full deployment: `python deploy_to_cml.py`
4. ✅ Verify GitHub Actions also passes

## See Also

- [cai_integration/local_test/README.md](cai_integration/local_test/README.md) - Full testing guide
- [cai_integration/local_test/check_env.sh](cai_integration/local_test/check_env.sh) - Environment checker
- [cai_integration/local_test/test_project_creation.py](cai_integration/local_test/test_project_creation.py) - Project creation test
- [cai_integration/deploy_to_cml.py](cai_integration/deploy_to_cml.py) - Full deployment script
