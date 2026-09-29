# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Cross-platform build scripts (build.sh for Linux/Mac, build.ps1 for Windows)
- Cross-platform deployment scripts (deploy.sh for Linux/Mac, deploy.ps1 for Windows)
- Makefile for unified cross-platform commands
- Comprehensive architecture documentation with Mermaid diagrams
- GitHub Actions deployment workflow with automated testing
- Enhanced validation workflow with security scanning
- CONTRIBUTING.md with contribution guidelines
- CI/CD badges to README
- Terraform security scanning with tfsec
- Secrets scanning with truffleHog
- Automated deployment summary in GitHub Actions

### Changed
- Updated Python runtime to 3.12 in Terraform configuration
- Enhanced GitHub Actions validation workflow with additional checks
- Improved error handling and logging

### Fixed
- Fixed build.sh to use cross-platform zip command instead of PowerShell
- Fixed deployment.zip path issue in Terraform validation

### Security
- Added security scanning to CI/CD pipeline
- Enhanced secrets detection
- Improved credential management documentation

## [1.0.0] - 2024-01-15

### Added
- Initial release of PowerScale Cluster Monitor
- Local CLI for ad-hoc monitoring
- AWS Lambda deployment for automated monitoring
- CloudWatch metrics integration (11 custom metrics)
- SNS alerting with configurable thresholds
- EventBridge scheduling (default: 5 minutes)
- Health scoring algorithm (0-100 based on events)
- Multi-configuration support (CLI args, environment variables, YAML)
- JSON report export functionality
- Retry logic with exponential backoff
- SSL verification flexibility
- Comprehensive error handling
- Terraform infrastructure as code
- IAM role and policy management
- CloudWatch dashboard
- CloudWatch alarms (3 pre-configured)
- Unit tests for health scoring logic
- GitHub Actions validation workflow
- Cross-platform support documentation

### Security
- No credentials in code
- Environment variable support for sensitive data
- SSL/TLS support for API communication
- IAM least privilege permissions

## [0.9.0] - 2024-01-10

### Added
- Initial development version
- Basic PowerScale API integration
- Local CLI monitoring
- Event analysis and categorization
- Node statistics collection
- Basic health scoring

---

## Version Format

- **MAJOR**: Incompatible API changes
- **MINOR**: Backwards-compatible functionality additions
- **PATCH**: Backwards-compatible bug fixes

## Release Process

1. Update version in relevant files
2. Update CHANGELOG.md
3. Create git tag: `git tag -a v1.0.0 -m "Release version 1.0.0"`
4. Push tag: `git push origin v1.0.0`
5. Create GitHub release
