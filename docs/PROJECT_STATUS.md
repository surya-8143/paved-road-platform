# Project status

Updated: 2026-11-20 (Asia/Kolkata).

**The complete project is not finished.** Public CI/release signing, offline infrastructure policy and local GitOps/admission are implemented and tested. Live AWS deployment, account-level operations and teardown remain unverified. The personal managed Free Plan account blocks IAM identity-provider setup; the college AWS Academy Learner Lab is confirmed, with IAM capabilities still being checked. No account upgrade or AWS deployment has been performed.

## Constraints

- Owner: surya-8143; workspace D:\CLOUD. Preserve unrelated work and Docker containers.
- Spending authorization remains INR 0. Promotional credits are not evidence of zero resource cost.
- Never put passwords, access tokens, credentials or state in Git.
- The supplied implementation PDF is a design reference; defects are corrected using executable checks and primary documentation.

## Completed with evidence

| Area | Result |
| --- | --- |
| Foundation | Ubuntu 24.04/WSL2, Python 3.12 and Docker work; tools, Actions, images, chart and manifests pinned/checksummed |
| Repositories | Public platform, template and generated demo service repositories; template marked as a GitHub template |
| Service | 20 tests; 100% measured coverage of the current application; non-root/read-only container HTTP smoke and isolated Lambda package smoke |
| Packaging | Identical ZIP SHA-256 across separate local environments and hosted CI |
| Supply chain | Native AMD64/ARM64 build and scan, exact scanned-image publication, keyless signatures, SBOM attestations, signed ZIP and release manifest, independent verification |
| Negative gates | Real vulnerable dependencies blocked publication; empty scanner inventory also blocked release |
| Infrastructure | OpenTofu format/validate, 3 mocked service-module tests, real offline plan, 18 policy checks; 18 platform unit/regression tests |
| Policy scope | Nested/unchanged resources, create-before-destroy peaks, other-stack capacity, critical unknowns, expired public exceptions and URL/function matching |
| Second service | Generated through GitHub template API; first full successful CI run elapsed 221 seconds (not total onboarding time) |
| GitOps | Argo CD reconciles the public demo GitOps path; application reached Synced/Healthy with an immutable signed image |
| Admission | 15 live server-dry-run cases, including real unsigned/wrong-signer registry images, unsafe configs and init containers |
| Recovery | 7 live checks: ephemeral-container denial, automatic drift repair, zero-scale/deletion guard, actual webhook outage rejection and recovery, HTTP smoke |

Raw local admission/recovery evidence is tracked under `docs/evidence/`; full build/scan artifacts are linked from [supply-chain evidence](SUPPLY_CHAIN_EVIDENCE.md). [Kubernetes runbook](KUBERNETES.md) documents the shutdown gap discovered and the independent native admission guard added for it.

## Remaining acceptance work

- [ ] Finish and record clean-checkout cluster recreation; repeat admission/recovery checks on the new node.
- [ ] Resolve AWS account compatibility without assuming that a college lab permits IAM/OIDC administration.
- [ ] Bootstrap scoped roles, boundaries, GitHub OIDC trust and versioned/encrypted state storage in a compatible account.
- [ ] Verify the actual GitHub OIDC subject, including immutable repository/owner IDs; test rejected repository/branch contexts.
- [ ] Add and execute cloud deployment with fresh account inventory, exact saved-plan application and verified matching release package.
- [ ] Verify concurrency quotas, live DynamoDB writes, authenticated endpoint, temporary reviewed public exception and authentication restoration.
- [ ] Implement/execute cloud drift, usage and charge/credit monitoring; do not treat budget alerts as a spending cap.
- [ ] Test service teardown before bootstrap teardown; audit remaining resources and object versions before deleting state storage.
- [x] Retain signed release archives and scan reports in public supply-chain prereleases.
- [ ] Finish the demo recording and verify resume claims against measured results.

## Honest limits

The offline checker resolves one provider-computed DynamoDB index field using a reviewed source fingerprint; this is not online-deployment approval or account inventory. AWS is still the main blocker to claiming a complete cloud project. Local kind uses a single node and does not enforce NetworkPolicy. Application counters are in memory in Kubernetes. Admission/signatures do not make the application production-ready or guarantee future vulnerability results.

## Account evidence

The console supplied by the owner showed the new Builder ID managed project experience, Free Plan, USD 100 credits and 182 days remaining. Email login alone does not establish that the session is an AWS root identity.

AWS documents restrictions on identity-provider operations for this account configuration and a separate advanced activation path. Activating advanced features requires a paid-plan decision; it must not be done automatically. Recheck effective policies after any authorized account change rather than assuming all restrictions disappear.

- [Managed project policies](https://docs.aws.amazon.com/accounts/latest/reference/scps-and-rcps-for-projects.html)
- [Compare sign-up options](https://docs.aws.amazon.com/accounts/latest/reference/sign-up-for-aws.html)
- [GitHub OIDC subject formats](https://docs.github.com/en/actions/reference/security/oidc)

The college screenshots confirm AWS Academy Learner Lab, a USD 50 budget limit (remaining balance not shown), a voclabs role session and us-east-1. This establishes lab type, not permission to create roles or OIDC providers. The lab instructions must be checked before selecting an AWS deployment path.
