# Supply-chain evidence

Checked on 2026-11-20 (Asia/Kolkata).

## Successful template release

- Source commit: `55091ac27f590c6c6731d0d8ef1e734534f84110`.
- [Successful GitHub run](https://github.com/surya-8143/paved-road-template/actions/runs/44575315864).
- Reusable workflow: `48a1185737433a535dd09b3d99d9d08e01e86c60`.
- Multiarchitecture image: `ghcr.io/surya-8143/paved-road-template@sha256:9d04e7aa31cd41d7903e716ba281fab5d01fa17a5668a38897951457e4fa4068`.
- Lambda ZIP SHA-256: `7fb797e3eb70d7b40a4bde8e40ef5687ce4f99194f63eab72cca65b5240684e7`.
- AMD64 and ARM64 builds both passed native HTTP smoke tests and strict HIGH/CRITICAL vulnerability gates. Their exact scanned artifacts were then pushed, signed, SBOM-attested and verified.
- Lambda's installed packages were scanned independently; the inventory is checked against every packaged `.dist-info/METADATA` entry.
- Local verification independently checked the signed release, ZIP/SBOM hashes, index bytes/digest, both architecture signatures and SBOM attestations. Anonymous registry access returned HTTP 200.

The signing identity includes both the pinned platform workflow and the caller repository/source SHA. No wildcard workflow identity is used by the release verifier.

## Generated demo consumer

[Demo repository](https://github.com/surya-8143/paved-road-demo-service) was generated through GitHub's template mechanism. Its initial source commit is `488bacc23f56269ee009a90aeba8aabdc1aeae06`.

[The first full run](https://github.com/surya-8143/paved-road-demo-service/actions/runs/44657834823) passed. GitHub recorded run creation at `2026-11-20T02:01:42Z` and final update at `2026-11-20T02:05:23Z`: 221 seconds of run elapsed time. This is a CI timing measurement, not a claim about a new user's total onboarding time.

## Negative evidence and fixes

- The first Lambda scan used filesystem mode, which did not inventory installed packages. The empty-inventory gate blocked release. Root-filesystem mode plus a complete-inventory assertion corrected the scan.
- Debian Bookworm produced 101 HIGH/CRITICAL findings on each architecture, and both publish/release jobs were skipped: [blocked run](https://github.com/surya-8143/paved-road-template/actions/runs/44573337693).
- Alpine reduced the finding set to 16 Kerberos advisories. Pinning `krb5-libs=1.22.3-r0` removed those findings. No vulnerability ignore file or `--ignore-unfixed` bypass is used.
- A deliberately vulnerable Django/Jinja2 fixture is scanned in platform CI and must fail with an actual HIGH/CRITICAL finding: [passed negative test](https://github.com/surya-8143/paved-road-platform/actions/runs/44573325192).

Scanner databases change. These results apply to the recorded builds and database timestamps, not every future rebuild. GitHub artifacts have finite retention. A signature proves identity/integrity; it does not certify software safety or establish a SLSA level.

## Repository-bound release used by Kubernetes

The shared workflow now signs repository/main-branch annotations on each child image and the multiarchitecture index. Kyverno verifies those signed annotations together with the exact reusable-workflow certificate identity.

- Approved reusable-workflow SHA: `ae9fce4325796a513e52492e0bf4850948108b6a`.
- [Demo release run](https://github.com/surya-8143/paved-road-demo-service/actions/runs/44691820011), source `d6f8381c057d2e03260595265eefb146d848ea6c`.
- Demo index: `ghcr.io/surya-8143/paved-road-demo-service@sha256:4a7ed1dabc8e3ff651cd88b6eec2aaebcb937705805113cdfcdf3f2b2fef6a70`.
- AMD64: `sha256:ad9fbc6e0b30b063f2ee7903c661c83fdccb2c76d3f0d279a719b1295f2445f2`.
- ARM64: `sha256:4174010df178901c441488f6d2eeeca206152c368fc177e0ae72e422b79c6cde`.
- Lambda ZIP retains the deterministic SHA-256 recorded above. The independent release verifier passed again.
- [Matching template run](https://github.com/surya-8143/paved-road-template/actions/runs/44691811051) also passed.
- [Admission fixture run](https://github.com/surya-8143/paved-road-demo-service/actions/runs/44660420658) publishes inert unsigned and wrong-workflow-signed images in the same approved demo registry repository. Both are rejected by real admission tests.

The demo GitOps promotion at `225ec909a1b96f5071dd4c1dbc86c40bbff256d4` changes the deployment manifest only. Source-code release SHA and deployment-manifest SHA are distinct and recorded separately. GitOps-only changes do not rebuild a release and trigger an endless promotion loop.

## Retained artifacts

The verified bytes and scan reports are retained in public prereleases, independent of Actions artifact expiry:

- [Template supply-chain checkpoint](https://github.com/surya-8143/paved-road-template/releases/tag/v0.1.0-supply-chain)
- [Demo supply-chain checkpoint](https://github.com/surya-8143/paved-road-demo-service/releases/tag/v0.1.0-supply-chain)

Each contains `verified-release.tar.gz` and `SHA256SUMS`. Extract with a path-safe extractor and use `scripts/verify_release.py` with the repository/source/workflow pins above. The outer checksum detects download corruption; the embedded Sigstore bundles and signed manifest establish release identity and integrity. These are engineering prereleases, not completed AWS deployments.
