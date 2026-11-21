variable "enable_github_oidc" {
  type        = bool
  default     = false
  description = "Disabled for managed Free Plan accounts. Enable only after explicit authorization and account compatibility checks."
}
variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Provide the verified 12-digit personal AWS account ID."
  }
}
variable "region" {
  type    = string
  default = "ap-southeast-2"
  validation {
    condition     = contains(["ap-southeast-2", "ap-south-1", "us-east-1"], var.region)
    error_message = "Choose one explicitly reviewed project region."
  }
}
variable "manage_github_provider" {
  type        = bool
  default     = false
  description = "False uses an existing provider without owning it. True creates a new project-owned provider after inspection."
}
variable "services" {
  type = map(object({ repository = string, repository_id = string, owner_id = string }))
  default = {
    demo     = { repository = "surya-8143/paved-road-demo-service", repository_id = "1464870818", owner_id = "194671008" }
    template = { repository = "surya-8143/paved-road-template", repository_id = "1464428547", owner_id = "194671008" }
  }
  validation {
    condition = length(var.services) >= 1 && length(var.services) <= 2 && alltrue([
      for name, service in var.services : can(regex("^[a-z][a-z0-9-]{2,24}$", name)) &&
      can(regex("^surya-8143/[a-zA-Z0-9_.-]+$", service.repository)) &&
      can(regex("^[0-9]+$", service.repository_id)) && service.owner_id == "194671008"
    ])
    error_message = "Allow one or two named services belonging to the reviewed GitHub owner and immutable repository IDs."
  }
}
