"""Exercise policy decisions against a complete representative plan, not change-only snippets."""
import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAGS = {"Project": "paved-road", "Owner": "surya-8143", "Environment": "demo", "Service": "demo", "ManagedBy": "opentofu"}


def resource(kind, name, values):
    return {"address": f"module.demo.{kind}.{name}", "mode": "managed", "type": kind,
            "values": {"tags": TAGS.copy(), **values}}


def baseline():
    function = resource("aws_lambda_function", "app", {
        "runtime": "python3.12", "package_type": "Zip", "handler": "app.main.handler", "architectures": ["x86_64"],
        "memory_size": 128, "timeout": 5, "reserved_concurrent_executions": 2, "ephemeral_storage": [{"size": 512}],
        "publish": False, "source_code_hash": "A" * 43 + "=", "function_name": "paved-demo",
        "role": "arn:aws:iam::123456789012:role/paved-road/demo-runtime", "vpc_config": []})
    table = resource("aws_dynamodb_table", "hits", {"billing_mode": "PROVISIONED", "read_capacity": 1,
        "write_capacity": 1, "hash_key": "pk", "server_side_encryption": [{"enabled": False}],
        "point_in_time_recovery": [{"enabled": False}]})
    url = resource("aws_lambda_function_url", "app", {"function_name": "paved-demo", "authorization_type": "AWS_IAM", "invoke_mode": "BUFFERED"})
    resources = [function, table, url, resource("aws_cloudwatch_log_group", "app", {"retention_in_days": 7})]
    return {"plan": {"format_version": "1.2", "planned_values": {"root_module": {"child_modules": [{"resources": resources}]}},
                     "resource_changes": [{"address": r["address"], "type": r["type"], "change": {"actions": ["create"], "after": r["values"], "after_unknown": {}}} for r in resources]},
            "context": {"mode": "offline", "other_usage": {"functions": 0, "read_capacity": 0, "write_capacity": 0, "alarms": 0}}}


class PlanPolicy(unittest.TestCase):
    def decide(self, envelope, expected, fragment="", exceptions=None):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.json"
            path.write_text(json.dumps(envelope))
            data = json.loads((ROOT / "policy/guardrails.json").read_text())
            if exceptions:
                data["guardrails"]["public_exceptions"] = exceptions
            config = Path(temporary) / "data.json"
            config.write_text(json.dumps(data))
            result = subprocess.run(["conftest", "test", str(path), "--policy", str(ROOT / "policy"), "--data", str(config), "--output", "json"], capture_output=True, text=True)
            self.assertEqual(result.returncode == 0, expected, result.stdout + result.stderr)
            if fragment:
                self.assertIn(fragment, result.stdout)

    def test_valid_nested_plan(self):
        self.decide(baseline(), True)

    def test_oversized_lambda_preserves_change_actions(self):
        plan = baseline()
        plan["plan"]["planned_values"]["root_module"]["child_modules"][0]["resources"][0]["values"]["memory_size"] = 1024
        self.assertEqual(plan["plan"]["resource_changes"][0]["change"]["actions"], ["create"])
        self.decide(plan, False, "Lambda configuration")

    def test_unknown_limits_and_missing_tags_fail_closed(self):
        for field in ("memory_size", "timeout", "role", "reserved_concurrent_executions", "tags"):
            plan = baseline()
            del plan["plan"]["planned_values"]["root_module"]["child_modules"][0]["resources"][0]["values"][field]
            plan["plan"]["resource_changes"][0]["change"]["after_unknown"][field] = True
            with self.subTest(field=field):
                self.decide(plan, False)

    def test_missing_actions_is_invalid(self):
        plan = baseline()
        del plan["plan"]["resource_changes"][0]["change"]["actions"]
        self.decide(plan, False, "Missing change actions")

    def test_unchanged_resources_and_other_stacks_count(self):
        plan = baseline()
        for change in plan["plan"]["resource_changes"]:
            change["change"]["actions"] = ["no-op"]
        plan["context"]["other_usage"]["functions"] = 2
        self.decide(plan, False, "Aggregate Lambda")
        plan["context"]["other_usage"]["functions"] = 0
        plan["context"]["other_usage"]["write_capacity"] = 5
        self.decide(plan, False, "Aggregate DynamoDB write")

    def test_create_before_destroy_peak_counts(self):
        plan = baseline()
        plan["context"]["other_usage"]["functions"] = 1
        plan["plan"]["resource_changes"][0]["change"]["actions"] = ["create", "delete"]
        self.decide(plan, False, "Aggregate Lambda")

    def test_public_url_requires_specific_exception_and_own_concurrency(self):
        plan = baseline()
        resources = plan["plan"]["planned_values"]["root_module"]["child_modules"][0]["resources"]
        resources[2]["values"]["authorization_type"] = "NONE"
        plan["plan"]["resource_changes"][2]["change"]["actions"] = ["update"]
        self.decide(plan, False, "function URL")
        exception = {"paved-demo": {"reason": "Reviewed temporary public demo", "review": "https://github.com/surya-8143/paved-road-platform/pull/1", "expires_at": "2099-01-01T00:00:00Z"}}
        resources[0]["values"]["reserved_concurrent_executions"] = 1
        self.decide(plan, True, exceptions=exception)
        resources[2]["values"]["function_name"] = "different-function"
        self.decide(plan, False, "function URL", exception)

    def test_expired_exception_is_rejected(self):
        plan = baseline()
        resources = plan["plan"]["planned_values"]["root_module"]["child_modules"][0]["resources"]
        resources[2]["values"]["authorization_type"] = "NONE"
        resources[0]["values"]["reserved_concurrent_executions"] = 1
        exception = {"paved-demo": {"reason": "Expired public demo permission", "review": "https://github.com/surya-8143/paved-road-platform/pull/1", "expires_at": "2020-01-01T00:00:00Z"}}
        self.decide(plan, False, "function URL", exception)

    def test_unapproved_resource_type(self):
        plan = baseline()
        plan["plan"]["planned_values"]["root_module"]["child_modules"][0]["resources"].append(resource("aws_nat_gateway", "expensive", {}))
        self.decide(plan, False, "not approved")

    def test_empty_or_stale_context_is_not_account_evidence(self):
        self.decide({}, False, "envelope")
        plan = baseline()
        plan["context"].update(mode="online", account_id="123456789012", inventory_timestamp="2020-01-01T00:00:00Z")
        self.decide(plan, False, "15 minutes")

    def test_destroy_plan_is_allowed(self):
        plan = baseline()
        plan["plan"]["planned_values"]["root_module"] = {}
        for change in plan["plan"]["resource_changes"]:
            change["change"]["actions"] = ["delete"]
        self.decide(plan, True)
