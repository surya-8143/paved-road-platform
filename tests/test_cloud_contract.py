"""Adversarial checks for account, temporary-credential and exact-plan binding."""
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location("cloud_contract", Path(__file__).resolve().parents[1]/"scripts/cloud_contract.py")
cloud = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cloud)
NOW = datetime(2026,11,21,tzinfo=timezone.utc)
ACCOUNT = "123456789012"

class CloudContract(unittest.TestCase):
    def credentials(self):
        return {"Version":1,"AccessKeyId":"temporary-test-id","SecretAccessKey":"test-only-secret", "SessionToken":"test-only-session",
                "Expiration":(NOW+timedelta(hours=1)).isoformat()}

    def test_removes_ambient_identity_endpoint_and_debug_overrides(self):
        env = cloud.isolated_environment(
            {"AWS_PROFILE":"wrong", "AWS_ENDPOINT_URL":"https://untrusted.example", "AWS_WEB_IDENTITY_TOKEN_FILE":"bad",
             "TF_LOG":"TRACE","TF_CLI_ARGS_apply":"-target=wrong","TOFU_LOG":"TRACE","PATH":"/bin"}, "/private/config")
        self.assertNotIn("AWS_PROFILE",env)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY",env)
        self.assertNotIn("AWS_ENDPOINT_URL",env)
        self.assertNotIn("AWS_WEB_IDENTITY_TOKEN_FILE",env)
        self.assertNotIn("TF_LOG",env)
        self.assertNotIn("TF_CLI_ARGS_apply",env)
        self.assertNotIn("TOFU_LOG",env)
        self.assertEqual(env["AWS_CONFIG_FILE"],"/private/config")
        self.assertEqual(env["PATH"],"/bin")

    def test_static_keys_and_near_expiry_are_rejected(self):
        for field in ("SessionToken","Expiration"):
            value = self.credentials()
            del value[field]
            with self.assertRaises(ValueError):
                cloud.validate_process_credentials(json.dumps(value),NOW)
        value = self.credentials()
        value["Expiration"] = (NOW+timedelta(seconds=30)).isoformat()
        with self.assertRaises(ValueError):
            cloud.validate_process_credentials(json.dumps(value),NOW)

    def free_plan(self):
        return {"accountId":ACCOUNT,"accountPlanType":"FREE","accountPlanStatus":"ACTIVE",
                "accountPlanRemainingCredits":{"amount":100,"unit":"USD"}, "accountPlanExpirationDate":NOW+timedelta(days=180)}

    def test_wrong_account_paid_status_low_credit_and_expiry_stop(self):
        for key,value in (("accountId","999999999999"),("accountPlanType","PAID"),("accountPlanStatus","EXPIRED"),
                          ("accountPlanRemainingCredits",{"amount":19,"unit":"USD"}),
                          ("accountPlanExpirationDate",NOW+timedelta(hours=1))):
            plan = self.free_plan()
            plan[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                cloud.require_free_plan(plan,ACCOUNT,NOW)
        cloud.require_free_plan(self.free_plan(),ACCOUNT,NOW)

    def test_saved_plan_cannot_be_swapped_or_reused_across_sources_accounts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"saved.tfplan"
            path.write_bytes(b"reviewed binary")
            digest = cloud.sha256(path)
            meta = {"created_at":NOW.isoformat(),"account_id":ACCOUNT,"region":"ap-southeast-2","source_sha256":"source","sha256":digest}
            cloud.validate_saved_plan(meta,path,digest,ACCOUNT,"ap-southeast-2","source",NOW)
            for field,value in (("account_id","999999999999"),("region","us-east-1"),("source_sha256","changed"),
                                ("created_at",(NOW-timedelta(minutes=16)).isoformat())):
                with self.subTest(field=field), self.assertRaises(ValueError):
                    cloud.validate_saved_plan({**meta,field:value},path,digest,ACCOUNT,"ap-southeast-2","source",NOW)
            path.write_bytes(b"unreviewed binary")
            with self.assertRaises(ValueError):
                cloud.validate_saved_plan(meta,path,digest,ACCOUNT,"ap-southeast-2","source",NOW)

    def test_plan_package_hash_and_path_must_match_verified_bytes(self):
        import base64
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"lambda.zip"
            path.write_bytes(b"signed artifact fixture")
            value = {"filename":str(path),"source_code_hash":base64.b64encode(hashlib.sha256(path.read_bytes()).digest()).decode()}
            plan = {"resource_changes":[{"type":"aws_lambda_function","change":{"after":value}}]}
            cloud.validate_plan_package(plan,path)
            value["filename"] = "/different/package.zip"
            with self.assertRaises(ValueError): cloud.validate_plan_package(plan,path)
            value["filename"] = str(path)
            path.write_bytes(b"changed bytes")
            with self.assertRaises(ValueError): cloud.validate_plan_package(plan,path)
