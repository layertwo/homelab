#!/usr/bin/env python3
"""Render and check tunnels deployment boundaries. Requires kubectl, Helm and PyYAML."""

import argparse
import os
from pathlib import Path
import subprocess
import tomllib

import yaml

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "clusters/home/apps/network/tunnels"


def run(*args, input=None):
    return subprocess.check_output(args, input=input, text=True, cwd=ROOT)


def check(condition, message):
    if not condition:
        raise SystemExit("FAIL: " + message)


def resource(resources, kind, name):
    found = [r for r in resources if r["kind"] == kind and r["metadata"]["name"] == name]
    check(len(found) == 1, f"expected one {kind}/{name}, found {len(found)}")
    return found[0]


def matches(selector, labels):
    check(not selector.get("matchExpressions"), "checker supports matchLabels selectors only")
    return all(labels.get(k) == v for k, v in selector.get("matchLabels", {}).items())


def allowed(objects, target, peer, port, direction, protocol="TCP"):
    """Evaluate the label/port-only policies used here, including additive rules."""
    policies = [r["spec"] for r in objects if r["kind"] == "NetworkPolicy"
                and direction in r["spec"]["policyTypes"] and matches(r["spec"]["podSelector"], target)]
    if not policies:
        return True
    side = "from" if direction == "Ingress" else "to"
    for policy in policies:
        for rule in policy.get(direction.lower(), []):
            ports = rule.get("ports", [])
            if ports and not any(p["port"] == port and p.get("protocol", "TCP") == protocol for p in ports):
                continue
            if not rule.get(side):
                return True
            for entry in rule[side]:
                check(not entry.get("ipBlock"), "checker supports label-based peers only")
                namespace = entry.get("namespaceSelector", {"matchLabels": {"kubernetes.io/metadata.name": "tunnels"}})
                if matches(namespace, {"kubernetes.io/metadata.name": peer[0]}) and matches(entry.get("podSelector", {}), peer[1]):
                    return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=int, choices=(1, 2, 3), default=3)
    parser.add_argument("--chart", default=os.environ.get("TUNNELS_CHART", "bjw-s/app-template"))
    args = parser.parse_args()
    # Kubernetes distinguishes no rules (deny) from a rule with no peers (allow all).
    for rules, want in (([], False), ([{}], True), ([{"from": []}], True)):
        policy = {"kind": "NetworkPolicy", "spec": {
            "podSelector": {}, "policyTypes": ["Ingress"], "ingress": rules,
        }}
        check(allowed([policy], {}, ("tunnels", {}), 8080, "Ingress") == want,
              "NetworkPolicy checker mishandles empty rules/peers")
    objects = list(yaml.safe_load_all(run("kubectl", "kustomize", str(APP))))
    broker = resource(objects, "HelmRelease", "broker")
    frps = resource(objects, "HelmRelease", "frps")
    rendered = []
    for release in (broker, frps):
        spec = release["spec"]
        rendered.extend(r for r in yaml.safe_load_all(run(
            "helm", "template", release["metadata"]["name"], args.chart,
            "--version", spec["chart"]["spec"]["version"], "--namespace", "tunnels",
            "--values", "-", input=yaml.safe_dump(spec["values"]),
        )) if r)
    db = resource(objects, "Cluster", "cnpg-tunnels")
    check(not db["spec"].get("enableSuperuserAccess", False), "database must not expose superuser credentials")
    for name in ("broker", "frps"):
        deploy = resource(rendered, "Deployment", name)
        check(deploy["metadata"].get("annotations", {}).get("reloader.stakater.com/auto") == "true",
              f"{name} Deployment must reload on credential changes (pod annotations are insufficient)")
        pod = deploy["spec"]["template"]["spec"]
        security = pod["securityContext"]
        check(security.get("runAsNonRoot") and security.get("runAsUser") == 65532,
              f"{name} must run non-root as uid 65532")
        check(security.get("seccompProfile", {}).get("type") == "RuntimeDefault", f"{name} seccomp missing")
        check(pod.get("automountServiceAccountToken") is False, f"{name} must not mount API credentials")
        for container in pod["containers"]:
            context = container["securityContext"]
            check(context.get("readOnlyRootFilesystem") and context.get("allowPrivilegeEscalation") is False,
                  f"{name} container hardening missing")
            check(context.get("capabilities", {}).get("drop") == ["ALL"], f"{name} capabilities not dropped")
    pod = resource(rendered, "Deployment", "broker")["spec"]["template"]["spec"]
    container = pod["containers"][0]
    check(container["image"].startswith("ghcr.io/layertwo/tunnels-broker:v0.1.0@sha256:"),
          "broker release image must be pinned by digest")
    env = {e["name"]: e for e in container["env"]}
    check(env["CLI_CLIENT_ID"]["value"] == "dbf1099c-ebad-4c97-b1da-137372140feb", "wrong CLI client")
    check(env["DATABASE_URL"]["valueFrom"]["secretKeyRef"] == {"name": "cnpg-tunnels-app", "key": "uri"},
          "database credentials must come from CNPG's application secret")
    check(container["envFrom"] == [{"secretRef": {"name": "secrets-tunnels-broker"}}], "broker credentials missing")
    for probe in ("livenessProbe", "readinessProbe"):
        check(container[probe]["httpGet"]["path"] == "/healthz", f"broker {probe} must use /healthz")
    service = resource(rendered, "Service", "broker")
    check(service["spec"].get("type", "ClusterIP") == "ClusterIP", "broker must not expose a public service")
    check(any(p["name"] == "http" and p["port"] == 8080 for p in service["spec"]["ports"]), "broker HTTP port missing")
    secret = resource(objects, "Secret", "secrets-tunnels-broker")
    check(all(str(secret["stringData"][key]).startswith("ENC[AES256_GCM,")
              for key in ("PLUGIN_SECRET", "FRPS_DASHBOARD_PASSWORD")), "broker secrets must be SOPS encrypted")
    print("PASS: broker/database wiring, private service, image pin and workload hardening")

    if args.stage >= 2:
        deploy = resource(rendered, "Deployment", "frps")
        pod = deploy["spec"]["template"]["spec"]
        check(pod["containers"][0]["image"].startswith("ghcr.io/layertwo/tunnels-frps:v0.1.0@sha256:"),
              "frps release image must be pinned by digest")
        check(any(v.get("configMap", {}).get("name") == "frps-config" for v in pod["volumes"]),
              "frps must mount its readable TOML ConfigMap")
        env = {e["name"]: e for e in pod["containers"][0]["env"]}
        for key in ("PLUGIN_SECRET", "FRPS_DASHBOARD_PASSWORD"):
            check(env[key].get("valueFrom", {}).get("secretKeyRef") == {"name": "secrets-tunnels-broker", "key": key},
                  f"frps {key} must reference the shared credential Secret")
        template = resource(objects, "ConfigMap", "frps-config")["data"]["frps.toml"]
        # Substitute test credentials only; the native frps loader performs expansion at startup.
        config = tomllib.loads(template.replace("{{ .Envs.PLUGIN_SECRET }}", "test-plugin-secret")
                              .replace("{{ .Envs.FRPS_DASHBOARD_PASSWORD }}", "test-dashboard-password"))
        check(config["webServer"]["password"] == "test-dashboard-password", "dashboard must use its Secret-backed template")
        check(config["httpPlugins"][0]["path"] == "/plugin/test-plugin-secret", "plugin must use its Secret-backed template")
        check(set(config["auth"]["additionalScopes"]) == {"HeartBeats", "NewWorkConns"}, "missing auth scope")
        check(config["auth"]["oidc"]["issuer"] == "https://idp.layertwo.dev" and
              config["auth"]["oidc"]["audience"] == "https://tunnels.layertwo.dev", "wrong frps issuer/audience")
        check(config["transport"]["heartbeatTimeout"] == 90, "missing heartbeat revocation backstop")
        check(config["httpPlugins"][0]["addr"] == "http://broker:8080" and
              config["httpPlugins"][0]["ops"] == ["Login", "NewProxy", "CloseProxy"], "wrong plugin wiring")
        check(any(p["port"] == 7500 for p in resource(rendered, "Service", "frps")["spec"]["ports"]), "private dashboard port missing")
        broker_labels = resource(rendered, "Deployment", "broker")["spec"]["template"]["metadata"]["labels"]
        frps_labels = deploy["spec"]["template"]["metadata"]["labels"]
        db_labels = {"cnpg.io/cluster": "cnpg-tunnels"}
        peers = {
            "broker": ("tunnels", broker_labels), "frps": ("tunnels", frps_labels),
            "db": ("tunnels", db_labels), "unknown": ("tunnels", {"app": "unknown"}),
            "external": ("traefik-system", {"app.kubernetes.io/instance": "traefik-external-traefik-system"}),
            "internal": ("traefik-system", {"app.kubernetes.io/instance": "traefik-internal-traefik-system"}),
            "operator": ("default", {"app.kubernetes.io/name": "cloudnative-pg", "app.kubernetes.io/instance": "cloudnative-pg"}),
        }
        for target, source, port, want in (
            ("frps", "external", 7000, True), ("frps", "external", 8080, True),
            ("frps", "external", 7500, False), ("frps", "broker", 7500, True),
            ("frps", "unknown", 7000, False), ("frps", "internal", 7000, False),
            ("broker", "external", 8080, True), ("broker", "frps", 8080, True),
            ("broker", "unknown", 8080, False), ("broker", "internal", 8080, False),
            ("db", "broker", 5432, True), ("db", "unknown", 5432, False),
            ("db", "operator", 8000, True), ("db", "unknown", 8000, False),
        ):
            check(allowed(objects, peers[target][1], peers[source], port, "Ingress") == want,
                  f"unexpected ingress: {source} -> {target}:{port}")
        for source, target, port, want in (
            ("broker", "frps", 7500, True), ("broker", "db", 5432, True),
            ("broker", "unknown", 5432, False), ("broker", "unknown", 7500, False),
            ("frps", "broker", 8080, True), ("frps", "unknown", 8080, False),
            ("frps", "db", 5432, False),
        ):
            check(allowed(objects, peers[source][1], peers[target], port, "Egress") == want,
                  f"unexpected egress: {source} -> {target}:{port}")
        print("PASS: frps TOML/auth scopes, shared Secret environment and private dashboard; NetworkPolicy allow/deny matrix")

    if args.stage >= 3:
        apex = resource(objects, "IngressRoute", "tunnels-apex")["spec"]["routes"]
        check(len(apex) == 2, "apex must expose only control and the explicit broker endpoints")
        check(apex[0]["match"] == "Host(`tunnels.layertwo.dev`) && PathPrefix(`/~!frp`)", "native control route changed")
        check(apex[0]["services"] == [{"name": "frps", "port": "control"}], "control must go directly to frps")
        check(apex[1]["match"] == "Host(`tunnels.layertwo.dev`) && (Path(`/api/me`) || Path(`/.well-known/tunnels.json`) || Path(`/healthz`))",
              "broker route must not expose plugin, authz, dashboard or arbitrary paths")
        check(apex[1]["services"] == [{"name": "broker", "port": "http"}], "API must go to broker")
        for route in apex:
            check([m["name"] for m in route.get("middlewares", [])] == ["tunnels-ratelimit", "tunnels-inflight"],
                  "public API/control connection limits missing")
        sites = resource(objects, "IngressRoute", "tunnels-sites")["spec"]["routes"]
        check(len(sites) == 1 and sites[0]["services"] == [{"name": "frps", "port": "vhost"}], "visitor route changed")
        check([m["name"] for m in sites[0]["middlewares"]] == [
            "tunnels-strip-identity", "tunnels-oidc", "tunnels-authz", "tunnels-strip-internal",
            "tunnels-ratelimit", "tunnels-inflight",
        ], "sites must authenticate and authorize before reaching frps")
        identity = ["X-Tunnels-Sub", "X-Tunnels-User", "X-Tunnels-Groups"]
        strip = resource(objects, "Middleware", "tunnels-strip-identity")["spec"]["headers"]["customRequestHeaders"]
        check(strip == dict.fromkeys(identity + ["X-Tunnel-User"], ""), "client identity headers must be stripped before OIDC")
        strip = resource(objects, "Middleware", "tunnels-strip-internal")["spec"]["headers"]["customRequestHeaders"]
        check(strip == dict.fromkeys(identity, ""), "internal identity must not reach the tunneled app")
        authz = resource(objects, "Middleware", "tunnels-authz")["spec"]["forwardAuth"]
        check(authz["address"] == "http://broker:8080/authz" and authz.get("trustForwardHeader") is False,
              "authorization must derive host from Traefik, not trusted client forwarded headers")
        check(set(authz["authResponseHeaders"]) == {"X-Tunnels-Sub", "X-Tunnels-User", "X-Tunnel-User"},
              "forwardAuth must replace identity headers with broker response headers")
        oidc = resource(objects, "Middleware", "tunnels-oidc")["spec"]["plugin"]["oidc"]
        headers = {h["Name"]: h for h in oidc["Headers"]}
        check(headers["X-Tunnels-Sub"]["Value"] == "{{ .claims.sub }}" and
              headers["X-Tunnels-User"]["Value"] == "{{ .claims.preferred_username }}", "OIDC identity claims missing")
        check(headers["X-Tunnels-Groups"]["Values"] == "[]", "visitor groups must not be forwarded")
        check(oidc["Authorization"]["CheckOnEveryRequest"] is True and oidc["Provider"]["UsePkce"] is True,
              "OIDC group revalidation/PKCE missing")
        print("PASS: private endpoints excluded; site identity stripping and fail-closed authorization chain")


if __name__ == "__main__":
    main()
