output "zone_id" {
  description = "Cloudflare zone ID"
  value       = data.cloudflare_zone.domain.id
}

output "zone_name" {
  description = "Cloudflare zone name"
  value       = data.cloudflare_zone.domain.name
}

output "nameservers" {
  description = "Cloudflare nameservers for this zone"
  value       = data.cloudflare_zone.domain.name_servers
}

output "server_record_name" {
  description = "DNS record name for the server"
  value       = cloudflare_record.server.hostname
}

output "server_record_value" {
  description = "DNS record value (IP address)"
  value       = cloudflare_record.server.value
}

output "dns_status" {
  description = "Cloudflare DNS status (active when nameservers are pointed correctly)"
  value       = data.cloudflare_zone.domain.status
}

output "ssl_mode" {
  description = "Cloudflare SSL/TLS mode"
  value       = cloudflare_zone_settings_override.domain_settings.settings[0].ssl
}
