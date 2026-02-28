#!/usr/bin/env python3
"""
Test script to create a job in CML and debug script path issues.

This script tests job creation with different script path formats to identify
the correct path format that CML expects.

Usage:
    python test_job_creation.py [project_id]

Examples:
    python test_job_creation.py 4u5o-hjm5-h635-k7u2
"""

import os
import requests
import json
import sys


class CMLJobTester:
    def __init__(self, project_id: str = None):
        """Initialize CML job tester."""
        self.cml_host = os.environ.get("CML_HOST", "https://ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site/")
        self.api_key = os.environ.get("CML_API_KEY", "")
        self.project_id = project_id or os.environ.get("PROJECT_ID", "")

        print("=" * 80)
        print("🧪 CML Job Creation Test")
        print("=" * 80)
        print(f"\n📋 Configuration:")
        print(f"   CML Host: {self.cml_host}")
        print(f"   API Key: {'***' + self.api_key[-4:] if self.api_key else 'NOT SET'}")
        print(f"   Project ID: {self.project_id}")

        if not self.cml_host or not self.api_key:
            print("\n❌ Error: Missing required environment variables")
            print("   Required: CML_HOST, CML_API_KEY")
            raise SystemExit(1)

        if not self.project_id:
            print("\n❌ Error: Missing project ID")
            print("   Usage: python test_job_creation.py <project_id>")
            raise SystemExit(1)

        # Setup API base URL and headers
        self.api_url = f"{self.cml_host.rstrip('/')}/api/v2"
        print(f"   API URL: {self.api_url}")

        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key.strip()}",
        }
        print("\n✅ CML Job Tester initialized successfully.\n")

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
                try:
                    response_json = response.json()
                    print(f"   Response: {json.dumps(response_json, indent=2)}")
                except:
                    print(f"   Response Body: {response.text[:500]}")

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
            print(f"❌ An error occurred during the API request: {e}")
            return None

    def verify_project_exists(self):
        """Verify project exists and is ready."""
        print("\n" + "=" * 80)
        print("1️⃣  Verifying Project")
        print("=" * 80)
        result = self.make_request("GET", f"projects/{self.project_id}")

        if result:
            status = result.get("creation_status", "unknown")
            print(f"\n✅ Project found")
            print(f"   Name: {result.get('name')}")
            print(f"   Status: {status}")
            if status not in ["success", "ready", "running"]:
                print(f"⚠️  WARNING: Project status is '{status}', expected 'success' or 'ready'")
            return True
        else:
            print(f"\n❌ Project not found or unable to access")
            return False

    def list_project_files(self):
        """List files in project to verify git clone."""
        print("\n" + "=" * 80)
        print("2️⃣  Listing Project Files (Git Clone Status)")
        print("=" * 80)
        result = self.make_request("GET", f"projects/{self.project_id}/files")

        if result:
            files = result.get("files", [])
            print(f"\n✅ Found {len(files)} files")

            # Check for key files
            file_names = [f.get("path", "") for f in files]
            key_files = [".git_sync.py", "cai_integration/setup_environment.py", "cai_integration/build_frontend.py"]

            print("\n📂 Key Files Status:")
            for key_file in key_files:
                if any(key_file in fname for fname in file_names):
                    print(f"   ✅ {key_file} - FOUND")
                else:
                    print(f"   ❌ {key_file} - NOT FOUND")

            # Show first 20 files
            print("\n📋 Sample Files (first 20):")
            for file in files[:20]:
                print(f"   - {file.get('path')}")
            if len(files) > 20:
                print(f"   ... and {len(files) - 20} more files")

            return True
        else:
            print(f"\n❌ Failed to list project files")
            return False

    def test_job_creation(self, script_path: str, job_name: str, description: str):
        """Test creating a job with a specific script path."""
        print("\n" + "=" * 80)
        print(f"Testing: {description}")
        print("=" * 80)
        print(f"Script path: {script_path}\n")

        job_data = {
            "project_id": self.project_id,
            "name": f"Test Job - {job_name}",
            "type": "manual",
            "script": script_path,
            "arguments": "",
            "kernel": "python3",
            "cpu": 1,
            "memory": 2,
            "gpu": 0,
            "runtime_identifier": "docker.repository.cloudera.com/cloudera/cdsw/ml-runtime-pbj-jupyterlab-python3.11-standard:2026.01.1-b6",
            "environment": {},
            "timeout": 300,
        }

        result = self.make_request("POST", f"projects/{self.project_id}/jobs", data=job_data)

        if result:
            job_id = result.get("id")
            print(f"\n✅ SUCCESS! Job created with ID: {job_id}")
            print(f"   Name: {result.get('name')}")
            print(f"   Script: {result.get('script')}")
            return job_id
        else:
            print(f"\n❌ FAILED - See error response above")
            return None

    def test_all_script_paths(self):
        """Test different script path formats."""
        print("\n" + "=" * 80)
        print("3️⃣  Testing Script Path Formats")
        print("=" * 80)

        test_cases = [
            ("/home/cdsw/.git_sync.py", "git_sync_absolute", "Absolute path: /home/cdsw/.git_sync.py"),
            (".git_sync.py", "git_sync_relative", "Relative path: .git_sync.py"),
            ("/home/cdsw/cai_integration/setup_environment.py", "setup_env_absolute", "Absolute: cai_integration/setup_environment.py"),
            ("cai_integration/setup_environment.py", "setup_env_relative", "Relative: cai_integration/setup_environment.py"),
        ]

        results = {}
        for script_path, key, description in test_cases:
            print(f"\n{'─' * 80}")
            job_id = self.test_job_creation(script_path, key, description)
            results[key] = {
                "script_path": script_path,
                "success": job_id is not None,
                "job_id": job_id,
            }

        return results

    def run_all_tests(self):
        """Run all tests."""
        print("\n🚀 Starting all tests...\n")

        # Test 1: Verify project
        if not self.verify_project_exists():
            print("\n❌ Cannot proceed without valid project!")
            return False

        # Test 2: List files to check git clone
        if not self.list_project_files():
            print("\n⚠️  Cannot list files - git clone may not be complete")
            print("   Proceeding anyway to test job creation...")

        # Test 3: Test different script paths
        results = self.test_all_script_paths()

        print("\n" + "=" * 80)
        print("✅ All tests completed!")
        print("=" * 80)

        print("\n📊 Summary:")
        successful = [k for k, v in results.items() if v["success"]]
        failed = [k for k, v in results.items() if not v["success"]]

        print(f"\n   ✅ Successful ({len(successful)}):")
        for key in successful:
            print(f"      - {key}: {results[key]['script_path']}")

        print(f"\n   ❌ Failed ({len(failed)}):")
        for key in failed:
            print(f"      - {key}: {results[key]['script_path']}")

        if successful:
            print(f"\n🎯 RECOMMENDED SCRIPT PATH:")
            recommended = results[successful[0]]["script_path"]
            print(f"   Use: {recommended}")

        return len(successful) > 0


def main():
    """Main execution function."""
    try:
        project_id = sys.argv[1] if len(sys.argv) > 1 else None
        tester = CMLJobTester(project_id)
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except SystemExit:
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
