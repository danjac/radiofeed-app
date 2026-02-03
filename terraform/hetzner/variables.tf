variable "hcloud_token" {
  description = "Hetzner Cloud API token"
  type        = string
  sensitive   = true
}

variable "cluster_name" {
  description = "Name prefix for all resources"
  type        = string
  default     = "radiofeed"
}

variable "location" {
  description = "Hetzner datacenter location"
  type        = string
  default     = "nbg1" # Nuremberg, Germany
}

variable "network_zone" {
  description = "Hetzner network zone"
  type        = string
  default     = "eu-central"
}

variable "network_ip_range" {
  description = "IP range for the private network"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_ip_range" {
  description = "IP range for the private subnet"
  type        = string
  default     = "10.0.0.0/24"
}

variable "ssh_public_key" {
  description = "SSH public key for server access"
  type        = string
}

variable "server_image" {
  description = "OS image for all servers"
  type        = string
  default     = "ubuntu-24.04"
}

variable "server_type" {
  description = "Server type for k3s server node"
  type        = string
  default     = "cx23" # 2 vCPU, 4 GB RAM
}

variable "database_server_type" {
  description = "Server type for database node"
  type        = string
  default     = "cx23" # 2 vCPU, 4 GB RAM
}

variable "agent_server_type" {
  description = "Server type for agent nodes (jobrunner, webapps)"
  type        = string
  default     = "cx23" # 2 vCPU, 4 GB RAM
}

variable "webapp_count" {
  description = "Number of webapp instances to create"
  type        = number
  default     = 2
}

variable "postgres_volume_size" {
  description = "Size of PostgreSQL volume in GB"
  type        = number
  default     = 50
}
