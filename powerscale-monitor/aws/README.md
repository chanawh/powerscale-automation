# AWS Deployment

Deploy the PowerScale monitor as an AWS Lambda function with CloudWatch metrics and SNS alerting for automated, serverless cluster monitoring.

## Architecture

```
☁️ AWS: Lambda (scheduled via EventBridge) → polls pAPI → pushes metrics to CloudWatch → triggers SNS alerts on thresholds
```

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- Terraform installed (for Terraform deployment)
- PowerScale cluster with API access
- Python 3.8+ (for building deployment package)

## Quick Start

### Option 1: Terraform Deployment (Recommended)

#### Step 1: Build Deployment Package
```bash
cd aws
./build.sh
```

#### Step 2: Configure Terraform
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your configuration:
```hcl
aws_region = "us-east-1"
powerscale_host = "192.168.1.50"
powerscale_username = "root"
powerscale_password = "your_password"
powerscale_port = 8080
powerscale_ssl_verify = false
alert_emails = ["admin@example.com"]
critical_threshold = 50
degraded_threshold = 80
schedule_expression = "rate(5 minutes)"
```

#### Step 3: Deploy
```bash
terraform init
terraform plan
terraform apply
```

### Option 2: Manual Deployment

#### Step 1: Build Deployment Package
```bash
cd aws
./build.sh
```

#### Step 2: Configure Deployment Script
Edit `deploy.sh` and update these lines:
```bash
POWERSCALE_HOST="192.168.1.50"
POWERSCALE_USERNAME="root"
POWERSCALE_PASSWORD="your_password"
SNS_TOPIC_ARN="arn:aws:sns:us-east-1:123456789012:your-topic-name"
```

#### Step 3: Deploy
```bash
chmod +x deploy.sh
./deploy.sh
```

## Detailed Usage

### Building the Deployment Package

The `build.sh` script creates a Lambda deployment package with all dependencies:

```bash
cd aws
./build.sh
```

This creates `deployment.zip` containing:
- `lambda_function.py` - The Lambda handler
- `requests` library - For HTTP requests
- `urllib3` library - For SSL handling
- `boto3` library - For AWS SDK

### Terraform Deployment Steps

#### 1. Initialize Terraform
```bash
cd terraform
terraform init
```

#### 2. Review the Plan
```bash
terraform plan
```

This shows what resources will be created:
- Lambda function
- IAM role and policies
- SNS topic for alerts
- EventBridge schedule rule
- CloudWatch log group
- CloudWatch alarms

#### 3. Apply the Configuration
```bash
terraform apply
```

Type `yes` when prompted to confirm.

#### 4. Note the Outputs
Terraform will display important information:
- Lambda function ARN
- SNS topic ARN
- CloudWatch dashboard link

### Manual Deployment Steps

#### 1. Create IAM Role
```bash
aws iam create-role \
  --role-name powerscale-monitor-role \
  --assume-role-policy-document file://iam-trust-policy.json
```

#### 2. Attach IAM Policy
```bash
aws iam put-role-policy \
  --role-name powerscale-monitor-role \
  --policy-name PowerScaleMonitorPolicy \
  --policy-document file://iam-policy.json
```

#### 3. Create Lambda Function
```bash
aws lambda create-function \
  --function-name powerscale-monitor \
  --runtime python3.9 \
  --role <role-arn-from-previous-step> \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://deployment.zip \
  --timeout 30
```

#### 4. Configure Environment Variables
```bash
aws lambda update-function-configuration \
  --function-name powerscale-monitor \
  --environment Variables={
    POWERSCALE_HOST="192.168.1.50",
    POWERSCALE_USERNAME="root",
    POWERSCALE_PASSWORD="your_password",
    POWERSCALE_PORT="8080",
    POWERSCALE_SSL_VERIFY="false",
    SNS_TOPIC_ARN="arn:aws:sns:us-east-1:123456789012:your-topic",
    CRITICAL_THRESHOLD="50",
    DEGRADED_THRESHOLD="80"
  }
```

#### 5. Create EventBridge Schedule
```bash
aws events put-rule \
  --name powerscale-monitoring-schedule \
  --schedule-expression 'rate(5 minutes)'

aws events put-targets \
  --rule powerscale-monitoring-schedule \
  --targets '{"Id": "1", "Arn": "arn:aws:lambda:us-east-1:123456789012:function:powerscale-monitor"}'

aws lambda add-permission \
  --function-name powerscale-monitor \
  --statement-id "AllowExecutionFromEventBridge" \
  --action "lambda:InvokeFunction" \
  --principal "events.amazonaws.com" \
  --source-arn "arn:aws:events:us-east-1:123456789012:rule/powerscale-monitoring-schedule"
```

## Features

- **Automated Monitoring**: Scheduled polling via EventBridge (default: every 5 minutes)
- **CloudWatch Metrics**: 11 custom metrics for health, events, nodes, and performance
- **SNS Alerting**: Email notifications when thresholds are breached
- **CloudWatch Alarms**: Pre-configured alarms for critical/degraded states
- **Serverless**: No infrastructure management, pay-per-use
- **Multi-cluster**: Deploy multiple instances for different clusters

## Metrics Collected

The Lambda function sends these metrics to CloudWatch:

- **Health Score** (0-100) - Overall cluster health
- **Unresolved Events** - Total count of unresolved events
- **Critical Events** - Count of critical severity events
- **Warning Events** - Count of warning severity events
- **Total Nodes** - Total number of nodes in cluster
- **Up Nodes** - Number of nodes currently up
- **Down Nodes** - Number of nodes currently down
- **Has Quorum** - Quorum status (1/0)
- **AvgCpuIdle** - Average CPU idle percentage
- **AvgCpuUsed** - Average CPU used percentage
- **AvgDiskBusy** - Average disk busy percentage

## Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `POWERSCALE_HOST` | Yes | PowerScale cluster hostname/IP | - |
| `POWERSCALE_USERNAME` | Yes | API username | - |
| `POWERSCALE_PASSWORD` | Yes | API password | - |
| `POWERSCALE_PORT` | No | API port | 8080 |
| `POWERSCALE_SSL_VERIFY` | No | Enable SSL verification | false |
| `SNS_TOPIC_ARN` | No | SNS topic for alerts | - |
| `CRITICAL_THRESHOLD` | No | Health score critical threshold | 50 |
| `DEGRADED_THRESHOLD` | No | Health score degraded threshold | 80 |
| `CLOUDWATCH_NAMESPACE` | No | CloudWatch namespace | PowerScale/Cluster |

### Terraform Variables

See `terraform/terraform.tfvars.example` for all configuration options including:
- AWS region
- PowerScale connection settings
- Alert email addresses
- Health score thresholds
- Schedule expression
- CloudWatch namespace

### Schedule Expressions

EventBridge supports cron or rate expressions:
- `rate(5 minutes)` - Every 5 minutes
- `rate(1 hour)` - Every hour
- `cron(0/10 * * * ? *)` - Every 10 minutes
- `cron(0 9 * * ? *)` - Daily at 9 AM UTC

## Monitoring and Verification

### Check Lambda Function Status
```bash
aws lambda get-function-configuration --function-name powerscale-monitor
```

### Test Lambda Manually
```bash
aws lambda invoke \
  --function-name powerscale-monitor \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  response.json

cat response.json
```

### View CloudWatch Logs
```bash
aws logs tail /aws/lambda/powerscale-monitor --follow
```

### Check CloudWatch Metrics
```bash
aws cloudwatch list-metrics --namespace PowerScale/Cluster
```

### Verify EventBridge Schedule
```bash
aws events describe-rule --name powerscale-monitoring-schedule
```

### View CloudWatch Console
Navigate to:
```
https://<region>.console.aws.amazon.com/cloudwatch/home?region=<region>#metricsV2:namespace=PowerScale/Cluster
```

## CloudWatch Alarms

The deployment creates three pre-configured alarms:

### 1. Health Score Critical
- Triggers when: Health score < 50
- Evaluation: 1 consecutive period
- Actions: SNS alert

### 2. Health Score Degraded
- Triggers when: Health score < 80
- Evaluation: 2 consecutive periods
- Actions: SNS alert

### 3. Node Down
- Triggers when: Any node is down
- Evaluation: 1 consecutive period
- Actions: SNS alert

## Cost Estimation

Based on us-east-1 pricing:

- **Lambda**: $0.20 per 1M requests (~8,640 requests/month = ~$0.002)
- **CloudWatch Metrics**: $0.30 per metric per month (11 metrics = ~$3.30)
- **CloudWatch Logs**: $0.50 per GB ingested (minimal logs)
- **SNS**: $0.64 per 1M email deliveries

**Estimated monthly cost**: <$5 for single cluster monitoring

## Security Best Practices

### Credential Management
- **Development**: Environment variables (current implementation)
- **Production**: AWS Secrets Manager
- **Alternative**: AWS Parameter Store with encryption

### IAM Security
- Use IAM roles with least privilege
- Enable MFA for AWS account
- Regularly rotate access keys
- Use IAM policies to restrict permissions

### Network Security
- Enable VPC endpoints for private clusters
- Use security groups to restrict access
- Enable encryption for data in transit
- Consider VPC peering for private network access

### Environment Variable Encryption
- Enable AWS KMS encryption for Lambda environment variables
- Use customer-managed CMKs for sensitive data
- Regularly rotate encryption keys

## Troubleshooting

### Lambda Timeout Issues
- Increase timeout in function configuration
- Check network connectivity to PowerScale cluster
- Verify API response times
- Add logging to identify slow operations

### Authentication Errors
- Verify credentials in environment variables
- Check API user permissions
- Ensure account is not locked
- Test credentials with local script first

### Missing Metrics in CloudWatch
- Check CloudWatch Logs for errors
- Verify IAM permissions for CloudWatch
- Ensure Lambda has internet access
- Check CloudWatch namespace configuration

### SNS Alerts Not Received
- Verify SNS topic subscription is confirmed
- Check email spam folder
- Verify CloudWatch alarm thresholds
- Check SNS topic permissions

### EventBridge Not Triggering
- Verify rule is enabled
- Check schedule expression syntax
- Ensure Lambda permission is granted
- Check EventBridge logs for errors

See the main [README.md](../README.md) for additional troubleshooting information.

## Advanced Usage

### Monitoring Multiple Clusters

Deploy multiple instances with different configurations:

```bash
# Cluster 1
terraform apply -var="powerscale_host=cluster1.example.com" -var="function_name=powerscale-monitor-cluster1"

# Cluster 2
terraform apply -var="powerscale_host=cluster2.example.com" -var="function_name=powerscale-monitor-cluster2"
```

### Custom Metrics

Add custom metrics in `lambda_function.py`:

```python
def put_custom_metric(self, metric_name: str, value: float):
    self.put_cloudwatch_metric(f"Custom/{metric_name}", value)
```

### Webhook Integration

Add webhook notifications in addition to SNS:

```python
def send_webhook_alert(self, webhook_url: str, message: str):
    requests.post(webhook_url, json={"text": message})
```

## Maintenance

### Updating the Function

#### Terraform
```bash
cd terraform
terraform apply
```

#### Manual
```bash
# Rebuild package
./build.sh

# Update function code
aws lambda update-function-code \
  --function-name powerscale-monitor \
  --zip-file fileb://deployment.zip
```

### Rotating Credentials

```bash
aws lambda update-function-configuration \
  --function-name powerscale-monitor \
  --environment Variables={
    POWERSCALE_PASSWORD="new_password"
  }
```

### Adjusting Schedule

```bash
aws events put-rule \
  --name powerscale-monitoring-schedule \
  --schedule-expression 'rate(10 minutes)'
```

## Cleanup

### Terraform Cleanup
```bash
cd terraform
terraform destroy
```

### Manual Cleanup
```bash
# Delete Lambda function
aws lambda delete-function --function-name powerscale-monitor

# Delete EventBridge rule
aws events delete-rule --name powerscale-monitoring-schedule

# Delete IAM role
aws iam delete-role-policy --role-name powerscale-monitor-role --policy-name PowerScaleMonitorPolicy
aws iam delete-role --role-name powerscale-monitor-role

# Delete SNS topic (if desired)
aws sns delete-topic --topic-arn <your-topic-arn>
```

## Support

For issues related to:
- **AWS Deployment**: Check AWS CloudWatch Logs and CloudWatch metrics
- **PowerScale API**: Consult Dell PowerScale documentation
- **Terraform**: Check Terraform state and configuration
- **Lambda**: Check Lambda configuration and logs

## Architecture Diagrams

### High-Level Architecture
```
┌─────────────────┐
│  EventBridge    │
│  (Scheduler)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AWS Lambda     │
│  (Monitor)      │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌──────────┐
│PowerScale│ │CloudWatch│
│   API    │ │ Metrics  │
└─────────┘ └────┬─────┘
                 │
         ┌───────┴───────┐
         │               │
         ▼               ▼
    ┌─────────┐    ┌─────────┐
    │CloudWatch│    │   SNS   │
    │  Alarms │    │ Alerts  │
    └─────────┘    └─────────┘
```

### Data Flow
```
1. EventBridge triggers Lambda (every 5 minutes)
2. Lambda authenticates to PowerScale API
3. Lambda fetches cluster configuration, events, statistics
4. Lambda calculates health score
5. Lambda pushes metrics to CloudWatch
6. CloudWatch alarms evaluate thresholds
7. SNS sends email alerts on threshold breaches
```

## Testing Strategy

### Local Testing
Test the Lambda function locally before deployment:

```bash
# Set environment variables
export POWERSCALE_HOST="192.168.1.50"
export POWERSCALE_USERNAME="root"
export POWERSCALE_PASSWORD="password"

# Test the function
python -c "
from lambda_function import lambda_handler
import json
result = lambda_handler({}, None)
print(json.dumps(result, indent=2))
"
```

### Unit Testing
Create test cases for individual components:

```python
# test_lambda_function.py
import unittest
from lambda_function import PowerScaleMonitor

class TestPowerScaleMonitor(unittest.TestCase):
    def test_health_score_calculation(self):
        monitor = PowerScaleMonitor({})
        events = {'eventgroups': [
            {'severity': 'critical', 'causes': []},
            {'severity': 'warning', 'causes': []}
        ]}
        score = monitor.calculate_health_score(events)
        self.assertEqual(score, 75)  # 100 - 20 - 5
```

### Integration Testing
Test the deployed Lambda function:

```bash
# Test invocation
aws lambda invoke \
  --function-name powerscale-monitor \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  test_response.json

# Verify response
cat test_response.json | jq
```

### End-to-End Testing
Verify the complete monitoring pipeline:

1. Deploy the function
2. Wait for scheduled execution
3. Check CloudWatch metrics appear
4. Trigger a condition that should alert
5. Verify SNS notification received

## Performance Considerations

### Lambda Optimization

#### Memory Configuration
- **Default**: 128 MB (may be insufficient)
- **Recommended**: 256 MB for better performance
- **High Load**: 512 MB for large clusters

```bash
aws lambda update-function-configuration \
  --function-name powerscale-monitor \
  --memory-size 256
```

#### Timeout Configuration
- **Default**: 30 seconds
- **Adjust based on**: API response times, cluster size
- **Maximum**: 15 minutes

```bash
aws lambda update-function-configuration \
  --function-name powerscale-monitor \
  --timeout 60
```

#### Cold Start Mitigation
- **Provisioned Concurrency**: Keep functions warm
- **Scheduled Warm-up**: Trigger function before critical monitoring

```bash
aws lambda put-provisioned-concurrency-config \
  --function-name powerscale-monitor \
  --provisioned-concurrent-executions 1
```

### API Optimization

#### Connection Reuse
The Lambda function reuses HTTP sessions for better performance.

#### Retry Logic
Built-in retry with exponential backoff handles transient failures.

#### Parallel Requests
Consider parallelizing API calls for large clusters:

```python
import concurrent.futures

def fetch_all_data():
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(self.get_cluster_config): 'config',
            executor.submit(self.get_unresolved_events): 'events',
            executor.submit(self.get_node_statistics): 'stats'
        }
        results = {}
        for future in concurrent.futures.as_completed(futures):
            results[futures[future]] = future.result()
        return results
```

## CI/CD Integration

### GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy PowerScale Monitor

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          cd powerscale-monitor/aws
          pip install -r aws-requirements.txt
      - name: Run tests
        run: |
          python -m pytest test_lambda_function.py

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v2
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - name: Build deployment package
        run: |
          cd powerscale-monitor/aws
          ./build.sh
      - name: Deploy with Terraform
        run: |
          cd powerscale-monitor/aws/terraform
          terraform init
          terraform apply -auto-approve
```

### Automated Testing in CI/CD

Add these test steps to your pipeline:

1. **Linting**: Check code quality
2. **Security Scanning**: Scan for vulnerabilities
3. **Terraform Validation**: Validate infrastructure code
4. **Unit Tests**: Test individual components
5. **Integration Tests**: Test deployed function

## Multi-Environment Setup

### Environment Strategy

```
terraform/
├── environments/
│   ├── dev/
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   ├── staging/
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   └── prod/
│       ├── terraform.tfvars
│       └── backend.tf
└── modules/
    └── lambda-monitor/
```

### Dev Environment
- **Purpose**: Development and testing
- **Schedule**: Every 30 minutes
- **Alerting**: Email to developers
- **Cost**: Minimal

### Staging Environment
- **Purpose**: Pre-production testing
- **Schedule**: Every 10 minutes
- **Alerting**: Email to ops team
- **Cost**: Moderate

### Production Environment
- **Purpose**: Production monitoring
- **Schedule**: Every 5 minutes
- **Alerting**: Email + SMS to on-call
- **Cost**: Full monitoring

### State Management

Use separate Terraform states for each environment:

```hcl
# dev/backend.tf
terraform {
  backend "s3" {
    bucket = "terraform-state-dev"
    key    = "powerscale-monitor/terraform.tfstate"
    region = "us-east-1"
  }
}
```

## Cost Optimization

### Detailed Cost Breakdown

| Service | Component | Cost/Month | Optimization |
|---------|-----------|-------------|--------------|
| Lambda | Invocations | $0.002 | Reduce frequency |
| Lambda | Compute | $0.50 | Optimize memory |
| CloudWatch | Metrics | $3.30 | Reduce metrics |
| CloudWatch | Logs | $0.10 | Reduce log retention |
| CloudWatch | Alarms | $0.00 | Free tier |
| SNS | Notifications | $0.01 | Consolidate alerts |
| **Total** | | **~$4/month** | |

### Optimization Strategies

#### 1. Reduce Monitoring Frequency
```hcl
# Change from 5 minutes to 15 minutes
schedule_expression = "rate(15 minutes)"
# Saves ~66% on Lambda costs
```

#### 2. Optimize Lambda Memory
```bash
# Find optimal memory setting
aws lambda update-function-configuration \
  --function-name powerscale-monitor \
  --memory-size 256  # Balance cost/performance
```

#### 3. Reduce Metrics
Comment out non-essential metrics in `lambda_function.py`:
```python
# Comment out expensive metrics
# self.put_cloudwatch_metric("DetailedMetric", value)
```

#### 4. Reduce Log Retention
```hcl
resource "aws_cloudwatch_log_group" "lambda_logs" {
  retention_in_days = 3  # Instead of 7
}
```

#### 5. Use Free Tier
- Lambda: 1M free requests/month
- CloudWatch: 10 custom metrics free
- Stay within free tier limits

### Budget Alerts

Set up AWS budget alerts:

```bash
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget file://budget.json
```

## Security Compliance

### Security Checklist

- [ ] **Authentication**: API credentials stored securely
- [ ] **Encryption**: TLS for API calls
- [ ] **IAM**: Least privilege permissions
- [ ] **Secrets Management**: Use AWS Secrets Manager
- [ ] **VPC**: Private network access if needed
- [ ] **Logging**: Enable CloudTrail logging
- [ ] **Monitoring**: Monitor for suspicious activity
- [ ] **Compliance**: Follow organizational policies

### Compliance Considerations

#### SOC2 Compliance
- Enable audit logging
- Implement access controls
- Regular security reviews
- Change management procedures

#### HIPAA Compliance
- Encrypt data at rest and in transit
- Business associate agreements
- Access logging and monitoring
- Regular risk assessments

#### GDPR Compliance
- Data minimization
- Right to erasure
- Data portability
- Consent management

### Audit Logging

Enable CloudTrail for API logging:

```bash
aws cloudtrail create-trail \
  --name powerscale-monitor-trail \
  --s3-bucket-name audit-logs-bucket
```

## Troubleshooting Matrix

| Issue | Symptoms | Cause | Solution |
|-------|----------|-------|----------|
| **Lambda Timeout** | Function times out | Slow API response | Increase timeout, optimize code |
| **Auth Failure** | 401 errors | Invalid credentials | Verify credentials, check account lock |
| **No Metrics** | CloudWatch empty | IAM permissions | Check CloudWatch permissions |
| **No Alerts** | SNS not firing | Threshold not met | Adjust thresholds, check alarm config |
| **Cold Starts** | Slow first execution | No provisioned concurrency | Enable provisioned concurrency |
| **Memory Issues** | OOM errors | Insufficient memory | Increase Lambda memory |
| **Network Errors** | Connection timeouts | Network issues | Check VPC configuration, security groups |
| **Schedule Issues** | Function not running | EventBridge misconfig | Verify schedule expression, rule status |

## FAQ

### General Questions

**Q: Can I monitor multiple clusters?**
A: Yes, deploy multiple Lambda instances with different configurations.

**Q: How do I change the monitoring frequency?**
A: Update the `schedule_expression` in Terraform or EventBridge rule.

**Q: Can I use this with PowerScale clusters in a VPC?**
A: There are two common approaches.

1) VPC / VPN: Configure VPC endpoints, a Site-to-Site VPN, or VPC peering so the Lambda (or resources in a VPC) can reach the on-prem PowerScale API. This is the enterprise option — secure and private but requires network configuration and potentially additional AWS networking costs.

2) Outbound tunnel (used in this repo): Use an outbound-only tunnel (e.g., Tailscale Funnel / Tailscale Funnel + NAT) to provide a secure HTTPS ingress that the Lambda can call. This is lower cost and simpler for personal labs since it requires no router changes and uses only outbound connections from the on-prem side. It's convenient for demos and personal projects but evaluate enterprise networking and security requirements before using in production.


**Q: What happens if the PowerScale API is down?**
A: Lambda will retry and log errors. CloudWatch will show missing metrics.

### Technical Questions

**Q: How do I handle SSL certificate errors?**
A: Set `POWERSCALE_SSL_VERIFY=false` or add certificates to Lambda layer.

**Q: Can I add custom metrics?**
A: Yes, modify `lambda_function.py` to add additional `put_cloudwatch_metric` calls.

**Q: How do I debug Lambda execution?**
A: Enable detailed monitoring, check CloudWatch Logs, use X-Ray for tracing.

**Q: What's the maximum cluster size this can handle?**
A: Tested with clusters up to 100 nodes. Larger clusters may need optimization.

### Cost Questions

**Q: Can I reduce costs further?**
A: Reduce monitoring frequency, optimize Lambda memory, reduce metrics collected.

**Q: Are there free tier limitations?**
A: Yes, Lambda free tier is 1M requests/month (~5-min intervals = 8,640 requests).

**Q: How do I monitor AWS costs?**
A: Use AWS Cost Explorer, set up budget alerts, review CloudWatch billing metrics.

## Performance Benchmarks

### Expected Performance

| Metric | Small Cluster | Medium Cluster | Large Cluster |
|--------|---------------|---------------|--------------|
| **Execution Time** | 2-5 seconds | 5-10 seconds | 10-20 seconds |
| **Memory Usage** | 128 MB | 256 MB | 512 MB |
| **API Calls** | 3 | 3 | 3 |
| **Cold Start** | 1-2 seconds | 2-3 seconds | 3-5 seconds |

### Resource Utilization

- **CPU**: Low (mostly I/O bound)
- **Memory**: Moderate (depends on cluster size)
- **Network**: Low (small API payloads)
- **Storage**: Minimal (only logs)

### Scaling Characteristics

- **Horizontal**: Deploy multiple instances for multiple clusters
- **Vertical**: Increase memory for larger clusters
- **Geographic**: Deploy in multiple AWS regions

## Disaster Recovery

### Backup Strategy

- **Terraform State**: Store in S3 with versioning
- **Configuration**: Store in Git repository
- **Credentials**: Use AWS Secrets Manager with rotation
- **Logs**: Export to S3 for long-term retention

### Recovery Procedures

#### Restore from Terraform State
```bash
terraform state pull > backup.tfstate
terraform state push backup.tfstate
```

#### Redeploy from Scratch
```bash
terraform destroy
terraform apply
```

#### Failover to Another Region
```bash
# Deploy in backup region
terraform apply -var="aws_region=us-west-2"
```

### RTO/RPO Considerations

- **Recovery Time Objective (RTO)**: 15 minutes
- **Recovery Point Objective (RPO)**: 5 minutes (last successful execution)

## Integration Examples

### Slack Integration

Add Slack webhook notifications:

```python
def send_slack_alert(self, webhook_url: str, message: str):
    payload = {"text": message}
    requests.post(webhook_url, json=payload)
```

### PagerDuty Integration

Add PagerDuty alerts:

```python
def send_pagerduty_alert(self, service_key: str, event_data: dict):
    url = f"https://events.pagerduty.com/v2/enqueue"
    headers = {"Content-Type": "application/json"}
    payload = {
        "routing_key": service_key,
        "event_action": "trigger",
        "payload": event_data
    }
    requests.post(url, json=payload, headers=headers)
```

### Datadog Integration

Send metrics to Datadog:

```python
def send_datadog_metric(self, metric_name: str, value: float):
    from datadog import DogStatsd
    statsd = DogStatsd()
    statsd.gauge(metric_name, value)
```

## Contributing Guidelines

### Code Style
- Follow PEP 8 guidelines
- Use type hints for all functions
- Add docstrings for all public functions
- Keep functions small and focused

### Testing
- Write unit tests for new features
- Test locally before deploying
- Update documentation for changes
- Ensure backward compatibility

### Documentation
- Update README for user-facing changes
- Add inline comments for complex logic
- Update architecture diagrams for structural changes
- Maintain changelog for version releases

### Pull Request Process
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests and documentation
5. Submit a pull request
6. Address review feedback
7. Merge when approved
