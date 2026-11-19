# Verified local tool versions

Verified 2026-11-19 inside Ubuntu-24.04 as the regular user nstr9.

| Tool | Version |
| --- | --- |
| Python | 3.12.3 |
| pip (new virtual environment) | 24.0 |
| Git (Ubuntu) | 2.43.0 |
| Docker client/server | 29.6.1 |
| jq | 1.7 |
| pipx | 1.4.3 |

Installed base packages: python3-venv, python3-pip, pipx, unzip, zip, jq, make, build-essential, ca-certificates, curl, git.

Verification passed: Python virtual environment with pip, Linux Docker server connectivity and required base command availability.
Run again with: bash scripts/check-local-environment.sh

These are observed versions, not release pins for CI. OpenTofu, policy/scanning/signing tools and Kubernetes components remain to be selected, pinned and verified.
