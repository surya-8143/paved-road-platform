variable "service_name" {
  type        = string
  description = "Short service identifier; also used for resource ownership tags."
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,24}$", var.service_name))
    error_message = "Use 3-25 lowercase letters, digits or hyphens."
  }
}
variable "execution_role_arn" {
  type        = string
  description = "Pre-bootstrapped, bounded runtime role; the deployment role cannot create or modify IAM roles."
  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:role/paved-road/[a-z0-9-]+-runtime$", var.execution_role_arn))
    error_message = "Provide a service runtime role under the paved-road IAM path."
  }
}
variable "lambda_zip" {
  type        = string
  description = "Verified Lambda release ZIP; its file hash is bound into the saved plan."
}
variable "owner" {
  type    = string
  default = "surya-8143"
}
variable "public_url" {
  type        = bool
  default     = false
  description = "Requires an unexpired platform-policy exception for this exact function. IAM authentication is the default."
}
variable "reserved_concurrency" {
  type    = number
  default = 2
  validation {
    condition     = contains([0, 1, 2], var.reserved_concurrency)
    error_message = "Only 0 (stop), 1 or 2 reserved executions are allowed."
  }
}
