# Hetzner Cloud API Token
variable "hcloud_token" {
  description = "Hetzner Cloud API token"
  type        = string
  sensitive   = true
}

# General settings
variable "location" {
  description = "Hetzner datacenter location (fsn1, nbg1, hel1, ash, hil)"
  type        = string
  default     = "fsn1"
}

variable "ssh_keys" {
  description = "List of SSH key names or IDs to add to servers"
  type        = list(string)
  default     = []
}

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "image" {
  description = "OS image for all servers"
  type        = string
  default     = "ubuntu-24.04"
}

# Database VM
variable "database_server_type" {
  description = "Hetzner server type for database VM (e.g., cx22, cx32, cx42)"
  type        = string
  default     = "cx22"
}

variable "database_name" {
  description = "Name for the database server"
  type        = string
  default     = "database"
}

# Web VMs
variable "web_count" {
  description = "Number of web servers to create"
  type        = number
  default     = 2
}

variable "web_server_type" {
  description = "Hetzner server type for web VMs"
  type        = string
  default     = "cx22"
}

variable "web_name_prefix" {
  description = "Name prefix for web servers"
  type        = string
  default     = "web"
}

# Server VM (load balancer/reverse proxy)
variable "server_server_type" {
  description = "Hetzner server type for server VM"
  type        = string
  default     = "cx22"
}

variable "server_name" {
  description = "Name for the server"
  type        = string
  default     = "server"
}

# Job Runner VM
variable "jobrunner_server_type" {
  description = "Hetzner server type for job runner VM"
  type        = string
  default     = "cx22"
}

variable "jobrunner_name" {
  description = "Name for the job runner server"
  type        = string
  default     = "jobrunner"
}

# Volume
variable "volume_size" {
  description = "Size of the volume in GB"
  type        = number
  default     = 50
}

variable "volume_name" {
  description = "Name for the volume"
  type        = string
  default     = "data"
}

variable "volume_format" {
  description = "Filesystem format for the volume (ext4, xfs)"
  type        = string
  default     = "ext4"
}

variable "volume_automount" {
  description = "Whether to automount the volume"
  type        = bool
  default     = true
}

# Network settings
variable "create_network" {
  description = "Whether to create a private network"
  type        = bool
  default     = true
}

variable "network_ip_range" {
  description = "IP range for the private network"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_ip_range" {
  description = "IP range for the subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "network_name" {
  description = "Name for the private network"
  type        = string
  default     = "cluster-network"
}

# Cloudflare settings
variable "cloudflare_api_token" {
  description = "Cloudflare API token"
  type        = string
  sensitive   = true
}

variable "cloudflare_account_id" {
  description = "Cloudflare Account ID"
  type        = string
}

variable "cloudflare_zone_id" {
  description = "Cloudflare Zone ID (leave empty to create new zone)"
  type        = string
  default     = ""
}

variable "domain" {
  description = "Domain name for the application"
  type        = string
}

variable "cloudflare_proxied" {
  description = "Whether to proxy traffic through Cloudflare"
  type        = bool
  default     = true
}

variable "cloudflare_ssl_mode" {
  description = "SSL/TLS encryption mode (off, flexible, full, strict)"
  type        = string
  default     = "full"
}

variable "cloudflare_always_use_https" {
  description = "Always redirect HTTP to HTTPS"
  type        = bool
  default     = true
}

variable "cloudflare_min_tls_version" {
  description = "Minimum TLS version (1.0, 1.1, 1.2, 1.3)"
  type        = string
  default     = "1.2"
}
