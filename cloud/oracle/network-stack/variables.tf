# OCI Provider Authentication
variable "tenancy_ocid" {
  description = "OCI Tenancy OCID"
  type        = string
  default     = ""
}

variable "user_ocid" {
  description = "OCI User OCID"
  type        = string
  default     = ""
}

variable "fingerprint" {
  description = "OCI API Key Fingerprint"
  type        = string
  default     = ""
}

variable "private_key_path" {
  description = "Path to OCI API private key"
  type        = string
  default     = ""
}

variable "region" {
  description = "OCI Region"
  type        = string
  default     = "us-phoenix-1"
}

variable "compartment_ocid" {
  description = "OCI Compartment OCID (usually same as tenancy for Always Free)"
  type        = string
  default     = ""
}

# Network Configuration
variable "vcn_cidr" {
  description = "VCN CIDR block"
  type        = string
  default     = "172.31.2.0/23"
}

variable "public_subnet_cidr" {
  description = "Public subnet CIDR block"
  type        = string
  default     = "172.31.2.0/24"
}

variable "home_infra_network_cidr" {
  description = "Home infrastructure network CIDR block (K3s cluster)"
  type        = string
  default     = "172.31.0.0/24"
}

variable "home_regular_network_cidr" {
  description = "Home regular network CIDR block (user devices)"
  type        = string
  default     = "192.168.255.0/24"
}

variable "home_public_ip" {
  description = "Home public IP address or hostname (e.g., ip.layertwo.dev)"
  type        = string
  default     = ""
  
  validation {
    condition     = length(var.home_public_ip) > 0
    error_message = "Home public IP or hostname must be provided for VPN and SSH access."
  }
}

# VPN Configuration
variable "ipsec_shared_secret" {
  description = "IPSec pre-shared key (leave empty to auto-generate)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "enable_vpn" {
  description = "Enable VPN configuration"
  type        = bool
  default     = true
}

# Resource Naming
variable "resource_prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "layertwo-cloud"
}

variable "tags" {
  description = "Freeform tags to apply to resources"
  type        = map(string)
  default = {
    Environment = "homelab"
    ManagedBy   = "terraform"
    Purpose     = "layertwo-cloud"
    Stack       = "network"
  }
}