"""Install only checksum-pinned Linux x86_64 tools; never extract arbitrary paths."""
import argparse
import hashlib
import io
import json
import os
import platform
import tarfile
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("tools", nargs="+")
parser.add_argument("--directory", type=Path, default=Path.home() / ".local/bin")
args = parser.parse_args()
architecture = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine())
if platform.system() != "Linux" or not architecture:
    raise SystemExit("Tool installer currently supports Linux amd64/arm64 runners only")
manifest = json.loads((Path(__file__).resolve().parents[1] / f"tools/linux-{architecture}.json").read_text())
args.directory.mkdir(parents=True, exist_ok=True)
for name in args.tools:
    entry = manifest[name]
    request = urllib.request.Request(entry["url"], headers={"User-Agent": "paved-road-installer"})
    with urllib.request.urlopen(request, timeout=120) as response:
        archive = response.read()
    if hashlib.sha256(archive).hexdigest() != entry["sha256"]:
        raise SystemExit(f"SHA256 verification failed for {name}")
    if entry["member"]:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            member = tar.getmember(entry["member"])
            if not member.isfile():
                raise SystemExit(f"Unexpected archive member for {name}")
            data = tar.extractfile(member).read()
    else:
        data = archive
    target = args.directory / name
    temporary = target.with_suffix(".installing")
    temporary.write_bytes(data)
    temporary.chmod(0o755)
    os.replace(temporary, target)
    print(f"Installed {name} {entry['version']} (SHA256 verified)", flush=True)
