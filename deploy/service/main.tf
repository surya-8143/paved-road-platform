terraform {
  required_version = "= 1.13.9"
  required_providers {
    aws = { source = "hashicorp/aws", version = "= 6.73.0" }
  }
  backend "s3" {}
}
provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}
variable "account_id" { type = string }
variable "region" { type = string }
variable "service_name" {
  type = string
  validation {
    condition     = contains(["demo", "template"], var.service_name)
    error_message = "Use a reviewed service release."
  }
}
variable "lambda_zip" { type = string }
module "service" {
  source               = "../../modules/serverless-service"
  service_name         = var.service_name
  execution_role_arn   = "arn:aws:iam::${var.account_id}:role/paved-road/${var.service_name}-runtime"
  lambda_zip           = var.lambda_zip
  public_url           = false
  reserved_concurrency = 2
}
output "service" { value = module.service }
