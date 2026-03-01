output "server_public_ip" {
  description = "Public IPv4 address of the server node"
  value       = hcloud_server.server.ipv4_address
}

output "server_private_ip" {
  description = "Private IP address of the server node"
  value       = local.server_private_ip
}

output "database_public_ip" {
  description = "Public IPv4 address of the database node"
  value       = hcloud_server.database.ipv4_address
}

output "database_private_ip" {
  description = "Private IP address of the database node"
  value       = local.database_private_ip
}

output "jobrunner_public_ip" {
  description = "Public IPv4 address of the jobrunner node"
  value       = hcloud_server.jobrunner.ipv4_address
}

output "jobrunner_private_ip" {
  description = "Private IP address of the jobrunner node"
  value       = local.jobrunner_private_ip
}

output "webapp_public_ips" {
  description = "Public IPv4 addresses of webapp nodes"
  value       = hcloud_server.webapp[*].ipv4_address
}

output "webapp_private_ips" {
  description = "Private IP addresses of webapp nodes"
  value       = local.webapp_private_ips
}

output "postgres_volume_id" {
  description = "ID of the PostgreSQL volume"
  value       = hcloud_volume.postgres.id
}

output "postgres_volume_linux_device" {
  description = "Linux device path for PostgreSQL volume"
  value       = hcloud_volume.postgres.linux_device
}

output "postgres_volume_mount_path" {
  description = "Automount path for PostgreSQL volume — use as postgres.volumePath in helm/radiofeed/values.yaml"
  value       = "/mnt/HC_Volume_${hcloud_volume.postgres.id}"
}

output "network_id" {
  description = "ID of the private network"
  value       = hcloud_network.private_network.id
}

output "get_kubeconfig_cmd" {
  description = "Command to fetch kubeconfig from the server"
  value       = "ssh ubuntu@${hcloud_server.server.ipv4_address} 'cat /home/ubuntu/.kube/config' | sed 's/127.0.0.1/${hcloud_server.server.ipv4_address}/g' > ~/.kube/radiofeed.yaml"
}
