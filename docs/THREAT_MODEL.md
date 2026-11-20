# Threat model and trust boundaries

Scope: a student portfolio platform on public GitHub and a disposable local kind cluster. The AWS design is not a verified production deployment. Findings below describe controls that exist today and gaps that still require work.

## Assets and trusted actors

Protected assets are released executable bytes, source/workflow identity, deployment manifests, cluster admission configuration and future AWS state/credentials. The repository owner, platform workflow maintainers, GitHub Actions infrastructure, Docker/WSL host administrator and cluster administrator are trusted. A compromised host or administrator can alter controls. Public source, logs and transparency records are intentionally visible; credentials and infrastructure state are not.

## Build and release

| Threat | Implemented control | Residual risk |
| --- | --- | --- |
| A pull request runs code with publishing credentials | Read-only test/build jobs; publishing only for main push in separate privileged jobs | Main/workflow maintainers remain trusted; repository administration is not defended by signatures |
| An image is rebuilt after a passing scan | Transfer exact Docker image bytes with SHA-256/config identity, load and push them | Artifact/runner compromise before verification is within the CI trust boundary |
| One architecture bypasses scanning | Native AMD64 and ARM64 gates both required before index release | Architecture-specific unknown vulnerabilities remain possible |
| Lambda dependencies evade scanning | Scan extracted deployed ZIP; require complete installed-package inventory | Scanner database freshness and coverage are finite |
| A scanner error looks like success | Nonzero exit, empty inventory and HIGH/CRITICAL findings block release | Availability failures stop publication |
| A mutable tool/action/tag changes | Full Action SHAs; checksummed tools, chart/manifests and image digests | Pins require maintenance and can preserve known-old software |
| A different repository/workflow supplies an image | Exact workflow certificate identity, repository-bound signed annotations; independent release verifies source SHA | A trusted workflow/repository compromise can sign malicious bytes |
| Release components are mixed | Signed manifest binds source commit, image children/index, ZIP and SBOM hashes | The verifier itself must come from a trusted platform checkout |

No SLSA certification, malware-free guarantee or continuous vulnerability rescanning claim is made. Signatures establish identity and integrity, not intent or safety. Public prerelease archives retain the signed bytes beyond short-lived CI artifacts; archive download is still followed by independent signature/hash verification.

## Local runtime

| Threat | Implemented control | Residual risk |
| --- | --- | --- |
| Workload gains host privileges | Pod Security Restricted, non-root UID, dropped capabilities, no escalation, read-only root | Kernel/container-runtime vulnerabilities are outside the application controls |
| Unsigned or untrusted workload is admitted | Kyverno CEL image validation, immutable approved repository/digests, exact signer and annotations | Uncached verification depends on registry/Sigstore availability |
| Init or debug containers bypass rules | Init images and security settings included; ephemeral subresource explicitly denied | Administrators can grant exec or alter policies |
| Webhook cannot be called | Registered webhook failure policy Fail; real stopped-pod outage verified | New workload availability is reduced during outage |
| Graceful controller shutdown removes webhooks | Independent native admission rejects scale-to-zero and deployment deletion | An administrator can remove the binding, delete the namespace or alter RBAC |
| Manual deployment changes persist | Argo CD automated self-heal; measured replica drift repair | Bad changes committed to Git become desired state |
| Service accesses Kubernetes API | Token automount disabled; no application role binding | Network connectivity itself is not isolated |
| Unbounded workload replication/resources | Namespace quota, positive requests/limits and bounded deployment | Laptop-level resource pressure can still affect all workloads |

The default kind CNI does not enforce NetworkPolicy. The application has no configured ingress/TLS/authentication for local HTTP; access is through a loopback port forward. It is a demonstration service. The memory counter is not durable or shared and is not suitable for billing. Runtime admission is not a substitute for RBAC, patching or network controls.

## AWS work still required

No AWS workload exists from this project yet. Account compatibility, OIDC trust, role permission boundaries, state-backend controls, account inventory, live deploy/teardown and usage evidence are unfinished acceptance work. The offline plan policy limits approved resource shapes and counts; it cannot prove account-wide cost or enforce a hard spending cap. Reserved concurrency, quotas, DynamoDB capacity and log retention reduce particular risks but do not guarantee zero charges.

Do not put long-lived administrator keys into GitHub to work around the managed account's IAM restriction. Inspect the exact college lab capabilities or obtain an explicitly authorized compatible account configuration. Upgrading an account is a separate user decision, not a setup script action.

## Incident handling

For a bad release, stop promotion, retain evidence and move GitOps back to a previously verified digest through a reviewed commit. A runtime vulnerability may require a rebuilt, rescanned release; a valid signature alone does not make an older digest safe. For controller recovery, use the pinned setup/runbook and retain fail-closed checks. For a suspected secret leak, revoke it at the provider before attempting history cleanup; do not rely on deleting a file from Git.
