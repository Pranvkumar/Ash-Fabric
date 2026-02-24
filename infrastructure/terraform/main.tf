terraform {
  required_version = ">= 1.5.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {
  # Uses local Docker socket — no cloud costs during development
  host = "unix:///var/run/docker.sock"
}

# ── Variables (injected by Execution Agent) ──────────────────

variable "service_name" {
  description = "Name of the service to manage"
  type        = string
  default     = "api-gateway"
}

variable "service_image" {
  description = "Docker image for the service"
  type        = string
  default     = "nginx:alpine"
}

variable "replica_count" {
  description = "Number of container replicas"
  type        = number
  default     = 1
}

variable "memory_limit" {
  description = "Memory limit in MB"
  type        = number
  default     = 256
}

variable "cpu_limit" {
  description = "CPU shares (relative weight)"
  type        = number
  default     = 512
}

# ── Resources ────────────────────────────────────────────────

resource "docker_network" "ash_network" {
  name = "ash-fabric-net"
}

resource "docker_container" "service" {
  count = var.replica_count
  name  = "${var.service_name}-${count.index}"
  image = var.service_image

  memory = var.memory_limit
  cpu_shares = var.cpu_limit

  networks_advanced {
    name = docker_network.ash_network.name
  }

  labels {
    label = "managed-by"
    value = "ash-fabric"
  }

  labels {
    label = "service"
    value = var.service_name
  }

  restart = "unless-stopped"

  lifecycle {
    create_before_destroy = true
  }
}

# ── Outputs ──────────────────────────────────────────────────

output "container_ids" {
  value = docker_container.service[*].id
}

output "container_names" {
  value = docker_container.service[*].name
}
