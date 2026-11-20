# Paved Road Platform

A small platform-engineering project for reproducible Python services, reviewed AWS serverless infrastructure, and local Kubernetes admission controls.

**Status: implementation in progress.** The public supply-chain pipeline has passed for two service repositories. Offline infrastructure policies and local Argo CD/Kyverno admission and recovery checks are verified. AWS deployment is blocked by IAM restrictions on the owner's managed Free Plan project account. No live AWS deployment, zero-cost guarantee, or production-readiness claim is made.

## Repositories

- [Platform](https://github.com/surya-8143/paved-road-platform): shared CI, policy, infrastructure modules, operational scripts, and evidence.
- [Service template](https://github.com/surya-8143/paved-road-template): FastAPI, Lambda packaging, container, and service tests.
- [Generated demo service](https://github.com/surya-8143/paved-road-demo-service): signed multiarchitecture release and digest-pinned GitOps deployment.

## Supply-chain workflow

`.github/workflows/build-scan-sign.yml` is called by a service repository using a full commit SHA.

1. Install hash-locked Python dependencies, lint, run tests, build the Lambda ZIP twice, and exercise it in an isolated container.
2. Scan the ZIP's actual contents; reject HIGH or CRITICAL vulnerabilities, scanner errors, or an empty inventory.
3. Build AMD64 and ARM64 images on native GitHub-hosted runners. Smoke-test and scan each image. Preserve the exact built images as immutable workflow artifacts.
4. Only after all gates pass, separate main-push jobs push those images, sign their digests, attest their CycloneDX SBOMs, and verify the expected workflow and source identity.
5. Sign the multiarchitecture index, Lambda ZIP, and a release manifest binding the image digests, source commit, ZIP hash, and Lambda SBOM hash.

Pull requests have read-only build permissions and never publish. Privileged jobs execute only pinned platform helpers. There are no long-lived AWS or signing keys in this workflow. Tool downloads and GitHub Actions are pinned. A deliberately vulnerable fixture proves that scanner findings block the gate.

## Local checks

Use Ubuntu/WSL and Python 3.12:

```bash
python3 scripts/install_tools.py trivy cosign conftest tofu actionlint
export PATH="$HOME/.local/bin:$PATH"
python3 -m unittest discover -s tests -v
actionlint
```

To exercise the negative security case (failure is expected):

```bash
python3 scripts/scan_artifact.py fs tests/fixtures/vulnerable build/negative-scan
```

The fixture intentionally pins an old Django and Jinja2 versions. It is never installed in or copied into a released service.

## Scope and limitations

Vulnerability results reflect the database available at scan time; a signature authenticates an artifact and signer, not its safety. Pinning reduces accidental change but requires deliberate updates. Public CI logs, signatures, and transparency-log entries disclose repository and build identity. GitHub's standard runners are free for public repositories; artifacts have short retention and are not permanent release storage.

See [project status](docs/PROJECT_STATUS.md), [local setup](docs/LOCAL_SETUP.md), and [version record](docs/VERSIONS.md). The [Kubernetes runbook](docs/KUBERNETES.md) covers setup, live enforcement checks and recovery. AWS deployment, account-level operations and final portfolio evidence remain on the acceptance checklist.

Licensed under Apache-2.0.
