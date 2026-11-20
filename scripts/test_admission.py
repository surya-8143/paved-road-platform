"""Exercise real admission webhooks with server dry runs; never run unsafe pods."""
import argparse
import copy
import datetime
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--release", required=True, type=Path)
parser.add_argument("--fixtures", required=True, type=Path)
parser.add_argument("--output", type=Path, default=Path("build/admission-evidence.json"))
args = parser.parse_args()
release = json.loads(args.release.read_text())
fixtures = {name: json.loads((args.fixtures / (name + ".json")).read_text())["image"] for name in ("unsigned", "wrong-signer")}
kubectl = ["kubectl", "--kubeconfig", str(Path.home() / ".kube/paved-road.yaml"), "--context", "kind-paved-road"]
image = release["image"]
container = {"name": "app", "image": image, "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "500m", "memory": "256Mi"}},
    "securityContext": {"allowPrivilegeEscalation": False, "readOnlyRootFilesystem": True, "capabilities": {"drop": ["ALL"]}}}
base = {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "admission-check", "namespace": "paved-road-demo"}, "spec": {
    "automountServiceAccountToken": False, "restartPolicy": "Never", "securityContext": {"runAsNonRoot": True, "runAsUser": 10001, "runAsGroup": 10001, "seccompProfile": {"type": "RuntimeDefault"}}, "containers": [container]}}
results = []


def check(name, pod, allowed, reasons=()):
    pod["metadata"]["name"] = "check-" + name
    result = subprocess.run([*kubectl, "create", "--dry-run=server", "-f", "-", "-o", "json"], input=json.dumps(pod), capture_output=True, text=True, timeout=65)
    output = result.stderr + result.stdout
    passed = (result.returncode == 0) if allowed else (result.returncode != 0 and any(reason in output for reason in reasons))
    results.append({"case": name, "expected": "allow" if allowed else "deny", "passed": passed,
                    "returncode": result.returncode, "response": output[:12000]})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "image": image, "source_commit": release["commit"], "results": results}, indent=2) + "\n")
    print(("PASS" if passed else "FAIL") + ": " + name, flush=True)
    if not passed:
        raise RuntimeError(output)


check("trusted-signed", copy.deepcopy(base), True)
for scenario in ("unsigned", "wrong-signer"):
    pod = copy.deepcopy(base)
    pod["spec"]["containers"][0]["image"] = fixtures[scenario]
    check(scenario, pod, False, ("paved-road-trusted-builds",))
pod = copy.deepcopy(base)
pod["spec"]["containers"][0]["image"] = image.split("@")[0] + ":latest"
check("mutable-tag", pod, False, ("paved-road-runtime", "paved-road-trusted-builds"))
pod = copy.deepcopy(base)
pod["spec"]["containers"][0]["image"] = "docker.io/library/busybox@sha256:" + "a" * 64
check("outside-registry", pod, False, ("paved-road-runtime", "paved-road-trusted-builds"))
pod = copy.deepcopy(base)
pod["spec"]["securityContext"]["runAsUser"] = 0
check("root-user", pod, False, ("violates PodSecurity",))
pod = copy.deepcopy(base)
pod["spec"]["hostNetwork"] = True
check("host-network", pod, False, ("violates PodSecurity",))
pod = copy.deepcopy(base)
pod["spec"]["containers"][0]["securityContext"]["allowPrivilegeEscalation"] = True
check("privilege-escalation", pod, False, ("violates PodSecurity", "paved-road-runtime"))
pod = copy.deepcopy(base)
pod["spec"]["containers"][0]["securityContext"]["readOnlyRootFilesystem"] = False
check("writable-rootfs", pod, False, ("paved-road-runtime",))
pod = copy.deepcopy(base)
pod["spec"]["automountServiceAccountToken"] = True
check("service-account-token", pod, False, ("paved-road-runtime",))
pod = copy.deepcopy(base)
pod["spec"]["containers"][0]["resources"]["limits"]["cpu"] = "0"
pod["spec"]["containers"][0]["resources"]["requests"]["cpu"] = "0"
check("unbounded-cpu", pod, False, ("paved-road-runtime",))
pod = copy.deepcopy(base)
init = copy.deepcopy(container)
init.update(name="init", command=["python", "-c", "pass"])
pod["spec"]["initContainers"] = [init]
check("trusted-init", copy.deepcopy(pod), True)
pod["spec"]["initContainers"][0]["image"] = fixtures["unsigned"]
check("unsigned-init", pod, False, ("paved-road-trusted-builds",))
pod = copy.deepcopy(base)
init = copy.deepcopy(container)
init.update(name="init", command=["python", "-c", "pass"])
init["securityContext"]["readOnlyRootFilesystem"] = False
pod["spec"]["initContainers"] = [init]
check("unsafe-init", pod, False, ("paved-road-runtime",))
check("trusted-still-allowed", copy.deepcopy(base), True)
print(f"Admission tests: {len(results)} passed", flush=True)
