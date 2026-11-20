"""Validate the repository's offline example, including a fingerprinted module contract.

This is intentionally not a generic online-deployment approval command.
"""
import argparse
import copy
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


def fingerprint(module):
    digest = hashlib.sha256()
    for path in sorted(module.glob("*.tf")):
        digest.update(path.name.encode() + b"\0" + path.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return digest.hexdigest()


def offline_envelope(plan, root):
    expected = json.loads((root / "policy/guardrails.json").read_text())["guardrails"]["approved_module_sha256"]
    actual = fingerprint(root / "modules/serverless-service")
    if actual != expected:
        raise ValueError("Module source changed; review and update its policy contract before planning")
    calls = plan["configuration"]["root_module"]["module_calls"]
    if set(calls) != {"service"} or calls["service"]["source"] != "../../modules/serverless-service":
        raise ValueError("This checker only accepts the repository's fixed offline example")
    configured = {r["address"]: r for r in calls["service"]["module"]["resources"]}
    table_address = "module.service.aws_dynamodb_table.hits"
    expressions = configured["aws_dynamodb_table.hits"]["expressions"]
    if "global_secondary_index" in expressions:
        raise ValueError("The approved module must not configure secondary indexes")
    normalized = copy.deepcopy(plan)
    resolutions = []
    for change in normalized["resource_changes"]:
        if change["address"] != table_address or change["change"]["actions"] != ["create"]:
            continue
        after = change["change"]["after"]
        if any(after.get(key) is not None for key in ("restore_backup_arn", "restore_source_name", "restore_source_table_arn", "import_table") if key != "import_table") or after.get("import_table"):
            raise ValueError("The empty-index contract cannot authorize a restored or imported table")
        # The fixed, fingerprinted source has no dynamic/index blocks and creates
        # a fresh table. Provider 6.73.0 reports this omitted Optional+Computed set
        # as unknown. Resolve ONLY this field for ONLY this source/resource.
        if change["change"]["after_unknown"].get("global_secondary_index") is True:
            change["change"]["after_unknown"]["global_secondary_index"] = False
            after["global_secondary_index"] = []
            for module in normalized["planned_values"]["root_module"].get("child_modules", []):
                for resource in module.get("resources", []):
                    if resource["address"] == table_address:
                        resource["values"]["global_secondary_index"] = []
            resolutions.append(table_address + ".global_secondary_index = []")
    return {"plan": normalized, "context": {"mode": "offline", "module_sha256": actual,
        "resolved_from_source": resolutions,
        "other_usage": {"functions": 0, "read_capacity": 0, "write_capacity": 0, "alarms": 0}}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    envelope = offline_envelope(json.loads(args.plan.read_text()), root)
    with tempfile.TemporaryDirectory(prefix="paved-road-plan-") as temporary:
        source = Path(temporary) / "envelope.json"
        source.write_text(json.dumps(envelope))
        subprocess.run(["conftest", "test", str(source), "--policy", str(root / "policy"),
                        "--data", str(root / "policy/guardrails.json")], check=True)
    print("Source-proven resolutions:", envelope["context"]["resolved_from_source"])
    print("Offline plan passed. This is not approval to deploy and does not verify account usage.")


if __name__ == "__main__":
    main()
