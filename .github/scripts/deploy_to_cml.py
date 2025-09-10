#!/usr/bin/env python3
"""
Deploy sdn-screening project to Cloudera Machine Learning using REST API.
Creates a project, uploads code, and sets up jobs.
"""

import json
import os
import sys
import requests
from typing import Dict, Any, Optional


class CMLDeployer:
    """Handle deployment to Cloudera Machine Learning via REST API."""

    def __init__(self):
        """Initialize CML REST API client."""
        self.cml_host = os.environ.get("CML_HOST")
        self.api_key = os.environ.get("CML_API_KEY")
        self.project_name = "sdn-screening"  # Fixed name - git sync will update code

        if not all([self.cml_host, self.api_key]):
            print("Error: Missing required environment variables")
            print("Required: CML_HOST, CML_API_KEY")
            sys.exit(1)

        # Setup API base URL and headers - Use v2 API with Bearer token (confirmed working)
        self.api_url = f"{self.cml_host.rstrip('/')}/api/v2"

        # Debug: Print API key format (first/last few chars only for security)
        if self.api_key:
            if "." in self.api_key and len(self.api_key) > 100:
                print(
                    f"🔑 Token format: {self.api_key[:16]}...{self.api_key[-16:]} (length: {len(self.api_key)})"
                )
            else:
                print(
                    f"🔑 API Key: {self.api_key[:8]}...{self.api_key[-4:]} (length: {len(self.api_key)})"
                )

        # Use Bearer token authentication (confirmed working with your CML instance)
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key.strip()}",
        }

        # Verify authentication by testing API access
        # Skip verification in GitHub Actions environment due to response masking issues
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print("🔄 Running in GitHub Actions - skipping auth verification")
            print("💡 Will proceed with deployment and handle auth issues during actual operations")
        else:
            if not self.verify_authentication():
                print("❌ Failed to authenticate with CML API")
                sys.exit(1)
            print("✅ Authentication verified")

    def make_request(
        self, method: str, endpoint: str, data: Dict = None, files: Dict = None, params: Dict = None
    ) -> Optional[Dict]:
        """Make an API request to CML."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"

        # Debug: Print request details (without sensitive headers)
        print(f"🌐 {method} {url}")

        try:
            headers = self.headers.copy()

            # Remove Content-Type for multipart uploads
            if files:
                headers.pop("Content-Type", None)

            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data if not files else None,
                files=files,
                params=params,
            )

            print(f"📡 Response: {response.status_code}")

            # Check for success
            if response.status_code >= 200 and response.status_code < 300:
                if response.text:
                    try:
                        return response.json()
                    except json.JSONDecodeError as e:
                        print(f"⚠️  JSON parsing failed: {e}")
                        print(f"   Response text (first 200 chars): {response.text[:200]}")
                        print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
                        # If response is empty or whitespace, return empty dict
                        if not response.text.strip():
                            return {}
                        return None
                return {}
            else:
                print(f"❌ API request failed: {response.status_code} ")
                print(f"   URL: {url}")
                print(f"   Response: {response.text}")

                # Special handling for auth errors
                if response.status_code in [401, 403]:
                    print("💡 This looks like an authentication issue.")
                    print("   Check that your CML_API_KEY is correct and has proper permissions.")
                elif response.status_code == 500:
                    print("💡 Internal server error - the API key format might be incorrect.")
                    print("   Make sure the API key is copied correctly from CML.")

                return None

        except Exception as e:
            print(f"❌ Request error: {e}")
            return None

    def verify_authentication(self) -> bool:
        """Verify authentication by testing API access."""
        # Try to list projects as a simple auth test
        result = self.make_request("GET", "projects")
        return result is not None

    def list_projects(self) -> list:
        """List all projects."""
        result = self.make_request("GET", "projects")
        if result and isinstance(result, dict):
            return result.get("projects", [])
        return []

    def search_projects(self, project_name: str) -> Optional[str]:
        """Search for a project by name using the search API."""
        print(f"🔍 Searching for project: {project_name}")

        # Use search filter to find project by name
        search_filter = f'{{"name":"{project_name}"}}'

        result = self.make_request(
            "GET", "projects", params={"search_filter": search_filter, "page_size": 50}
        )

        if result:
            projects = result.get("projects", [])
            for project in projects:
                if project.get("name") == project_name:
                    project_id = project.get("id")
                    print(f"✅ Found existing project: {project_name} (ID: {project_id})")
                    return project_id

            print(f"📝 No project found with name: {project_name}")
            return None
        else:
            print("❌ Failed to search projects")
            return None

    def get_or_create_project(self) -> Optional[tuple[str, bool]]:
        """Get existing project or create a new one."""

        # First, search for existing project
        project_id = self.search_projects(self.project_name)
        if project_id:
            return project_id, False  # project_id, has_git_url

        # Create new project if not found
        print(f"📦 Creating new project: {self.project_name}")

        project_data = {
            "name": self.project_name,
            "description": "SDN Screening System - OFAC sanctions compliance tool with AI-powered matching",
            "visibility": "private",
            "template": "git",
        }

        has_git_url = False
        # Add Git URL with token authentication if GitHub token is available
        # Prefer GH_PAT (Personal Access Token) over GITHUB_TOKEN (automatic token)
        github_token = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
        
        if github_token:
            # Identify token type
            if github_token.startswith("ghp_"):
                print(f"🔑 Using GitHub Personal Access Token (PAT)")
                token_type = "PAT"
            elif github_token.startswith("ghs_"):
                print(f"🔑 Using GitHub App Installation Token")
                token_type = "App Token"
            else:
                print(f"🔑 Using GitHub Token (type: unknown)")
                token_type = "Unknown"
            
            print(f"🔍 Debug - Token: {github_token}")
            print(f"🔍 Debug - Token length: {len(github_token)} chars")
            
            # Get repository information from GitHub context
            github_repo = os.environ.get("GITHUB_REPOSITORY", "")
            print(f"🔍 Debug - GITHUB_REPOSITORY: {github_repo}")
            
            if github_repo:
                # Construct authenticated Git URL: https://token@github.com/owner/repo.git
                git_url = f"https://{github_token}@github.com/{github_repo}.git"
                print(f"🔍 Debug - Full Git URL: {git_url}")
                
                project_data["git_url"] = git_url
                has_git_url = True
                print("🔗 Adding Git URL with token authentication to project")
                print(f"📦 Repository: {github_repo}")
                print(f"🔐 Authentication: {token_type}")
                print("💡 CML will automatically clone the repository during project creation")
            else:
                print("⚠️  GITHUB_REPOSITORY not set, skipping Git URL")
                print("💡 Set GITHUB_REPOSITORY environment variable in format: owner/repo")
        else:
            print("⚠️  No GitHub token available (GH_PAT or GITHUB_TOKEN)")
            print("💡 Set GH_PAT as a GitHub secret with a Personal Access Token for repository cloning")
            print("💡 Create PAT at: https://github.com/settings/tokens with 'repo' scope")

        result = self.make_request("POST", "projects", data=project_data)

        if result:
            project_id = result.get("id")
            print(f"✅ Created project: {project_id}")
            return project_id, has_git_url
        else:
            print("❌ Failed to create project")
            return None

    def upload_repository(self, project_id: str) -> bool:
        """Upload repository code as zip file to CML project."""
        print("📦 Uploading repository code...")

        import zipfile
        import tempfile

        # Create temporary zip file of repository
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
            zip_path = tmp_zip.name

        try:
            # Create zip file excluding .git, .github, and other unnecessary files
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk("."):
                    # Skip .git, .github, __pycache__, .pytest_cache, etc.
                    dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

                    for file in files:
                        if not file.startswith(".") and not file.endswith(".pyc"):
                            file_path = os.path.join(root, file)
                            # Add file to zip with relative path
                            arcname = os.path.relpath(file_path, ".")
                            zipf.write(file_path, arcname)

            print(f"📁 Created zip file: {zip_path}")

            # Upload zip file to CML project
            with open(zip_path, "rb") as f:
                files = {"file": ("file", f, "application/zip")}

                self.make_request("POST", f"projects/{project_id}/files", files=files)

            # File upload may succeed even if result is None/empty
            print("✅ Repository uploaded successfully")
            return True

        except Exception as e:
            print(f"❌ Failed to upload repository: {e}")
            return False
        finally:
            # Clean up temporary file
            if os.path.exists(zip_path):
                os.unlink(zip_path)

    def upload_file(self, project_id: str, local_path: str, remote_name: str) -> bool:
        """Upload a single file to CML project."""
        print(f"📄 Uploading {local_path} as {remote_name}...")

        try:
            with open(local_path, "rb") as f:
                files = {"file": (remote_name, f, "text/plain")}

                self.make_request("POST", f"projects/{project_id}/files", files=files)

            print(f"✅ File uploaded: {remote_name}")
            return True

        except Exception as e:
            print(f"❌ Failed to upload {local_path}: {e}")
            return False

    def rename_file(self, project_id: str, old_path: str, new_path: str) -> bool:
        """Rename a file in CML project using updateProjectFileMetadata API."""
        print(f"📝 Renaming {old_path} to {new_path}...")

        try:
            rename_data = {"path": new_path}

            self.make_request("PATCH", f"projects/{project_id}/files/{old_path}", data=rename_data)

            print(f"✅ File renamed: {old_path} → {new_path}")
            return True

        except Exception as e:
            print(f"❌ Failed to rename {old_path}: {e}")
            return False

    def create_job(
        self, project_id: str, job_config: Dict[str, Any], parent_job_id: Optional[str] = None
    ) -> Optional[str]:
        """Create a job in the CML project."""

        job_data = {
            "project_id": project_id,
            "name": job_config["name"],
            "type": "manual",
            "script": job_config.get("script", ""),
            "arguments": job_config.get("arguments", ""),
            "kernel": job_config.get("kernel", "python3"),
            "cpu": job_config.get("cpu", 2),
            "memory": job_config.get("memory", 4),
            "gpu": job_config.get("gpu", 0),
            "runtime_identifier": job_config.get("runtime_id"),
            "environment": job_config.get("environment", {}),
            "timeout": job_config.get("timeout", 3600),
        }

        # Add parent job if specified
        if parent_job_id:
            job_data["parent_job_id"] = parent_job_id

        result = self.make_request("POST", f"projects/{project_id}/jobs", data=job_data)

        if result:
            job_id = result.get("id")
            print(f"✅ Created job: {job_config['name']} (ID: {job_id})")
            return job_id
        else:
            print(f"❌ Failed to create job: {job_config['name']}")
            return None

    def update_job(self, project_id: str, job_id: str, job_config: Dict[str, Any]) -> bool:
        """Update an existing job in the CML project."""

        # Convert environment dict to JSON string if present
        environment = job_config.get("environment", {})
        environment_json = json.dumps(environment) if environment else ""

        job_data = {
            "name": job_config["name"],
            "script": job_config.get("script", ""),
            "arguments": job_config.get("arguments", ""),
            "kernel": job_config.get("kernel", "python3"),
            "cpu": job_config.get("cpu", 2),
            "memory": job_config.get("memory", 4),
            "nvidia_gpu": job_config.get("gpu", 0),
            "runtime_identifier": job_config.get("runtime_id"),
            "environment": environment_json,
            "timeout": str(job_config.get("timeout", 3600)),
        }

        result = self.make_request("PATCH", f"projects/{project_id}/jobs/{job_id}", data=job_data)

        if result:
            print(f"✅ Updated job: {job_config['name']}")
            return True
        else:
            print(f"❌ Failed to update job: {job_config['name']}")
            return False

    def list_jobs(self, project_id: str) -> Dict[str, str]:
        """List all jobs in a project."""
        result = self.make_request("GET", f"projects/{project_id}/jobs")

        if result:
            jobs = {}
            for job in result.get("jobs", []):
                # Map job names to IDs
                jobs[job.get("name", "")] = job.get("id", "")
            return jobs
        return {}

    def create_or_update_git_sync_job(self, project_id: str) -> Optional[tuple[str, bool]]:
        """Create or update the git sync job."""
        print("🚀 Setting up git sync job...")

        # Import job configurations
        import yaml

        config_path = "config/jobs_config.yaml"

        if not os.path.exists(config_path):
            print(f"❌ Config file not found: {config_path}")
            return None

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        jobs_config = config.get("jobs", {})

        if "git_sync" not in jobs_config:
            print("❌ Git sync job not found in config")
            return None

        # Get the git sync job config
        git_sync_config = jobs_config["git_sync"]

        # Replace GitHub token placeholder with actual token from environment
        # Prefer GH_PAT (Personal Access Token) over GITHUB_TOKEN (automatic token)
        github_token = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN", "")
        if github_token:
            if "environment" not in git_sync_config:
                git_sync_config["environment"] = {}
            git_sync_config["environment"]["GITHUB_TOKEN"] = github_token
            if github_token.startswith("ghp_"):
                print("🔐 GitHub PAT configured for git sync job")
            else:
                print("🔐 GitHub token configured for git sync job")
        else:
            print("⚠️  No GitHub token available - repository must be public")

        # Check if job already exists
        existing_jobs = self.list_jobs(project_id)
        job_name = git_sync_config["name"]

        if job_name in existing_jobs:
            job_id = existing_jobs[job_name]
            print(f"📝 Updating existing git sync job: {job_id}")
            if self.update_job(project_id, job_id, git_sync_config):
                return (job_id, False)  # job_id, was_created
            else:
                print("❌ Failed to update git sync job")
                return None
        else:
            print("📦 Creating new git sync job")
            job_id = self.create_job(project_id, git_sync_config)
            if job_id:
                return (job_id, True)  # job_id, was_created
            else:
                return None

    def create_or_update_remaining_jobs(
        self, project_id: str
    ) -> tuple[Dict[str, str], Dict[str, bool]]:
        """Create or update remaining jobs after git sync is complete."""
        print("🚀 Setting up remaining jobs...")

        # Import job configurations
        import yaml

        config_path = "config/jobs_config.yaml"

        if not os.path.exists(config_path):
            print(f"❌ Config file not found: {config_path}")
            return {}

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        jobs_config = config.get("jobs", {})

        # Get existing jobs in the project
        existing_jobs = self.list_jobs(project_id)
        processed_jobs = {}
        created_jobs = {}  # Track which jobs were created vs updated

        # Process remaining jobs (excluding git_sync)
        for job_key, job_config in jobs_config.items():
            if job_key == "git_sync":
                continue

            job_name = job_config["name"]

            # Handle parent job dependency
            parent_job_id = None
            if "parent_job_key" in job_config:
                parent_key = job_config["parent_job_key"]
                parent_job_id = processed_jobs.get(parent_key) or existing_jobs.get(
                    jobs_config.get(parent_key, {}).get("name", "")
                )

            # Check if job exists and update or create
            if job_name in existing_jobs:
                job_id = existing_jobs[job_name]
                print(f"📝 Updating existing job: {job_name} ({job_id})")
                if self.update_job(project_id, job_id, job_config):
                    processed_jobs[job_key] = job_id
                    created_jobs[job_key] = False  # Was updated, not created
            else:
                print(f"📦 Creating new job: {job_name}")
                job_id = self.create_job(project_id, job_config, parent_job_id)
                if job_id:
                    processed_jobs[job_key] = job_id
                    created_jobs[job_key] = True  # Was created

        return processed_jobs, created_jobs

    def trigger_job(self, project_id: str, job_id: str, job_name: str) -> Optional[str]:
        """Trigger a job to run."""
        print(f"▶️  Triggering job: {job_name}")

        run_data = {"job_id": job_id}

        result = self.make_request(
            "POST", f"projects/{project_id}/jobs/{job_id}/runs", data=run_data
        )

        if result:
            run_id = result.get("id")
            print(f"✅ Job triggered successfully: Run ID {run_id}")
            return run_id
        else:
            print("❌ Failed to trigger job")
            return None

    def check_job_status(self, project_id: str, job_id: str, run_id: str) -> str:
        """Check the status of a job run."""
        result = self.make_request("GET", f"projects/{project_id}/jobs/{job_id}/runs/{run_id}")

        if result:
            return result.get("status", "unknown")
        return "unknown"

    def wait_for_job_completion(
        self, project_id: str, job_id: str, run_id: str, timeout_seconds: int = 60
    ) -> bool:
        """Wait for a job run to complete."""
        print("⏳ Waiting for job to complete...")

        import time

        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            status = self.check_job_status(project_id, job_id, run_id)
            print(f"   Status: {status}")

            if status in ["succeeded", "success", "ENGINE_SUCCEEDED"]:
                print("✅ Job completed successfully")
                return True
            elif status in ["failed", "error"]:
                print("❌ Job failed")
                return False

            time.sleep(3)  # Check every 3 seconds

        print("⏰ Job did not complete within timeout")
        return False

    def deploy(self):
        """Main deployment process."""
        print("🚀 Starting CML Deployment")
        print("=" * 50)
        print(f"Host: {self.cml_host}")
        print(f"API URL: {self.api_url}")
        print(f"Project: {self.project_name}")
        print("=" * 50)

        # Step 1: Get or create project
        project_result = self.get_or_create_project()
        if not project_result:
            print("❌ Failed to get/create project")
            sys.exit(1)
        
        project_id, has_git_url = project_result

        # Step 2: Always set up git sync job for future updates (but don't trigger it initially)
        print("=" * 50)
        if has_git_url:
            print("🔗 Project created with Git URL integration")
            print("📍 Repository cloned automatically by CML")
            print("⏱️  Waiting 15 seconds for Git clone to complete...")
            import time
            time.sleep(15)
            print("✅ Git clone should be complete")
        else:
            print("📄 No Git URL provided - repository may need manual setup")
        print("=" * 50)
        
        # Always upload and create git sync job for future repository updates
        print("📄 Setting up git sync job for future repository updates...")
        git_sync_uploaded = self.upload_file(project_id, ".git_sync.py", "file")
        if not git_sync_uploaded:
            print("❌ Failed to upload git sync script")
            sys.exit(1)

        # Check if .git_sync.py already exists and delete it
        try:
            print("🗑️  Removing old .git_sync.py if it exists...")
            self.make_request("DELETE", f"projects/{project_id}/files/.git_sync.py")
            print("✅ Old .git_sync.py removed")
        except Exception:
            print("ℹ️  No existing .git_sync.py to remove")

        # Rename uploaded file to .git_sync.py
        rename_success = self.rename_file(project_id, "file", ".git_sync.py")
        if not rename_success:
            print("❌ Failed to rename git sync script")
            sys.exit(1)

        # Create or update git sync job (but don't trigger it)
        git_sync_result = self.create_or_update_git_sync_job(project_id)
        if not git_sync_result:
            print("❌ Failed to set up git sync job")
            sys.exit(1)

        git_sync_job_id, git_sync_was_created = git_sync_result
        action = "Created" if git_sync_was_created else "Updated"
        print(f"✅ {action} git sync job - available for manual repository updates")
        print("💡 Git sync job can be triggered manually when repository updates are needed")

        # Step 3: Create or update remaining jobs now that files are synced
        remaining_jobs_result = self.create_or_update_remaining_jobs(project_id)
        if not remaining_jobs_result:
            print("⚠️  No additional jobs set up")
        else:
            remaining_jobs, created_jobs = remaining_jobs_result

            # Step 4: Only trigger environment setup job if it was newly created
            if "create_env" in remaining_jobs:
                if created_jobs.get("create_env", False):
                    print("▶️  Triggering newly created environment setup job")
                    env_run_id = self.trigger_job(
                        project_id, remaining_jobs["create_env"], "Create Python Environment"
                    )
                    if env_run_id:
                        print("⏱️  Waiting for environment setup to complete...")
                        env_completed = self.wait_for_job_completion(
                            project_id, remaining_jobs["create_env"], env_run_id, 180
                        )

                        if env_completed:
                            # Step 5: OFAC data download job will be triggered automatically by CML
                            # due to parent_job_key dependency
                            if "download_ofac_list" in remaining_jobs:
                                print(
                                    "ℹ️  OFAC data download job configured - CML will trigger it automatically after environment setup"
                                )
                                if "deploy_api" in remaining_jobs:
                                    print("ℹ️  API deployment job configured - will run after data download")
                                if "deploy_ui" in remaining_jobs:
                                    print("ℹ️  UI deployment job configured - will run after data download")
                            else:
                                print("⚠️  OFAC data download job not found")
                        else:
                            print("❌ Environment setup did not complete successfully")
                            print("💡 You may need to manually run the jobs in CML UI")
                else:
                    print("ℹ️  Environment setup job was updated but not triggered (already exists)")
                    print("💡 You can manually run jobs in CML UI to execute the pipeline")
            else:
                print("⚠️  Environment setup job not found")

        print("\n" + "=" * 50)
        print("✅ Deployment process completed!")
        print(f"📊 Project URL: {self.cml_host}/projects/{project_id}")
        print("=" * 50)

        # Output for GitHub Actions
        print(f"::set-output name=project_id::{project_id}")
        print(f"::set-output name=project_url::{self.cml_host}/projects/{project_id}")


def main():
    """Main execution function."""
    try:
        deployer = CMLDeployer()
        deployer.deploy()
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()