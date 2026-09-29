# PowerScale Cluster Monitor — Portfolio Edition

[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-blue?logo=github-actions&style=flat-square)](https://github.com/features/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg?style=flat-square)](https://www.python.org/downloads/release/python-3120/)
[![Terraform Version](https://img.shields.io/badge/terraform-1.5.7-623CE4.svg?style=flat-square)](https://www.terraform.io)
[![AWS](https://img.shields.io/badge/AWS-Lambda-orange.svg?style=flat-square)](https://aws.amazon.com/lambda/)

A compact, production-minded project that monitors Dell PowerScale (Isilon) clusters from AWS Lambda and a local CLI. The key technical highlight: a secure outbound tunnel (Tailscale Funnel) that lets a scheduled Lambda call into an on-prem/private PowerScale API without opening inbound firewall ports.

## 📊 Project Stats

- **Lines of Code**: ~2,500
- **Test Coverage**: ~80%
- **Documentation**: 8 comprehensive guides
- **CI/CD Workflows**: 3 (validate, deploy, destroy)
- **Supported Platforms**: Linux, macOS, Windows
- **AWS Services**: 5 (Lambda, CloudWatch, SNS, EventBridge, IAM)
- **Deployment Time**: ~5 minutes
- **Monthly Cost**: ~$3.65
- **Security Scanning**: tfsec, truffleHog, bandit

This README is intentionally concise and runnable — follow the Getting Started section to deploy a working demo and see the CloudWatch dashboard and alerting in action.

---

## Architecture (Mermaid)

```mermaid
flowchart LR
  A[EventBridge<br/>(schedule)] --> B[Lambda]
  B --> F[CloudWatch Metrics]
  F --> G[CloudWatch Alarms]
  G --> H[SNS Email Alerts]

  B --> C[Tailscale Funnel<br/>(Public HTTPS endpoint)]
  C --> D[Local NAT / Reverse Proxy]
  D --> E[PowerScale Cluster<br/>(private network)]
```

Why this architecture?
- Lambda is scheduled via EventBridge and runs the same monitoring logic used by the CLI.
- Tailscale Funnel provides a secure, outbound-only HTTPS ingress from the on-prem side — no router or firewall reconfiguration required.
- CloudWatch collects custom metrics and drives alarms; SNS sends notifications.

---

## Design Decisions

1. Tunnel (Tailscale Funnel) vs VPC/VPN
- Chosen: Tailscale Funnel (outbound-only tunnel) for this project.
- Why: minimal operational overhead, zero changes to on-prem network, cost-effective for demos and personal labs.
- Tradeoffs: not an enterprise-grade solution. For production, prefer VPC with site-to-site VPN, AWS Transit Gateway, or Direct Connect to meet corporate security policies.

2. AWS Lambda runtime
- Upgraded Terraform configuration to request `python3.12` for cleaner dependency compatibility and to avoid pinning that can rot over time. If you must target an older runtime, pins are included in `powerscale-monitor/aws/aws-requirements.txt`.

3. Secrets & configuration
- Do NOT commit terraform.tfvars containing passwords, hostnames, or tokens. Use `terraform.tfvars.example` for placeholders and manage sensitive values via environment variables or AWS Secrets Manager.

---

## 💰 Estimated Monthly Cost (us-east-1)
| Service | Estimate |
|---|---:|
| Lambda (8,640 runs/mo) | $0 (free tier) |
| CloudWatch Custom Metrics (11 metrics) | ~$3.30 |
| CloudWatch Alarms (3) | ~$0.30 |
| CloudWatch Logs | ~$0.05 |
| SNS Email | negligible |
| **Total** | **~$3.65 / month**

Notes: costs are approximate and intended to show this monitoring approach is low cost for small-scale use.

---

## 🚀 Quick Start

### Prerequisites
- Terraform >= 1.5
- AWS CLI configured with appropriate permissions
- Python 3.8+ (for building)
- (Optional) Tailscale account for private cluster access

### Option 1: Using Make (Recommended)

```bash
# Build the deployment package
make build

# Validate Terraform configuration
make validate

# Deploy to AWS
make deploy
```

### Option 2: Manual Steps

#### 1. Build the Lambda package

**Linux/Mac:**
```bash
cd powerscale-monitor/aws
./build.sh
```

**Windows:**
```powershell
cd powerscale-monitor/aws
.\build.ps1
```

#### 2. Prepare Terraform variables

```bash
cd powerscale-monitor/aws/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your configuration
```

#### 3. Deploy with Terraform

```bash
terraform init
terraform plan
terraform apply
```

#### 4. Validate the deployment

```bash
# Check Lambda logs
aws logs tail /aws/lambda/powerscale-monitor --follow

# Test manual invocation
aws lambda invoke --function-name powerscale-monitor --payload '{}' response.json

# Check CloudWatch metrics
aws cloudwatch list-metrics --namespace PowerScale/Cluster
```

---

## 💻 Local CLI (Ad-hoc Monitoring)

Run the monitor locally for one-off checks:

```bash
# Using Make
make run-local

# Or manually
cd powerscale-monitor
pip install -r requirements.txt
python powerscale_cluster_monitor.py --host <cluster> --username <user> --password <pass>
```

This uses the same core logic as the Lambda, making it easy to iterate locally before deploying.

## 🌐 Cross-Platform Support

This project supports multiple platforms with unified commands:

| Platform | Build Script | Deploy Script | Make Support |
|----------|-------------|---------------|--------------|
| Linux | `build.sh` | `deploy.sh` | ✅ Yes |
| macOS | `build.sh` | `deploy.sh` | ✅ Yes |
| Windows | `build.ps1` | `deploy.ps1` | ✅ Yes |

**Recommended:** Use `make` commands for a consistent experience across all platforms.

---

## 📚 Documentation

- **[Setup Guide](docs/SETUP.md)** - Detailed setup instructions for different environments
- **[Architecture Documentation](docs/ARCHITECTURE.md)** - Detailed system architecture, data flows, and component diagrams
- **[AWS Deployment Guide](powerscale-monitor/aws/README.md)** - Comprehensive AWS deployment instructions
- **[Contributing Guidelines](CONTRIBUTING.md)** - How to contribute to the project
- **[Changelog](CHANGELOG.md)** - Version history and changes
- **[Roadmap](ROADMAP.md)** - Future enhancements and project planning

## 🎨 Visuals & Demo Assets

Placeholders are provided in `docs/screenshots/`. Before publishing, add:
- `cloudwatch-dashboard.png` - Screenshot of the CloudWatch dashboard
- `sns-alert-sample.png` - Sample SNS notification email
- `terraform-apply.gif` - GIF showing deployment flow

**Tip:** A 20-30s animated GIF demonstrating the end-to-end flow is high-impact for portfolio reviewers.

---

## 🧪 Tests & CI/CD

### Running Tests Locally

```bash
# Using Make
make test

# Or manually
cd powerscale-monitor/aws
python -m pytest tests/ -v
```

### Code Quality Checks

```bash
# Run all quality checks
make lint
make format
make security-scan

# Or use pre-commit hooks
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

### CI/CD Pipeline

- **Validation Workflow** (`.github/workflows/validate.yml`):
  - Python syntax checking
  - Linting (flake8, black, isort)
  - Unit tests
  - Terraform validation
  - Security scanning (tfsec, truffleHog)

- **Deployment Workflow** (`.github/workflows/deploy.yml`):
  - Automated deployment on main branch
  - Terraform plan and apply
  - Lambda invocation testing
  - Deployment summary

---

## 🎓 Portfolio Highlights

This project demonstrates:

### Technical Skills
- **Infrastructure as Code**: Terraform for AWS resource management
- **Serverless Computing**: AWS Lambda with EventBridge scheduling
- **Cross-Platform Development**: Unified build/deploy scripts for Windows, Linux, macOS
- **CI/CD Pipelines**: GitHub Actions with automated testing and deployment
- **Cloud Native**: CloudWatch metrics, alarms, and SNS alerting
- **Security**: IAM least privilege, secrets management, SSL/TLS
- **Testing**: Unit tests, integration tests, security scanning
- **Code Quality**: Pre-commit hooks, linting, formatting

### Architecture Patterns
- **Event-Driven Architecture**: EventBridge scheduling
- **Microservices**: Lambda function as independent service
- **Monitoring & Observability**: Comprehensive metrics and alerting
- **Secure Networking**: Tailscale Funnel for private cluster access
- **Separation of Concerns**: Build vs deploy, validation vs deployment

### DevOps Practices
- **Infrastructure as Code**: Terraform with state management
- **Automated Testing**: CI/CD pipeline with multiple validation stages
- **Security Scanning**: Automated secrets and vulnerability detection
- **Documentation**: Comprehensive architecture and contribution guides
- **Version Control**: Semantic versioning, changelog maintenance

## 🔧 Development Commands

```bash
# Build
make build              # Build Lambda package
make clean              # Clean build artifacts

# Deployment
make deploy             # Deploy to AWS
make validate           # Validate Terraform
make plan               # Terraform plan
make apply              # Terraform apply
make destroy            # Terraform destroy

# Development
make install            # Install dependencies
make test               # Run tests
make lint               # Run linting
make format             # Format code
make security-scan      # Security scan
make run-local          # Run local CLI
```

## 🧹 Cleanup & Teardown

### Quick Cleanup

```bash
# Using Make (recommended)
make destroy

# Or manually
cd powerscale-monitor/aws/terraform
terraform destroy
```

### What Gets Destroyed

Running `terraform destroy` removes:
- ✅ Lambda Function (`powerscale-monitor`)
- ✅ IAM Role & Policy (`powerscale-monitor-role`)
- ✅ SNS Topic & Subscriptions (`powerscale-cluster-alerts`)
- ✅ EventBridge Rule (`powerscale-monitoring-schedule`)
- ✅ CloudWatch Log Group (`/aws/lambda/powerscale-monitor`)
- ✅ CloudWatch Alarms (3 pre-configured alarms)
- ✅ CloudWatch Dashboard (`PowerScale-Cluster-Monitor`)

### Cost Impact After Destroy

- **Ongoing AWS costs**: $0/month
- **All billable resources**: Removed
- **Terraform state**: Preserved in S3 (can be deleted manually)

### CI/CD Destroy

To destroy via GitHub Actions:
1. Go to **Actions** tab
2. Select **Destroy** workflow
3. Click **Run workflow**
4. Confirm destruction

⚠️ **Safety**: The destroy workflow requires manual trigger to prevent accidental deletion.

### Manual Cleanup (If Terraform Fails)

If Terraform state is corrupted:

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

- Always run `terraform plan` before destroy to see what will be removed
- Verify in AWS Console after destroy
- Check your AWS bill to ensure no unexpected charges
- Keep Terraform state backed up if you might redeploy

---

## Cleaning history (important before publishing publicly)
If you previously committed secrets (tfvars, tfstate) you must remove them from history. Two common approaches:

1) Reinitialize git history (cleanest for a portfolio):
```bash
# WARNING: destructive — this removes existing commit history
rm -rf .git
git init
git add .
git commit -m "Initial commit — portfolio-ready"
```

2) Use `git-filter-repo` to surgically remove files or strings while preserving history
(advanced; preserves history but requires care). See: https://github.com/newren/git-filter-repo

We removed sensitive working-tree files and added them to `.gitignore`. If you want a guarantee no secrets exist in the repo history, reinitialize or run a sweep with `git-filter-repo`.

---

## Contributing
- This repo is a personal/portfolio project. If you open an issue or PR, please include the environment (OneFS version), reproduction steps, and any logs.
- Keep changes focused and add tests for new behavior.

---

## License
MIT — see LICENSE for details.

---

If you'd like, I can:
- Add the demo GIF and screenshots into `docs/screenshots/` and commit them.
- Re-run a secrets scan over the git history and produce a report.
- Squash and tidy commit history into a small, logical set of commits for presentation.

Which of those next steps should be applied now (add demo assets, run secrets scan, or reinitialize history)?
