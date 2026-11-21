# AWS account decision

Checked 2026-11-20 against the owner's supplied Learner Lab Readme (instructions dated 2025-06-24), screenshots and personal-account documentation. Do not publish the user's credentials or lab account identifiers.

## Confirmed Learner Lab restrictions

- Custom IAM users, groups and roles cannot be created; service-linked roles are the stated exception. The pre-created LabRole is intended for Lambda and other workloads.
- The Readme does not explicitly establish OIDC-provider creation permission. Even if a provider were permitted, inability to create the dedicated federated deployment role blocks the designed GitHub-to-AWS trust path.
- LabRole is broadly privileged across the permitted lab services. Using it is valid for a lab runtime demonstration, but cannot demonstrate our custom least-privilege execution role or permissions boundary.
- Supported service regions are us-east-1 and us-west-2. Lambda, DynamoDB, S3 and CloudWatch are listed as available, with service restrictions.
- Lambda is limited to 10 concurrent execution environments. Check actual account concurrency and reservation behavior before deploying; do not silently remove the intended bound to make an apply pass.
- The owner reported USD 32.10 used of a USD 50 budget: displayed remainder USD 17.90. The Readme says budget updates typically lag 8-12 hours. This is not a verified current balance or a project cost estimate.
- Ending a lab session does not delete all resources or stop all charges. Previously stopped EC2 instances can restart with the next session. Reset deletes work and does not refill the budget.

## What each route can prove

| Route | Can demonstrate | Cannot honestly claim |
| --- | --- | --- |
| Local Docker/kind and public GitHub | Tests, packaging, native architecture scans, signed releases, GitOps, admission and recovery | Live AWS behavior, IAM/OIDC deployment or AWS cleanup |
| Academy with existing LabRole | A bounded, temporary AWS runtime demonstration after read-only inventory and quota checks | The complete custom-IAM/OIDC architecture or durable account availability |
| Personal managed Free Plan (selected) | Custom bounded runtime roles, private state and local CLI deployment, after live validation | GitHub-to-AWS OIDC or unattended cloud CD |
| Compatible account permitting required IAM administration | Full intended bootstrap, GitHub OIDC, service-specific roles, deployment and teardown after validation | Guaranteed zero spending; account compatibility alone does not prove the implementation works |

The owner's current personal account uses AWS's managed Builder ID project experience. Its IAM restrictions are a separate blocker. AWS documents an advanced activation path; changing plan/account features is an explicit user decision. Do not assume that upgrading removes every organization policy, and do not use administrator access keys in GitHub as a workaround.

## Selected route

The owner has explicitly selected the personal AWS account. The Learner Lab is no longer the deployment target. A dedicated personal CLI profile was verified, and a live read returned an explicit SCP denial of IAM provider operations. The owner subsequently declined Paid Plan/advanced activation and chose to keep the Free Plan. On 2026-11-21, the private state bucket and custom bounded runtime roles were successfully created. Identity-provider operations remain blocked, so service deployment uses a local, automatically refreshed CLI credential process. See the [Free Plan runbook](AWS_BOOTSTRAP.md).

## Archived Academy diagnostic

`scripts/aws_lab_diagnostic.py` remains an optional read-only diagnostic for the supplied lab constraints. It is not part of the selected deployment path. It checks the expected account first and treats denied reads as unknown, not empty inventory. No lab resources were deployed or changed for this project.

Primary references: [AWS managed project policies](https://docs.aws.amazon.com/accounts/latest/reference/scps-and-rcps-for-projects.html), [account sign-up comparison](https://docs.aws.amazon.com/accounts/latest/reference/sign-up-for-aws.html), [GitHub immutable OIDC subjects](https://docs.github.com/en/actions/reference/security/oidc).
