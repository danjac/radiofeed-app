output "server_public_ip" {
  description = "Public IPv4 address of the server node"
  value       = hcloud_server.server.ipv4_address
}

output "server_private_ip" {
  description = "Private IP address of the server node"
  value       = hcloud_server_network.server_network.ip
}

output "database_public_ip" {
  description = "Public IPv4 address of the database node"
  value       = hcloud_server.database.ipv4_address
}

output "database_private_ip" {
  description = "Private IP address of the database node"
  value       = hcloud_server_network.database_network.ip
}

output "jobrunner_public_ip" {
  description = "Public IPv4 address of the jobrunner node"
  value       = hcloud_server.jobrunner.ipv4_address
}

output "jobrunner_private_ip" {
  description = "Private IP address of the jobrunner node"
  value       = hcloud_server_network.jobrunner_network.ip
}

output "webapp_public_ips" {
  description = "Public IPv4 addresses of webapp nodes"
  value       = hcloud_server.webapp[*].ipv4_address
}

output "webapp_private_ips" {
  description = "Private IP addresses of webapp nodes"
  value       = hcloud_server_network.webapp_network[*].ip
}

output "postgres_volume_id" {
  description = "ID of the PostgreSQL volume"
  value       = hcloud_volume.postgres.id
}

output "postgres_volume_linux_device" {
  description = "Linux device path for PostgreSQL volume"
  value       = hcloud_volume.postgres.linux_device
}

output "network_id" {
  description = "ID of the private network"
  value       = hcloud_network.private_network.id
}

output "ansible_inventory" {
  description = "Ansible inventory snippet for hosts.yml"
  value = templatefile("${path.module}/templates/ansible_inventory.tftpl", {
    server_public_ip    = hcloud_server.server.ipv4_address
    server_private_ip   = hcloud_server_network.server_network.ip
    database_public_ip  = hcloud_server.database.ipv4_address
    jobrunner_public_ip = hcloud_server.jobrunner.ipv4_address
    webapp_public_ips   = hcloud_server.webapp[*].ipv4_address
    postgres_volume_id  = hcloud_volume.postgres.id
  })
}
