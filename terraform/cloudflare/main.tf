terraform {
  required_version = ">= 1.0"

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# Get the zone (domain must already exist in Cloudflare)
data "cloudflare_zone" "domain" {
  name = var.domain
}

# A record pointing to the server node (k3s control plane + load balancer)
resource "cloudflare_record" "server" {
  zone_id         = data.cloudflare_zone.domain.id
  name            = var.subdomain != "" ? var.subdomain : "@"
  content         = var.server_ip
  type            = "A"
  proxied         = true # Enable Cloudflare proxy (CDN + SSL)
  ttl             = 1    # Automatic TTL when proxied
  allow_overwrite = true # Adopt existing record if present
  comment         = "Radiofeed server node - managed by Terraform"
}

# Optional: WWW redirect
resource "cloudflare_record" "www" {
  count           = var.enable_www_redirect ? 1 : 0
  zone_id         = data.cloudflare_zone.domain.id
  name            = "www"
  content         = var.subdomain != "" ? "${var.subdomain}.${var.domain}" : var.domain
  type            = "CNAME"
  proxied         = true
  ttl             = 1
  allow_overwrite = true # Adopt existing record if present
  comment         = "WWW redirect - managed by Terraform"
}

locals {
  mailgun_dkim_value = trimspace(var.mailgun_dkim_value)
}

# Mailgun DNS records (optional, only created when mailgun_dkim_value is set)
resource "cloudflare_record" "mailgun_mx" {
  count           = local.mailgun_dkim_value != "" ? length(var.mailgun_mx_servers) : 0
  zone_id         = data.cloudflare_zone.domain.id
  name            = "mg"
  content         = var.mailgun_mx_servers[count.index]
  type            = "MX"
  priority        = 10
  ttl             = 1
  allow_overwrite = true
  comment         = "Mailgun MX - managed by Terraform"
}

resource "cloudflare_record" "mailgun_spf" {
  count           = local.mailgun_dkim_value != "" ? 1 : 0
  zone_id         = data.cloudflare_zone.domain.id
  name            = "mg"
  content         = "\"${var.mailgun_spf_value}\""
  type            = "TXT"
  ttl             = 1
  allow_overwrite = true
  comment         = "Mailgun SPF - managed by Terraform"
}

resource "cloudflare_record" "mailgun_dkim" {
  count           = local.mailgun_dkim_value != "" ? 1 : 0
  zone_id         = data.cloudflare_zone.domain.id
  name            = "mta._domainkey.mg"
  content         = "\"${local.mailgun_dkim_value}\""
  type            = "TXT"
  ttl             = 1
  allow_overwrite = true
  comment         = "Mailgun DKIM - managed by Terraform"
}

resource "cloudflare_record" "mailgun_tracking" {
  count           = local.mailgun_dkim_value != "" ? 1 : 0
  zone_id         = data.cloudflare_zone.domain.id
  name            = "email.mg"
  content         = "eu.mailgun.org"
  type            = "CNAME"
  proxied         = false # DNS only
  ttl             = 1
  allow_overwrite = true
  comment         = "Mailgun tracking - managed by Terraform"
}

# SSL/TLS settings
resource "cloudflare_zone_settings_override" "domain_settings" {
  zone_id = data.cloudflare_zone.domain.id

  settings {
    # SSL/TLS
    ssl                      = "full" # Full (strict) requires valid certificate on origin
    always_use_https         = "on"
    automatic_https_rewrites = "on"
    min_tls_version          = "1.2"
    tls_1_3                  = "on"

    # Security
    security_level = "medium"
    challenge_ttl  = 1800
    browser_check  = "on"

    # Performance
    brotli                   = "on"
    early_hints              = "on"
    http3                    = "on"
    opportunistic_encryption = "on"
    rocket_loader            = "off" # Disable for HTMX/Alpine.js compatibility

    # Caching
    browser_cache_ttl = 14400 # 4 hours
    cache_level       = "aggressive"

    # Other
    ipv6       = "on"
    websockets = "on"
  }
}

# Page rule for caching static assets by file extension
resource "cloudflare_page_rule" "cache_static_assets" {
  zone_id  = data.cloudflare_zone.domain.id
  target   = "${var.subdomain != "" ? "${var.subdomain}.${var.domain}" : var.domain}/*.{css,js,png,jpg,jpeg,webp,gif,svg,ico,woff,woff2}"
  priority = 1

  actions {
    cache_level       = "cache_everything"
    edge_cache_ttl    = 2592000 # 30 days
    browser_cache_ttl = 1800    # 30 minutes
  }
}

# Firewall rule to allow only HTTPS traffic
resource "cloudflare_ruleset" "zone_level_firewall" {
  zone_id = data.cloudflare_zone.domain.id
  name    = "Zone-level firewall"
  kind    = "zone"
  phase   = "http_request_firewall_custom"

  rules {
    action      = "block"
    expression  = "(http.request.uri.path contains \".env\") or (http.request.uri.path contains \".git\") or (http.request.uri.path contains \"wp-admin\")"
    description = "Block common exploit paths"
    enabled     = true
  }
}

# Security headers
resource "cloudflare_ruleset" "transform_response_headers" {
  zone_id = data.cloudflare_zone.domain.id
  name    = "Transform Rules - Response Headers"
  kind    = "zone"
  phase   = "http_response_headers_transform"

  rules {
    action      = "rewrite"
    description = "Add security headers"
    enabled     = true
    expression  = "true"

    action_parameters {
      headers {
        name      = "Referrer-Policy"
        operation = "set"
        value     = "strict-origin-when-cross-origin"
      }
      headers {
        name      = "X-Content-Type-Options"
        operation = "set"
        value     = "nosniff"
      }
      headers {
        name      = "X-Frame-Options"
        operation = "set"
        value     = "SAMEORIGIN"
      }
    }
  }
}
