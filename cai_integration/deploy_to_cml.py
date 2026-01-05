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
        self.cml_host = os.environ.get("CML_HOST")
        self.api_key = os.environ.get("CML_API_KEY")
        self.project_name = "open-webui"  # Fixed name - git sync will update code

        if not all([self.cml_host, self.api_key]):
            print("Error: Missing required environment variables")
            print("Required: CML_HOST, CML_API_KEY")
            sys.exit(1)

        # Setup API base URL and headers - Use v2 API with Bearer token (confirmed working)
        self.api_url = f"{self.cml_host.rstrip('/')}/api/v2"

        # Use Bearer token authentication (confirmed working with your CML instance)
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key.strip()}",
        }

    def make_request(
        self, method: str, endpoint: str, data: Dict = None, files: Dict = None, params: Dict = None
    ) -> Optional[Dict]:
        """Make an API request to CML."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"

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

            if 200 <= response.status_code < 300:
                if response.text:
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        return {}
                return {}
            else:
                return None

        except Exception as e:
            return None

    def search_projects(self, project_name: str) -> Optional[str]:
        """Search for a project by name using the search API."""
        search_filter = f'{{"name":"{project_name}"}}'

        result = self.make_request(
            "GET", "projects", params={"search_filter": search_filter, "page_size": 50}
        )

        if result:
            projects = result.get("projects", [])
            for project in projects:
                if project.get("name") == project_name:
                    project_id = project.get("id")
                    return project_id
            return None
        else:
            return None

    def get_or_create_project(self) -> Optional[tuple[str, bool]]:
        """Get existing project or create a new one."""
        project_id = self.search_projects(self.project_name)
        if project_id:
            return project_id, False

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
                git_url = f"https://{github_token}@github.com/{github_repo}.git"
                project_data["git_url"] = git_url
                has_git_url = True

        result = self.make_request("POST", "projects", data=project_data)

        if result:
            project_id = result.get("id")
            return project_id, has_git_url
        else:
            return None

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

        if parent_job_id:
            job_data["parent_job_id"] = parent_job_id

        result = self.make_request("POST", f"projects/{project_id}/jobs", data=job_data)

        if result:
            job_id = result.get("id")
            return job_id
        else:
            return None

    def update_job(self, project_id: str, job_id: str, job_config: Dict[str, Any]) -> bool:
        """Update an existing job in the CML project."""
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

        return result is not None

    def list_jobs(self, project_id: str) -> Dict[str, str]:
        """List all jobs in a project."""
        result = self.make_request("GET", f"projects/{project_id}/jobs")

        if result:
            jobs = {}
            for job in result.get("jobs", []):
                jobs[job.get("name", "")] = job.get("id", "")
            return jobs
        return {}

    def create_or_update_jobs(self, project_id: str) -> None:
        """Create or update all jobs from the config file."""
        import yaml

        config_path = "cai_integration/jobs_config.yaml"

        if not os.path.exists(config_path):
            return

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        jobs_config = config.get("jobs", {})
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
        app_data = {
            "name": "Open-WebUI",
            "project_id": project_id,
            "subdomain": f"open-webui-{project_id}",
            "script": "cai_integration/run_merged_app.py",
            "kernel": "python3",
            "cpu": 2,
            "memory": 8,
            "runtime_identifier": "docker.repository.cloudera.com/cloudera/cdsw/ml-runtime-pbj-jupyterlab-python3.11-standard:2025.09.1-b5",
        }
        self.make_request("POST", "applications", data=app_data)

    def deploy(self):
        """Main deployment process."""
        project_result = self.get_or_create_project()
        if not project_result:
            sys.exit(1)
        
        project_id, _ = project_result

        self.create_or_update_jobs(project_id)
        self.create_application(project_id)

def main():
    """Main execution function."""
    try:
        deployer = CMLDeployer()
        deployer.deploy()
    except Exception as e:
        sys.exit(1)


if __name__ == "__main__":
    main()
