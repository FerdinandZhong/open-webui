#!/usr/bin/env python3
"""
Local test script to verify CML connection and retrieve project information.
This script tests basic API connectivity and retrieves the project ID.

Usage:
    python test_cml_connection.py
"""

import os
import requests
import json


class CMLTester:
    def __init__(self):
        """Initialize CML connection tester."""
        self.cml_host = os.environ.get("CML_HOST", "https://ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site/")
        self.api_key = os.environ.get("CML_API_KEY", "")
        self.project_name = "open-webui"

        print("=" * 70)
        print("🧪 CML Connection Test")
        print("=" * 70)
        print(f"\n📋 Configuration:")
        print(f"   CML Host: {self.cml_host}")
        print(f"   API Key: {'***' + self.api_key[-4:] if self.api_key else 'NOT SET'}")
        print(f"   Project Name: {self.project_name}")

        if not self.cml_host or not self.api_key:
            print("\n❌ Error: Missing required environment variables")
            print("   Required: CML_HOST, CML_API_KEY")
            raise SystemExit(1)

        # Setup API base URL and headers
        self.api_url = f"{self.cml_host.rstrip('/')}/api/v2"
        print(f"   API URL: {self.api_url}")

        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key.strip()}",
        }
        print("\n✅ CML Tester initialized successfully.\n")

    def make_request(self, method: str, endpoint: str, data: dict = None, params: dict = None):
        """Make an API request to CML."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        print(f"➡️  {method} {url}")
        if params:
            print(f"   Params: {params}")
        if data:
            print(f"   Data: {json.dumps(data, indent=2)}")

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params,
                timeout=30,
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
                try:
                    error_data = response.json()
                    print(f"   Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"   Error Body: {response.text}")
                return None

        except Exception as e:
            print(f"❌ An error occurred during the API request: {e}")
            return None

    def test_auth(self):
        """Test basic authentication."""
        print("\n" + "=" * 70)
        print("1️⃣  Testing Authentication")
        print("=" * 70)
        result = self.make_request("GET", "projects", params={"page_size": 1})
        if result is not None:
            print("✅ Authentication successful!")
            return True
        else:
            print("❌ Authentication failed!")
            return False

    def search_project(self):
        """Search for the open-webui project."""
        print("\n" + "=" * 70)
        print("2️⃣  Searching for Project")
        print("=" * 70)
        search_filter = f'{{"name":"{self.project_name}"}}'
        print(f"🔍 Searching for project: {self.project_name}")

        result = self.make_request(
            "GET", "projects", params={"search_filter": search_filter, "page_size": 50}
        )

        if result:
            projects = result.get("projects", [])
            for project in projects:
                if project.get("name") == self.project_name:
                    project_id = project.get("id")
                    print(f"\n✅ Found project: {self.project_name}")
                    print(f"   Project ID: {project_id}")
                    print(f"   Status: {project.get('creation_status', 'unknown')}")
                    print(f"   Created: {project.get('created_at', 'N/A')}")
                    print(f"   Owner: {project.get('creator', {}).get('name', 'N/A')}")
                    return project_id
            print(f"\n❌ Project '{self.project_name}' not found in CML")
            print(f"   Found {len(projects)} projects total")
            if projects:
                print("   Available projects:")
                for p in projects:
                    print(f"     - {p.get('name')} (ID: {p.get('id')})")
            return None
        else:
            print("❌ Failed to search for projects.")
            return None

    def get_project_details(self, project_id: str):
        """Get detailed project information."""
        print("\n" + "=" * 70)
        print("3️⃣  Getting Project Details")
        print("=" * 70)
        result = self.make_request("GET", f"projects/{project_id}")

        if result:
            print(f"\n✅ Project Details:")
            print(f"   Name: {result.get('name')}")
            print(f"   ID: {result.get('id')}")
            print(f"   Status: {result.get('creation_status')}")
            print(f"   Visibility: {result.get('visibility')}")
            print(f"   Created: {result.get('created_at')}")
            print(f"   Owner: {result.get('owner', {}).get('name')}")
            return result
        else:
            print("❌ Failed to get project details.")
            return None

    def list_project_files(self, project_id: str):
        """List files in the project."""
        print("\n" + "=" * 70)
        print("4️⃣  Listing Project Files")
        print("=" * 70)
        result = self.make_request("GET", f"projects/{project_id}/files")

        if result:
            files = result.get("files", [])
            print(f"\n✅ Found {len(files)} files in project:")
            for file in files[:20]:  # Show first 20 files
                print(f"   - {file.get('path')} ({file.get('type', 'unknown')})")
            if len(files) > 20:
                print(f"   ... and {len(files) - 20} more files")
            return files
        else:
            print("❌ Failed to list project files.")
            return None

    def list_project_jobs(self, project_id: str):
        """List jobs in the project."""
        print("\n" + "=" * 70)
        print("5️⃣  Listing Project Jobs")
        print("=" * 70)
        result = self.make_request("GET", f"projects/{project_id}/jobs")

        if result:
            jobs = result.get("jobs", [])
            print(f"\n✅ Found {len(jobs)} jobs in project:")
            for job in jobs:
                print(f"   - {job.get('name')} (ID: {job.get('id')})")
            return jobs
        else:
            print("❌ Failed to list project jobs.")
            return None

    def run_all_tests(self):
        """Run all tests."""
        print("\n🚀 Starting all tests...\n")

        # Test 1: Authentication
        if not self.test_auth():
            print("\n❌ Cannot proceed without authentication!")
            return False

        # Test 2: Search for project
        project_id = self.search_project()
        if not project_id:
            print("\n❌ Cannot proceed without project!")
            return False

        # Test 3: Get project details
        project_details = self.get_project_details(project_id)

        # Test 4: List files
        files = self.list_project_files(project_id)

        # Test 5: List jobs
        jobs = self.list_project_jobs(project_id)

        print("\n" + "=" * 70)
        print("✅ All tests completed!")
        print("=" * 70)
        print(f"\n📝 Summary:")
        print(f"   Project ID: {project_id}")
        print(f"   Project Status: {project_details.get('creation_status') if project_details else 'N/A'}")
        print(f"   Files in Project: {len(files) if files else 0}")
        print(f"   Jobs in Project: {len(jobs) if jobs else 0}")

        return True


def main():
    """Main execution function."""
    try:
        tester = CMLTester()
        tester.run_all_tests()
    except SystemExit:
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
