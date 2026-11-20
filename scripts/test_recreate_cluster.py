"""Recreate only this project's disposable kind cluster and rerun real checks."""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--release", type=Path, required=True)
parser.add_argument("--fixtures", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
os.chdir(root)
os.environ["KUBECONFIG"] = str(Path.home() / ".kube/paved-road.yaml")
os.environ["PATH"] = str(Path.home() / ".local/bin") + ":" + os.environ["PATH"]


def command(*argv):
    return subprocess.check_output(argv, text=True).strip()


def containers():
    ids = command("docker", "ps", "-aq").splitlines()
    return json.loads(command("docker", "inspect", *ids)) if ids else []


before = containers()
owned = [c for c in before if c["Config"].get("Labels", {}).get("io.x-k8s.kind.cluster") == "paved-road"]
if len(owned) != 1 or owned[0]["Name"] != "/paved-road-control-plane":
    raise SystemExit("Expected exactly the project's single control-plane container")
expected_image = "kindest/node:v1.35.8@sha256:07b2536e30b803ed61d1677a79df6115f798ce64c80f9e22f6ed45afd09323c0"
if owned[0]["Config"]["Image"] != expected_image:
    raise SystemExit("Existing cluster node does not match the project's pinned image")
other = {c["Id"]: c["State"]["Running"] for c in before if c not in owned}
k = ["kubectl", "--context", "kind-paved-road"]
old_node = json.loads(command(*k, "get", "node", "paved-road-control-plane", "-o", "json"))
evidence = {"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "platform_commit": command("git", "rev-parse", "HEAD"), "old_node_uid": old_node["metadata"]["uid"],
            "other_container_count": len(other), "passed": False}
if command("git", "status", "--porcelain"):
    raise SystemExit("Use a clean committed checkout for the reproduction drill")
started = time.monotonic()
try:
    subprocess.run(["kind", "delete", "cluster", "--name", "paved-road"], check=True)
    subprocess.run(["bash", "scripts/setup_kubernetes.sh"], check=True)
    evidence["rebuild_seconds"] = round(time.monotonic() - started, 3)
    new_node = json.loads(command(*k, "get", "node", "paved-road-control-plane", "-o", "json"))
    evidence["new_node_uid"] = new_node["metadata"]["uid"]
    if evidence["old_node_uid"] == evidence["new_node_uid"]:
        raise RuntimeError("Node identity did not change")
    subprocess.run(["python3", "scripts/test_admission.py", "--release", str(args.release.resolve()), "--fixtures", str(args.fixtures.resolve())], check=True)
    subprocess.run(["python3", "scripts/test_kubernetes_recovery.py"], check=True)
    after = {c["Id"]: c["State"]["Running"] for c in containers()}
    if any(after.get(identity) != running for identity, running in other.items()):
        raise RuntimeError("An unrelated container's existence/running state changed")
    evidence["other_containers_preserved"] = True
    evidence["checks_sha256"] = {name: hashlib.sha256((root / "build" / name).read_bytes()).hexdigest()
        for name in ("admission-evidence.json", "recovery-evidence.json")}
    evidence["passed"] = True
finally:
    (root / "build").mkdir(exist_ok=True)
    (root / "build/recreation-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
print("PASS: cluster recreation from a clean checkout", flush=True)
