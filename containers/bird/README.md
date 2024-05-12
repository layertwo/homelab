# BIRD for PureLB

PureLB is a load-balancer orchestrator for Kubernetes clusters.
It uses standard Linux networking and routing protocols, and works with the operating system to announce service addresses.

This is a simple packaging of the open source routing software [BIRD](https://bird.network.cz) Version 2.0 (currently 2.0.9).

The included sample configuration bird-cm.yml imports the routing table entries created when PureLB adds allocated load-balancer addresses to kube-lb0.

## Documentation

The PureLB documentation describes use alongside PureLB.

https://purelb.gitlab.io/docs
