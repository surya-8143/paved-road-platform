locals {
  name = "paved-${var.service_name}"
  tags = {
    Project     = "paved-road"
    Owner       = var.owner
    Environment = "demo"
    Service     = var.service_name
    ManagedBy   = "opentofu"
  }
}
resource "aws_dynamodb_table" "hits" {
  name                        = local.name
  billing_mode                = "PROVISIONED"
  read_capacity               = 1
  write_capacity              = 1
  hash_key                    = "pk"
  stream_enabled              = false
  table_class                 = "STANDARD"
  deletion_protection_enabled = false
  attribute {
    name = "pk"
    type = "S"
  }
  # AWS-owned encryption is always on; false avoids opting into a KMS key.
  server_side_encryption {
    enabled = false
  }
  point_in_time_recovery {
    enabled = false
  }
  tags = local.tags
}
resource "aws_cloudwatch_log_group" "service" {
  name              = "/aws/lambda/${local.name}"
  retention_in_days = 7
  tags              = local.tags
}
resource "aws_lambda_function" "service" {
  function_name                  = local.name
  description                    = "Paved Road ${var.service_name} demo"
  role                           = var.execution_role_arn
  filename                       = var.lambda_zip
  source_code_hash               = filebase64sha256(var.lambda_zip)
  package_type                   = "Zip"
  runtime                        = "python3.12"
  handler                        = "app.main.handler"
  architectures                  = ["x86_64"]
  memory_size                    = 128
  timeout                        = 5
  reserved_concurrent_executions = var.reserved_concurrency
  publish                        = false
  ephemeral_storage {
    size = 512
  }
  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.hits.name
    }
  }
  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.service.name
  }
  tags       = local.tags
  depends_on = [aws_cloudwatch_log_group.service]
}
resource "aws_lambda_function_url" "service" {
  function_name      = aws_lambda_function.service.function_name
  authorization_type = var.public_url ? "NONE" : "AWS_IAM"
  invoke_mode        = "BUFFERED"
}
resource "aws_cloudwatch_metric_alarm" "errors" {
  alarm_name                = "${local.name}-errors"
  alarm_description         = "Service Lambda errors; inspect CloudWatch. No email subscription is assumed."
  namespace                 = "AWS/Lambda"
  metric_name               = "Errors"
  statistic                 = "Sum"
  comparison_operator       = "GreaterThanOrEqualToThreshold"
  threshold                 = 1
  evaluation_periods        = 1
  period                    = 300
  treat_missing_data        = "notBreaching"
  alarm_actions             = []
  ok_actions                = []
  insufficient_data_actions = []
  dimensions                = { FunctionName = aws_lambda_function.service.function_name }
  tags                      = local.tags
}
resource "aws_cloudwatch_metric_alarm" "throttles" {
  alarm_name                = "${local.name}-throttles"
  alarm_description         = "Service Lambda throttling; alarm state has no configured notification target."
  namespace                 = "AWS/Lambda"
  metric_name               = "Throttles"
  statistic                 = "Sum"
  comparison_operator       = "GreaterThanOrEqualToThreshold"
  threshold                 = 1
  evaluation_periods        = 1
  period                    = 300
  treat_missing_data        = "notBreaching"
  alarm_actions             = []
  ok_actions                = []
  insufficient_data_actions = []
  dimensions                = { FunctionName = aws_lambda_function.service.function_name }
  tags                      = local.tags
}
