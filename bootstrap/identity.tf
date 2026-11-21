resource "aws_iam_openid_connect_provider" "github" {
  count          = var.enable_github_oidc && var.manage_github_provider ? 1 : 0
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  # AWS retrieves the CA thumbprint when omitted; no stale hard-coded fingerprint.
  lifecycle { prevent_destroy = true }
}
data "aws_iam_openid_connect_provider" "github" {
  count = var.enable_github_oidc && !var.manage_github_provider ? 1 : 0
  url   = "https://token.actions.githubusercontent.com"
}
locals {
  github_provider_arn = "arn:aws:iam::${var.account_id}:oidc-provider/token.actions.githubusercontent.com"
  subjects = { for name, service in var.services : name =>
    "repo:${split("/", service.repository)[0]}@${service.owner_id}/${split("/", service.repository)[1]}@${service.repository_id}:ref:refs/heads/main"
  }
  runtime_policy = { for name, service in var.services : name => jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["dynamodb:UpdateItem"], Resource = "arn:aws:dynamodb:${var.region}:${var.account_id}:table/paved-${name}",
    Condition = { "ForAllValues:StringEquals" = { "dynamodb:LeadingKeys" = ["hits"] } } },
    { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"],
    Resource = "arn:aws:logs:${var.region}:${var.account_id}:log-group:/aws/lambda/paved-${name}:log-stream:*" }
  ] }) }
}
resource "aws_iam_policy" "runtime_boundary" {
  for_each = var.services
  name     = "${each.key}-runtime-boundary"
  path     = "/paved-road/"
  policy   = local.runtime_policy[each.key]
}
resource "aws_iam_role" "runtime" {
  for_each             = var.services
  name                 = "${each.key}-runtime"
  path                 = "/paved-road/"
  permissions_boundary = aws_iam_policy.runtime_boundary[each.key].arn
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole"
  }] })
}
resource "aws_iam_role_policy" "runtime" {
  for_each = var.services
  name     = "runtime"
  role     = aws_iam_role.runtime[each.key].id
  policy   = local.runtime_policy[each.key]
}
resource "aws_iam_policy" "deployment_boundary" {
  for_each = var.enable_github_oidc ? var.services : {}
  name     = "${each.key}-deployment-boundary"
  path     = "/paved-road/"
  policy   = local.deployment_policy[each.key]
}
resource "aws_iam_role" "deployment" {
  depends_on           = [aws_iam_openid_connect_provider.github, data.aws_iam_openid_connect_provider.github]
  for_each             = var.enable_github_oidc ? var.services : {}
  name                 = "${each.key}-deploy"
  path                 = "/paved-road/"
  max_session_duration = 3600
  permissions_boundary = aws_iam_policy.deployment_boundary[each.key].arn
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Federated = local.github_provider_arn }, Action = "sts:AssumeRoleWithWebIdentity",
    Condition = { StringEquals = {
      "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com",
      "token.actions.githubusercontent.com:sub" = local.subjects[each.key]
    } }
  }] })
}
resource "aws_iam_role_policy" "deployment" {
  for_each = var.enable_github_oidc ? var.services : {}
  name     = "deploy-service"
  role     = aws_iam_role.deployment[each.key].id
  policy   = local.deployment_policy[each.key]
}
