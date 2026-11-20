"""Prepare pinned upstream images and a small, single-node controller profile."""
import copy
import json
import re
import subprocess
from pathlib import Path
import yaml

root = Path(__file__).resolve().parents[1]
assets = root / "build/kubernetes"
pins = json.loads((root / "kubernetes/image-pins.json").read_text())
values = yaml.safe_load((root / "kubernetes/kyverno-values.yaml").read_text())
defaults = yaml.safe_load(subprocess.check_output(["helm", "show", "values", str(assets / "kyverno-3.10.0.tgz")], text=True))


def set_value(path, value):
    target = values
    for key in path[:-1]:
        target = target.setdefault(key, {})
    target[path[-1]] = value


def find_images(value, path=()):
    if not isinstance(value, dict):
        return
    if "repository" in value and "tag" in value:
        registry = value.get("registry") or value.get("defaultRegistry") or "ghcr.io"
        reference = f"{registry}/{value['repository']}:{value['tag']}"
        if reference in pins:
            set_value((*path, "tag"), str(value["tag"]) + "@" + pins[reference].split("@")[1])
    for name, child in value.items():
        find_images(child, (*path, name))


find_images(defaults)
(assets / "kyverno-pinned-values.yaml").write_text(yaml.safe_dump(values, sort_keys=False))
rendered = subprocess.check_output(["helm", "template", "kyverno", str(assets / "kyverno-3.10.0.tgz"), "--namespace", "kyverno", "--include-crds", "-f", str(assets / "kyverno-pinned-values.yaml")], text=True)
pattern = r'(?m)^[ \t]*image:[ \t]*[\"\x27]?([^ \t\n\"\x27]+)[\"\x27]?[ \t]*$'
for reference in re.findall(pattern, rendered):
    if reference not in pins.values():
        raise ValueError("Unpinned rendered Kyverno image: " + reference)
(assets / "kyverno-pinned-rendered.yaml").write_text(rendered)

manifests = list(yaml.safe_load_all((assets / "argocd-install.yaml").read_text()))
for item in manifests:
    if not item or item.get("kind") not in {"Deployment", "StatefulSet"}:
        continue
    name = item["metadata"]["name"]
    if name in {"argocd-dex-server", "argocd-notifications-controller", "argocd-applicationset-controller"}:
        item["spec"]["replicas"] = 0
    pod = item["spec"]["template"]["spec"]
    for container in [*pod.get("containers", []), *pod.get("initContainers", [])]:
        reference = container["image"]
        if reference not in pins:
            raise ValueError("Unpinned Argo CD image: " + reference)
        container["image"] = pins[reference]
        container["resources"] = {"requests": {"cpu": "50m", "memory": "128Mi"}, "limits": {"cpu": "1", "memory": "1Gi" if name == "argocd-application-controller" else "512Mi"}}
(assets / "argocd-pinned.yaml").write_text(yaml.safe_dump_all(manifests, sort_keys=False))
print("Prepared all upstream images with immutable digests and bounded controller resources")
