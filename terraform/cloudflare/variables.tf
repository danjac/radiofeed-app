variable "cloudflare_api_token" {
  description = "Cloudflare API token (zone-level permissions): Zone, Zone Settings, DNS, Page Rules, Zone WAF, Transform Rules (all Edit)"
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

variable "grafana_subdomain" {
  description = "Subdomain for Grafana UI (e.g. 'grafana' → grafana.radiofeed.app). Leave empty to skip."
  type        = string
  default     = "grafana"
}

variable "mailgun_dkim_value" {
  description = "Mailgun DKIM public key (from Mailgun dashboard: Sending → Domains → DNS Records). If empty, Mailgun DNS records are skipped."
  type        = string
  default     = ""
}

variable "mailgun_mx_servers" {
  description = "Mailgun MX servers"
  type        = list(string)
  default     = ["mxa.eu.mailgun.org", "mxb.eu.mailgun.org"]
}

variable "mailgun_spf_value" {
  description = "Mailgun SPF record value"
  type        = string
  default     = "v=spf1 include:mailgun.org ~all"
}
