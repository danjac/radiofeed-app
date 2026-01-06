# Cloudflare Zone (use existing or create new)
data "cloudflare_zone" "existing" {
  count = var.cloudflare_zone_id != "" ? 1 : 0
  zone_id = var.cloudflare_zone_id
}

resource "cloudflare_zone" "new" {
  count   = var.cloudflare_zone_id == "" ? 1 : 0
  account_id = var.cloudflare_account_id
  zone    = var.domain
}

locals {
  zone_id = var.cloudflare_zone_id != "" ? var.cloudflare_zone_id : cloudflare_zone.new[0].id
}

# SSL/TLS settings
resource "cloudflare_zone_settings_override" "ssl" {
  zone_id = local.zone_id

  settings {
    ssl                      = var.cloudflare_ssl_mode
    always_use_https         = var.cloudflare_always_use_https ? "on" : "off"
    min_tls_version          = var.cloudflare_min_tls_version
    automatic_https_rewrites = "on"
    tls_1_3                  = "on"
  }
}

# A record for root domain -> server IP
resource "cloudflare_record" "root" {
  zone_id = local.zone_id
  name    = "@"
  content = hcloud_server.server.ipv4_address
  type    = "A"
  proxied = var.cloudflare_proxied
  ttl     = var.cloudflare_proxied ? 1 : 300
}

# CNAME record for www -> root domain
resource "cloudflare_record" "www" {
  zone_id = local.zone_id
  name    = "www"
  content = var.domain
  type    = "CNAME"
  proxied = var.cloudflare_proxied
  ttl     = var.cloudflare_proxied ? 1 : 300
}
