mock_provider "aws" {
  mock_resource "aws_iam_policy" {
    defaults = { arn = "arn:aws:iam::123456789012:policy/paved-road/test-boundary" }
  }
  mock_resource "aws_iam_openid_connect_provider" {
    defaults = { arn = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com" }
  }
  mock_resource "aws_s3_bucket" {
    defaults = { id = "paved-road-state-123456789012-ap-southeast-2", arn = "arn:aws:s3:::paved-road-state-123456789012-ap-southeast-2" }
  }
}
variables {
  account_id             = "123456789012"
  enable_github_oidc     = true
  manage_github_provider = true
}
run "scoped_roles_and_private_state" {
  command = plan
  assert {
    condition     = aws_s3_bucket_public_access_block.state.block_public_acls && aws_s3_bucket_public_access_block.state.block_public_policy && aws_s3_bucket_public_access_block.state.ignore_public_acls && aws_s3_bucket_public_access_block.state.restrict_public_buckets
    error_message = "State bucket public access must be fully blocked."
  }
  assert {
    condition     = aws_s3_bucket_versioning.state.versioning_configuration[0].status == "Enabled" && aws_s3_bucket_server_side_encryption_configuration.state.rule != null && aws_s3_bucket.state.force_destroy == false
    error_message = "Preserve versioned, encrypted state and refuse forced bucket deletion."
  }
  assert {
    condition     = local.subjects.demo == "repo:surya-8143@194671008/paved-road-demo-service@1464870818:ref:refs/heads/main"
    error_message = "Trust must bind immutable owner/repository IDs and main branch."
  }
  assert {
    condition     = jsondecode(local.runtime_policy.demo).Statement[0].Action == ["dynamodb:UpdateItem"] && jsondecode(local.runtime_policy.demo).Statement[0].Resource == "arn:aws:dynamodb:ap-southeast-2:123456789012:table/paved-demo"
    error_message = "Runtime database access must target only its own table."
  }
  assert {
    condition     = alltrue([for statement in jsondecode(local.deployment_policy.demo).Statement : alltrue([for action in statement.Action : !startswith(action, "iam:") || contains(["iam:PassRole", "iam:GetRole"], action)])])
    error_message = "Deployment roles cannot manage IAM roles, policies or providers."
  }

}
run "rendered_trust_is_exact" {
  command = plan
  assert {
    condition = jsondecode(aws_iam_role.deployment["demo"].assume_role_policy).Statement[0].Condition.StringEquals == {
      "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
      "token.actions.githubusercontent.com:sub" = "repo:surya-8143@194671008/paved-road-demo-service@1464870818:ref:refs/heads/main"
    }
    error_message = "Rendered trust must use exact audience and immutable main-branch subject."
  }
  assert {
    condition     = jsondecode(aws_iam_role.deployment["demo"].assume_role_policy).Statement[0].Principal.Federated == "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
    error_message = "The trusted provider must belong to the verified target account."
  }
}
run "policy_size_and_trust" {
  command = plan
  assert {
    condition     = alltrue([for name, policy in local.deployment_policy : length(policy) <= 6144])
    error_message = "Managed IAM policies must fit the 6144-character size limit."
  }
  assert {
    condition     = alltrue([for name, subject in local.subjects : endswith(subject, ":ref:refs/heads/main") && !strcontains(subject, "*") && !strcontains(subject, ":pull_request")])
    error_message = "No wildcard, pull-request or alternate branch trust is permitted."
  }
}
run "invalid_account_rejected" {
  command = plan
  variables { account_id = "not-an-account" }
  expect_failures = [var.account_id]
}
run "foreign_owner_rejected" {
  command = plan
  variables { services = { demo = { repository = "outsider/repo", repository_id = "1", owner_id = "2" } } }
  expect_failures = [var.services]
}

run "free_plan_avoids_federation" {
  command = plan
  variables {
    enable_github_oidc     = false
    manage_github_provider = false
  }
  assert {
    condition     = length(aws_iam_openid_connect_provider.github) == 0 && length(data.aws_iam_openid_connect_provider.github) == 0 && length(aws_iam_role.deployment) == 0 && length(aws_iam_policy.deployment_boundary) == 0 && length(aws_iam_role_policy.deployment) == 0
    error_message = "Free Plan mode must not create/read identity providers or provision federated deployment roles."
  }
  assert {
    condition     = length(aws_iam_role.runtime) == 2 && aws_s3_bucket_public_access_block.state.block_public_policy
    error_message = "Keep scoped runtime roles and private state even when federation is disabled."
  }
}
