"""Fail closed on scanner errors or HIGH/CRITICAL findings; retain JSON and SBOM."""
import argparse
import hashlib
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


def extract_package(source, target):
    with zipfile.ZipFile(source) as archive:
        for info in archive.infolist():
            name = PurePosixPath(info.filename)
            if name.is_absolute() or ".." in name.parts or "\\" in info.filename:
                raise ValueError(f"Unsafe ZIP path: {info.filename}")
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("ZIP symlinks are not permitted")
        archive.extractall(target)


def scan(mode, target, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    common = ["trivy", mode, "--config", str(Path(__file__).resolve().parents[1] / "tools/trivy.yaml"),
              "--ignorefile", "/dev/null", "--scanners", "vuln", "--timeout", "10m", "--quiet"]
    if mode == "image":
        common += ["--image-src", "docker"]
    result = subprocess.run(common + ["--format", "json", "--severity", "HIGH,CRITICAL",
                            "--exit-code", "1", "--output", str(output / "scan.json"), str(target)])
    if result.returncode not in (0, 1) or not (output / "scan.json").is_file():
        raise RuntimeError("Scanner failed; no release is permitted")
    report = json.loads((output / "scan.json").read_text())
    # An empty successful report must not silently authorize an unrecognized artifact.
    packages = sum(len(item.get("Packages", [])) for item in report.get("Results", []))
    if not packages:
        raise RuntimeError("Scanner did not inventory any packages")
    subprocess.run(common + ["--skip-db-update", "--format", "cyclonedx", "--output",
                            str(output / "sbom.cdx.json"), str(target)], check=True)
    metadata = subprocess.check_output(["trivy", "version", "--format", "json"], text=True)
    (output / "scanner.json").write_text(metadata)
    findings = [finding for item in report.get("Results", []) for finding in item.get("Vulnerabilities", [])]
    print(f"Inventoried {packages} packages; {len(findings)} HIGH/CRITICAL findings", flush=True)
    if result.returncode or findings:
        raise RuntimeError("Vulnerability gate failed; see scan.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["image", "lambda", "fs"])
    parser.add_argument("target")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.kind == "lambda":
        with tempfile.TemporaryDirectory(prefix="paved-road-scan-") as temporary:
            extract_package(args.target, temporary)
            scan("fs", temporary, args.output)
        digest = hashlib.sha256(Path(args.target).read_bytes()).hexdigest()
        (args.output / "lambda.sha256").write_text(digest + "  lambda.zip\n")
    else:
        scan(args.kind, args.target, args.output)


if __name__ == "__main__":
    main()
