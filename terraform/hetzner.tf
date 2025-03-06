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

resource "hcloud_firewall" "firewall" {
  name = "vm-firewall"

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
}

resource "hcloud_load_balancer" "lb" {
  name               = "load-balancer"
  load_balancer_type = "lb11"
  location           = "hel1"
}

resource "hcloud_load_balancer_target" "lb_target_agents" {
  load_balancer_id = hcloud_load_balancer.lb.id
  type             = "label_selector"
  label_selector   = "role=agent"
}

resource "hcloud_load_balancer_service" "lb_http" {
  load_balancer_id = hcloud_load_balancer.lb.id
  protocol         = "http"
  listen_port      = 300081
  destination_port = 8000

  health_check {
    protocol = "http"
    port     = 300081
    interval = 15
    timeout  = 10
    retries  = 3
  }
}

resource "hcloud_server" "database" {
  name        = "database"
  image       = "ubuntu-24.04"
  server_type = "cpx11"
  location    = "hel1"
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
  image       = "ubuntu-24.04"
  server_type = "cpx11"
  location    = "hel1"
  ssh_keys    = [hcloud_ssh_key.default.id]
  labels      = { role = "server" }
  firewall_ids = [hcloud_firewall.firewall.id]

  network {
    network_id = hcloud_network.private_net.id
  }
}

resource "hcloud_server" "agents" {
  count       = 2
  name        = "agent-${count.index + 1}"
  image       = "ubuntu-24.04"
  server_type = "cpx11"
  location    = "hel1"
  ssh_keys    = [hcloud_ssh_key.default.id]
  labels      = { role = "agent" }
  firewall_ids = [hcloud_firewall.firewall.id]

  network {
    network_id = hcloud_network.private_net.id
  }
}
