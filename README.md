# PowerScale Cluster Monitor — Portfolio Edition

A compact, production-minded project that monitors Dell PowerScale (Isilon) clusters from AWS Lambda and a local CLI. The key technical highlight: a secure outbound tunnel (Tailscale Funnel) that lets a scheduled Lambda call into an on-prem/private PowerScale API without opening inbound firewall ports.

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

## Getting started — quick path (recommended for evaluation)

Prereqs
- Terraform >= 1.5
- AWS CLI configured with an account that can create Lambda/IAM/SNS/CloudWatch resources
- (Optional) Tailscale account if you plan to use the Funnel approach

1) Build the Lambda package

```bash
cd powerscale-monitor/aws
./build.sh
```

2) Prepare Terraform variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars and supply safe values. Keep secrets local (or use environment variables / secrets manager).
```

3) Deploy with Terraform (recommended)

```bash
terraform init
terraform plan
terraform apply
```

4) Validate the deployment
- Check Lambda logs: `aws logs tail /aws/lambda/powerscale-monitor --follow`
- Invoke manually (for a quick smoke):
  `aws lambda invoke --function-name powerscale-monitor --payload '{}' response.json`
- Check CloudWatch metrics/alarms and look for the custom namespace: `PowerScale/Cluster`

5) Confirm alerting
- If thresholds are breached (or you force an event in the cluster), an SNS email will be sent to the configured address.

---

## Local CLI (ad-hoc)

There is a CLI variant for one-off checks. To run locally:

```bash
cd powerscale-monitor
pip install -r requirements.txt
python powerscale_cluster_monitor.py --host <cluster> --username <user> --password <pass>
```

This uses the same core logic as the Lambda, making it easy to iterate locally before deploying.

---

## Visuals & Demo Assets
Placeholders are provided here; include your screenshots in `docs/screenshots/` before publishing the repo:
- cloudwatch-dashboard.png — screenshot of the dashboard created by Terraform
- sns-alert-sample.png — sample notification email
- terraform-apply.gif — short GIF showing terraform apply → manual invoke → CloudWatch metric update

Tip: a short 20–30s animated GIF demonstrating the end-to-end flow is high-impact for portfolio reviewers.

---

## Tests & CI
- Basic unit tests for core logic: `powerscale-monitor/aws/tests/test_health_score.py` (3 tests pass locally).
- GitHub Actions workflow `.github/workflows/validate.yml` runs `python -m py_compile` and `terraform validate` to catch obvious breakages on PRs.

To run tests locally:
```bash
python -m pytest -q
```

---

## Lessons Learned / Troubleshooting
- Python runtime compatibility: some modern dependency releases use newer Python type syntax; pin dependencies when targeting older runtimes or upgrade the runtime (we chose python3.12 in Terraform).
- Networking: Lambda-to-private endpoints is a common friction point. An outbound tunnel (Tailscale Funnel) simplifies demos but plan for enterprise networking in production.
- Secrets: Terraform state may contain sensitive values. Never commit `terraform.tfstate` or `terraform.tfvars` and rotate any leaked credentials immediately.

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
