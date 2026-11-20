output "function_name" { value = aws_lambda_function.service.function_name }
output "function_arn" { value = aws_lambda_function.service.arn }
output "function_url" { value = aws_lambda_function_url.service.function_url }
output "table_name" { value = aws_dynamodb_table.hits.name }
output "package_sha256" { value = filebase64sha256(var.lambda_zip) }
