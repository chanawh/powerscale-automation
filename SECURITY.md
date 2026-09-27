# Security & Secrets

Sensitive files (terraform state, tfvars, deployment zips, and debug artifacts) were removed from the working tree and are listed in .gitignore. If you previously stored credentials or hostnames in these files, rotate any exposed credentials (passwords, API keys, tunnel tokens) immediately.

What was removed or ignored:
- terraform.tfvars and terraform.tfstate files
- deployment.zip and package build artifacts
- response.html / response.json / events.json / codedump.txt

Recommendations for portfolio readiness:
1. Rotate any credentials that were ever used with the removed files (Tailscale hostnames, passwords, AWS keys, etc.).
2. Keep sensitive configuration local (use terraform.tfvars locally and never commit it).
3. Use environment variables or a secret manager (AWS Secrets Manager, HashiCorp Vault) for production secrets.
4. If you find secrets in git history later, consider using git-filter-repo or reinitializing the repository history.

If you'd like, this repository can be scrubbed and reinitialized (fresh git history) to guarantee no historical secrets remain — say the word and specify whether to preserve the current commit metadata in a new initial commit or to create a single new commit as the project initial state.
