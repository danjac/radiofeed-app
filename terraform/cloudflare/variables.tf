variable "cloudflare_api_token" {
  description = "Cloudflare API token with Zone:Edit permissions"
  type        = string
  sensitive   = true
}

variable "domain" {
  description = "Domain name (must already exist in Cloudflare)"
  type        = string
}

variable "subdomain" {
  description = "Subdomain for the application (leave empty for root domain)"
  type        = string
  default     = ""
}

variable "server_ip" {
  description = "Public IP address of the server node (from Hetzner Terraform output)"
  type        = string
}

variable "enable_www_redirect" {
  description = "Enable www subdomain redirect to main domain"
  type        = bool
  default     = true
}
