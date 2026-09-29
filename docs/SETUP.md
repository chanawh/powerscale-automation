# Setup Guide

This guide provides detailed setup instructions for different environments and use cases.

## Table of Contents

- [Local Development Setup](#local-development-setup)
- [Windows Setup](#windows-setup)
- [Linux/macOS Setup](#linuxmacos-setup)
- [AWS Deployment Setup](#aws-deployment-setup)
- [CI/CD Setup](#cicd-setup)
- [Troubleshooting](#troubleshooting)

## Local Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- (Optional) Make for convenience commands
- (Optional) Virtual environment tool (venv, conda, etc.)

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/powerscale-automation.git
cd powerscale-automation
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Using venv
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Using conda
conda create -n powerscale-monitor python=3.12
conda activate powerscale-monitor
```

### Step 3: Install Dependencies

```bash
# Using Make
make install

# Or manually
pip install -r powerscale-monitor/requirements.txt
pip install -r powerscale-monitor/aws/aws-requirements.txt
```

### Step 4: Install Development Tools (Optional)

```bash
pip install pytest flake8 black isort pylint mypy pre-commit
```

### Step 5: Install Pre-commit Hooks (Optional)

```bash
pre-commit install
```

### Step 6: Test Local Setup

```bash
# Run tests
make test

# Run local CLI
make run-local
```

## Windows Setup

### Option 1: Using PowerShell

1. **Install Python**
   - Download from [python.org](https://www.python.org/downloads/)
   - Check "Add Python to PATH" during installation

2. **Install Git**
   - Download from [git-scm.com](https://git-scm.com/download/win)
   - This includes Git Bash for Unix-like commands

3. **Install Dependencies**
   ```powershell
   pip install -r powerscale-monitor\requirements.txt
   pip install -r powerscale-monitor\aws\aws-requirements.txt
   ```

4. **Build Deployment Package**
   ```powershell
   cd powerscale-monitor\aws
   .\build.ps1
   ```

5. **Deploy (if using manual deployment)**
   ```powershell
   .\deploy.ps1
   ```

### Option 2: Using Git Bash

1. **Install Git for Windows** (includes Git Bash)
2. **Use Unix-style commands**
   ```bash
   cd powerscale-monitor/aws
   ./build.sh
   ```

### Option 3: Using WSL (Windows Subsystem for Linux)

1. **Enable WSL**
   ```powershell
   wsl --install
   ```

2. **Use Linux commands in WSL**
   ```bash
   cd /mnt/c/path/to/powerscale-automation
   make build
   ```

### Option 4: Using Make on Windows

1. **Install Make**
   - Download from [equation.com](https://equation.com/ffmpeg/)
   - Or use via Chocolatey: `choco install make`

2. **Use Make commands**
   ```bash
   make build
   make test
   ```

## Linux/macOS Setup

### Step 1: Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv git make zip
```

**macOS (using Homebrew):**
```bash
brew install python3 git make zip
```

### Step 2: Clone and Setup

```bash
git clone https://github.com/your-username/powerscale-automation.git
cd powerscale-automation

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
make install
```

### Step 3: Test Setup

```bash
make test
make build
```

## AWS Deployment Setup

### Step 1: Configure AWS Credentials

```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure
```

You'll need:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., us-east-1)
- Default output format (json)

### Step 2: Verify Permissions

Ensure your AWS account has permissions to create:
- Lambda functions
- IAM roles and policies
- SNS topics
- EventBridge rules
- CloudWatch metrics and alarms

### Step 3: Set Up Terraform State Backend (Optional but Recommended)

```bash
# Create S3 bucket for Terraform state
aws s3 mb s3://your-terraform-state-bucket

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket your-terraform-state-bucket \
  --versioning-configuration Status=Enabled
```

### Step 4: Configure GitHub Secrets (for CI/CD)

Add these secrets to your GitHub repository:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `TERRAFORM_STATE_BUCKET`
- `POWERSCALE_HOST`
- `POWERSCALE_USERNAME`
- `POWERSCALE_PASSWORD`
- `ALERT_EMAILS`

### Step 5: Deploy Locally

```bash
# Build package
make build

# Configure Terraform
cd powerscale-monitor/aws/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Deploy
terraform init
terraform plan
terraform apply
```

### Step 6: Deploy via CI/CD

```bash
# Push to main branch
git add .
git commit -m "feat: initial deployment"
git push origin main

# Monitor deployment in GitHub Actions
```

## CI/CD Setup

### GitHub Actions Setup

1. **Repository Settings**
   - Go to Settings → Secrets and variables → Actions
   - Add required secrets (see AWS Deployment Setup)

2. **Enable Workflows**
   - `.github/workflows/validate.yml` - Runs on every push/PR
   - `.github/workflows/deploy.yml` - Runs on main branch push

3. **Manual Deployment**
   - Go to Actions tab
   - Select "Deploy" workflow
   - Click "Run workflow"

### Self-Hosted Runner Setup (Optional)

1. **Install Runner**
   ```bash
   # On your server
   mkdir actions-runner && cd actions-runner
   curl -o actions-runner-linux-x64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz
   tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz
   ./config.sh --url https://github.com/your-username/powerscale-automation --token YOUR_TOKEN
   ./run.sh
   ```

2. **Configure Workflow**
   ```yaml
   jobs:
     deploy:
       runs-on: self-hosted
   ```

## Environment-Specific Configurations

### Development Environment

```hcl
# terraform/terraform.tfvars.dev
aws_region = "us-east-1"
schedule_expression = "rate(30 minutes)"
alert_emails = ["dev@example.com"]
critical_threshold = 40
degraded_threshold = 70
```

### Staging Environment

```hcl
# terraform/terraform.tfvars.staging
aws_region = "us-east-1"
schedule_expression = "rate(10 minutes)"
alert_emails = ["staging@example.com"]
critical_threshold = 50
degraded_threshold = 80
```

### Production Environment

```hcl
# terraform/terraform.tfvars.prod
aws_region = "us-east-1"
schedule_expression = "rate(5 minutes)"
alert_emails = ["oncall@example.com", "ops@example.com"]
critical_threshold = 50
degraded_threshold = 80
```

## Troubleshooting

### Python Issues

**Problem:** Module not found errors
```bash
# Solution: Ensure virtual environment is activated
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

**Problem:** Permission denied when installing packages
```bash
# Solution: Use user directory or virtual environment
pip install --user package-name
# or
python -m venv .venv
```

### Build Issues

**Problem:** `zip` command not found (Windows)
```bash
# Solution: Use PowerShell script instead
.\build.ps1
```

**Problem:** Deployment package too large
```bash
# Solution: Check package contents
unzip -l deployment.zip
# Remove unnecessary dependencies
```

### Terraform Issues

**Problem:** Terraform init fails
```bash
# Solution: Check network connectivity and AWS credentials
aws sts get-caller-identity
```

**Problem:** State lock error
```bash
# Solution: Force unlock (use with caution)
terraform force-unlock <LOCK_ID>
```

### AWS Issues

**Problem:** Lambda timeout
```bash
# Solution: Increase timeout in Terraform
timeout = 60  # Increase from 30
```

**Problem:** IAM permission errors
```bash
# Solution: Check IAM policy
aws iam get-role-policy --role-name powerscale-monitor-role --policy-name PowerScaleMonitorPolicy
```

### CI/CD Issues

**Problem:** GitHub Actions fails
```bash
# Solution: Check logs in Actions tab
# Verify secrets are set correctly
# Test locally with act tool
```

**Problem:** Deployment fails in CI but works locally
```bash
# Solution: Check environment differences
# Verify AWS credentials in secrets
# Check Terraform backend configuration
```

## Cleanup and Teardown

### Local Destroy

```bash
# Using Make
make destroy

# Or manually
cd powerscale-monitor/aws/terraform
terraform init
terraform destroy
```

### CI/CD Destroy

To destroy resources via GitHub Actions:

1. Go to **Actions** tab in your repository
2. Select **Destroy** workflow
3. Click **Run workflow**
4. Select branch (usually `main`)
5. Click **Run workflow** button

⚠️ **Note**: The destroy workflow requires manual trigger for safety.

### What Gets Destroyed

When you run destroy, the following resources are removed:

| Resource | Name |
|----------|------|
| Lambda Function | `powerscale-monitor` |
| IAM Role | `powerscale-monitor-role` |
| IAM Policy | `PowerScaleMonitorPolicy` |
| SNS Topic | `powerscale-cluster-alerts` |
| SNS Subscription | Email subscription |
| EventBridge Rule | `powerscale-monitoring-schedule` |
| Lambda Permission | EventBridge invoke permission |
| CloudWatch Log Group | `/aws/lambda/powerscale-monitor` |
| CloudWatch Alarms | 3 alarms (health score critical/degraded, node down) |
| CloudWatch Dashboard | `PowerScale-Cluster-Monitor` |

### Cost Impact After Destroy

- **Lambda**: $0 (function deleted)
- **CloudWatch Metrics**: ~$0 (metrics stop being sent)
- **CloudWatch Logs**: ~$0 (log group deleted)
- **SNS**: $0 (topic deleted)
- **Total ongoing costs**: $0/month

### Verification After Destroy

```bash
# Verify Lambda is deleted
aws lambda get-function --function-name powerscale-monitor
# Should return error: ResourceNotFoundException

# Verify IAM role is deleted
aws iam get-role --role-name powerscale-monitor-role
# Should return error: NoSuchEntity

# Verify SNS topic is deleted
aws sns list-topics
# Should not show powerscale-cluster-alerts
```

### Manual Cleanup (If Terraform Fails)

If Terraform state is corrupted or unavailable:

```bash
# Delete Lambda function
aws lambda delete-function --function-name powerscale-monitor

# Delete EventBridge rule
aws events delete-rule --name powerscale-monitoring-schedule

# Delete IAM role and policy
aws iam delete-role-policy --role-name powerscale-monitor-role --policy-name PowerScaleMonitorPolicy
aws iam delete-role --role-name powerscale-monitor-role

# Delete SNS topic
aws sns delete-topic --topic-arn $(aws sns list-topics --query "Topics[?contains(TopicArn, 'powerscale')].TopicArn" --output text)

# Delete CloudWatch resources
aws logs delete-log-group --log-group-name /aws/lambda/powerscale-monitor
aws cloudwatch delete-alarms --alarm-names powerscale-health-score-critical powerscale-health-score-degraded powerscale-node-down
aws cloudwatch delete-dashboards --dashboard-names PowerScale-Cluster-Monitor
```

### Safety Tips

1. **Always review what will be destroyed**:
   ```bash
   terraform plan -destroy
   ```

2. **Backup Terraform state** before destroy (if you might redeploy):
   ```bash
   aws s3 cp s3://your-bucket/powerscale-monitor/terraform.tfstate terraform.tfstate.backup
   ```

3. **Verify in AWS Console** after destroy to confirm cleanup

4. **Check your AWS bill** to ensure no unexpected charges continue

5. **Keep documentation** of what was deployed for reference

### Troubleshooting Destroy Issues

**Problem:** Terraform destroy fails with state lock error
```bash
# Solution: Force unlock (use with caution)
terraform force-unlock <LOCK_ID>
```

**Problem:** Resources still exist after destroy
```bash
# Solution: Manual cleanup (see above)
# Or check if resources were created outside Terraform
```

**Problem:** Accidental destroy
```bash
# Solution: If you have state backup, you can redeploy
terraform apply
# Otherwise, you'll need to redeploy from scratch
```

## Next Steps

After setup:

1. **Test the deployment**
   ```bash
   make test
   aws lambda invoke --function-name powerscale-monitor --payload '{}' response.json
   ```

2. **Monitor the logs**
   ```bash
   aws logs tail /aws/lambda/powerscale-monitor --follow
   ```

3. **Check CloudWatch metrics**
   ```bash
   aws cloudwatch list-metrics --namespace PowerScale/Cluster
   ```

4. **Verify alerting**
   - Trigger a condition that should alert
   - Check email for SNS notification

## Additional Resources

- [AWS Documentation](https://docs.aws.amazon.com/)
- [Terraform Documentation](https://www.terraform.io/docs)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Python Documentation](https://docs.python.org/3/)
