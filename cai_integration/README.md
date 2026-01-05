# Open-WebUI CML Integration

This document provides instructions for deploying and testing the Open-WebUI application in a Cloudera Machine Learning (CML) environment.

## Overview

This integration package is designed to automate the deployment of the Open-WebUI application to CML. It consists of the following components:

- **`deploy_to_cml.py`**: The main entry script that creates the CML project and sets up the necessary jobs.
- **`jobs_config.yaml`**: The configuration file that defines the CML jobs.
- **`setup_environment.py`**: A script to set up the Python environment within the CML session.
- **`run_merged_app.py`**: A script to install frontend/backend dependencies and run the Open-WebUI application.

## Prerequisites

Before you begin, ensure you have the following:

1.  **CML Workspace**: Access to a CML workspace.
2.  **Environment Variables**: The following environment variables must be set in your local environment where you will run the deployment script:
    - `CML_HOST`: The URL of your CML workspace.
    - `CML_API_KEY`: Your CML API key.
    - `GH_PAT`: A GitHub Personal Access Token with `repo` scope to allow CML to clone the repository.
    - `OPENAI_API_KEY`: (Optional) Your OpenAI API key if you want to use OpenAI models.

## Manual Deployment and Testing



Follow these steps to manually deploy and test the Open-WebUI application in CML.



### Step 1: Run the Deployment Script



From the root of this repository, run the deployment script:



```bash

python cai_integration/deploy_to_cml.py

```



This script will perform the following actions:

- Connect to your CML workspace.

- Create a new CML project named `open-webui`.

- Build a custom CML Runtime with all dependencies pre-installed.

- Create a CML Application that uses the new custom runtime.



### Step 2: Access Open-WebUI



Once the deployment script has successfully completed, navigate to the "Applications" tab in your CML project. You will find the "Open-WebUI" application. Click on it to access the application.



## CML Application Description



### Open-WebUI (Application)



- **Script**: `cai_integration/run_merged_app.py`

- **Description**: This application starts the backend server on the port specified by the `$CDSW_APP_PORT` environment variable. All dependencies are pre-installed in the custom CML Runtime.
