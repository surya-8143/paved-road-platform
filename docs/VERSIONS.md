# Version record

Verified on 2026-11-20. Full hashes and download locations live in `tools/linux-*.json`, `kubernetes/assets.json`, `kubernetes/image-pins.json`, provider lockfiles and workflow action references.

| Component | Version |
| --- | --- |
| Ubuntu / Python | 24.04.5 / 3.12.3 |
| Windows Git / GitHub CLI | 2.52.0 / 2.96.0 |
| Docker client/server | 29.6.1 |
| Docker Desktop | 4.80.0 |
| OpenTofu / AWS provider | 1.13.9 / 6.73.0 |
| Conftest / embedded OPA | 0.71.1 / 1.21.1 |
| Trivy / cosign | 0.76.2 / 3.1.4 |
| actionlint | 1.7.12 |
| kind / Kubernetes / kubectl | 0.33.0 / 1.35.8 / 1.35.8 |
| Helm | 4.3.2 |
| Kyverno / Helm chart | 1.20.0 / 3.10.0 |
| Argo CD | 3.6.2 |
| System PyYAML | 6.0.1 |

Service dependency versions and distribution hashes are recorded in each consumer's `requirements.txt` and `requirements-dev.txt`. Its Python 3.12 Alpine base is digest-pinned and patches Kerberos with `krb5-libs=1.22.3-r0` following measured scanner failures.

Kubernetes tools are currently pinned for Linux AMD64 (the tested laptop). Shared service CI has separate AMD64/ARM64 tool manifests. The local Kubernetes profile is not advertised as tested on ARM laptops.

Keep Python virtual environments, provider caches and temporary package generation in native Linux storage. Source remains in D:\CLOUD. Windows-mounted filesystem permission/atomic-replacement behavior can disrupt package managers; scripts avoid relying on those operations for service builds.
