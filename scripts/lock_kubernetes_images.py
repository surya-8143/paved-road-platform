"""Resolve explicit upstream versions once; setup subsequently uses checked-in digests."""
import json
import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
rendered = subprocess.check_output(["helm", "template", "kyverno", str(root / "build/kubernetes/kyverno-3.10.0.tgz"),
    "--namespace", "kyverno", "--include-crds", "-f", str(root / "kubernetes/kyverno-values.yaml")], text=True)
(root / "build/kubernetes/kyverno-rendered.yaml").write_text(rendered)
pattern = r'(?m)^\s*image:\s*[\"\x27]?([^\s\"\x27]+)[\"\x27]?\s*$'
images = set(re.findall(pattern, rendered + "\n" + (root / "build/kubernetes/argocd-install.yaml").read_text()))
pins = {}
for reference in sorted(images):
    digest = subprocess.check_output(["docker", "buildx", "imagetools", "inspect", reference, "--format", "{{.Manifest.Digest}}"], text=True).strip()
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ValueError("Unexpected digest for " + reference)
    pins[reference] = reference + "@" + digest
    print(reference, digest, flush=True)
(root / "kubernetes/image-pins.json").write_text(json.dumps(pins, indent=2, sort_keys=True) + "\n")
