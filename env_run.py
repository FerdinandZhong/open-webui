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
    print("✅ cmlapi is available")
except ImportError:
    print("❌ cmlapi not available - should have been installed during environment setup")
    sys.exit(1)


def list_applications(client, project_id):
    """List all applications in the project."""
    try:
        apps = client.list_applications(project_id=project_id)
        app_dict = {}
        for app in apps.applications:
            app_dict[app.name] = app.id
        return app_dict
    except Exception as e:
        print(f"⚠️  Could not list existing applications: {e}")
        return {}


def create_or_update_application(project_id, app_config):
    """Create or update a CML application using cmlapi SDK."""
    print(f"📱 Processing application: {app_config['name']}")
    
    try:
        # Create CML API client - uses default CML environment credentials
        client = cmlapi.default_client()
        
        # Check for existing applications
        existing_apps = list_applications(client, project_id)
        app_id = None
        
        if app_config["name"] in existing_apps:
            # Delete existing application to recreate with new settings
            app_id = existing_apps[app_config["name"]]
            print(f"🗑️  Deleting existing application: {app_config['name']} (ID: {app_id})")
            try:
                client.delete_application(project_id=project_id, application_id=app_id)
                print(f"✅ Deleted existing application")
                time.sleep(2)  # Wait for deletion to complete
            except Exception as e:
                print(f"⚠️  Could not delete existing application: {e}")
        
        # Create application request
        app_body = cmlapi.CreateApplicationRequest()
        
        # Basic application properties
        app_body.name = app_config["name"]
        app_body.description = app_config.get("description", "")
        app_body.script = app_config["script"]
        app_body.kernel = app_config.get("kernel", "python3")
        
        # Resource configuration
        app_body.cpu = float(app_config.get("cpu", 2))
        app_body.memory = float(app_config.get("memory", 4))
        app_body.nvidia_gpu = int(app_config.get("gpu", 0))
        
        # Runtime identifier if specified
        if app_config.get("runtime_id"):
            app_body.runtime_identifier = app_config["runtime_id"]
            
        # Environment variables
        app_body.environment = app_config.get("environment", {})
        
        # Application-specific settings
        if app_config.get("subdomain"):
            app_body.subdomain = app_config["subdomain"]
        app_body.bypass_authentication = app_config.get("bypass_auth", True)
        
        # Create the application
        print(f"📦 Creating new application: {app_config['name']}")
        app = client.create_application(app_body, project_id=project_id)
        app_id = app.id
        print(f"✅ Created application: {app_config['name']} (ID: {app_id})")
        
        # Try to start the application
        try:
            print(f"▶️  Starting application: {app_config['name']}")
            client.restart_application(project_id=project_id, application_id=app_id)
            print(f"✅ Application start initiated")
        except Exception as e:
            print(f"⚠️  Could not start application automatically: {e}")
            print("   You may need to start it manually from the CML UI")
        
        return app_id
        
    except Exception as e:
        print(f"❌ Error creating application {app_config['name']}: {e}")
        return None


def wait_for_application(project_id, app_id, timeout_seconds=300):
    """Wait for application to be running."""
    print(f"⏳ Waiting for application {app_id} to start...")
    
    try:
        # Create CML API client
        client = cmlapi.default_client()
        
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            try:
                # Get application status
                app = client.get_application(
                    project_id=project_id,
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
                    
            except Exception as e:
                print(f"⚠️  Error checking application status: {e}")
            
            time.sleep(10)  # Check every 10 seconds
        
        print("⏰ Application did not start within timeout")
        return False
        
    except Exception as e:
        print(f"❌ Error waiting for application: {e}")
        return False


def main():
    """Create CML applications for SDN screening system."""
    print("=" * 60)
    print("Creating CML Applications for SDN Screening System")
    print("=" * 60)
    
    # Get project ID
    project_id = os.getenv("CDSW_PROJECT_ID")
    if not project_id:
        print("❌ CDSW_PROJECT_ID environment variable not set")
        sys.exit(1)
    
    print(f"📋 Project ID: {project_id}")
    
    # Define application to create - single merged app
    applications = [
        {
            "name": "SDN Screening Application",
            "description": "Merged SDN Screening web interface with integrated API",
            "script": "scripts/run_merged_app.py",
            "kernel": "python3",
            "cpu": 4,
            "memory": 8,
            "gpu": 0,
            "subdomain": "sdn-screening",
            "bypass_auth": True,
            "environment": {
                "FLASK_ENV": "production",
                "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
                "USE_LLM": "true",
                "SDN_FILE_PATH": "data_list/sdn_final.csv",
                "API_HOST": "0.0.0.0",
                "API_PORT": "8000",
                "MAX_SEARCH_RESULTS": "10",
                "NAME_MATCH_THRESHOLD": "0.4",
                "CDSW_APP_PORT": "8090",
                "CDSW_READONLY_PORT": "8090"
            },
            "runtime_id": "docker.repository.cloudera.com/cloudera/cdsw/ml-runtime-pbj-jupyterlab-python3.11-standard:2025.01.3-b8"
        }
    ]
    
    created_apps = []
    
    # Create each application
    for app_config in applications:
        app_id = create_or_update_application(project_id, app_config)
        if app_id:
            created_apps.append({
                "id": app_id,
                "name": app_config["name"]
            })
        else:
            print(f"❌ Failed to create {app_config['name']}")
    
    # Don't wait for applications to start - let them start asynchronously
    print("\n" + "=" * 60)
    print("Applications will start in the background...")
    print("=" * 60)
    
    print("\n" + "=" * 60)
    print("✅ CML Application creation completed!")
    print("=" * 60)
    
    if created_apps:
        print("Created applications:")
        for app in created_apps:
            print(f"  - {app['name']} (ID: {app['id']})")
    else:
        print("❌ No applications were created successfully ")
        sys.exit(1)


if __name__ == "__main__":
    main()