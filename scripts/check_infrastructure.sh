#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export AWS_EC2_METADATA_DISABLED=true
export TF_IN_AUTOMATION=1
export TF_PLUGIN_CACHE_DIR="${TF_PLUGIN_CACHE_DIR:-$HOME/.cache/paved-road/tofu-plugins}"
mkdir -p "$TF_PLUGIN_CACHE_DIR"
mkdir -p build
python3 - <<'PY'
import zipfile
from pathlib import Path
path = Path('modules/serverless-service/tests/fixture.zip')
with zipfile.ZipFile(path, 'w') as archive:
    info = zipfile.ZipInfo('app/main.py', date_time=(2020,1,1,0,0,0))
    archive.writestr(info, '# Offline fixture only; never deploy this file.\n')
PY
tofu fmt -check -recursive modules examples bootstrap deploy
tofu -chdir=modules/serverless-service init -backend=false -input=false -lockfile=readonly
tofu -chdir=modules/serverless-service validate
tofu -chdir=modules/serverless-service test
tofu -chdir=examples/offline init -backend=false -input=false -lockfile=readonly
tofu -chdir=examples/offline validate
tofu -chdir=examples/offline plan -refresh=false -input=false -out=../../build/offline.tfplan
tofu -chdir=examples/offline show -json ../../build/offline.tfplan > build/offline-plan.json

tofu -chdir=bootstrap init -backend=false -input=false -lockfile=readonly
tofu -chdir=bootstrap validate
tofu -chdir=bootstrap test -json -verbose > build/bootstrap-tests.jsonl
python3 scripts/check_bootstrap.py build/bootstrap-tests.jsonl

tofu -chdir=deploy/service init -backend=false -input=false -lockfile=readonly
tofu -chdir=deploy/service validate
