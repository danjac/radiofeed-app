# Private Network
resource "hcloud_network" "cluster" {
  count    = var.create_network ? 1 : 0
  name     = var.network_name
  ip_range = var.network_ip_range
  labels   = var.labels
}

resource "hcloud_network_subnet" "cluster" {
  count        = var.create_network ? 1 : 0
  network_id   = hcloud_network.cluster[0].id
  type         = "cloud"
  network_zone = "eu-central"
  ip_range     = var.subnet_ip_range
}

# Database Server
resource "hcloud_server" "database" {
  name        = var.database_name
  server_type = var.database_server_type
  image       = var.image
  location    = var.location
  ssh_keys    = var.ssh_keys
  labels      = merge(var.labels, { role = "database" })

  public_net {
    ipv4_enabled = true
    ipv6_enabled = true
  }

  dynamic "network" {
    for_each = var.create_network ? [1] : []
    content {
      network_id = hcloud_network.cluster[0].id
    }
  }

  depends_on = [hcloud_network_subnet.cluster]
}

# Web Servers
resource "hcloud_server" "web" {
  count       = var.web_count
  name        = "${var.web_name_prefix}-${count.index + 1}"
  server_type = var.web_server_type
  image       = var.image
  location    = var.location
  ssh_keys    = var.ssh_keys
  labels      = merge(var.labels, { role = "web" })

  public_net {
    ipv4_enabled = true
    ipv6_enabled = true
  }

  dynamic "network" {
    for_each = var.create_network ? [1] : []
    content {
      network_id = hcloud_network.cluster[0].id
    }
  }

  depends_on = [hcloud_network_subnet.cluster]
}

# Load Balancer Server
resource "hcloud_server" "server" {
  name        = var.server_name
  server_type = var.server_server_type
  image       = var.image
  location    = var.location
  ssh_keys    = var.ssh_keys
  labels      = merge(var.labels, { role = "server" })

  public_net {
    ipv4_enabled = true
    ipv6_enabled = true
  }

  dynamic "network" {
    for_each = var.create_network ? [1] : []
    content {
      network_id = hcloud_network.cluster[0].id
    }
  }

  depends_on = [hcloud_network_subnet.cluster]
}

# Job Runner Server
resource "hcloud_server" "jobrunner" {
  name        = var.jobrunner_name
  server_type = var.jobrunner_server_type
  image       = var.image
  location    = var.location
  ssh_keys    = var.ssh_keys
  labels      = merge(var.labels, { role = "jobrunner" })

  public_net {
    ipv4_enabled = true
    ipv6_enabled = true
  }

  dynamic "network" {
    for_each = var.create_network ? [1] : []
    content {
      network_id = hcloud_network.cluster[0].id
    }
  }

  depends_on = [hcloud_network_subnet.cluster]
}

# Data Volume (attached to database server)
resource "hcloud_volume" "data" {
  name      = var.volume_name
  size      = var.volume_size
  location  = var.location
  format    = var.volume_format
  automount = var.volume_automount
  labels    = var.labels
}

resource "hcloud_volume_attachment" "data" {
  volume_id = hcloud_volume.data.id
  server_id = hcloud_server.database.id
  automount = var.volume_automount
}

# Firewall for SSH access (all servers)
resource "hcloud_firewall" "ssh" {
  name   = "ssh"
  labels = var.labels

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
}

# Firewall for HTTP/HTTPS (server only)
resource "hcloud_firewall" "web" {
  name   = "web"
  labels = var.labels

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
}

# Attach SSH firewall to all servers
resource "hcloud_firewall_attachment" "ssh_database" {
  firewall_id = hcloud_firewall.ssh.id
  server_ids  = [hcloud_server.database.id]
}

resource "hcloud_firewall_attachment" "ssh_web" {
  firewall_id = hcloud_firewall.ssh.id
  server_ids  = hcloud_server.web[*].id
}

resource "hcloud_firewall_attachment" "ssh_server" {
  firewall_id = hcloud_firewall.ssh.id
  server_ids  = [hcloud_server.server.id]
}

resource "hcloud_firewall_attachment" "ssh_jobrunner" {
  firewall_id = hcloud_firewall.ssh.id
  server_ids  = [hcloud_server.jobrunner.id]
}

# Attach web firewall to server only
resource "hcloud_firewall_attachment" "web_server" {
  firewall_id = hcloud_firewall.web.id
  server_ids  = [hcloud_server.server.id]
}
