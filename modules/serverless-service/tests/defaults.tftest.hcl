mock_provider "aws" {}
variables {
  service_name       = "unit-test"
  execution_role_arn = "arn:aws:iam::123456789012:role/paved-road/unit-test-runtime"
  lambda_zip         = "tests/fixture.zip"
}
run "secure_defaults" {
  command = plan
  assert {
    condition     = aws_lambda_function_url.service.authorization_type == "AWS_IAM"
    error_message = "The function URL must require IAM authentication by default."
  }
  assert {
    condition     = aws_lambda_function.service.reserved_concurrent_executions == 2 && aws_lambda_function.service.memory_size == 128 && aws_lambda_function.service.timeout == 5
    error_message = "Runtime limits changed."
  }
  assert {
    condition     = aws_dynamodb_table.hits.read_capacity == 1 && aws_dynamodb_table.hits.write_capacity == 1 && aws_dynamodb_table.hits.billing_mode == "PROVISIONED"
    error_message = "Database capacity must be bounded."
  }
  assert {
    condition     = aws_cloudwatch_log_group.service.retention_in_days == 7
    error_message = "Logs must expire after seven days."
  }
}
run "invalid_role_rejected" {
  command = plan
  variables {
    execution_role_arn = "arn:aws:iam::123456789012:role/Administrator"
  }
  expect_failures = [var.execution_role_arn]
}
run "invalid_concurrency_rejected" {
  command = plan
  variables {
    reserved_concurrency = -1
  }
  expect_failures = [var.reserved_concurrency]
}
