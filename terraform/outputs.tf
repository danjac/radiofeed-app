# Database Server
output "database_ipv4" {
  description = "Public IPv4 address of the database server"
  value       = hcloud_server.database.ipv4_address
}

output "database_ipv6" {
  description = "Public IPv6 address of the database server"
  value       = hcloud_server.database.ipv6_address
}

output "database_private_ip" {
  description = "Private IP address of the database server"
  value       = var.create_network ? hcloud_server.database.network[*].ip : null
}

# Web Servers
output "web_ipv4" {
  description = "Public IPv4 addresses of web servers"
  value       = hcloud_server.web[*].ipv4_address
}

output "web_ipv6" {
  description = "Public IPv6 addresses of web servers"
  value       = hcloud_server.web[*].ipv6_address
}

output "web_private_ips" {
  description = "Private IP addresses of web servers"
  value       = var.create_network ? [for s in hcloud_server.web : s.network[*].ip] : null
}

# Server (load balancer/reverse proxy)
output "server_ipv4" {
  description = "Public IPv4 address of the server"
  value       = hcloud_server.server.ipv4_address
}

output "server_ipv6" {
  description = "Public IPv6 address of the server"
  value       = hcloud_server.server.ipv6_address
}

output "server_private_ip" {
  description = "Private IP address of the server"
  value       = var.create_network ? hcloud_server.server.network[*].ip : null
}

# Job Runner Server
output "jobrunner_ipv4" {
  description = "Public IPv4 address of the job runner server"
  value       = hcloud_server.jobrunner.ipv4_address
}

output "jobrunner_ipv6" {
  description = "Public IPv6 address of the job runner server"
  value       = hcloud_server.jobrunner.ipv6_address
}

output "jobrunner_private_ip" {
  description = "Private IP address of the job runner server"
  value       = var.create_network ? hcloud_server.jobrunner.network[*].ip : null
}

# Volume
output "volume_id" {
  description = "ID of the data volume"
  value       = hcloud_volume.data.id
}

output "volume_linux_device" {
  description = "Linux device path of the volume"
  value       = hcloud_volume.data.linux_device
}

# Network
output "network_id" {
  description = "ID of the private network"
  value       = var.create_network ? hcloud_network.cluster[0].id : null
}

# All server IPs (useful for Ansible inventory)
output "all_servers" {
  description = "Map of all servers with their IPs"
  value = {
    database = {
      ipv4       = hcloud_server.database.ipv4_address
      ipv6       = hcloud_server.database.ipv6_address
      private_ip = var.create_network ? hcloud_server.database.network[*].ip : null
    }
    server = {
      ipv4       = hcloud_server.server.ipv4_address
      ipv6       = hcloud_server.server.ipv6_address
      private_ip = var.create_network ? hcloud_server.server.network[*].ip : null
    }
    jobrunner = {
      ipv4       = hcloud_server.jobrunner.ipv4_address
      ipv6       = hcloud_server.jobrunner.ipv6_address
      private_ip = var.create_network ? hcloud_server.jobrunner.network[*].ip : null
    }
    web = [for i, s in hcloud_server.web : {
      name       = s.name
      ipv4       = s.ipv4_address
      ipv6       = s.ipv6_address
      private_ip = var.create_network ? s.network[*].ip : null
    }]
  }
}

# Cloudflare
output "cloudflare_zone_id" {
  description = "Cloudflare Zone ID"
  value       = local.zone_id
}

output "cloudflare_nameservers" {
  description = "Cloudflare nameservers (update your domain registrar with these)"
  value       = var.cloudflare_zone_id == "" ? cloudflare_zone.new[0].name_servers : data.cloudflare_zone.existing[0].name_servers
}

output "domain_url" {
  description = "Application URL"
  value       = "https://${var.domain}"
}
