output "state_bucket" { value = aws_s3_bucket.state.id }
output "github_subjects" { value = local.subjects }
output "runtime_roles" { value = { for name, role in aws_iam_role.runtime : name => role.arn } }
output "deployment_roles" { value = { for name, role in aws_iam_role.deployment : name => role.arn } }
