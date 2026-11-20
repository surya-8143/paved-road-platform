# Architecture decisions

Decisions recorded 2026-11-20. These reflect implemented choices, with live AWS work explicitly pending.

## 1. Separate application, platform and consumer repositories

The platform owns shared CI, release verification, policy and cluster setup. The template owns a small application and its dependency locks. A third repository generated through GitHub proves a consumer can call the pinned platform workflow. This separates reusable platform behavior from application onboarding without pretending three repositories alone create a platform.

## 2. Two independently gated runtime artifacts

Containers support local Kubernetes; a deterministic Python 3.12 ZIP supports the planned Lambda path. Container scanning cannot stand in for Lambda-package scanning: their Linux distributions, wheels and dependency inventories differ. Both artifacts have their own smoke/security gates and a signed manifest ties the release together. Native AMD64/ARM64 jobs avoid claiming an architecture was tested under a different native runtime.

## 3. Patch and pin the container base based on observed findings

Initial Debian and Alpine builds failed the actual vulnerability gate. The selected Alpine image plus a pinned Kerberos update passed without ignore files or ignore-unfixed flags. This is a measured result for the database at build time, not a permanent assertion that Alpine is safer. Rebuilds must keep failing when newly disclosed HIGH/CRITICAL vulnerabilities appear.

## 4. Resolve one offline provider unknown through a source contract

AWS provider 6.73.0 marks an omitted DynamoDB secondary-index set unknown for a new table. The offline checker accepts an empty set only for the fixed, fingerprinted module, exact new-table address and no restore/import source. It preserves the original plan, rejects changed sources and leaves other unknowns intact. This targeted offline rule is not an online apply gate; cloud planning still needs fresh account evidence and a reviewed equivalent contract.

## 5. Use current Kyverno CEL policy APIs and a native availability guard

Kyverno 1.20 no longer enforces legacy ClusterPolicy rules. Runtime/image policies use its current CEL APIs, with actual acceptance/rejection tests. Image verification uses the exact workflow certificate subject and signed publisher annotations because this API does not expose all certificate extension selectors. The independent release verifier also checks source-repository/source-SHA certificate information.

An outage drill discovered that a graceful zero-replica shutdown deletes managed webhooks. A native Kubernetes admission policy now blocks that transition and deployment deletion. The real outage test keeps desired replicas one, stops the old pod with an unschedulable Recreate rollout, verifies rejection and restores the exact configuration. This preserves useful fail-closed behavior while making administrator powers and availability tradeoffs explicit.

## 6. Keep local infrastructure small and claims narrow

One kind node and one admission replica fit the 16 GB laptop. Optional Argo components are scaled to zero, service resources are bounded, and API/HTTP access is loopback-only. This is not high availability. NetworkPolicy enforcement is deliberately not claimed with the default kind CNI. Use a real enforcing CNI and test connectivity before adding that claim.

## 7. Do not bypass the AWS account restriction with static administrator keys

The supplied console is the managed Builder ID project experience, whose IAM constraints conflict with the planned GitHub OIDC bootstrap. A paid-plan/advanced activation must not happen automatically. The college lab is a possible alternative only if its actual permissions permit the required resources and identity setup. Offline infrastructure checks and local Kubernetes demonstrate useful engineering while this account decision remains unresolved; they do not count as an AWS deployment.
