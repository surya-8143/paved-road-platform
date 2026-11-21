import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("diagnostic", Path(__file__).resolve().parents[1] / "scripts/aws_lab_diagnostic.py")
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


class LabDiagnostic(unittest.TestCase):
    def test_wrong_account_stops_before_any_other_api(self):
        calls = []
        def reader(*args):
            calls.append(args)
            return {"Account": "999999999999"}
        with self.assertRaisesRegex(ValueError, "different AWS account"):
            diagnostic.collect("learner-lab", "us-east-1", "123456789012", reader)
        self.assertEqual(len(calls), 1)

    def test_reads_do_not_prove_oidc_creation_permission(self):
        def reader(profile, region, *args):
            if args[0] == "sts":
                return {"Account": "123456789012", "Arn": "arn:aws:sts::123456789012:assumed-role/voclabs/demo"}
            if "get-role" in args:
                return {"Role": {"Arn": "arn:aws:iam::123456789012:role/LabRole"}}
            return {}
        result = diagnostic.collect("learner-lab", "us-east-1", "123456789012", reader)
        self.assertFalse(result["full_pipeline_ready"])
        self.assertEqual(result["oidc_creation_permission"], "NOT_VERIFIED")
        self.assertTrue(all(item["status"] == "READ_SUCCEEDED" for item in result["checks"].values()))

    def test_denied_reads_are_unknown_not_empty_inventory(self):
        def reader(profile, region, *args):
            if args[0] == "sts":
                return {"Account": "123456789012"}
            raise diagnostic.AwsReadError("AccessDenied")
        result = diagnostic.collect("learner-lab", "us-east-1", "123456789012", reader)
        self.assertTrue(all(item == {"status": "UNVERIFIED", "error": "AccessDenied"} for item in result["checks"].values()))

    def test_invalid_profile_region_and_account_are_rejected_before_cli(self):
        def reader(*args):
            self.fail("CLI should not be invoked")
        for profile, region, account in [("--debug", "us-east-1", "123456789012"), ("lab", "eu-west-1", "123456789012"), ("lab", "us-east-1", "bad")]:
            with self.assertRaises(ValueError):
                diagnostic.collect(profile, region, account, reader)
