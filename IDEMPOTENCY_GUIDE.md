# Deployment Idempotency Guide

## Problem

Currently, re-running the deployment will always:
1. Re-run "Create Python Environment" job (setup venv, install deps)
2. Re-run "Build Frontend" job (rebuild all assets)

This wastes time and resources, especially for the expensive frontend build.

## Solution Strategies

### Strategy 1: Skip Jobs if Already Successful (Recommended)

**Approach:** Check if job has already run successfully, skip if done.

**Implementation:**
```python
def should_skip_job(self, project_id: str, job_id: str) -> bool:
    """
    Check if job has already run successfully.

    Returns True if we should skip re-running this job.
    """
    # Get the most recent job run
    result = self.make_request("GET", f"projects/{project_id}/jobs/{job_id}/runs")

    if not result or not result.get("runs"):
        return False  # No runs yet, don't skip

    # Get first (most recent) run
    latest_run = result.get("runs", [])[0]
    status = latest_run.get("status", "")

    # Skip if the most recent run succeeded
    if status in ["succeeded", "success", "ENGINE_SUCCEEDED"]:
        print(f"   ✅ Job already completed successfully, skipping")
        return True

    # Skip if currently running (will be caught by get_active_job_run)
    if status in ["queued", "running", "ENGINE_QUEUED", "ENGINE_RUNNING"]:
        print(f"   ⏳ Job already running, skipping")
        return True

    return False
```

**Pros:**
- ✅ Simple and fast
- ✅ No special tracking needed
- ✅ Works with existing CML API

**Cons:**
- ❌ Doesn't handle partial failures well
- ❌ If frontend assets changed but code didn't, still rebuilds

---

### Strategy 2: Check for Build Artifacts

**Approach:** Verify build output exists before skipping.

**Implementation:**
```python
def check_build_artifacts(self, project_id: str) -> bool:
    """
    Check if frontend build artifacts exist in the project.

    Returns True if build is already complete.
    """
    files = self.projects.list_files(project_id)
    file_paths = [f.get("path", "") for f in files]

    # Check for common build output directories/files
    expected_artifacts = [
        "dist/",           # Vite/webpack build output
        "build/",          # Alternative build location
        ".next/",          # Next.js build output
        "out/",            # Another common build dir
    ]

    for artifact in expected_artifacts:
        for path in file_paths:
            if artifact in path:
                print(f"   ✅ Found build artifact: {artifact}")
                return True

    print(f"   ❌ No build artifacts found")
    return False
```

**Pros:**
- ✅ Detects actual build status
- ✅ Handles code changes properly

**Cons:**
- ❌ Makes extra API call to list files
- ❌ Need to know build output locations

---

### Strategy 3: Use Status File / Marker

**Approach:** Create a `.deployment_complete` or similar marker file after successful build.

**Implementation in build_frontend.py:**
```python
def main():
    # ... existing build code ...

    print("Install frontend dependencies and build")
    run_command("npm install --force", cwd=project_root, env=current_env)
    run_command("npm run build", cwd=project_root, env=current_env)

    # ✅ Mark deployment as complete
    marker_file = "/home/cdsw/.deployment_complete"
    with open(marker_file, "w") as f:
        f.write("Frontend build completed successfully\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")

    print(f"✅ Deployment marker created: {marker_file}")
```

**In deploy_to_cml.py:**
```python
def is_build_complete(self, project_id: str) -> bool:
    """Check if deployment marker exists in project."""
    files = self.projects.list_files(project_id)
    file_paths = [f.get("path", "") for f in files]

    return ".deployment_complete" in file_paths
```

**Pros:**
- ✅ Explicit, reliable indicator
- ✅ Easy to check

**Cons:**
- ❌ Marker can get out of sync if build partially fails
- ❌ Need to clean up marker for rebuilds

---

### Strategy 4: Use Environment Variable Flag

**Approach:** Allow environment variable to control whether to rebuild.

**Implementation:**
```python
def deploy(self):
    """Main deployment process."""
    # ... existing code ...

    # Check if we should skip already-built components
    skip_env_setup = os.environ.get("SKIP_ENV_SETUP", "false").lower() == "true"
    skip_build = os.environ.get("SKIP_BUILD", "false").lower() == "true"

    if skip_env_setup:
        print("⏭️  Skipping environment setup (SKIP_ENV_SETUP=true)")
        env_run_id = None
    else:
        env_run_id = self.trigger_job(project_id, env_job_id)

    if skip_build:
        print("⏭️  Skipping frontend build (SKIP_BUILD=true)")
        build_run_id = None
    else:
        build_run_id = self.trigger_job(project_id, build_job_id)
```

**Usage:**
```bash
# Skip both
SKIP_ENV_SETUP=true SKIP_BUILD=true python deploy_to_cml.py

# Skip only build
SKIP_BUILD=true python deploy_to_cml.py
```

**Pros:**
- ✅ User control
- ✅ Simple to implement

**Cons:**
- ❌ Requires manual intervention
- ❌ Error-prone (user might forget)

---

### Strategy 5: Hybrid Approach (Recommended)

**Combine multiple strategies:**

```python
def should_run_job(self, project_id: str, job_name: str) -> bool:
    """
    Determine if a job should run.

    Checks in order:
    1. Environment variable override
    2. Job already running (don't start duplicate)
    3. Job succeeded recently (check last run)
    """
    # 1. Check environment override
    skip_env = os.environ.get(f"SKIP_{job_name.upper()}", "").lower() == "true"
    if skip_env:
        print(f"   ⏭️  Skipping {job_name} (env override)")
        return False

    # 2. Check if already running
    job_id = self.jobs_dict.get(job_name)
    if self.get_active_job_run(project_id, job_id):
        print(f"   ⏳ {job_name} already running, monitoring...")
        return False  # Already running, just wait for it

    # 3. Check if already succeeded
    if self.job_succeeded_recently(project_id, job_id):
        print(f"   ✅ {job_name} already succeeded, skipping")
        return False

    return True
```

**Usage:**
```bash
# Re-run everything
python deploy_to_cml.py

# Skip env setup, rebuild frontend
SKIP_ENV_SETUP=true python deploy_to_cml.py

# Just check status, don't rebuild anything
SKIP_ENV_SETUP=true SKIP_BUILD=true python deploy_to_cml.py
```

---

## Recommendation: Implement Strategy 1 + 4

**Best balance of automation and control:**

1. **Default (auto-skip):** Check if job already succeeded, skip if yes
2. **Override:** Allow env variables to force re-run when needed

**Implementation:**
```python
def deploy(self):
    """Main deployment process."""
    # ...existing code...

    # Check if we should force re-run
    force_rebuild = os.environ.get("FORCE_REBUILD", "false").lower() == "true"

    env_job_id = jobs.get("Create Python Environment")
    build_job_id = jobs.get("Build Frontend")

    # Environment setup with smart skipping
    if not force_rebuild and self.job_succeeded_recently(project_id, env_job_id):
        print("✅ Environment already setup, skipping")
        env_run_id = None
    else:
        env_run_id = self.trigger_job(project_id, env_job_id)
        if env_run_id and not self.wait_for_job_completion(...):
            print("❌ Environment setup failed")
            return

    # Frontend build with smart skipping
    if not force_rebuild and self.job_succeeded_recently(project_id, build_job_id):
        print("✅ Frontend already built, skipping")
        build_run_id = None
    else:
        build_run_id = self.trigger_job(project_id, build_job_id)
        if build_run_id and not self.wait_for_job_completion(...):
            print("❌ Frontend build failed")
            return

    # Create application
    self.create_application(project_id)
```

**Usage:**
```bash
# Normal deployment - auto-skips if already done
python deploy_to_cml.py

# Force rebuild everything
FORCE_REBUILD=true python deploy_to_cml.py

# Force rebuild only frontend
FORCE_REBUILD=true SKIP_ENV_SETUP=true python deploy_to_cml.py
```

---

## Implementation Steps

1. **Add helper method** `job_succeeded_recently(project_id, job_id)` to CMLDeployer
2. **Update `deploy()` method** to check before triggering jobs
3. **Add environment variables** for override control
4. **Update jobs_config.yaml** documentation about idempotency
5. **Test:**
   - First run: both jobs execute
   - Second run: both jobs skipped
   - `FORCE_REBUILD=true`: both jobs execute again
   - Partial failure: can re-run just the failed job

---

## Notes

- The current `get_active_job_run()` already prevents duplicate runs
- Build artifacts could be deleted manually to force rebuild
- Consider adding "rebuild reason" for logging/debugging
- Could emit metrics/events for monitoring
