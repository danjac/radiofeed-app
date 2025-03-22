terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.43"
    }
  }
}

provider "hcloud" {
  token = var.hcloud_token
}

variable "hcloud_token" {}

variable "ssh_public_key_path" {
  default = "~/.ssh/id_rsa.pub"
}

variable "image" {
    default = "ubuntu-24.04"
}

variable "server_type" {
    default = "cpx11"
}

variable "location" {
    default = "hel1"
}

variable "webapp_count" {
    default = 2
}

variable "listen_port" {
    default = 300081
}

resource "hcloud_ssh_key" "default" {
  name       = "my-ssh-key"
  public_key = file(var.ssh_public_key_path)
}

resource "hcloud_network" "private_net" {
  name     = "private-network"
  ip_range = "10.0.0.0/16"
}

resource "hcloud_network_subnet" "private_subnet" {
  network_id   = hcloud_network.private_net.id
  type         = "cloud"
  network_zone = "eu-central"
  ip_range     = "10.0.1.0/24"
}

resource "hcloud_firewall" "firewall-ssh" {
  name = "vm-firewall"

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
}

resource "hcloud_firewall" "firewall-https" {
  name = "vm-firewall"

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
}

resource "hcloud_server" "database" {
  name        = "database"
  image       = var.image
  server_type = var.server_type
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.default.id]
  labels      = { role = "database" }
  firewall_ids = [hcloud_firewall.firewall.id]
  backups     = true

  network {
    network_id = hcloud_network.private_net.id
  }
}

resource "hcloud_server" "server" {
  name        = "server"
  image       = var.image
  server_type = var.server_type
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.default.id]
  labels      = { role = "server" }
  firewall_ids = [hcloud_firewall.firewall.id]

  network {
    network_id = hcloud_network.private_net.id
  }
}

resource "hcloud_server" "jobrunner" {
  name        = "jobrunner"
  image       = var.image
  server_type = var.server_type
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.default.id]
  labels      = { role = "jobrunner" }
  firewall_ids = [hcloud_firewall.firewall.id]

  network {
    network_id = hcloud_network.private_net.id
  }
}

resource "hcloud_server" "webapp" {
  count       = var.webapp_count
  name        = "webapp-${count.index + 1}"
  image       = var.image
  server_type = var.server_type
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.default.id]
  labels      = { role = "webapp" }
  firewall_ids = [hcloud_firewall.firewall.id]

  network {
    network_id = hcloud_network.private_net.id
  }
}
