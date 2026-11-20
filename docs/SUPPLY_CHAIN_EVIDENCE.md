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
