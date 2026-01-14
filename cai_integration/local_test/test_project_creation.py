#!/usr/bin/env python3
"""
Local test script to test CML project creation.
Tests the get_or_create_project functionality.
"""

import os
import sys
import json
import requests
from typing import Optional, Dict, Any

# Configuration
CML_HOST = os.environ.get("CML_HOST", "")
CML_API_KEY = os.environ.get("CML_API_KEY", "")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
GH_PAT = os.environ.get("GH_PAT", "")

PROJECT_NAME = "open-webui"
VERBOSE = os.environ.get("VERBOSE", "false").lower() == "true"


class CMLProjectTester:
    """Test CML project creation functionality."""

    def __init__(self):
        """Initialize the tester."""
        print("[*] Initializing CML Project Tester...")

        # Check for required environment variables
        if not CML_HOST or not CML_API_KEY:
            print("[-] Missing environment variables")
            print("    Required: CML_HOST, CML_API_KEY")
            print("    Optional: GITHUB_REPOSITORY, GH_PAT")
            print("\nQuick setup:")
            print("  export CML_HOST='https://your-cml-instance.cloudera.site'")
            print("  export CML_API_KEY='your-api-key'")
            sys.exit(1)

        self.api_url = f"{CML_HOST.rstrip('/')}/api/v2"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {CML_API_KEY.strip()}",
        }

        if VERBOSE:
            print("[DEBUG] Environment variables:")
            print(f"  CML_HOST: {CML_HOST}")
            print(f"  CML_API_KEY: {'***' if CML_API_KEY else '(not set)'}")
            print(f"  GITHUB_REPOSITORY: {GITHUB_REPOSITORY or '(not set)'}")
            print(f"  GH_PAT: {'***' if GH_PAT else '(not set)'}")

        print(f"[+] API URL: {self.api_url}")
        print(f"[+] Project Name: {PROJECT_NAME}")

        # Test basic connectivity
        self._test_connectivity()

    def _test_connectivity(self) -> bool:
        """Test basic connectivity to CML API."""
        if VERBOSE:
            print("[DEBUG] Testing CML API connectivity...")
        try:
            response = requests.get(
                f"{self.api_url}/projects",
                headers=self.headers,
                timeout=10,
                params={"page_size": 1}
            )
            if response.status_code == 200:
                if VERBOSE:
                    print("[DEBUG] ✅ CML API connectivity OK")
                return True
            else:
                print(f"[-] API connectivity failed: HTTP {response.status_code}")
                print(f"    Response: {response.text[:200]}")
                return False
        except requests.exceptions.ConnectionError as e:
            print(f"[-] Connection error: {e}")
            print(f"    Check CML_HOST: {CML_HOST}")
            return False
        except requests.exceptions.Timeout:
            print(f"[-] Connection timeout")
            print(f"    Check network connectivity to: {CML_HOST}")
            return False
        except Exception as e:
            print(f"[-] Unexpected error during connectivity test: {e}")
            return False

    def make_request(
        self, method: str, endpoint: str, data: Dict = None, params: Dict = None
    ) -> Optional[Dict]:
        """Make an API request to CML."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"

        if VERBOSE:
            print(f"[DEBUG] {method} {url}")
            if params:
                print(f"[DEBUG]   Params: {params}")
            if data:
                print(f"[DEBUG]   Data: {json.dumps(data, indent=2)}")
        else:
            print(f"    {method} {url}")

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            else:
                print(f"[-] Unsupported method: {method}")
                return None

            if response.status_code in [200, 201]:
                if VERBOSE:
                    print(f"[DEBUG] Response: {response.status_code} OK")
                return response.json()
            else:
                print(f"[-] API Error {response.status_code}: {response.text}")
                return None

        except requests.exceptions.Timeout:
            print(f"[-] Request timeout")
            return None
        except Exception as e:
            print(f"[-] Request error: {e}")
            return None

    def search_projects(self, name: str) -> Optional[str]:
        """Search for existing project by name."""
        print(f"\n[*] Searching for project: {name}")

        # Use exact same format as deploy_to_cml.py for consistency
        search_filter = f'{{"name":"{name}"}}'
        params = {"page_size": 50, "search_filter": search_filter}

        if VERBOSE:
            print(f"[DEBUG] Search filter: {search_filter}")

        result = self.make_request("GET", "projects", params=params)

        if result and result.get("projects"):
            for project in result["projects"]:
                if project.get("name") == name:
                    project_id = project.get("id")
                    status = project.get("creation_status", "unknown")
                    print(f"[+] Found project: {name} (ID: {project_id}, Status: {status})")
                    return project_id

        print(f"[-] Project not found")
        return None

    def create_project(self) -> Optional[tuple[str, bool]]:
        """Create a new CML project."""
        print(f"\n[*] Creating project: {PROJECT_NAME}")

        project_data = {
            "name": PROJECT_NAME,
            "description": "Open-WebUI: User-friendly WebUI for LLMs",
            "visibility": "private",
            "template": "git",
        }

        has_git_url = False

        if GH_PAT and GITHUB_REPOSITORY:
            print(f"[*] Configuring Git repository: {GITHUB_REPOSITORY}")
            git_url = f"https://{GH_PAT}@github.com/{GITHUB_REPOSITORY}.git"
            project_data["git_url"] = git_url
            has_git_url = True
            print(f"[+] Git URL configured (masked for security)")
        else:
            if not GH_PAT:
                print("[-] GH_PAT not set - Git repository will not be configured")
            if not GITHUB_REPOSITORY:
                print("[-] GITHUB_REPOSITORY not set - Git repository will not be configured")

        result = self.make_request("POST", "projects", data=project_data)

        if result:
            project_id = result.get("id")
            creation_status = result.get("creation_status", "unknown")
            print(f"[+] Project created successfully")
            print(f"    Project ID: {project_id}")
            print(f"    Status: {creation_status}")
            return project_id, has_git_url
        else:
            print(f"[-] Failed to create project")
            return None

    def get_project_details(self, project_id: str) -> Optional[Dict]:
        """Get detailed information about a project."""
        print(f"\n[*] Getting project details: {project_id}")

        result = self.make_request("GET", f"projects/{project_id}")

        if result:
            print(f"[+] Project details retrieved")
            print(f"    Name: {result.get('name')}")
            print(f"    Status: {result.get('creation_status')}")
            print(f"    Description: {result.get('description')}")
            print(f"    Visibility: {result.get('visibility')}")
            if result.get("git_url"):
                print(f"    Git URL: [configured]")
            return result
        else:
            print(f"[-] Failed to get project details")
            return None

    def test_get_or_create_project(self) -> Optional[str]:
        """Test the get_or_create_project workflow."""
        print("\n" + "="*60)
        print("Testing: Get or Create Project Workflow")
        print("="*60)

        # Step 1: Try to find existing project
        project_id = self.search_projects(PROJECT_NAME)

        if project_id:
            print(f"\n[+] Using existing project: {project_id}")
            self.get_project_details(project_id)
            return project_id

        # Step 2: Create new project if not found
        print(f"\n[*] Project does not exist, creating new one...")
        result = self.create_project()

        if result:
            project_id, has_git = result
            print(f"\n[+] Project creation workflow successful")
            print(f"    Project ID: {project_id}")
            print(f"    Git configured: {has_git}")

            # Step 3: Verify the created project
            print(f"\n[*] Verifying created project...")
            self.get_project_details(project_id)

            return project_id
        else:
            print(f"\n[-] Project creation failed")
            return None


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("🏁 CML Project Creation Test Suite")
    print("="*60)

    try:
        tester = CMLProjectTester()

        # Run the main workflow test
        project_id = tester.test_get_or_create_project()

        if project_id:
            print("\n" + "="*60)
            print("✅ All tests passed!")
            print("="*60)
        else:
            print("\n" + "="*60)
            print("❌ Tests failed!")
            print("="*60)
            sys.exit(1)

    except Exception as e:
        print(f"\n[-] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Quick diagnostic info
    print("\n📋 CML Project Creation Test")
    print("=" * 60)
    print("\nQuick Start:")
    print("  1. Set environment variables:")
    print("     export CML_HOST='https://your-cml-instance.cloudera.site'")
    print("     export CML_API_KEY='your-api-key'")
    print("     export GITHUB_REPOSITORY='your-org/your-repo'  # Optional")
    print("     export GH_PAT='your-github-token'               # Optional")
    print("\n  2. Run the test:")
    print("     python cai_integration/local_test/test_project_creation.py")
    print("\n  3. For verbose debugging output:")
    print("     VERBOSE=true python cai_integration/local_test/test_project_creation.py")
    print("\n" + "=" * 60)

    main()
