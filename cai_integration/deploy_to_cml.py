#!/usr/bin/env python3
"""
Deploy open-webui project to Cloudera Machine Learning using REST API.
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
        print("🚀 Initializing CML Deployer...")
        self.cml_host = os.environ.get("CML_HOST")
        self.api_key = os.environ.get("CML_API_KEY")
        self.project_name = "open-webui"  # Fixed name - git sync will update code

        print(f"CML Host: {self.cml_host}")
        print(f"Project Name: {self.project_name}")

        if not all([self.cml_host, self.api_key]):
            print("❌ Error: Missing required environment variables")
            print("Required: CML_HOST, CML_API_KEY")
            sys.exit(1)

        # Setup API base URL and headers - Use v2 API with Bearer token (confirmed working)
        self.api_url = f"{self.cml_host.rstrip('/')}/api/v2"
        print(f"API URL: {self.api_url}")

        # Use Bearer token authentication (confirmed working with your CML instance)
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key.strip()}",
        }
        print("✅ CML Deployer initialized successfully.")

    def make_request(
        self, method: str, endpoint: str, data: Dict = None, files: Dict = None, params: Dict = None
    ) -> Optional[Dict]:
        """Make an API request to CML."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        print(f"➡️  {method} {url}")
        if params:
            print(f"   Params: {params}")
        if data:
            print(f"   Data: {json.dumps(data, indent=2)}")

        try:
            headers = self.headers.copy()

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

            print(f"⬅️  Response: {response.status_code}")
            if response.text:
                print(f"   Response Body: {response.text[:500]}...")

            if 200 <= response.status_code < 300:
                if response.text:
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        print("⚠️  Could not decode JSON from response.")
                        return {}
                return {}
            else:
                print(f"❌ API Request Failed: {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ An error occurred during the API request: {e}")
            return None

    def search_projects(self, project_name: str) -> Optional[str]:
        """Search for a project by name using the search API."""
        print(f"🔍 Searching for project: {project_name}")
        search_filter = f'{{"name":"{project_name}"}}'

        result = self.make_request(
            "GET", "projects", params={"search_filter": search_filter, "page_size": 50}
        )

        if result:
            projects = result.get("projects", [])
            for project in projects:
                if project.get("name") == project_name:
                    project_id = project.get("id")
                    print(f"✅ Found existing project with ID: {project_id}")
                    return project_id
            print("ℹ️  No existing project found.")
            return None
        else:
            print("❌ Failed to search for projects.")
            return None

    def get_or_create_project(self) -> Optional[tuple[str, bool]]:
        """Get existing project or create a new one."""
        print("\n--- Getting or Creating Project ---")
        project_id = self.search_projects(self.project_name)
        if project_id:
            return project_id, False

        print(f"📦 Creating new project: {self.project_name}")
        project_data = {
            "name": self.project_name,
            "description": "Open-WebUI: User-friendly WebUI for LLMs",
            "visibility": "private",
            "template": "git",
        }

        has_git_url = False
        github_token = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
        
        if github_token:
            github_repo = os.environ.get("GITHUB_REPOSITORY", "")
            if github_repo:
                print(f"🔗 Configuring Git repository: {github_repo}")
                git_url = f"https://{github_token}@github.com/{github_repo}.git"
                project_data["git_url"] = git_url
                has_git_url = True
            else:
                print("⚠️  GITHUB_REPOSITORY environment variable not set. Cannot configure Git repository.")
        else:
            print("⚠️  GH_PAT or GITHUB_TOKEN not found. Cannot configure Git repository.")

        result = self.make_request("POST", "projects", data=project_data)

        if result:
            project_id = result.get("id")
            print(f"✅ Successfully created project with ID: {project_id}")
            return project_id, has_git_url
        else:
            print("❌ Failed to create project.")
            return None

    def create_job(
        self, project_id: str, job_config: Dict[str, Any], parent_job_id: Optional[str] = None
    ) -> Optional[str]:
        """Create a job in the CML project."""
        print(f"📄 Creating job: {job_config['name']}")
        
        script_path = job_config.get("script", "")
        if not script_path.startswith("/"):
            script_path = f"/home/cdsw/{script_path}"

        job_data = {
            "project_id": project_id,
            "name": job_config["name"],
            "type": "manual",
            "script": script_path,
            "arguments": job_config.get("arguments", ""),
            "kernel": job_config.get("kernel", "python3"),
            "cpu": job_config.get("cpu", 2),
            "memory": job_config.get("memory", 4),
            "gpu": job_config.get("gpu", 0),
            "runtime_identifier": job_config.get("runtime_id"),
            "environment": job_config.get("environment", {}),
            "timeout": job_config.get("timeout", 3600),
        }

        if parent_job_id:
            job_data["parent_job_id"] = parent_job_id
            print(f"   Parent Job ID: {parent_job_id}")

        result = self.make_request("POST", f"projects/{project_id}/jobs", data=job_data)

        if result:
            job_id = result.get("id")
            print(f"✅ Successfully created job with ID: {job_id}")
            return job_id
        else:
            print(f"❌ Failed to create job: {job_config['name']}")
            return None

    def update_job(self, project_id: str, job_id: str, job_config: Dict[str, Any]) -> bool:
        """Update an existing job in the CML project."""
        print(f"🔄 Updating job: {job_config['name']} (ID: {job_id})")
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

        if result is not None:
            print(f"✅ Successfully updated job: {job_config['name']}")
            return True
        else:
            print(f"❌ Failed to update job: {job_config['name']}")
            return False

    def list_jobs(self, project_id: str) -> Dict[str, str]:
        """List all jobs in a project."""
        print("📋 Listing existing jobs...")
        result = self.make_request("GET", f"projects/{project_id}/jobs")

        if result:
            jobs = {}
            for job in result.get("jobs", []):
                jobs[job.get("name", "")] = job.get("id", "")
            print(f"Found {len(jobs)} jobs.")
            return jobs
        print("❌ Failed to list jobs.")
        return {}

    def create_or_update_jobs(self, project_id: str) -> None:
        """Create or update all jobs from the config file."""
        print("\n--- Creating or Updating Jobs ---")
        import yaml

        config_path = "cai_integration/jobs_config.yaml"
        print(f"Loading job configurations from: {config_path}")

        if not os.path.exists(config_path):
            print(f"⚠️  Job config file not found at: {config_path}")
            return

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        jobs_config = config.get("jobs", {})
        print(f"Found {len(jobs_config)} job configurations.")
        existing_jobs = self.list_jobs(project_id)
        processed_jobs = {}

        for job_key, job_config in jobs_config.items():
            job_name = job_config["name"]
            
            parent_job_id = None
            if "parent_job_key" in job_config:
                parent_key = job_config["parent_job_key"]
                parent_job_id = processed_jobs.get(parent_key) or existing_jobs.get(
                    jobs_config.get(parent_key, {}).get("name", "")
                )

            if job_name in existing_jobs:
                job_id = existing_jobs[job_name]
                if self.update_job(project_id, job_id, job_config):
                    processed_jobs[job_key] = job_id
            else:
                job_id = self.create_job(project_id, job_config, parent_job_id)
                if job_id:
                    processed_jobs[job_key] = job_id

    def create_application(self, project_id: str) -> None:
        """Create a CML application."""
        print("\n--- Creating Application ---")
        app_data = {
            "name": "Open-WebUI",
            "project_id": project_id,
            "subdomain": f"open-webui-{project_id.lower()}",
            "script": "cai_integration/run_merged_app.py",
            "kernel": "python3",
            "cpu": 8,
            "memory": 64,
            "runtime_identifier": "docker.repository.cloudera.com/cloudera/cdsw/ml-runtime-pbj-jupyterlab-python3.11-standard:2025.09.1-b5",
            "bypass_authentication": True,
        }
        print("Application data:")
        print(json.dumps(app_data, indent=2))
        
        result = self.make_request("POST", f"projects/{project_id}/applications", data=app_data)
        if result is not None:
            print("✅ Application creation/update request sent successfully.")
        else:
            print("❌ Failed to send application creation/update request.")

    def trigger_job(self, project_id: str, job_id: str) -> Optional[str]:
        """Trigger a job to run."""
        print(f"▶️  Triggering job with ID: {job_id}")
        result = self.make_request("POST", f"projects/{project_id}/jobs/{job_id}/runs")
        if result and result.get("id"):
            run_id = result["id"]
            print(f"✅ Job run created with ID: {run_id}")
            return run_id
        else:
            print("❌ Failed to trigger job.")
            return None

    def wait_for_job_completion(self, project_id: str, job_id: str, run_id: str, timeout_seconds: int = 600) -> bool:
        """Wait for a job run to complete."""
        print(f"⏳ Waiting for job run {run_id} to complete...")
        import time
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            status_result = self.make_request("GET", f"projects/{project_id}/jobs/{job_id}/runs/{run_id}")
            if status_result:
                status = status_result.get("status")
                print(f"   Current status: {status}")
                if status in ["succeeded", "success"]:
                    print("✅ Job completed successfully.")
                    return True
                elif status in ["failed", "error"]:
                    print("❌ Job failed.")
                    return False
            time.sleep(10)
        print("⏰ Timed out waiting for job to complete.")
        return False

    def deploy(self):
        """Main deployment process."""
        print("\n🏁 Starting CML Deployment Process 🏁")
        project_result = self.get_or_create_project()
        if not project_result:
            print("❌ Deployment failed: Could not get or create project.")
            sys.exit(1)
        
        project_id, _ = project_result

        self.create_or_update_jobs(project_id)
        
        jobs = self.list_jobs(project_id)
        env_job_id = jobs.get("Create Python Environment")
        build_job_id = jobs.get("Build Frontend")

        if env_job_id and build_job_id:
            env_run_id = self.trigger_job(project_id, env_job_id)
            if env_run_id:
                if self.wait_for_job_completion(project_id, env_job_id, env_run_id):
                    build_run_id = self.trigger_job(project_id, build_job_id)
                    if build_run_id:
                        if self.wait_for_job_completion(project_id, build_job_id, build_run_id):
                            self.create_application(project_id)
                        else:
                            print("❌ Frontend build job failed. Application not created.")
                    else:
                        print("❌ Failed to trigger frontend build job.")
                else:
                    print("❌ Environment setup job failed. Application not created.")
            else:
                print("❌ Failed to trigger environment setup job.")
        else:
            print("⚠️  Required jobs not found. Cannot create application.")

        print("\n🎉 Deployment process finished. Check CML for status. 🎉")

def main():
    """Main execution function."""
    try:
        deployer = CMLDeployer()
        deployer.deploy()
    except Exception as e:
        sys.exit(1)


if __name__ == "__main__":
    main()
