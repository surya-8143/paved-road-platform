"""Credential-process adapter. Its stdout is consumed ONLY by the SDK/OpenTofu.

Do not run this directly in a terminal: successful output contains temporary secrets.
The Windows CLI owns login/cache refresh. This adapter never writes credentials to disk.
"""
import argparse
import json
import os
import subprocess
import sys
from cloud_contract import validate_process_credentials


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--region", required=True)
    args = parser.parse_args()
    env = {k:v for k,v in os.environ.items() if not k.startswith(("AWS_", "TF_", "TOFU_"))}
    result = subprocess.run([args.cli,"configure","export-credentials","--profile",args.profile,"--region",args.region,"--format","process"],
                            env=env,capture_output=True,text=True,timeout=60)
    if result.returncode:
        raise ValueError("AWS CLI could not refresh the session; run aws login in PowerShell")
    credentials = validate_process_credentials(result.stdout)
    # Standard credential_process protocol, captured by the calling SDK/provider.
    sys.stdout.write(json.dumps(credentials))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("Temporary credential refresh failed; run aws login for the personal profile.",file=sys.stderr)
        sys.exit(1)
