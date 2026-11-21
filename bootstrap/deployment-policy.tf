locals {
  deployment_policy = { for name, service in var.services : name => jsonencode({ Version = "2012-10-17", Statement = [
    { Sid = "ServiceFunction", Effect = "Allow", Action = [
      "lambda:CreateFunction", "lambda:DeleteFunction", "lambda:GetFunction", "lambda:GetFunctionConfiguration",
      "lambda:UpdateFunctionCode", "lambda:UpdateFunctionConfiguration", "lambda:ListTags", "lambda:TagResource", "lambda:UntagResource",
      "lambda:GetFunctionConcurrency", "lambda:PutFunctionConcurrency", "lambda:DeleteFunctionConcurrency",
      "lambda:GetFunctionCodeSigningConfig", "lambda:GetRuntimeManagementConfig", "lambda:GetPolicy",
      "lambda:CreateFunctionUrlConfig", "lambda:GetFunctionUrlConfig", "lambda:UpdateFunctionUrlConfig", "lambda:DeleteFunctionUrlConfig",
      "lambda:AddPermission", "lambda:RemovePermission", "lambda:InvokeFunction", "lambda:InvokeFunctionUrl"
    ], Resource = ["arn:aws:lambda:${var.region}:${var.account_id}:function:paved-${name}"] },
    { Sid = "ServiceTable", Effect = "Allow", Action = [
      "dynamodb:CreateTable", "dynamodb:DeleteTable", "dynamodb:UpdateTable", "dynamodb:DescribeTable",
      "dynamodb:DescribeContinuousBackups", "dynamodb:UpdateContinuousBackups", "dynamodb:DescribeTimeToLive", "dynamodb:UpdateTimeToLive",
      "dynamodb:ListTagsOfResource", "dynamodb:TagResource", "dynamodb:UntagResource"
    ], Resource = "arn:aws:dynamodb:${var.region}:${var.account_id}:table/paved-${name}" },
    { Sid = "ServiceLogs", Effect = "Allow", Action = [
      "logs:CreateLogGroup", "logs:DeleteLogGroup", "logs:PutRetentionPolicy", "logs:DeleteRetentionPolicy", "logs:ListTagsForResource",
      "logs:TagResource", "logs:UntagResource", "logs:ListTagsLogGroup", "logs:TagLogGroup", "logs:UntagLogGroup", "logs:DescribeLogStreams"
    ], Resource = ["arn:aws:logs:${var.region}:${var.account_id}:log-group:/aws/lambda/paved-${name}", "arn:aws:logs:${var.region}:${var.account_id}:log-group:/aws/lambda/paved-${name}:*"] },
    { Sid = "ServiceAlarms", Effect = "Allow", Action = ["cloudwatch:PutMetricAlarm", "cloudwatch:DeleteAlarms", "cloudwatch:ListTagsForResource", "cloudwatch:TagResource", "cloudwatch:UntagResource"],
    Resource = ["arn:aws:cloudwatch:${var.region}:${var.account_id}:alarm:paved-${name}-errors", "arn:aws:cloudwatch:${var.region}:${var.account_id}:alarm:paved-${name}-throttles"] },
    { Sid = "RegionalInventory", Effect = "Allow", Action = ["lambda:ListFunctions", "lambda:GetAccountSettings", "dynamodb:ListTables", "cloudwatch:DescribeAlarms", "logs:DescribeLogGroups"],
    Resource = "*", Condition = { StringEquals = { "aws:RequestedRegion" = var.region } } },
    { Sid = "ReadRegionalTableCapacity", Effect = "Allow", Action = ["dynamodb:DescribeTable"], Resource = "arn:aws:dynamodb:${var.region}:${var.account_id}:table/*" },
    { Sid = "PassOnlyOwnRuntimeRole", Effect = "Allow", Action = ["iam:PassRole"], Resource = "arn:aws:iam::${var.account_id}:role/paved-road/${name}-runtime",
    Condition = { StringEquals = { "iam:PassedToService" = "lambda.amazonaws.com" } } },
    { Sid = "InspectOwnRuntimeRole", Effect = "Allow", Action = ["iam:GetRole"], Resource = "arn:aws:iam::${var.account_id}:role/paved-road/${name}-runtime" },
    { Sid = "ListOwnStatePrefix", Effect = "Allow", Action = ["s3:ListBucket"], Resource = "arn:aws:s3:::${local.state_bucket}",
    Condition = { StringLike = { "s3:prefix" = ["services/${name}/*"] } } },
    { Sid = "ReadStateBucket", Effect = "Allow", Action = ["s3:GetBucketLocation", "s3:GetBucketVersioning"], Resource = "arn:aws:s3:::${local.state_bucket}" },
    { Sid = "OwnState", Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"], Resource = "arn:aws:s3:::${local.state_bucket}/services/${name}/terraform.tfstate" },
    { Sid = "OwnLock", Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], Resource = "arn:aws:s3:::${local.state_bucket}/services/${name}/terraform.tfstate.tflock" }
  ] }) }
}
