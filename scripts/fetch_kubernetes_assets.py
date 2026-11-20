"""Fetch pinned Kubernetes manifests/charts and verify their SHA-256 before use."""
import hashlib
import json
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
assets = json.loads((root / "kubernetes/assets.json").read_text())
directory = root / "build/kubernetes"
directory.mkdir(parents=True, exist_ok=True)
for name, entry in assets.items():
    if Path(name).name != name:
        raise ValueError("Asset filename must not contain a directory")
    target = directory / name
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == entry["sha256"]:
        print("Verified cached", name, flush=True)
        continue
    with urllib.request.urlopen(entry["url"], timeout=120) as response:
        body = response.read()
    if hashlib.sha256(body).hexdigest() != entry["sha256"]:
        raise ValueError("Asset SHA256 mismatch: " + name)
    target.write_bytes(body)
    print("Downloaded and verified", name, flush=True)
