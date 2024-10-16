terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
  }
}


# Set the variable value in *.tfvars file
# or using the -var="hcloud_token=..." CLI option
variable "hcloud_token" {
  sensitive = true
}

variable "domain" {
  type = string
}

variable "server_type" {
  type    = string
  default = "cx11"
}

variable "image" {
  type    = string
  default = "ubuntu-20.04"
}


variable "app_servers" {
  type    = list(string)
  default = ["app-1", "app-2"]
}

variable "db_server" {
  type    = string
  default = "db-1"
}

variable "cron_server" {
  type    = string
  default = "cron-1"
}

variable "network" {
  type    = string
  default = "network-1"
}

variable "network_ip_range" {
  type    = string
  default = "10.0.0.0/16"
}

variable "network_subnet_ip_range" {
  type    = string
  default = "10.0.0.0/24"

}
variable "network_zone" {
  type    = string
  default = "eu-central"
}

variable "ssh_key" {
  type    = string
  default = "ssh-key-1"
}

variable "load_balancer" {
  type    = string
  default = "lb-1"
}

# Configure the Hetzner Cloud Provider
provider "hcloud" {
  token = var.hcloud_token
}

# Create firewall
resource "hcloud_firewall" "firewall" {
  name = "firewall"

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "22"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
  }
}

# Create a network
resource "hcloud_network" "network" {
  name     = var.network
  ip_range = var.network_ip_range
}

resource "hcloud_network_subnet" "subnet" {
  network_id   = hcloud_network.network.id
  type         = "cloud"
  network_zone = var.network_zone
  ip_range     = var.network_subnet_ip_range
}

# Add SSH keys
resource "hcloud_ssh_key" "ssh_key" {
  name       = var.ssh_key
  public_key = file("~/.ssh/id_rsa.pub")
}

# Create app servers
resource "hcloud_server" "web" {
  count        = length(var.app_servers)
  name         = var.app_servers[count.index]
  server_type  = var.server_type
  image        = var.image
  ssh_keys     = [var.ssh_key]
  firewall_ids = [hcloud_firewall.firewall.id]
}

# Create cron server
resource "hcloud_server" "cron" {
  name         = var.cron_server
  server_type  = var.server_type
  image        = var.image
  ssh_keys     = [var.ssh_key]
  firewall_ids = [hcloud_firewall.firewall.id]
}

# Create db server
resource "hcloud_server" "db" {
  name         = var.db_server
  server_type  = var.server_type
  image        = var.image
  ssh_keys     = [var.ssh_key]
  firewall_ids = [hcloud_firewall.firewall.id]
}

# Attach servers to network

resource "hcloud_load_balancer_network" "lb_srvnetwork" {
  load_balancer_id = hcloud_load_balancer.lb.id
  network_id       = hcloud_network.network.id
}

resource "hcloud_server_network" "app_srvnetwork" {
  count      = length(var.app_servers)
  network_id = hcloud_network.network.id
  server_id  = hcloud_server.web[count.index].id
}

resource "hcloud_server_network" "cron_srvnetwork" {
  network_id = hcloud_network.network.id
  server_id  = hcloud_server.cron.id
}

resource "hcloud_server_network" "db_srvnetwork" {
  network_id = hcloud_network.network.id
  server_id  = hcloud_server.db.id
}

# create a managed certificate
resource "hcloud_managed_certificate" "managed_cert" {
  name         = "managed_cert"
  domain_names = [var.domain]
}

# Create a load balancer
resource "hcloud_load_balancer" "lb" {
  name               = var.load_balancer
  load_balancer_type = "lb11"
  network_zone       = var.network_zone
}

# Attach app servers to load balancer
resource "hcloud_load_balancer_target" "load_balancer_target" {
  count            = length(var.app_servers)
  type             = "server"
  load_balancer_id = hcloud_load_balancer.lb.id
  server_id        = hcloud_server.web[count.index].id
}

resource "hcloud_load_balancer_service" "load_balancer_service" {
  load_balancer_id = var.load_balancer
  protocol         = "https"
  listen_port      = 443
  destination_port = 8000

  http {
    certificates = [hcloud_managed_certificate.managed_cert.id]
  }

  health_check {
    protocol = "https"
    port     = 443
    interval = 10
    timeout  = 5

    http {
      domain       = var.domain
      path         = "/ht/"
      response     = "OK"
      tls          = true
      status_codes = ["200"]
    }
  }
}
