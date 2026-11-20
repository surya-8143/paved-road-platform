import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("check_plan", Path(__file__).resolve().parents[1] / "scripts/check_plan.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class OfflineContract(unittest.TestCase):
    def fixture(self, root):
        directory = root / "modules/serverless-service"
        directory.mkdir(parents=True)
        (directory / "main.tf").write_text('# Approved fixture has no indexes\n')
        (root / "policy").mkdir()
        (root / "policy/guardrails.json").write_text(json.dumps({"guardrails": {"approved_module_sha256": module.fingerprint(directory)}}))
        address = "module.service.aws_dynamodb_table.hits"
        return {"configuration": {"root_module": {"module_calls": {"service": {"source": "../../modules/serverless-service", "module": {"resources": [{"address": "aws_dynamodb_table.hits", "expressions": {}}]}}}}},
                "resource_changes": [{"address": address, "change": {"actions": ["create"], "after": {}, "after_unknown": {"global_secondary_index": True, "read_capacity": True}}}],
                "planned_values": {"root_module": {"child_modules": [{"resources": [{"address": address, "values": {}}]}]}}}

    def test_only_omitted_index_is_resolved_and_original_remains_intact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = self.fixture(root)
            envelope = module.offline_envelope(plan, root)
            unknown = envelope["plan"]["resource_changes"][0]["change"]["after_unknown"]
            self.assertIs(unknown["global_secondary_index"], False)
            self.assertIs(unknown["read_capacity"], True)
            self.assertIs(plan["resource_changes"][0]["change"]["after_unknown"]["global_secondary_index"], True)

    def test_source_tampering_invalidates_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = self.fixture(root)
            (root / "modules/serverless-service/main.tf").write_text('# Changed source\n')
            with self.assertRaisesRegex(ValueError, "Module source changed"):
                module.offline_envelope(plan, root)

    def test_foreign_module_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = self.fixture(root)
            plan["configuration"]["root_module"]["module_calls"]["service"]["source"] = "attacker/module"
            with self.assertRaises(ValueError):
                module.offline_envelope(plan, root)

    def test_restore_does_not_inherit_empty_index_assumption(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = self.fixture(root)
            plan["resource_changes"][0]["change"]["after"]["restore_source_name"] = "existing-table"
            with self.assertRaises(ValueError):
                module.offline_envelope(plan, root)
