#!/usr/bin/env python3
"""
Deploy Open-WebUI as CAI Application.

This script creates/updates a CAI Application to serve Open-WebUI.
It runs as a job after environment setup and frontend build complete.

Environment Variables:
    CDSW_APIV2_KEY: Cloudera AI API key (required - auto-set by CML)
    CDSW_DOMAIN: CAI domain URL (required - auto-set by CML)
"""

import json
import os
import sys
import requests
from typing import Optional, Dict, Any


# Runtime image version
RUNTIME_IMAGE = "docker.repository.cloudera.com/cloudera/cdsw/ml-runtime-pbj-jupyterlab-python3.11-standard:2026.01.1-b6"


def print_status(message: str, status: str = "info"):
    """Print status message with emoji."""
    icons = {
        "info": "ℹ️ ",
        "success": "✅",
        "warning": "⚠️ ",
        "error": "❌"
    }
    icon = icons.get(status, "")
    print(f"{icon} {message}")


def get_cai_client(api_key: str) -> requests.Session:
    """Create authenticated CAI API client."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    })
    return session


def get_project_id(client: requests.Session, domain: str) -> str:
    """Get current CAI project ID from environment or API."""
    # CML sets CDSW_PROJECT_ID in job environment
    project_id = os.environ.get("CDSW_PROJECT_ID")
    if project_id:
        print_status(f"Using project ID from environment: {project_id}", "info")
        return project_id

    # Fallback: search for project by name
    project_name = os.environ.get("CDSW_PROJECT", "open-webui")
    url = f"{domain}/api/v2/projects"

    try:
        response = client.get(url)
        response.raise_for_status()

        data = response.json()
        projects = data.get("projects", []) if isinstance(data, dict) else data

        for project in projects:
            if project.get("name") == project_name:
                project_id = project.get("id")
                print_status(f"Found project: {project_name} ({project_id})", "success")
                return str(project_id)

        raise ValueError(f"Project '{project_name}' not found")

    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to get projects: {str(e)}")


def create_or_update_application(
    client: requests.Session,
    domain: str,
    project_id: str
) -> Dict[str, Any]:
    """Create or update CAI Application for Open-WebUI."""
    app_name = "Open-WebUI"
    subdomain = f"open-webui-{project_id.lower()}"

    app_config = {
        "name": app_name,
        "description": "Open-WebUI: User-friendly WebUI for LLMs",
        "subdomain": subdomain,
        "script": "cai_integration/run_merged_app.py",
        "kernel": "python3",
        "cpu": 8,
        "memory": 64,
        "bypass_authentication": True,
        "runtime_identifier": RUNTIME_IMAGE,
        "environment": {}
    }

    # Check if application already exists
    list_url = f"{domain}/api/v2/projects/{project_id}/applications"
    response = client.get(list_url)
    response.raise_for_status()

    data = response.json()
    existing_apps = data.get("applications", []) if isinstance(data, dict) else data

    existing_app = None
    for app in existing_apps:
        if app.get("name") == app_name:
            existing_app = app
            break

    if existing_app:
        # Update existing application
        print_status(f"Updating existing application: {app_name}", "info")
        update_url = f"{domain}/api/v2/projects/{project_id}/applications/{existing_app['id']}"

        response = client.patch(update_url, json=app_config)
        response.raise_for_status()
        print_status(f"Application updated (ID: {existing_app['id']})", "success")

        # Restart application
        restart_url = f"{update_url}/restart"
        response = client.post(restart_url)
        response.raise_for_status()
        print_status("Application restart initiated", "success")

        return existing_app

    else:
        # Create new application
        print_status(f"Creating new application: {app_name}", "info")

        response = client.post(list_url, json=app_config)
        response.raise_for_status()

        created_app = response.json()
        print_status(f"Application created (ID: {created_app.get('id', 'N/A')})", "success")

        return created_app


def main():
    print("=" * 60)
    print("Deploy Open-WebUI as CAI Application")
    print("=" * 60)
    print()

    # Get credentials from environment (auto-set by CML)
    api_key = os.environ.get("CDSW_APIV2_KEY")
    domain = os.environ.get("CDSW_DOMAIN")

    if not api_key:
        print_status("CDSW_APIV2_KEY not set", "error")
        sys.exit(1)

    if not domain:
        print_status("CDSW_DOMAIN not set", "error")
        sys.exit(1)

    # Ensure domain has https:// scheme
    if not domain.startswith(("http://", "https://")):
        domain = f"https://{domain}"

    print(f"Domain: {domain}")
    print()

    try:
        # Create API client
        print_status("Authenticating with CAI...", "info")
        client = get_cai_client(api_key)

        # Get project ID
        print_status("Getting project information...", "info")
        project_id = get_project_id(client, domain)

        # Deploy application
        print_status("Deploying Open-WebUI application...", "info")
        print()
        app = create_or_update_application(client, domain, project_id)

        if not app or not app.get("id"):
            print_status("Application deployment failed: No application ID returned", "error")
            sys.exit(1)

        print()
        print("=" * 60)
        print_status("Application Deployed Successfully!", "success")
        print("=" * 60)
        print()

        # Print application details
        subdomain = f"open-webui-{project_id.lower()}"
        app_url = f"{domain}/{subdomain}"

        print("Application Details:")
        print(f"  Name:     Open-WebUI")
        print(f"  ID:       {app.get('id', 'N/A')}")
        print(f"  Status:   Starting (wait 2-3 minutes)")
        print()
        print(f"Access URL: {app_url}")
        print()

    except requests.HTTPError as e:
        print_status(f"HTTP Error: {e.response.status_code}", "error")
        print(f"Response: {e.response.text}")
        sys.exit(1)

    except ValueError as e:
        print_status(f"Error: {str(e)}", "error")
        sys.exit(1)

    except Exception as e:
        print_status(f"Unexpected Error: {type(e).__name__}: {str(e)}", "error")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
    # Don't call sys.exit(0) - CML's IPython interprets it as an exception
