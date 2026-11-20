"""Verify a downloaded release against caller-supplied repository/commit/workflow pins."""
import argparse
import hashlib
import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path


def checked_hash(path, expected):
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"SHA256 mismatch for {path.name}")


def registry_manifest(reference):
    repository, digest = reference.removeprefix("ghcr.io/").split("@")
    url = "https://ghcr.io/token?" + urllib.parse.urlencode({"service": "ghcr.io", "scope": f"repository:{repository}:pull"})
    with urllib.request.urlopen(url, timeout=30) as response:
        token = json.load(response)["token"]
    request = urllib.request.Request(f"https://ghcr.io/v2/{repository}/manifests/{digest}", headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read()
    if "sha256:" + hashlib.sha256(body).hexdigest() != digest:
        raise ValueError("Registry manifest bytes do not match requested digest")
    return json.loads(body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--workflow-sha", required=True)
    args = parser.parse_args()
    for value in (args.commit, args.workflow_sha):
        if not re.fullmatch("[a-f0-9]{40}", value):
            raise ValueError("Commit and workflow SHA must be full immutable revisions")
    identity = "https://github.com/surya-8143/paved-road-platform/.github/workflows/build-scan-sign.yml@" + args.workflow_sha
    verify = ["--certificate-identity", identity, "--certificate-oidc-issuer", "https://token.actions.githubusercontent.com",
              "--certificate-github-workflow-repository", args.repository, "--certificate-github-workflow-sha", args.commit]
    root = args.directory
    subprocess.run(["cosign", "verify-blob", *verify, "--bundle", str(root / "release.sigstore.json"), str(root / "release.json")], check=True)
    release = json.loads((root / "release.json").read_text())
    if release["schema"] != 1 or release["commit"] != args.commit or release["signer"] != identity:
        raise ValueError("Unexpected release identity or schema")
    pattern = re.escape("ghcr.io/" + args.repository) + "@sha256:[a-f0-9]{64}"
    if not re.fullmatch(pattern, release["image"]):
        raise ValueError("Unexpected registry/repository/digest")
    checked_hash(root / "lambda/lambda.zip", release["lambda_sha256"])
    checked_hash(root / "lambda/sbom.cdx.json", release["lambda_sbom_sha256"])
    subprocess.run(["cosign", "verify-blob", *verify, "--bundle", str(root / "lambda/lambda.sigstore.json"), str(root / "lambda/lambda.zip")], check=True)
    subprocess.run(["cosign", "verify", *verify, release["image"]], check=True, stdout=subprocess.DEVNULL)
    children = set()
    for item in release["architectures"]:
        if not re.fullmatch(pattern, item["image"]) or item["commit"] != args.commit or item["identity"] != identity:
            raise ValueError("Invalid architecture release record")
        children.add((item["architecture"], item["image"].split("@")[1]))
        subprocess.run(["cosign", "verify", *verify, item["image"]], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["cosign", "verify-attestation", *verify, "--type", "cyclonedx", item["image"]], check=True, stdout=subprocess.DEVNULL)
    if {name for name, _ in children} != {"amd64", "arm64"} or len(children) != 2:
        raise ValueError("Release must contain exactly AMD64 and ARM64")
    index = registry_manifest(release["image"])
    actual = {(item["platform"]["architecture"], item["digest"]) for item in index["manifests"] if item["platform"]["os"] == "linux"}
    if actual != children or len(index["manifests"]) != 2:
        raise ValueError("Signed index does not match the scanned architecture records")
    print("PASS: release, Lambda ZIP/SBOM, image index, both architecture signatures and SBOM attestations")


if __name__ == "__main__":
    main()
