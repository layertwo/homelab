# VCN Outputs
output "vcn_id" {
  description = "VCN ID"
  value       = oci_core_vcn.vcn.id
}

output "vcn_cidr" {
  description = "VCN CIDR block"
  value       = var.vcn_cidr
}

# Subnet Outputs
output "subnet_id" {
  description = "Public subnet ID"
  value       = oci_core_subnet.public_subnet.id
}

output "subnet_cidr" {
  description = "Public subnet CIDR"
  value       = var.public_subnet_cidr
}

# Network Configuration Outputs
output "home_infra_network_cidr" {
  description = "Home infrastructure network CIDR"
  value       = var.home_infra_network_cidr
}

output "home_regular_network_cidr" {
  description = "Home regular network CIDR"
  value       = var.home_regular_network_cidr
}

# VPN Outputs
output "ipsec_shared_secret" {
  description = "IPSec pre-shared key for VPN configuration"
  value       = var.enable_vpn ? local.ipsec_shared_secret : "VPN not enabled"
  sensitive   = true
}

output "vpn_tunnel_1_ip" {
  description = "Oracle Cloud VPN Tunnel 1 public IP"
  value       = var.enable_vpn ? data.oci_core_ipsec_connection_tunnels.home_ipsec_tunnels[0].ip_sec_connection_tunnels[0].vpn_ip : "VPN not enabled"
}

output "vpn_tunnel_2_ip" {
  description = "Oracle Cloud VPN Tunnel 2 public IP"
  value       = var.enable_vpn ? data.oci_core_ipsec_connection_tunnels.home_ipsec_tunnels[0].ip_sec_connection_tunnels[1].vpn_ip : "VPN not enabled"
}

output "vpn_tunnel_1_status" {
  description = "VPN Tunnel 1 status"
  value       = var.enable_vpn ? data.oci_core_ipsec_connection_tunnels.home_ipsec_tunnels[0].ip_sec_connection_tunnels[0].status : "VPN not enabled"
}

output "vpn_tunnel_2_status" {
  description = "VPN Tunnel 2 status"
  value       = var.enable_vpn ? data.oci_core_ipsec_connection_tunnels.home_ipsec_tunnels[0].ip_sec_connection_tunnels[1].status : "VPN not enabled"
}

output "vpn_enabled" {
  description = "Whether VPN is enabled"
  value       = var.enable_vpn
}