# Serverless service module

Creates six resources: one Python 3.12 Lambda function, an IAM-authenticated function URL, a provisioned DynamoDB table, a seven-day log group, and two standard CloudWatch alarms. The alarms record state; no email/SNS notification destination is configured.

The Lambda ZIP is passed in after supply-chain verification, and its SHA-256 is included in the saved plan. The runtime role must already exist under `role/paved-road/<service>-runtime`. Service deployments do not create IAM roles. The separate bootstrap is still being implemented and has not been applied.

Defaults: 128 MB, five-second timeout, two reserved executions, 512 MB temporary storage, one DynamoDB read/write unit, no replicas/indexes, no PITR, and no published Lambda versions. DynamoDB encryption uses AWS-owned keys; `server_side_encryption.enabled = false` avoids opting into a KMS key and does not disable DynamoDB's default encryption at rest.

New AWS accounts can have concurrency quotas too small to reserve two executions. A deployment must check `lambda get-account-settings` first; do not silently remove the concurrency limit to make a deployment pass.

`public_url = true` alone is insufficient: policy requires an unexpired reviewed exception for the exact function and at most one reserved execution. The current exception list is empty. AWS provider 6.73.0 manages public URL resource permissions; their creation, removal and restoration to IAM must be verified in AWS before claiming that demo path complete.

## Offline checks

From the platform root:

```bash
export PATH="$HOME/.local/bin:$PATH"
bash scripts/check_infrastructure.sh
python3 scripts/check_plan.py build/offline-plan.json
```

`tofu test` uses a mocked provider. The example plan uses dummy credentials, disables credential/metadata lookups, and never applies resources. The generated ZIP is a deliberately non-deployable fixture.

The AWS provider models omitted global indexes as an unknown Optional+Computed set. The offline checker resolves that one field only for a newly created table from this exact fingerprinted module. It rejects changed module source, foreign module paths, restore/import sources, and leaves other unknowns untouched. Raw plans remain unchanged. The generic Rego policy still rejects unresolved security fields. This source contract is specific to the offline example; it is not a generic online deployment approval.

## Cost limits

These are resource limits, not a spending ceiling. A 128 MB function running continuously at concurrency two can consume 648,000 GB-seconds in 30 days. Requests, logs, databases, alarms, state storage and other account resources are separate usage sources. Promotional credits can offset charges without making usage free. The offline context explicitly assumes zero other-stack usage solely for tests; an online workflow must fetch fresh account inventory and include it before applying.

AWS deployment is currently blocked by the owner's managed Free Plan project IAM restrictions. No cloud execution is claimed.
