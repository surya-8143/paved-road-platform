terraform {
  required_version = "= 1.13.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.73.0"
    }
  }
}
# This configuration is for planning ONLY. The credentials are deliberate dummies.
provider "aws" {
  region                      = "ap-south-1"
  access_key                  = "offline-not-a-real-key"
  secret_key                  = "offline-not-a-real-secret"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  skip_region_validation      = true
}
module "service" {
  source             = "../../modules/serverless-service"
  service_name       = "offline-demo"
  execution_role_arn = "arn:aws:iam::123456789012:role/paved-road/offline-demo-runtime"
  lambda_zip         = "../../modules/serverless-service/tests/fixture.zip"
}
