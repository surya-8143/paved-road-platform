"""Measured recovery drills, restricted to the named disposable local kind cluster."""
import argparse
import copy
import datetime
import json
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=Path("build/recovery-evidence.json"))
args = parser.parse_args()
k = ["kubectl", "--kubeconfig", str(Path.home() / ".kube/paved-road.yaml"), "--context", "kind-paved-road"]
evidence = {"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "checks": []}


def run(*arguments, payload=None, check=True, timeout=90):
    result = subprocess.run([*k, *arguments], input=json.dumps(payload) if payload is not None else None,
                            capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(result.stderr)
    return result


def get(kind, name=None, namespace="paved-road-demo"):
    arguments = ["get", kind]
    if name:
        arguments.append(name)
    return json.loads(run(*arguments, "-n", namespace, "-o", "json").stdout)


def record(case, **fields):
    evidence["checks"].append({"case": case, "passed": True, **fields})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    print("PASS: " + case, flush=True)


def wait_for(predicate, seconds=180):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(2)
    raise TimeoutError("Condition was not met within " + str(seconds) + " seconds")


node = get("node", "paved-road-control-plane", "default")
if node["metadata"].get("labels", {}).get("kubernetes.io/hostname") != "paved-road-control-plane":
    raise RuntimeError("Unexpected target node")
evidence["node_uid"] = node["metadata"]["uid"]
app = get("application", "paved-road-demo", "argocd")
if (app.get("status", {}).get("sync", {}).get("status"), app.get("status", {}).get("health", {}).get("status")) != ("Synced", "Healthy"):
    raise RuntimeError("Start with a Synced/Healthy application")
deployment = get("deployment", "demo")
if deployment["spec"]["replicas"] != 1:
    raise RuntimeError("Expected Git's one-replica deployment")
evidence["git_revision"] = app["status"]["sync"]["revision"]
evidence["image"] = deployment["spec"]["template"]["spec"]["containers"][0]["image"]
pod = next(p for p in get("pods")["items"] if p["metadata"].get("labels", {}).get("app") == "paved-road-demo" and p["status"].get("phase") == "Running")

# Actual subresource UPDATE with dryRun=All; no debug container is persisted.
debug = copy.deepcopy(pod)
debug["spec"]["ephemeralContainers"] = [{"name": "debug-check", "image": evidence["image"],
    "command": ["python", "-c", "pass"], "targetContainerName": "app",
    "securityContext": {"runAsNonRoot": True, "runAsUser": 10001, "allowPrivilegeEscalation": False,
                        "readOnlyRootFilesystem": True, "capabilities": {"drop": ["ALL"]}, "seccompProfile": {"type": "RuntimeDefault"}}}]
response = run("replace", "--raw", "/api/v1/namespaces/paved-road-demo/pods/" + pod["metadata"]["name"] + "/ephemeralcontainers?dryRun=All", "-f", "-", payload=debug, check=False)
if response.returncode == 0 or "Ephemeral debug containers are disabled" not in response.stderr:
    raise RuntimeError("Ephemeral subresource was not rejected by the expected policy: " + response.stderr)
record("ephemeral-subresource-denied", response=response.stderr)

# Capture the API's accepted change, then let Argo repair it without a manual sync.
started = time.monotonic()
patched = json.loads(run("patch", "deployment", "demo", "-n", "paved-road-demo", "--type=merge", "-p", '{"spec":{"replicas":2}}', "-o", "json").stdout)
if patched["spec"]["replicas"] != 2:
    raise RuntimeError("Drift was never introduced")
try:
    wait_for(lambda: get("deployment", "demo")["spec"]["replicas"] == 1)
    restored = get("deployment", "demo")
    repaired_seconds = round(time.monotonic() - started, 3)
    wait_for(lambda: get("application", "paved-road-demo", "argocd")["status"]["sync"]["status"] == "Synced")
    record("argocd-self-heal", introduced_replicas=patched["spec"]["replicas"], restored_replicas=restored["spec"]["replicas"], seconds=repaired_seconds,
           introduced_resource_version=patched["metadata"]["resourceVersion"], restored_resource_version=restored["metadata"]["resourceVersion"])
finally:
    if get("deployment", "demo")["spec"]["replicas"] != 1:
        run("scale", "deployment/demo", "-n", "paved-road-demo", "--replicas=1")

# Native admission prevents the graceful scale-to-zero path that removes webhooks.
for case, command in (
    ("scale-to-zero-denied", ["scale", "deployment/kyverno-admission-controller", "-n", "kyverno", "--replicas=0", "--dry-run=server"]),
    ("controller-deletion-denied", ["delete", "deployment/kyverno-admission-controller", "-n", "kyverno", "--dry-run=server"]),
):
    response = run(*command, check=False)
    if response.returncode == 0 or "Keep at least one Kyverno admission replica" not in response.stderr:
        raise RuntimeError("Native availability guard did not reject request: " + response.stderr)
    record(case, response=response.stderr)

# Make the controller temporarily unschedulable with desired replicas still one.
# Recreate shuts down the old pod; unlike a service-selector change, this also
# closes established API-server keepalive connections. Webhooks must remain.
controller = get("deployment", "kyverno-admission-controller", "kyverno")
original_template = copy.deepcopy(controller["spec"]["template"])
original_strategy = copy.deepcopy(controller["spec"]["strategy"])
webhook_uid = get("validatingwebhookconfiguration", "kyverno-resource-validating-webhook-cfg", "default")["metadata"]["uid"]
spec = copy.deepcopy(deployment["spec"]["template"]["spec"])
probe = {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "webhook-outage-check", "namespace": "paved-road-demo"}, "spec": spec}
def set_controller(template, strategy):
    run("patch", "deployment/kyverno-admission-controller", "-n", "kyverno", "--type=json", "-p", json.dumps([
        {"op": "replace", "path": "/spec/template", "value": template},
        {"op": "replace", "path": "/spec/strategy", "value": strategy}]))
def unavailable():
    selector = ",".join(key + "=" + value for key, value in controller["spec"]["selector"]["matchLabels"].items())
    pods = json.loads(run("get", "pods", "-n", "kyverno", "-l", selector, "-o", "json").stdout)
    return bool(pods["items"]) and all(p["status"].get("phase") == "Pending" for p in pods["items"])
try:
    unavailable_template = copy.deepcopy(original_template)
    unavailable_template["spec"].setdefault("nodeSelector", {})["paved-road/outage-drill"] = "no-matching-node"
    set_controller(unavailable_template, {"type": "Recreate"})
    wait_for(unavailable, 120)
    if get("validatingwebhookconfiguration", "kyverno-resource-validating-webhook-cfg", "default")["metadata"]["uid"] != webhook_uid:
        raise RuntimeError("Registered webhooks changed during outage")
    response = run("create", "--dry-run=server", "-f", "-", payload=probe, check=False)
    if response.returncode == 0 or "failed calling webhook" not in response.stderr or "kyverno" not in response.stderr:
        raise RuntimeError("Admission did not fail closed as expected: " + response.stderr)
    record("webhook-outage-fails-closed", response=response.stderr, webhook_uid=webhook_uid)
finally:
    set_controller(original_template, original_strategy)
    run("rollout", "status", "deployment/kyverno-admission-controller", "-n", "kyverno", "--timeout=180s", timeout=190)
# Deployment availability can precede service routing convergence. Retry only
# transport failures for a bounded period; policy denials still fail immediately.
recovery_attempts = []
def admission_restored():
    result = run("create", "--dry-run=server", "-f", "-", payload=probe, check=False)
    if result.returncode == 0:
        return True
    transport_failure = "failed calling webhook" in result.stderr and any(
        reason in result.stderr for reason in ("connect: connection refused", "no endpoints available", "i/o timeout", "context deadline exceeded"))
    if not transport_failure:
        raise RuntimeError(result.stderr)
    recovery_attempts.append(result.stderr)
    return False
wait_for(admission_restored, 120)
record("webhook-restored-allows-trusted-pod", replicas=controller["spec"]["replicas"], transient_transport_failures=recovery_attempts)

# Loopback-only access, no externally exposed Service or ingress.
with socket.socket() as listener:
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
log_path = args.output.with_suffix(".port-forward.log")
with log_path.open("w") as log:
    forward = subprocess.Popen([*k, "port-forward", "-n", "paved-road-demo", "service/demo", str(port) + ":8080", "--address=127.0.0.1"], stdout=log, stderr=log)
    try:
        def request(path, method="GET"):
            req = urllib.request.Request(f"http://127.0.0.1:{port}" + path, method=method)
            with urllib.request.urlopen(req, timeout=5) as response:
                return json.load(response)
        def ready():
            if forward.poll() is not None:
                raise RuntimeError("Port forward exited: " + log_path.read_text())
            try:
                return request("/healthz")["status"] == "ok"
            except (OSError, TimeoutError):
                return False
        wait_for(ready, 30)
        greeting = request("/hello/Surya")
        first = request("/hits", "POST")["hits"]
        second = request("/hits", "POST")["hits"]
        if greeting != {"message": "Hello, Surya!"} or second != first + 1:
            raise RuntimeError("Unexpected service response")
        record("service-http-smoke", health=request("/healthz"), greeting=greeting, first_hits=first, second_hits=second)
    finally:
        forward.terminate()
        try:
            forward.wait(timeout=10)
        except subprocess.TimeoutExpired:
            forward.kill()
            forward.wait()
print("Recovery checks: " + str(len(evidence["checks"])) + " passed", flush=True)
