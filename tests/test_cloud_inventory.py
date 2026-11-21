"""Inventory failures, other stacks and unexpected state must fail closed."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from deploy_free_plan import inventory, own_names

class Pages:
    def __init__(self,pages): self.pages=pages
    def paginate(self,**kwargs): return self.pages

class Client:
    def __init__(self,pages=None,table=None): self.pages=pages; self.table=table
    def get_paginator(self,name): return Pages(self.pages)
    def get_account_settings(self): return {"AccountLimit":{"UnreservedConcurrentExecutions":400}}
    def describe_table(self,**kwargs): return {"Table":self.table}

class Session:
    def __init__(self,table=None):
        self.clients={"lambda":Client([{"Functions":[{"FunctionName":"paved-demo"}]},{"Functions":[{"FunctionName":"foreign"}]}]),
                      "dynamodb":Client([{"TableNames":["foreign"]}], table or {"TableStatus":"ACTIVE", "ProvisionedThroughput":{"ReadCapacityUnits":2,"WriteCapacityUnits":1},
                         "GlobalSecondaryIndexes":[{"ProvisionedThroughput":{"ReadCapacityUnits":1,"WriteCapacityUnits":2}}]}),
                      "cloudwatch":Client([{"MetricAlarms":[{"AlarmName":"foreign"}],"CompositeAlarms":[{"AlarmName":"composite"}]}])}
    def client(self,name): return self.clients[name]

class InventoryTests(unittest.TestCase):
    def prior(self,name="paved-demo"):
        return {"prior_state":{"values":{"root_module":{"child_modules":[{"resources":[{"type":"aws_lambda_function","values":{"id":name}}]}]}}}}

    def test_paginates_counts_indexes_and_includes_unmanaged_usage(self):
        result=inventory(Session(),"123456789012","ap-southeast-2",self.prior(),"demo")
        self.assertEqual(result["other_usage"],{"functions":1,"read_capacity":3,"write_capacity":3,"alarms":2})
        self.assertEqual(result["mode"],"online")

    def test_existing_matching_name_without_state_is_not_excluded(self):
        self.assertEqual(inventory(Session(),"123456789012","ap-southeast-2",{},"demo")["other_usage"]["functions"],2)

    def test_foreign_state_cannot_hide_existing_resources(self):
        with self.assertRaisesRegex(ValueError,"foreign resource"):
            own_names(self.prior("foreign"),"demo")

    def test_on_demand_or_non_active_tables_are_not_zero_capacity(self):
        for table in ({"TableStatus":"CREATING"},{"TableStatus":"ACTIVE","BillingModeSummary":{"BillingMode":"PAY_PER_REQUEST"}}):
            with self.assertRaises(ValueError):
                inventory(Session(table),"123456789012","ap-southeast-2",{},"demo")

    def test_denied_inventory_is_not_empty_inventory(self):
        class Denied(Session):
            def client(self,name): raise PermissionError("denied")
        with self.assertRaises(PermissionError):
            inventory(Denied(),"123456789012","ap-southeast-2",{},"demo")
