#!/usr/bin/env python3
"""
Create CML Applications for SDN Screening System using the Application API.
This script creates both the SDN API and Flask UI as CML applications.
"""

import os
import sys
import time
from typing import Dict, Any, Optional

try:
    import cmlapi
    from cmlapi.rest import ApiException
except ImportError:
    print("❌ cmlapi library not found. Installing...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "cmlapi"], check=True)
    import cmlapi
    from cmlapi.rest import ApiException


class CMLApplicationCreator:
    """Create CML Applications using the cmlapi library."""
    
    def __init__(self):
        """Initialize the application creator."""
        self.project_id = os.environ.get("CDSW_PROJECT_ID")
        
        if not self.project_id:
            print("Missing required environment variable:")
            print(f"  CDSW_PROJECT_ID: {self.project_id}")
            sys.exit(1)
        
        # Initialize CML API client (handles authentication automatically)
        try:
            self.client = cmlapi.default_client()
            print(f"✅ CML API client initialized")
            print(f"Project ID: {self.project_id}")
        except Exception as e:
            print(f"❌ Failed to initialize CML API client: {e}")
            sys.exit(1)
    
    def create_application(self, app_config: Dict[str, Any]) -> Optional[str]:
        """Create a CML application using cmlapi."""
        print(f"📱 Creating application: {app_config['name']}")
        
        try:
            # Create application request object
            create_app_request = cmlapi.CreateApplicationRequest(
                project_id=self.project_id,
                name=app_config["name"],
                description=app_config.get("description", ""),
                script=app_config["script"],
                kernel=app_config.get("kernel", "python3"),
                cpu=app_config.get("cpu", 2),
                memory=app_config.get("memory", 4),
                nvidia_gpu=app_config.get("gpu", 0),
                runtime_identifier=app_config.get("runtime_id", ""),
                environment=app_config.get("environment", {}),
                subdomain=app_config.get("subdomain", ""),
                bypass_authentication=app_config.get("bypass_auth", True)
            )
            
            # Create the application
            response = self.client.create_application(
                project_id=self.project_id,
                body=create_app_request
            )
            
            app_id = response.id
            print(f"✅ Created application: {app_config['name']} (ID: {app_id})")
            return app_id
            
        except ApiException as e:
            print(f"❌ Failed to create application {app_config['name']}: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error creating application {app_config['name']}: {e}")
            return None
    
    def wait_for_application(self, app_id: str, timeout_seconds: int = 300) -> bool:
        """Wait for application to be running."""
        print(f"⏳ Waiting for application {app_id} to start...")
        
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            try:
                # Get application status
                app = self.client.get_application(
                    project_id=self.project_id,
                    application_id=app_id
                )
                
                status = app.status
                print(f"   Status: {status}")
                
                if status == "running":
                    url = app.url or ""
                    print(f"✅ Application is running: {url}")
                    return True
                elif status in ["failed", "stopped"]:
                    print(f"❌ Application failed to start: {status}")
                    return False
                    
            except ApiException as e:
                print(f"⚠️  Error checking application status: {e}")
            
            time.sleep(10)  # Check every 10 seconds
        
        print("⏰ Application did not start within timeout")
        return False


def main():
    """Create CML applications for SDN screening system."""
    print("=" * 60)
    print("Creating CML Applications for SDN Screening System")
    print("=" * 60)
    
    creator = CMLApplicationCreator()
    
    # Define applications to create
    applications = [
        {
            "name": "SDN API",
            "description": "SDN Screening API with AI-powered matching",
            "script": "scripts/run_sdn_api.py",
            "kernel": "python3",
            "cpu": 4,
            "memory": 8,
            "gpu": 0,
            "subdomain": "sdn-api",
            "bypass_auth": True,
            "environment": {
                "API_HOST": "0.0.0.0",
                "API_PORT": "8000",
                "USE_LLM": "true",
                "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "")
            },
            "runtime_id": "docker.repository.cloudera.com/cloudera/cdsw/ml-runtime-pbj-jupyterlab-python3.11-standard:2025.01.3-b8"
        },
        {
            "name": "SDN Web UI",
            "description": "Web interface for SDN screening",
            "script": "scripts/run_flask_ui.py", 
            "kernel": "python3",
            "cpu": 2,
            "memory": 4,
            "gpu": 0,
            "subdomain": "sdn-ui",
            "bypass_auth": True,
            "environment": {
                "FLASK_APP": "flask_ui.app.app",
                "FLASK_ENV": "production",
                "USE_LLM": "true",
                "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "")
            },
            "runtime_id": "docker.repository.cloudera.com/cloudera/cdsw/ml-runtime-pbj-jupyterlab-python3.11-standard:2025.01.3-b8"
        }
    ]
    
    created_apps = []
    
    # Create each application
    for app_config in applications:
        app_id = creator.create_application(app_config)
        if app_id:
            created_apps.append({
                "id": app_id,
                "name": app_config["name"]
            })
        else:
            print(f"❌ Failed to create {app_config['name']}")
    
    # Wait for applications to start
    print("\n" + "=" * 60)
    print("Waiting for applications to start...")
    print("=" * 60)
    
    for app in created_apps:
        success = creator.wait_for_application(app["id"], timeout_seconds=300)
        if not success:
            print(f"⚠️  Application {app['name']} may not have started properly")
    
    print("\n" + "=" * 60)
    print("✅ CML Application creation completed!")
    print("=" * 60)
    
    if created_apps:
        print("Created applications:")
        for app in created_apps:
            print(f"  - {app['name']} (ID: {app['id']})")
    else:
        print("❌ No applications were created successfully")
        sys.exit(1)


if __name__ == "__main__":
    main()