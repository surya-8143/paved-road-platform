"""Pure checks for the personal Free Plan runner; no credentials are persisted."""
import base64
import hashlib
import json
from datetime import datetime, timezone


def validate_process_credentials(raw, now=None):
    now = now or datetime.now(timezone.utc)
    credentials = json.loads(raw)
    fields = ("Version", "AccessKeyId", "SecretAccessKey", "SessionToken", "Expiration")
    if credentials.get("Version") != 1 or not all(isinstance(credentials.get(k), str) and credentials[k] for k in fields[1:]):
        raise ValueError("A temporary AWS CLI credential response is required")
    expiry = datetime.fromisoformat(credentials["Expiration"].replace("Z", "+00:00"))
    if expiry.tzinfo is None or (expiry-now).total_seconds() < 60:
        raise ValueError("Temporary credentials have expired")
    return {k: credentials[k] for k in fields}


def require_free_plan(plan, account, now=None):
    now = now or datetime.now(timezone.utc)
    if plan.get("accountId") != account or plan.get("accountPlanType") != "FREE" or plan.get("accountPlanStatus") != "ACTIVE":
        raise ValueError("This runner requires the expected account on an active Free Plan")
    credits = plan.get("accountPlanRemainingCredits", {})
    if credits.get("unit") != "USD" or float(credits.get("amount", 0)) < 20:
        raise ValueError("Keep at least USD 20 credit headroom; provisioning stopped")
    expiry = plan.get("accountPlanExpirationDate")
    if isinstance(expiry, str):
        expiry = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
    if not isinstance(expiry, datetime) or expiry.tzinfo is None or (expiry-now).total_seconds() < 86400:
        raise ValueError("Free Plan expiry is too close or unavailable")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_saved_plan(meta, plan_path, expected, account, region, source_hash, now=None):
    now = now or datetime.now(timezone.utc)
    if not expected or meta["sha256"] != expected or sha256(plan_path) != expected:
        raise ValueError("Saved-plan digest does not match the reviewed plan")
    if meta["account_id"] != account or meta["region"] != region or meta["source_sha256"] != source_hash:
        raise ValueError("Account, region or reviewed source changed; create a fresh plan")
    age = (now-datetime.fromisoformat(meta["created_at"])).total_seconds()
    if age < -60 or age > 900:
        raise ValueError("Saved plan expired; create a fresh plan (15 minute maximum)")


def isolated_environment(inherited, config_path):
    env = {k: v for k,v in inherited.items() if not k.startswith(("AWS_", "TF_", "TOFU_"))}
    env.update(AWS_CONFIG_FILE=str(config_path), AWS_SHARED_CREDENTIALS_FILE="/dev/null",
               AWS_EC2_METADATA_DISABLED="true", AWS_SDK_LOAD_CONFIG="1", TF_IN_AUTOMATION="1", TF_INPUT="0")
    return env


def validate_plan_package(plan, package):
    changes = [r for r in plan.get("resource_changes",[]) if r.get("type") == "aws_lambda_function" and r["change"].get("after") is not None]
    if len(changes) != 1:
        raise ValueError("Expected exactly one planned service function")
    values = changes[0]["change"]["after"]
    expected = base64.b64encode(hashlib.sha256(package.read_bytes()).digest()).decode()
    if values.get("source_code_hash") != expected or values.get("filename") != str(package):
        raise ValueError("Saved plan is not bound to the verified Lambda package bytes and path")
