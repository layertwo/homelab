# Data source for availability domains
data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_ocid
}

# VCN (Virtual Cloud Network)
resource "oci_core_vcn" "vcn" {
  compartment_id = var.compartment_ocid
  cidr_blocks    = [var.vcn_cidr]
  display_name   = "${var.resource_prefix}-vcn"
  dns_label      = "layertwo"
  
  freeform_tags = var.tags
}

# Internet Gateway
resource "oci_core_internet_gateway" "igw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.vcn.id
  display_name   = "${var.resource_prefix}-igw"
  enabled        = true
  
  freeform_tags = var.tags
}

# Route Table for Public Subnet
resource "oci_core_route_table" "public_rt" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.vcn.id
  display_name   = "${var.resource_prefix}-public-rt"
  
  # Default route to Internet Gateway
  route_rules {
    network_entity_id = oci_core_internet_gateway.igw.id
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
  }
  
  # Route to home infrastructure network via DRG
  dynamic "route_rules" {
    for_each = var.enable_vpn ? [1] : []
    content {
      network_entity_id = oci_core_drg.drg[0].id
      destination       = var.home_infra_network_cidr
      destination_type  = "CIDR_BLOCK"
    }
  }
  
  # Route to home regular network via DRG
  dynamic "route_rules" {
    for_each = var.enable_vpn ? [1] : []
    content {
      network_entity_id = oci_core_drg.drg[0].id
      destination       = var.home_regular_network_cidr
      destination_type  = "CIDR_BLOCK"
    }
  }
  
  freeform_tags = var.tags
}

# Security List for Public Subnet
resource "oci_core_security_list" "public_sl" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.vcn.id
  display_name   = "${var.resource_prefix}-public-sl"
  
  # Egress Rules - Allow all outbound
  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
    stateless   = false
  }
  
  # Ingress Rules
  
  # SSH from home public IP
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "${var.home_public_ip}/32"
    stateless   = false
    description = "SSH from home public IP"
    
    tcp_options {
      min = 22
      max = 22
    }
  }
  
  # SSH from infrastructure network via VPN
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = var.home_infra_network_cidr
    stateless   = false
    description = "SSH from home infra network via VPN"
    
    tcp_options {
      min = 22
      max = 22
    }
  }
  
  # SSH from regular network via VPN
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = var.home_regular_network_cidr
    stateless   = false
    description = "SSH from home regular network via VPN"
    
    tcp_options {
      min = 22
      max = 22
    }
  }
  
  # Kubernetes API Server
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = var.home_infra_network_cidr
    stateless   = false
    description = "K8s API Server from home infra"
    
    tcp_options {
      min = 6443
      max = 6443
    }
  }
  
  # K3s server port
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = var.home_infra_network_cidr
    stateless   = false
    description = "K3s server port from home infra"
    
    tcp_options {
      min = 9443
      max = 9443
    }
  }
  
  # Kubelet API
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = var.home_infra_network_cidr
    stateless   = false
    description = "Kubelet API from home infra"
    
    tcp_options {
      min = 10250
      max = 10250
    }
  }
  
  # Allow all traffic from VCN (for inter-node communication)
  ingress_security_rules {
    protocol    = "all"
    source      = var.vcn_cidr
    stateless   = false
    description = "All traffic within VCN"
  }
  
  # Allow all traffic from infrastructure network
  ingress_security_rules {
    protocol    = "all"
    source      = var.home_infra_network_cidr
    stateless   = false
    description = "All traffic from home infra network"
  }
  
  # Allow all traffic from regular network
  ingress_security_rules {
    protocol    = "all"
    source      = var.home_regular_network_cidr
    stateless   = false
    description = "All traffic from home regular network"
  }
  
  # ICMP from infrastructure network
  ingress_security_rules {
    protocol    = "1" # ICMP
    source      = var.home_infra_network_cidr
    stateless   = false
    description = "ICMP from home infra network"
  }
  
  # ICMP from regular network
  ingress_security_rules {
    protocol    = "1" # ICMP
    source      = var.home_regular_network_cidr
    stateless   = false
    description = "ICMP from home regular network"
  }
  
  # ICMP within VCN
  ingress_security_rules {
    protocol    = "1" # ICMP
    source      = var.vcn_cidr
    stateless   = false
    description = "ICMP within VCN"
  }
  
  freeform_tags = var.tags
}

# Public Subnet
resource "oci_core_subnet" "public_subnet" {
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_vcn.vcn.id
  cidr_block        = var.public_subnet_cidr
  display_name      = "${var.resource_prefix}-public-subnet"
  dns_label         = "public"
  route_table_id    = oci_core_route_table.public_rt.id
  security_list_ids = [oci_core_security_list.public_sl.id]
  
  # Public subnet for Always Free instances
  prohibit_public_ip_on_vnic = false
  
  freeform_tags = var.tags
}
