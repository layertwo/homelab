# Generate IPSec shared secret if not provided
resource "random_password" "ipsec_secret" {
  count   = var.enable_vpn && var.ipsec_shared_secret == "" ? 1 : 0
  length  = 32
  special = true
}

locals {
  ipsec_shared_secret = var.enable_vpn ? (
    var.ipsec_shared_secret != "" ? var.ipsec_shared_secret : random_password.ipsec_secret[0].result
  ) : ""
}

# DRG (Dynamic Routing Gateway)
resource "oci_core_drg" "drg" {
  count          = var.enable_vpn ? 1 : 0
  compartment_id = var.compartment_ocid
  display_name   = "${var.resource_prefix}-drg"
  
  freeform_tags = var.tags
}

# DRG Attachment to VCN
resource "oci_core_drg_attachment" "drg_attachment" {
  count  = var.enable_vpn ? 1 : 0
  drg_id = oci_core_drg.drg[0].id
  
  network_details {
    id   = oci_core_vcn.vcn.id
    type = "VCN"
  }
  
  display_name  = "${var.resource_prefix}-drg-attachment"
  freeform_tags = var.tags
}

# CPE (Customer Premises Equipment) - Your home network
resource "oci_core_cpe" "home_cpe" {
  count          = var.enable_vpn ? 1 : 0
  compartment_id = var.compartment_ocid
  ip_address     = var.home_public_ip
  display_name   = "${var.resource_prefix}-home-cpe"
  
  freeform_tags = merge(
    var.tags,
    {
      Location = "home"
    }
  )
}

# IPSec Connection
resource "oci_core_ipsec" "home_ipsec" {
  count          = var.enable_vpn ? 1 : 0
  compartment_id = var.compartment_ocid
  cpe_id         = oci_core_cpe.home_cpe[0].id
  drg_id         = oci_core_drg.drg[0].id
  
  static_routes = [
    var.home_infra_network_cidr,
    var.home_regular_network_cidr
  ]
  display_name  = "${var.resource_prefix}-home-ipsec"
  
  freeform_tags = var.tags
}

# Get IPSec connection device config
data "oci_core_ipsec_connection_tunnels" "home_ipsec_tunnels" {
  count     = var.enable_vpn ? 1 : 0
  ipsec_id  = oci_core_ipsec.home_ipsec[0].id
}

# Configure IPSec Tunnel
resource "oci_core_ipsec_connection_tunnel_management" "tunnel_1" {
  count     = var.enable_vpn ? 1 : 0
  ipsec_id  = oci_core_ipsec.home_ipsec[0].id
  tunnel_id = data.oci_core_ipsec_connection_tunnels.home_ipsec_tunnels[0].ip_sec_connection_tunnels[0].id
  
  routing = "STATIC"
  
  ike_version = "V2"
  
  display_name = "${var.resource_prefix}-tunnel-1"
  
  shared_secret = local.ipsec_shared_secret

  bgp_session_info {
    customer_interface_ip = "169.254.0.1/30"
    oracle_interface_ip   = "169.254.0.2/30"
  }
}