terraform {
  required_version = ">= 1.0"

  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
  }
}

provider "hcloud" {
  token = var.hcloud_token
}

locals {
  # Fixed private IPs — deterministic, referenced in cloud-init templates
  server_private_ip    = cidrhost(var.subnet_ip_range, 2) # 10.0.0.2
  database_private_ip  = cidrhost(var.subnet_ip_range, 3) # 10.0.0.3
  jobrunner_private_ip = cidrhost(var.subnet_ip_range, 4) # 10.0.0.4
  webapp_private_ips   = [for i in range(var.webapp_count) : cidrhost(var.subnet_ip_range, 5 + i)]
}

# Private network for internal communication
resource "hcloud_network" "private_network" {
  name     = "${var.cluster_name}-network"
  ip_range = var.network_ip_range
}

resource "hcloud_network_subnet" "private_subnet" {
  network_id   = hcloud_network.private_network.id
  type         = "cloud"
  network_zone = var.network_zone
  ip_range     = var.subnet_ip_range
}

# SSH key for server access
resource "hcloud_ssh_key" "default" {
  name       = "${var.cluster_name}-key"
  public_key = var.ssh_public_key
}

# Firewall for server node (k3s control plane + load balancer)
resource "hcloud_firewall" "server" {
  name = "${var.cluster_name}-server-firewall"

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "any"
    source_ips = [var.network_ip_range]
  }

  rule {
    direction  = "in"
    protocol   = "udp"
    port       = "any"
    source_ips = [var.network_ip_range]
  }

  rule {
    direction  = "in"
    protocol   = "icmp"
    source_ips = [var.network_ip_range]
  }
}

# Firewall for agent nodes (database, jobrunner, webapps)
resource "hcloud_firewall" "agents" {
  name = "${var.cluster_name}-agents-firewall"

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "any"
    source_ips = [var.network_ip_range]
  }

  rule {
    direction  = "in"
    protocol   = "udp"
    port       = "any"
    source_ips = [var.network_ip_range]
  }

  rule {
    direction  = "in"
    protocol   = "icmp"
    source_ips = [var.network_ip_range]
  }
}

# Volume for PostgreSQL data (pre-formatted ext4)
resource "hcloud_volume" "postgres" {
  name     = "${var.cluster_name}-postgres-volume"
  size     = var.postgres_volume_size
  location = var.location
  format   = "ext4"
}

# Server node (k3s control plane + Traefik load balancer)
resource "hcloud_server" "server" {
  name         = "${var.cluster_name}-server"
  server_type  = var.server_type
  image        = var.server_image
  location     = var.location
  ssh_keys     = [hcloud_ssh_key.default.id]
  firewall_ids = [hcloud_firewall.server.id]

  user_data = templatefile("${path.module}/templates/cloud_init_server.tftpl", {
    hostname       = "${var.cluster_name}-server"
    private_ip     = local.server_private_ip
    k3s_token      = var.k3s_token
    ssh_public_key = var.ssh_public_key
  })

  labels = {
    cluster = var.cluster_name
    role    = "server"
  }

  public_net {
    ipv4_enabled = true
    ipv6_enabled = true
  }

  network {
    network_id = hcloud_network.private_network.id
    ip         = local.server_private_ip
  }

  depends_on = [hcloud_network_subnet.private_subnet]

  lifecycle {
    ignore_changes = [user_data, ssh_keys]
  }
}

# Database node (PostgreSQL + Redis)
resource "hcloud_server" "database" {
  name         = "${var.cluster_name}-database"
  server_type  = var.database_server_type
  image        = var.server_image
  location     = var.location
  ssh_keys     = [hcloud_ssh_key.default.id]
  firewall_ids = [hcloud_firewall.agents.id]

  user_data = templatefile("${path.module}/templates/cloud_init_database.tftpl", {
    hostname          = "${var.cluster_name}-database"
    server_private_ip = local.server_private_ip
    k3s_token         = var.k3s_token
    ssh_public_key    = var.ssh_public_key
  })

  labels = {
    cluster = var.cluster_name
    role    = "database"
  }

  public_net {
    ipv4_enabled = true
    ipv6_enabled = true
  }

  network {
    network_id = hcloud_network.private_network.id
    ip         = local.database_private_ip
  }

  depends_on = [hcloud_network_subnet.private_subnet]

  lifecycle {
    ignore_changes = [user_data, ssh_keys]
  }
}

resource "hcloud_volume_attachment" "postgres_attachment" {
  volume_id = hcloud_volume.postgres.id
  server_id = hcloud_server.database.id
  automount = true
}

# Job runner node (for cron jobs and background workers)
resource "hcloud_server" "jobrunner" {
  name         = "${var.cluster_name}-jobrunner"
  server_type  = var.agent_server_type
  image        = var.server_image
  location     = var.location
  ssh_keys     = [hcloud_ssh_key.default.id]
  firewall_ids = [hcloud_firewall.agents.id]

  user_data = templatefile("${path.module}/templates/cloud_init_agent.tftpl", {
    hostname          = "${var.cluster_name}-jobrunner"
    server_private_ip = local.server_private_ip
    k3s_token         = var.k3s_token
    ssh_public_key    = var.ssh_public_key
    role              = "jobrunner"
  })

  labels = {
    cluster = var.cluster_name
    role    = "jobrunner"
  }

  public_net {
    ipv4_enabled = true
    ipv6_enabled = true
  }

  network {
    network_id = hcloud_network.private_network.id
    ip         = local.jobrunner_private_ip
  }

  depends_on = [hcloud_network_subnet.private_subnet]

  lifecycle {
    ignore_changes = [user_data, ssh_keys]
  }
}

# Web application nodes
resource "hcloud_server" "webapp" {
  count        = var.webapp_count
  name         = "${var.cluster_name}-webapp-${count.index + 1}"
  server_type  = var.agent_server_type
  image        = var.server_image
  location     = var.location
  ssh_keys     = [hcloud_ssh_key.default.id]
  firewall_ids = [hcloud_firewall.agents.id]

  user_data = templatefile("${path.module}/templates/cloud_init_agent.tftpl", {
    hostname          = "${var.cluster_name}-webapp-${count.index + 1}"
    server_private_ip = local.server_private_ip
    k3s_token         = var.k3s_token
    ssh_public_key    = var.ssh_public_key
    role              = "webapp"
  })

  labels = {
    cluster = var.cluster_name
    role    = "webapp"
  }

  public_net {
    ipv4_enabled = true
    ipv6_enabled = true
  }

  network {
    network_id = hcloud_network.private_network.id
    ip         = local.webapp_private_ips[count.index]
  }

  depends_on = [hcloud_network_subnet.private_subnet]

  lifecycle {
    ignore_changes = [user_data, ssh_keys]
  }
}
