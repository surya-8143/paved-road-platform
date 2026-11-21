"""Read-only AWS lab diagnostic. Never creates resources or grants access."""
import argparse
import datetime
import json
import os
import re
import subprocess
from pathlib import Path


class AwsReadError(RuntimeError):
    pass


def aws_json(profile, region, *arguments):
    result = subprocess.run(["aws", "--profile", profile, "--region", region,
                             "--no-cli-pager", "--output", "json", *arguments],
                            env={**os.environ, "AWS_PAGER": "", "AWS_EC2_METADATA_DISABLED": "true"},
                            text=True, capture_output=True, timeout=60)
    if result.returncode:
        # Do not print environment variables, credential files or raw SDK debug logs.
        code = re.search(r"An error occurred \(([^)]+)\)", result.stderr)
        raise AwsReadError(code.group(1) if code else "CLI authentication/configuration/request failed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise AwsReadError("CLI returned invalid JSON") from error


def collect(profile, region, account_id, reader=aws_json):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", profile):
        raise ValueError("Use a simple named AWS profile")
    if region not in {"us-east-1", "us-west-2"}:
        raise ValueError("This Learner Lab diagnostic is limited to us-east-1/us-west-2")
    if not re.fullmatch(r"[0-9]{12}", account_id):
        raise ValueError("Expected account ID must be exactly 12 digits")
    identity = reader(profile, region, "sts", "get-caller-identity")
    if identity.get("Account") != account_id:
        raise ValueError("Profile resolves to a different AWS account; stopping before other API calls")
    report = {"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "region": region,
              "account_id": account_id, "identity_arn": identity.get("Arn"), "checks": {},
              "oidc_creation_permission": "NOT_VERIFIED", "full_pipeline_ready": False,
              "note": "Successful read APIs do not prove IAM mutation permissions, deployment access or remaining lab budget."}
    for name, arguments in {
        "lab_role": ("iam", "get-role", "--role-name", "LabRole"),
        "oidc_providers": ("iam", "list-open-id-connect-providers"),
        "lambda_quotas": ("lambda", "get-account-settings"),
        "regional_tables": ("dynamodb", "list-tables"),
    }.items():
        try:
            data = reader(profile, region, *arguments)
            if name == "lab_role":
                role = data["Role"]
                data = {"arn": role["Arn"], "permissions_boundary": role.get("PermissionsBoundary"),
                        "trust_policy": role.get("AssumeRolePolicyDocument")}
            report["checks"][name] = {"status": "READ_SUCCEEDED", "data": data}
        except (AwsReadError, KeyError, subprocess.TimeoutExpired) as error:
            report["checks"][name] = {"status": "UNVERIFIED", "error": str(error)}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--account-id", required=True, help="Expected Learner Lab account, not a personal account")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--output", type=Path, default=Path(".local/aws-lab-diagnostic.json"))
    args = parser.parse_args()
    try:
        report = collect(args.profile, args.region, args.account_id)
    except (ValueError, AwsReadError, subprocess.TimeoutExpired, FileNotFoundError) as error:
        raise SystemExit("Diagnostic stopped: " + str(error)) from error
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    for name, result in report["checks"].items():
        print(name + ": " + result["status"])
    print("OIDC creation permission: NOT VERIFIED. No resources were created.")
    print("Private diagnostic saved to", args.output)
    if any(item["status"] == "UNVERIFIED" for item in report["checks"].values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
