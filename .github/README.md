# GitHub Actions CI/CD Setup

## Required GitHub Secrets

To enable automated deployment to Cloudera Machine Learning, configure the following secrets in your GitHub repository settings:

### 1. CML_HOST
- **Description**: The base URL of your Cloudera Machine Learning workspace
- **Example**: `https://ml.your-domain.cloudera.com`
- **How to find**: Copy the URL from your browser when logged into CML (without trailing paths)

### 2. CML_API_KEY
- **Description**: Your personal CML API key for authentication
- **How to obtain**:
  1. Log into your CML wo rkspace 
  2. Go to User Settings → API Keys
  3. Click "Create API Key"
  4. Copy the generated key (save it securely, it won't be shown again)

### 3. GH_PAT (GitHub Personal Access Token)
- **Description**: GitHub Personal Access Token for repository cloning in CML
- **Required for**: Automatic repository cloning when creating CML projects
- **How to create**:
  1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
  2. Or directly visit: https://github.com/settings/tokens
  3. Click "Generate new token (classic)"
  4. Give it a descriptive name (e.g., "CML Repository Access")
  5. Select the `repo` scope (full control of private repositories)
  6. Click "Generate token"
  7. Copy the token (starts with `ghp_`)
  8. Save it securely - it won't be shown again!
- **Token format**: Should start with `ghp_` (e.g., `....`)
- **Note**: This is different from the automatic GITHUB_TOKEN and provides broader repository access

## Setting Up Secrets in GitHub

1. Navigate to your GitHub repository
2. Go to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add each secret with the exact names above
5. Paste the corresponding values

## Workflow Files

### `.github/workflows/ci.yml`
- Runs on every push and pull request
- Executes tests and linting
- Validates code quality

### `.github/workflows/deploy-cml.yml`
- Runs only on pushes to the main branch
- Deploys to Cloudera Machine Learning
- Creates/updates project and jobs

## Local Testing

Before pushing to GitHub, test locally:

```bash
# Run tests
uv run pytest -q

# Check linting
uv run ruff check .

# Test job execution locally
python test_run_jobs.py
```

## Deployment Process

1. **Automatic Deployment** (Recommended)
   - Push code to the `main` branch
   - GitHub Actions will automatically:
     - Run tests and linting
     - Deploy to CML if tests pass
     - Create project and jobs in CML

2. **Manual Deployment**
   - Go to Actions tab in GitHub
   - Select "Deploy to Cloudera ML" workflow
   - Click "Run workflow"
   - Select branch and run

## Troubleshooting

### API Key Issues
- Ensure your API key has necessary permissions
- Check if the key hasn't expired
- Verify the key is correctly copied (no extra spaces)

### Connection Issues
- Verify CML_HOST URL is correct (https://, no trailing slash)
- Check if you're behind a firewall or VPN
- Ensure CML workspace is accessible from GitHub Actions

### Job Creation Failures
- Check if you have permissions to create projects/jobs
- Verify runtime configurations in `config/jobs_config.yaml`
- Check CML resource quotas

## Support

For issues related to:
- **GitHub Actions**: Check workflow logs in the Actions tab
- **CML Integration**: Review CML documentation or contact your admin
- **Code Issues**: Create an issue in this repository