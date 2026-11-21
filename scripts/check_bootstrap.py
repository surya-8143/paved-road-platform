"""Check rendered mock bootstrap plans, including permission-boundary wiring."""
import argparse
import json
from pathlib import Path


def validate_plan(plan):
    configured = {r["address"]: r for r in plan["configuration"]["root_module"]["resources"]}
    for kind in ("runtime", "deployment"):
        expression = configured["aws_iam_role." + kind]["expressions"]["permissions_boundary"]
        if set(expression.get("references", [])) != {"aws_iam_policy." + kind + "_boundary", "each.key"}:
            raise ValueError("Every " + kind + " role must reference its corresponding boundary")
    values = {r["address"]: r["values"] for r in plan["planned_values"]["root_module"]["resources"]}
    services = plan["variables"]["services"]["value"]
    account = plan["variables"]["account_id"]["value"]
    region = plan["variables"]["region"]["value"]
    for service in services:
        for kind in ("runtime", "deployment"):
            suffix = '["' + service + '"]'
            boundary = json.loads(values["aws_iam_policy." + kind + "_boundary" + suffix]["policy"])
            attached = json.loads(values["aws_iam_role_policy." + kind + suffix]["policy"])
            if attached != boundary:
                raise ValueError("Attached role policy must match the reviewed boundary")
            for statement in boundary["Statement"]:
                actions = statement["Action"]
                if isinstance(actions, str):
                    actions = [actions]
                for action in actions:
                    if action == "*" or (action.startswith("iam:") and action not in {"iam:GetRole", "iam:PassRole"}):
                        raise ValueError("IAM administration or wildcard access is forbidden")
                    if action == "iam:PassRole":
                        if statement["Resource"] != f"arn:aws:iam::{account}:role/paved-road/{service}-runtime" or statement["Condition"] != {"StringEquals": {"iam:PassedToService": "lambda.amazonaws.com"}}:
                            raise ValueError("PassRole must target only this service's Lambda runtime role")
                if kind == "runtime":
                    permitted = {"dynamodb:UpdateItem", "logs:CreateLogStream", "logs:PutLogEvents"}
                    if not set(actions) <= permitted:
                        raise ValueError("Runtime permissions exceed application needs")
                    if "dynamodb:UpdateItem" in actions and (statement["Resource"] != f"arn:aws:dynamodb:{region}:{account}:table/paved-{service}" or statement["Condition"] != {"ForAllValues:StringEquals": {"dynamodb:LeadingKeys": ["hits"]}}):
                        raise ValueError("Runtime must access only its own counter item")
    return len(services)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.report.read_text().splitlines()]
    summaries = [r["test_summary"] for r in rows if r.get("type") == "test_summary"]
    if len(summaries) != 1 or summaries[0].get("status") != "pass" or any(summaries[0].get(k, 0) for k in ("failed", "errored", "skipped")):
        raise SystemExit("Bootstrap test suite did not finish cleanly")
    if any(r.get("diagnostic", {}).get("severity") == "error" for r in rows):
        raise SystemExit("Bootstrap tests emitted errors")
    plans = [r["test_plan"] for r in rows if r.get("type") == "test_plan" and r.get("@testrun") == "scoped_roles_and_private_state"]
    if len(plans) != 1:
        raise SystemExit("Expected exactly one rendered secure-default bootstrap plan")
    count = validate_plan(plans[0])
    print(f"PASS: {summaries[0]['passed']} mock tests and rendered IAM boundary/role checks for {count} services")


if __name__ == "__main__":
    main()
