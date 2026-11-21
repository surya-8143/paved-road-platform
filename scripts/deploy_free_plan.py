"""Serial local deployment for a managed personal Free Plan. No federation or account upgrade.

Temporary credentials use an automatically refreshed local credential process. Bootstrap state, plans and cloud evidence stay in
~/.local/state/paved-road/<account>/<region> (0700). This trusted-operator tool is not
an IAM enforcement boundary. Every apply uses a reviewed, hashed, recent saved plan.
"""
import argparse
import base64
import fcntl
import hashlib
import json
import os
import shutil
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from cloud_contract import isolated_environment, require_free_plan, sha256, validate_saved_plan, validate_plan_package
from check_plan import offline_envelope

ROOT = Path(__file__).resolve().parents[1]


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, default=lambda x: x.isoformat()) + "\n")


def run(command, cwd=None, capture=False, env=None):
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=capture, check=True)
    return result.stdout if capture else None


def source_files():
    paths = list((ROOT / "bootstrap").glob("*.tf")) + list((ROOT / "deploy/service").glob("*.tf"))
    paths += list((ROOT / "modules/serverless-service").glob("*.tf"))
    paths += list((ROOT / "policy").glob("*"))
    paths += [ROOT / "bootstrap/.terraform.lock.hcl", ROOT / "deploy/service/.terraform.lock.hcl",
              ROOT / "deploy/releases.json", ROOT / "scripts/check_plan.py", ROOT / "scripts/cloud_contract.py",
              ROOT / "scripts/deploy_free_plan.py", ROOT / "scripts/verify_release.py", ROOT / "scripts/export_cli_credentials.py"]
    return sorted(p for p in paths if p.is_file())


def source_digest():
    h = hashlib.sha256()
    for path in source_files():
        h.update(str(path.relative_to(ROOT)).encode()+b"\0"+path.read_bytes().replace(b"\r\n",b"\n")+b"\0")
    return h.hexdigest()


def sync_config(destination, source):
    destination.mkdir(parents=True, exist_ok=True)
    current = {p.name for p in source.glob("*.tf")}
    if {p.name for p in destination.glob("*.tf")} - current:
        raise ValueError("Unexpected private configuration file; inspect it before continuing")
    for path in source.glob("*.tf"):
        (destination/path.name).write_bytes(path.read_bytes().replace(b"\r\n",b"\n"))
    lock = source / ".terraform.lock.hcl"
    if lock.exists():
        shutil.copyfile(lock, destination/lock.name)


def resources(module):
    yield from module.get("resources", [])
    for child in module.get("child_modules", []):
        yield from resources(child)


def own_names(plan, service):
    allowed = {"aws_lambda_function": {f"paved-{service}"}, "aws_dynamodb_table": {f"paved-{service}"},
               "aws_cloudwatch_metric_alarm": {f"paved-{service}-errors", f"paved-{service}-throttles"}}
    result = {kind: set() for kind in allowed}
    prior = plan.get("prior_state", {}).get("values", {}).get("root_module", {})
    for resource in resources(prior):
        kind = resource["type"]
        if kind in result:
            name = resource["values"]["id"]
            if name not in allowed[kind]:
                raise ValueError("State contains a foreign resource; refusing to exclude it from usage")
            result[kind].add(name)
    return result


def inventory(session, account, region, plan, service):
    excluded = own_names(plan, service)
    lamb = session.client("lambda")
    functions = [f for page in lamb.get_paginator("list_functions").paginate() for f in page["Functions"]]
    settings = lamb.get_account_settings()
    if settings["AccountLimit"]["UnreservedConcurrentExecutions"] < 102:
        raise ValueError("Insufficient Lambda concurrency headroom above the unreserved minimum")
    dynamo = session.client("dynamodb")
    tables = []
    for page in dynamo.get_paginator("list_tables").paginate():
        for name in page["TableNames"]:
            table = dynamo.describe_table(TableName=name)["Table"]
            if table["TableStatus"] != "ACTIVE" or table.get("BillingModeSummary", {}).get("BillingMode", "PROVISIONED") != "PROVISIONED":
                raise ValueError("Inventory cannot bound a non-active or on-demand table")
            if table.get("Replicas"):
                raise ValueError("Regional guard cannot bound global-table usage")
            capacities = [table["ProvisionedThroughput"]] + [g["ProvisionedThroughput"] for g in table.get("GlobalSecondaryIndexes", [])]
            tables.append({"name": name, "read": sum(c["ReadCapacityUnits"] for c in capacities),
                           "write": sum(c["WriteCapacityUnits"] for c in capacities)})
    alarms = [a for page in session.client("cloudwatch").get_paginator("describe_alarms").paginate(AlarmTypes=["MetricAlarm", "CompositeAlarm"])
              for key in ("MetricAlarms", "CompositeAlarms") for a in page.get(key, [])]
    other_tables = [t for t in tables if t["name"] not in excluded["aws_dynamodb_table"]]
    return {"mode": "online", "account_id": account, "region": region, "inventory_timestamp": timestamp(),
            "other_usage": {"functions": sum(f["FunctionName"] not in excluded["aws_lambda_function"] for f in functions),
                            "read_capacity": sum(t["read"] for t in other_tables), "write_capacity": sum(t["write"] for t in other_tables),
                            "alarms": sum(a["AlarmName"] not in excluded["aws_cloudwatch_metric_alarm"] for a in alarms)},
            "observed": {"functions": [f["FunctionName"] for f in functions], "tables": tables,
                         "alarms": [a["AlarmName"] for a in alarms], "lambda_limits": settings["AccountLimit"]}}


def policy_check(plan, context, work, account, region, service):
    if plan["variables"]["account_id"]["value"] != account or plan["variables"]["region"]["value"] != region:
        raise ValueError("Plan account/region mismatch")
    # Reuse the same fingerprinted, narrowly-scoped GSI resolution; replace its
    # offline context with a fresh, successfully collected online inventory.
    envelope = offline_envelope(plan, ROOT)
    envelope["context"].update(context)
    for resource in resources(envelope["plan"]["planned_values"].get("root_module", {})):
        values = resource["values"]
        if resource["type"] == "aws_lambda_function":
            if values["role"] != f"arn:aws:iam::{account}:role/paved-road/{service}-runtime":
                raise ValueError("Runtime role belongs to the wrong account or service")
        if resource["type"] == "aws_lambda_function_url" and values["authorization_type"] != "AWS_IAM":
            raise ValueError("Free Plan profile requires authenticated URLs")
    write_json(work/"envelope.json", envelope)
    run(["conftest", "test", str(work/"envelope.json"), "--policy", str(ROOT/"policy"), "--data", str(ROOT/"policy/guardrails.json")])


def verify_release(directory, service):
    config = json.loads((ROOT/"deploy/releases.json").read_text())
    release = config["services"][service]
    no_credentials = {k:v for k,v in os.environ.items() if not k.startswith("AWS_")}
    run([sys.executable, str(ROOT/"scripts/verify_release.py"), str(directory), "--repository", release["repository"],
         "--commit", release["commit"], "--workflow-sha", config["workflow_sha"]], env=no_credentials)
    return json.loads((directory/"release.json").read_text())


def bootstrap_check(plan):
    if plan["variables"]["enable_github_oidc"]["value"] or plan["variables"]["manage_github_provider"]["value"]:
        raise ValueError("Federation must remain disabled on this account")
    allowed = {"aws_s3_bucket", "aws_s3_bucket_public_access_block", "aws_s3_bucket_ownership_controls",
               "aws_s3_bucket_versioning", "aws_s3_bucket_server_side_encryption_configuration", "aws_s3_bucket_policy",
               "aws_s3_bucket_lifecycle_configuration", "aws_iam_policy", "aws_iam_role", "aws_iam_role_policy"}
    for resource in resources(plan["planned_values"]["root_module"]):
        if resource["type"] not in allowed or "deployment" in resource["address"]:
            raise ValueError("Unapproved Free Plan bootstrap resource")
    if any("delete" in r["change"]["actions"] for r in plan["resource_changes"]):
        raise ValueError("Bootstrap deletion/replacement requires a separate reviewed recovery procedure")


def assert_state_bucket(session, bucket):
    s3 = session.client("s3")
    flags = s3.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"]
    if not all(flags.get(k) is True for k in ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")):
        raise ValueError("State bucket public access protection is incomplete")
    if s3.get_bucket_versioning(Bucket=bucket).get("Status") != "Enabled":
        raise ValueError("State bucket versioning is disabled")
    rules = s3.get_bucket_encryption(Bucket=bucket)["ServerSideEncryptionConfiguration"]["Rules"]
    if not any(r["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"] == "AES256" for r in rules):
        raise ValueError("State encryption is not the reviewed AES256 configuration")


def smoke(session, service, region, release, destination):
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    lamb = session.client("lambda")
    config = lamb.get_function_configuration(FunctionName=f"paved-{service}")
    if base64.b64decode(config["CodeSha256"]).hex() != release["lambda_sha256"]:
        raise ValueError("Live Lambda package differs from the signed release")
    url_config = lamb.get_function_url_config(FunctionName=f"paved-{service}")
    if url_config["AuthType"] != "AWS_IAM":
        raise ValueError("URL is not authenticated")
    base = url_config["FunctionUrl"].rstrip("/")
    try:
        urllib.request.urlopen(base+"/healthz", timeout=20)
    except urllib.error.HTTPError as error:
        if error.code != 403:
            raise
    else:
        raise ValueError("Unauthenticated request was accepted")
    def request(method, path):
        body = b"" if method == "POST" else None
        signing = AWSRequest(method=method, url=base+path, data=body)
        SigV4Auth(session.get_credentials().get_frozen_credentials(), "lambda", region).add_auth(signing)
        req = urllib.request.Request(base+path, method=method, data=body, headers=dict(signing.headers))
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.load(response)
    health = request("GET", "/healthz")
    hello = request("GET", "/hello/Surya")
    if health["status"] != "ok" or hello["message"] != "Hello, Surya!":
        raise ValueError("Live HTTP response mismatch")
    first = request("POST", "/hits")["hits"]
    time.sleep(1.1)
    second = request("POST", "/hits")["hits"]
    row = session.client("dynamodb").get_item(TableName=f"paved-{service}", Key={"pk":{"S":"hits"}}, ConsistentRead=True)["Item"]
    if second != first+1 or int(row["hit_count"]["N"]) != second:
        raise ValueError("Counter updates are not persisted in DynamoDB")
    evidence = {"at":timestamp(), "service":service, "unauthenticated_status":403, "authenticated_health":health,
                "hello":hello, "counter_values":[first,second], "dynamodb_consistent_read":second,
                "lambda_sha256":release["lambda_sha256"], "url_authentication":"AWS_IAM", "passed":True}
    write_json(destination, evidence)
    print(json.dumps(evidence))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["bootstrap-plan","bootstrap-apply","plan","apply","destroy-plan","destroy","status","smoke"])
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--region", choices=["ap-southeast-2"], default="ap-southeast-2")
    parser.add_argument("--service", choices=["demo","template"], default="demo")
    parser.add_argument("--credential-cli", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--plan-sha256")
    parser.add_argument("--release-directory", type=Path)
    args = parser.parse_args()
    if len(args.account_id) != 12 or not args.account_id.isdigit():
        raise ValueError("Expected 12-digit account ID")
    os.umask(0o077)
    if not args.credential_cli.is_absolute() or not args.credential_cli.is_file() or args.credential_cli.name.lower() != "aws.exe":
        raise ValueError("An installed Windows AWS CLI executable is required")
    base = Path.home()/".local/state/paved-road"/args.account_id/args.region
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(base,0o700)
    operator_lock = (base/"operator.lock").open("a")
    fcntl.flock(operator_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    process = [sys.executable,str(ROOT/"scripts/export_cli_credentials.py"),"--cli",str(args.credential_cli),
               "--profile",args.profile,"--region",args.region]
    config_path = base/"credential-process.config"
    config_path.write_text("[default]\nregion = "+args.region+"\ncredential_process = "+shlex.join(process)+"\n")
    clean_env = isolated_environment(dict(os.environ),config_path)
    clean_env.update(AWS_REGION=args.region, AWS_DEFAULT_REGION=args.region,
                     TF_PLUGIN_CACHE_DIR=str(Path.home()/".cache/paved-road/tofu-plugins"))
    clean_env["PATH"] = str(Path.home()/".local/bin")+":"+clean_env["PATH"]
    os.environ.clear()
    os.environ.update(clean_env)
    import boto3
    from botocore.config import Config
    session = boto3.Session(region_name=args.region)
    session._session.set_default_client_config(Config(retries={"mode":"standard","max_attempts":3}, connect_timeout=10, read_timeout=30))
    identity = session.client("sts").get_caller_identity()
    if identity["Account"] != args.account_id:
        raise ValueError("Authenticated account does not match target")
    base = Path.home()/".local/state/paved-road"/args.account_id/args.region
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(base, 0o700)
    with operator_lock:
        plan_state = session.client("freetier",region_name="us-east-1").get_account_plan_state()
        require_free_plan(plan_state, args.account_id)
        plan_state.pop("ResponseMetadata", None)
        write_json(base/"account-plan.json", plan_state)
        print(f"Verified account {args.account_id}: active FREE plan; credits USD {plan_state['accountPlanRemainingCredits']['amount']}", flush=True)
        bucket = f"paved-road-state-{args.account_id}-{args.region}"
        if args.action == "status":
            context = inventory(session,args.account_id,args.region,{},args.service)
            write_json(base/"inventory.json",context)
            print(json.dumps(context,indent=2))
            return
        bootstrap = args.action.startswith("bootstrap-")
        source = base/("bootstrap" if bootstrap else args.service)
        work = source/("bootstrap" if bootstrap else "deploy/service")
        work.mkdir(parents=True,exist_ok=True)
        if args.action == "smoke":
            release = verify_release(source/"release",args.service)
            smoke(session,args.service,args.region,release,source/"smoke.json")
            return
        creating_plan = args.action in {"bootstrap-plan","plan","destroy-plan"}
        if creating_plan:
            sync_config(work,ROOT/("bootstrap" if bootstrap else "deploy/service"))
            if bootstrap:
                variables = {"account_id":args.account_id,"region":args.region,"enable_github_oidc":False,"manage_github_provider":False}
                backend = []
            else:
                assert_state_bucket(session,bucket)
                sync_config(source/"modules/serverless-service",ROOT/"modules/serverless-service")
                if args.action == "plan":
                    if not args.release_directory:
                        raise ValueError("Specify the downloaded signed release directory")
                    shutil.copytree(args.release_directory,source/"release",dirs_exist_ok=True)
                elif not (source/"release/lambda/lambda.zip").is_file():
                    raise ValueError("Existing service release is needed for destroy planning")
                variables = {"account_id":args.account_id,"region":args.region,"service_name":args.service,
                             "lambda_zip":str(source/"release/lambda/lambda.zip")}
                backend = [f"-backend-config=bucket={bucket}",f"-backend-config=key=services/{args.service}/terraform.tfstate",
                           f"-backend-config=region={args.region}","-backend-config=encrypt=true","-backend-config=use_lockfile=true"]
            write_json(work/"input.auto.tfvars.json",variables)
            run(["tofu","init","-input=false","-lockfile=readonly",*backend],cwd=work)
            run(["tofu","validate"],cwd=work)
            if args.action == "plan":
                verify_release(source/"release",args.service)
            command = ["tofu","plan","-input=false","-lock-timeout=60s","-out=saved.tfplan"]
            if args.action == "destroy-plan":
                command += ["-destroy"]
            run(command,cwd=work)
            plan = json.loads(run(["tofu","show","-json","saved.tfplan"],cwd=work,capture=True))
            write_json(work/"saved-plan.json",plan)
            if bootstrap:
                bootstrap_check(plan)
            else:
                if args.action == "plan":
                    validate_plan_package(plan,source/"release/lambda/lambda.zip")
                context = inventory(session,args.account_id,args.region,plan,args.service)
                policy_check(plan,context,work,args.account_id,args.region,args.service)
            meta = {"created_at":timestamp(),"account_id":args.account_id,"region":args.region,"service":args.service,
                    "action":args.action,"source_sha256":source_digest(),"sha256":sha256(work/"saved.tfplan")}
            if not bootstrap:
                meta["lambda_sha256"] = sha256(source/"release/lambda/lambda.zip")
            write_json(work/"plan-metadata.json",meta)
            print("REVIEWED_PLAN_SHA256="+meta["sha256"])
            print("Private plan JSON: "+str(work/"saved-plan.json"))
            return
        meta = json.loads((work/"plan-metadata.json").read_text())
        validate_saved_plan(meta,work/"saved.tfplan",args.plan_sha256,args.account_id,args.region,source_digest())
        expected_action = {"bootstrap-apply":"bootstrap-plan","apply":"plan","destroy":"destroy-plan"}[args.action]
        if meta["action"] != expected_action or (not bootstrap and meta["service"] != args.service):
            raise ValueError("Plan operation does not match requested apply")
        # Re-read JSON from the hashed binary, never trust an editable sidecar.
        plan = json.loads(run(["tofu","show","-json","saved.tfplan"],cwd=work,capture=True))
        if bootstrap:
            bootstrap_check(plan)
        else:
            assert_state_bucket(session,bucket)
            if sha256(source/"release/lambda/lambda.zip") != meta["lambda_sha256"]:
                raise ValueError("Lambda ZIP changed since planning")
            if args.action == "apply":
                verify_release(source/"release",args.service)
                validate_plan_package(plan,source/"release/lambda/lambda.zip")
            context = inventory(session,args.account_id,args.region,plan,args.service)
            policy_check(plan,context,work,args.account_id,args.region,args.service)
        # Recheck hash after verification and inventory. Apply this binary only.
        validate_saved_plan(meta,work/"saved.tfplan",args.plan_sha256,args.account_id,args.region,source_digest())
        run(["tofu","apply","-input=false","-lock-timeout=60s","saved.tfplan"],cwd=work)
        write_json(source/("destroy.json" if args.action == "destroy" else "apply.json"),
                   {"at":timestamp(),"plan_sha256":args.plan_sha256,"account_id":args.account_id,"region":args.region,
                    "action":args.action,"source_sha256":meta["source_sha256"],"passed":True})
        if bootstrap:
            assert_state_bucket(session,bucket)
        print("PASS: applied the exact reviewed saved plan")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Avoid tracebacks/credential-bearing objects. AWS errors expose only code + message.
        if hasattr(error,"response"):
            detail = error.response.get("Error",{})
            print(f"STOP: {detail.get('Code','AWS error')}: {detail.get('Message','Request failed')}",file=sys.stderr)
        else:
            print(f"STOP: {type(error).__name__}: {error}",file=sys.stderr)
        sys.exit(1)
