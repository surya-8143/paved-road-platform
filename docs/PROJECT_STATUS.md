# Project status

Updated: 2026-11-19 (Asia/Kolkata).

## Objective and constraints

Complete the full Paved Road project: shared pipelines, AWS Lambda/DynamoDB deployment, local Kubernetes/GitOps enforcement, operations, a second service and measured demonstration evidence.

- Owner: surya-8143.
- Workspace: D:\CLOUD. Preserve unrelated projects.
- No deadline; correctness and understanding take priority.
- Spending assumption: INR 0 until the user explicitly chooses otherwise.
- Do not store passwords, AWS access keys, session tokens, state or credentials in Git.
- Treat the supplied implementation PDF as a design reference requiring corrections.
- Do not claim zero usage cost when promotional credits merely offset a charge.

## Verified setup

- Git 2.52.0.windows.1 and GitHub CLI 2.96.0 are installed.
- GitHub CLI is signed in as surya-8143.
- VS Code and AWS CLI 2.38.1 are installed.
- Windows Python is 3.11.9; project runtime target is Python 3.12.
- WSL2 is installed. Initially only docker-desktop was registered.
- Docker Linux engine 29.6.1 responds, with approximately 8 GB available to the engine.
- Docker hello-world download/execution test passed. Existing unrelated Docker containers must be preserved.
- Ubuntu 24.04.5 installed successfully under D:\CLOUD\.local\wsl\Ubuntu-24.04. The image SHA-256 matches the Microsoft WSL manifest. First-launch setup completed as nstr9; Docker WSL integration and the base environment check passed.
- Local repositories initialized; remote publication has not occurred.

## AWS deployment blocker

The account was created on 2026-11-19 through the new AWS Builder ID/project-account signup.
The user's console shows Free Plan, USD 100 credits, and 182 days remaining.

AWS's published managed project policies deny IAM identity-provider operations. The intended GitHub OIDC bootstrap therefore requires a compatible account configuration. Do not upgrade or activate advanced features automatically. AWS documents that advanced activation requires Paid Plan and cannot be reverted to Free Plan.

References checked on 2026-11-19:
- https://docs.aws.amazon.com/accounts/latest/reference/scps-and-rcps-for-projects.html
- https://docs.aws.amazon.com/accounts/latest/reference/sign-up-for-aws.html
- https://aws.amazon.com/resources/create-account/
- https://aws.amazon.com/free/free-tier-faqs/

## Acceptance criteria

### 1. Local foundation
- [x] Ubuntu/WSL2, Python 3.12 and Docker work together; scripts/check-local-environment.sh passed as nstr9.
- [ ] Record and pin project tool versions.
- [ ] Verify commands from /mnt/d/CLOUD; document Windows-mounted filesystem tradeoffs.
- [x] Separate platform, template and demo folders, with secret/state exclusions and LF line endings.
- [x] Public repositories selected with user authorization. Publication awaits a useful initial implementation.

### 2. Service and supply chain
- [ ] Tests cover memory storage, DynamoDB behavior and Lambda HTTP event handling.
- [ ] Container works as non-root with a read-only root filesystem.
- [ ] Scan every released architecture; sign the exact scanned digest.
- [ ] Associate SBOMs with the correct artifact digest.
- [ ] Scan the actual Lambda package and its locked dependencies.
- [ ] A failing security gate prevents deployment.
- [ ] Packaging identical locked inputs produces identical ZIP hashes.

### 3. Infrastructure and policy
- [ ] Format, validate, plan offline and unit-test policies without AWS credentials.
- [ ] Fix the oversized-Lambda test fixture, which drops change.actions in the PDF.
- [ ] Enforce resource types, tags, runtime limits, database capacity and log retention.
- [ ] Include unchanged stack resources when calculating limits; account separately for other stacks.
- [ ] Reject or explicitly handle security-critical unknown values. Re-reading a saved plan does not resolve unknowns.
- [ ] Match public URLs to their own functions; cover URL-only updates and multi-function plans.
- [ ] Describe cost estimates and budget alerts accurately; neither guarantees a spending ceiling.

### 4. AWS deployment
- [ ] Resolve the account restriction through an explicit user decision.
- [ ] Match actual GitHub OIDC subjects, including immutable IDs where applicable.
- [ ] Reject unauthorized repositories and deployment contexts.
- [ ] Make deployment depend on all required tests and security/policy checks.
- [ ] Apply the reviewed saved plan and matching package; verify artifact paths and hashes.
- [ ] Constrain IAM role creation and policy changes using permissions boundaries.
- [ ] Demonstrate authenticated endpoint, reviewed public exception and restoration of authentication.

### 5. Kubernetes/GitOps
- [ ] Pin compatible kind, Kubernetes, Argo CD, Kyverno and cosign versions.
- [ ] Accept trusted signed digests; reject unsigned and wrong-signer images.
- [ ] Reject images outside the approved registry scope, unpinned images and unsafe pod configurations.
- [ ] Cover init containers and other applicable container paths.
- [ ] Demonstrate drift repair and clean cluster recreation.

### 6. Operations and cleanup
- [ ] Verify drift and usage monitors, including error handling.
- [ ] Test service teardown and final bootstrap teardown separately.
- [ ] Keep the state backend until dependent service destruction completes.
- [ ] Audit real remaining resources and retained object versions; a tag query is not exhaustive.
- [ ] Record charges and credit consumption separately.

### 7. Final evidence
- [ ] Onboard a second service from the template.
- [ ] Run all documented negative cases and successful deployment paths.
- [ ] Measure onboarding/pipeline durations and retain raw evidence.
- [ ] Complete architecture decisions, threat model, runbooks and demo recording.
- [ ] Verify a clean-clone reproduction and only use measured resume claims.

## Review status

The PDF defects above are static-review findings, not yet executed regression tests.
Still requiring version-specific validation: Kyverno schema and signature formats, action inputs and SHAs, AWS provider arguments, Free Tier API output and exact account permissions.
