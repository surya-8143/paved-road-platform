#!/usr/bin/env bash
set -euo pipefail
for tool in python3 git docker jq zip unzip pipx make; do
  command -v "$tool" >/dev/null || { printf 'Missing tool: %s\n' "$tool" >&2; exit 1; }
done
python3 - <<'PY'
import pathlib
import subprocess
import sys
import tempfile
import venv
assert sys.version_info[:2] == (3, 12), f'Expected Python 3.12; got {sys.version}'
print(f'Python {sys.version.split()[0]}')
with tempfile.TemporaryDirectory(prefix='paved-road-venv-check-') as directory:
    venv.EnvBuilder(with_pip=True).create(directory)
    subprocess.run([str(pathlib.Path(directory) / 'bin/python'), '-m', 'pip', '--version'], check=True)
print('Python virtual environment creation: PASS')
PY
test "$(docker info --format '{{.OSType}}')" = linux
docker version --format 'Docker client={{.Client.Version}} server={{.Server.Version}}'
git --version
jq --version
printf 'pipx: '
pipx --version
printf 'Base development environment: PASS\n'
printf 'This check does not validate AWS access, deployment or project-specific infrastructure tools.\n'
