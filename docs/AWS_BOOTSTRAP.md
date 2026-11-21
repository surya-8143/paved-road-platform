# Personal Free Plan deployment

The owner explicitly chose **keep the current Free Plan**. This is the selected implementation profile. The original GitHub-to-AWS OIDC design remains optional and unexecuted because this managed project denies identity-provider operations. The runner never upgrades the account, activates advanced features, or creates/reads an identity provider.

## Architecture and authority

`bootstrap/` defaults `enable_github_oidc=false` and creates a private S3 state bucket plus bounded runtime roles for `demo` and `template`. Runtime permissions allow only `UpdateItem` on the service's own table with partition key `hits`, and stream writes in its pre-created log group. The same narrow policy is the role's permissions boundary. Runtime trust allows Lambda only.

The local operator uses the existing managed owner session from `aws login`. **That operator has broad account permissions.** The local checks are review and error-prevention controls, not an IAM boundary against a malicious operator. No credentials are stored in GitHub, and this is not unattended cloud CD. The optional OIDC deployment roles have scoped policies and immutable GitHub main-branch subjects, but mock tests/token inspection do not prove AWS federation works.

State storage enables all four Block Public Access flags, bucket-owner-enforced ownership, AES256 encryption, versioning and TLS-only requests. Noncurrent versions expire after 30 days; incomplete multipart uploads after one day. The bucket has `prevent_destroy` and no forced deletion. Runtime roles are created under `/paved-road/`; AWS-managed roles are not changed.

The selected region is Sydney (`ap-southeast-2`). Service stacks use `services/<service>/terraform.tfstate` and native S3 locking. Bootstrap state remains local under `~/.local/state/paved-road/<account>/<region>/bootstrap/bootstrap` in WSL. The parent directory is private and new files use umask 077. Keep an encrypted backup of this directory outside Git before changing or removing the WSL distribution.

## Setup

Requires Windows AWS CLI with `aws login`, WSL Ubuntu 24.04, Python 3.12, the pinned tools in `VERSIONS.md`, and the repository's checked-in provider lock files. In WSL:

```bash
cd /mnt/d/CLOUD/paved-road-platform
python3 -m venv ~/.cache/paved-road/cloud-tools
~/.cache/paved-road/cloud-tools/bin/python -m pip install --require-hashes -r requirements-cloud.txt
export PATH="$HOME/.local/bin:$PATH"
```

In ordinary PowerShell, refresh the dedicated personal profile when needed:

```powershell
aws login --profile paved-road-personal --region ap-southeast-2
aws sts get-caller-identity --profile paved-road-personal --region ap-southeast-2 --query Account --output text
```

Do not paste credentials into chat or files. `scripts/Invoke-FreePlan.ps1` configures a local SDK/provider credential process backed by the installed Windows CLI. Its private configuration contains a command and profile name, not secrets. The helper captures `aws configure export-credentials --format process`, accepts temporary sessions only, and returns the standard JSON protocol directly to the SDK/provider. This permits automatic refresh during longer operations. Never invoke the helper directly in a terminal. The runner clears ambient AWS identity/endpoint and OpenTofu debug/argument overrides. Credentials still exist in process memory; this is not protection against a compromised machine.

## Plan, review, apply

Replace `<account>` with the verified personal account ID. Run from the platform repository in PowerShell:

```powershell
.\scripts\Invoke-FreePlan.ps1 -Action bootstrap-plan -AccountId <account>
.\scripts\Invoke-FreePlan.ps1 -Action bootstrap-apply -AccountId <account> -PlanSha256 <printed-plan-hash>
```

Review the plan before passing its digest. The runner refuses a different account, region, configuration fingerprint, binary digest, operation, or plan older than 15 minutes. It checks that the account remains FREE/ACTIVE, has at least USD 20 credit headroom, and expires more than one day ahead. Credits/usage reporting can lag; this check is not a billing cap.

Download the retained signed archive from the relevant `v0.1.0-supply-chain` GitHub prerelease and extract it into a local directory. The release selection is fixed by repository, source commit and signing workflow SHA in `deploy/releases.json`. For the demo:

```powershell
.\scripts\Invoke-FreePlan.ps1 -Action plan -AccountId <account> -Service demo -ReleaseDirectory D:\CLOUD\.local\evidence\demo-admission-release
.\scripts\Invoke-FreePlan.ps1 -Action apply -AccountId <account> -Service demo -PlanSha256 <printed-plan-hash>
.\scripts\Invoke-FreePlan.ps1 -Action smoke -AccountId <account> -Service demo
```

Release verification covers the signed manifest, Lambda ZIP/SBOM, multi-architecture index, both architecture signatures and SBOM attestations. The exact ZIP hash is bound into the binary plan and checked again before apply. There is no deployment-time rebuild.

The online gate collects every page of regional Lambda/table/alarm inventory, counts unmanaged resources and DynamoDB indexes, and excludes only exact resources already owned by this stack's prior state. Denied reads fail closed. Non-active, on-demand or global tables stop provisioning because this profile cannot safely bound their capacity. The shared Rego gate checks full planned resources, tags, sizes, aggregate capacity, replacements and critical unknowns. The one omitted GSI field uses the same fingerprinted source contract as the offline gate; raw plans remain intact.

Inventory is refreshed immediately before apply. A local advisory lock serializes this runner for the account/region; the S3 lock protects each stack's state. Neither lock prevents a different workstation, console operator or unrelated AWS client from creating resources concurrently. Inventory is regional, not an organization-wide cost inventory.

## Live checks, drift and cleanup

The smoke test verifies the deployed ZIP hash, unauthenticated HTTP 403, signed health/hello responses, and two counter increments against a consistent DynamoDB read. The endpoint stays `AWS_IAM`; this profile does not expose a public demo URL. Function URLs require both invocation permissions under current AWS rules.

A fresh `plan` refreshes actual resources and reports drift. Apply the reviewed plan to repair it. There is no autonomous cloud drift-remediation schedule.

```powershell
.\scripts\Invoke-FreePlan.ps1 -Action status -AccountId <account>
.\scripts\Invoke-FreePlan.ps1 -Action destroy-plan -AccountId <account> -Service demo
.\scripts\Invoke-FreePlan.ps1 -Action destroy -AccountId <account> -Service demo -PlanSha256 <printed-plan-hash>
```

Destroy applies only the reviewed service plan. It removes the service's Lambda, URL, table (including demo counter data), log group and alarms. It leaves the bootstrap roles and versioned state bucket for future reproductions. A separate reviewed procedure is required to remove that bucket and its versions after service cleanup/state backup; do not remove state before its managed resources.

## Verification and honest limits

`python3 -m unittest discover -s tests -v` exercises account, credential, plan-substitution, inventory and policy failures. `bash scripts/check_infrastructure.sh` checks the service module, bootstrap's six mocked plans, boundary wiring and the deployment root without AWS access. Live results belong in `docs/evidence`; tests alone do not establish AWS permissions.

Lambda, DynamoDB provisioned capacity, S3 storage/requests/versions and CloudWatch are metered. This small, short-lived demo consumes credits and makes no zero-resource-cost guarantee. No NAT, load balancer, EC2, EKS or customer-managed KMS key is created. Local status queries show credits and usage counts; they are not budget alerts or a hard spend ceiling.

Sources: [managed project policies](https://docs.aws.amazon.com/accounts/latest/reference/scps-and-rcps-for-projects.html), [CLI credential configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html), [S3 state locking](https://opentofu.org/docs/language/settings/backends/s3/), [Lambda URL authorization](https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html).
