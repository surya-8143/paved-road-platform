package main

import rego.v1

allowed_types := {"aws_lambda_function", "aws_lambda_function_url", "aws_dynamodb_table", "aws_cloudwatch_log_group", "aws_cloudwatch_metric_alarm"}
tagged_types := allowed_types - {"aws_lambda_function_url"}
required_tags := {"Project", "Owner", "Environment", "Service", "ManagedBy"}
resources := [r | walk(input.plan.planned_values.root_module, [_, r]); is_object(r); r.mode == "managed"; r.address; r.type; r.values]
functions := [r | some r in resources; r.type == "aws_lambda_function"]
tables := [r | some r in resources; r.type == "aws_dynamodb_table"]
alarms := [r | some r in resources; r.type == "aws_cloudwatch_metric_alarm"]

# Planned values include unchanged resources. Create-before-destroy replacements
# also temporarily retain their previous provisioned capacity.
replacement_tables := [r.change.before | some r in input.plan.resource_changes; r.type == "aws_dynamodb_table"; r.change.actions == ["create", "delete"]]
replacement_functions := [r | some r in input.plan.resource_changes; r.type == "aws_lambda_function"; r.change.actions == ["create", "delete"]]
replacement_alarms := [r | some r in input.plan.resource_changes; r.type == "aws_cloudwatch_metric_alarm"; r.change.actions == ["create", "delete"]]

valid_envelope if {
	input.plan.format_version == "1.2"
	is_object(input.plan.planned_values.root_module)
	is_array(input.plan.resource_changes)
	object.get(input.plan, "errored", false) == false
	input.context.mode in {"offline", "online"}
	every field in {"functions", "read_capacity", "write_capacity", "alarms"} {
		is_number(input.context.other_usage[field])
		input.context.other_usage[field] >= 0
	}
}

deny contains "Invalid or incomplete plan/context envelope" if not valid_envelope

deny contains "Online account inventory must be no older than 15 minutes" if {
	input.context.mode == "online"
	not fresh_inventory
}

fresh_inventory if {
	regex.match(`^[0-9]{12}$`, input.context.account_id)
	timestamp := time.parse_rfc3339_ns(input.context.inventory_timestamp)
	age := time.now_ns() - timestamp
	age >= -60000000000
	age <= 900000000000
}

deny contains sprintf("Resource type is not approved: %s", [r.address]) if {
	some r in resources
	not r.type in allowed_types
}

deny contains sprintf("Missing change actions: %s", [r.address]) if {
	some r in input.plan.resource_changes
	not valid_actions(r)
}

valid_actions(r) if {
	is_array(r.change.actions)
	count(r.change.actions) > 0
	every action in r.change.actions { action in {"no-op", "read", "create", "update", "delete"} }
}

deny contains sprintf("Missing/unknown required tag %s: %s", [tag, r.address]) if {
	some r in resources
	r.type in tagged_types
	some tag in required_tags
	not valid_tag(r, tag)
}

valid_tag(r, tag) if {
	is_string(r.values.tags[tag])
	count(r.values.tags[tag]) > 0
}

deny contains sprintf("Unexpected ownership tags: %s", [r.address]) if {
	some r in resources
	r.type in tagged_types
	not owned(r)
}

owned(r) if {
	r.values.tags.Project == "paved-road"
	r.values.tags.Environment == "demo"
	r.values.tags.ManagedBy == "opentofu"
}

valid_function(r) if {
	r.values.runtime == "python3.12"
	r.values.package_type == "Zip"
	r.values.handler == "app.main.handler"
	r.values.architectures == ["x86_64"]
	r.values.memory_size == 128
	r.values.timeout > 0
	r.values.timeout <= 5
	r.values.reserved_concurrent_executions in {0, 1, 2}
	r.values.ephemeral_storage[0].size == 512
	r.values.publish == false
	is_string(r.values.source_code_hash)
	count(r.values.source_code_hash) == 44
	r.values.function_name == sprintf("paved-%s", [r.values.tags.Service])
	endswith(r.values.role, sprintf(":role/paved-road/%s-runtime", [r.values.tags.Service]))
	regex.match(`^arn:aws:iam::[0-9]{12}:role/paved-road/[a-z0-9-]+-runtime$`, r.values.role)
	count(object.get(r.values, "vpc_config", [])) == 0
}

deny contains sprintf("Unsafe or unknown Lambda configuration: %s", [r.address]) if {
	some r in functions
	not valid_function(r)
}

valid_table(r) if {
	r.values.billing_mode == "PROVISIONED"
	r.values.read_capacity >= 1
	r.values.read_capacity <= 2
	r.values.write_capacity >= 1
	r.values.write_capacity <= 2
	r.values.hash_key == "pk"
	count(object.get(r.values, "global_secondary_index", [])) == 0
	count(object.get(r.values, "replica", [])) == 0
	r.values.server_side_encryption[0].enabled == false
	r.values.point_in_time_recovery[0].enabled == false
}

deny contains sprintf("Unsafe or unknown DynamoDB configuration: %s", [r.address]) if {
	some r in tables
	not valid_table(r)
}

deny contains sprintf("Log retention must be 1-7 days: %s", [r.address]) if {
	some r in resources
	r.type == "aws_cloudwatch_log_group"
	not valid_log(r)
}

valid_log(r) if {
	r.values.retention_in_days >= 1
	r.values.retention_in_days <= 7
}

valid_alarm(r) if {
	r.values.namespace == "AWS/Lambda"
	r.values.metric_name in {"Errors", "Throttles"}
	r.values.period >= 60
	empty_actions(object.get(r.values, "alarm_actions", []))
	empty_actions(object.get(r.values, "ok_actions", []))
	empty_actions(object.get(r.values, "insufficient_data_actions", []))
}

deny contains sprintf("Unexpected alarm configuration: %s", [r.address]) if {
	some r in alarms
	not valid_alarm(r)
}

valid_public_exception(name) if {
	exception := data.guardrails.public_exceptions[name]
	is_string(exception.reason)
	count(exception.reason) >= 10
	startswith(exception.review, "https://github.com/surya-8143/paved-road-platform/pull/")
	time.parse_rfc3339_ns(exception.expires_at) > time.now_ns()
}

valid_url(r) if {
	r.values.invoke_mode == "BUFFERED"
	r.values.authorization_type == "AWS_IAM"
	some f in functions
	f.values.function_name == r.values.function_name
}

valid_url(r) if {
	r.values.invoke_mode == "BUFFERED"
	r.values.authorization_type == "NONE"
	some f in functions
	f.values.function_name == r.values.function_name
	f.values.reserved_concurrent_executions in {0, 1}
	valid_public_exception(f.values.function_name)
}

deny contains sprintf("Unapproved, unknown or unmatched function URL: %s", [r.address]) if {
	some r in resources
	r.type == "aws_lambda_function_url"
	not valid_url(r)
}

deny contains "Aggregate Lambda count exceeds the allowance" if {
	(count(functions) + count(replacement_functions)) + input.context.other_usage.functions > data.guardrails.max_functions
}

deny contains "Aggregate DynamoDB read capacity exceeds the allowance" if {
	(sum([r.values.read_capacity | some r in tables]) + sum([r.read_capacity | some r in replacement_tables])) + input.context.other_usage.read_capacity > data.guardrails.max_read_capacity
}

deny contains "Aggregate DynamoDB write capacity exceeds the allowance" if {
	(sum([r.values.write_capacity | some r in tables]) + sum([r.write_capacity | some r in replacement_tables])) + input.context.other_usage.write_capacity > data.guardrails.max_write_capacity
}

deny contains "Aggregate alarm count exceeds the allowance" if {
	(count(alarms) + count(replacement_alarms)) + input.context.other_usage.alarms > data.guardrails.max_alarms
}

critical_fields := {
	"aws_lambda_function": {"runtime", "package_type", "handler", "architectures", "memory_size", "timeout", "reserved_concurrent_executions", "ephemeral_storage", "publish", "source_code_hash", "function_name", "role", "tags", "vpc_config"},
	"aws_dynamodb_table": {"billing_mode", "read_capacity", "write_capacity", "hash_key", "global_secondary_index", "replica", "tags"},
	"aws_lambda_function_url": {"function_name", "authorization_type", "invoke_mode"},
	"aws_cloudwatch_log_group": {"retention_in_days", "tags"},
	"aws_cloudwatch_metric_alarm": {"namespace", "metric_name", "period", "alarm_actions", "ok_actions", "insufficient_data_actions", "tags"},
}

deny contains sprintf("Security-critical field remains unknown: %s.%s", [r.address, field]) if {
	some r in input.plan.resource_changes
	some field in critical_fields[r.type]
	walk(object.get(object.get(r.change, "after_unknown", {}), field, false), [path, value])
	value == true
}

deny contains sprintf("Security-critical DynamoDB setting remains unknown: %s", [r.address]) if {
	some r in input.plan.resource_changes
	r.type == "aws_dynamodb_table"
	some field in {"server_side_encryption", "point_in_time_recovery"}
	walk(object.get(object.get(r.change, "after_unknown", {}), field, false), [path, value])
	value == true
	count(path) == 0
}

deny contains sprintf("Security-critical DynamoDB flag remains unknown: %s", [r.address]) if {
	some r in input.plan.resource_changes
	r.type == "aws_dynamodb_table"
	some field in {"server_side_encryption", "point_in_time_recovery"}
	walk(object.get(object.get(r.change, "after_unknown", {}), field, false), [path, value])
	value == true
	path[count(path) - 1] == "enabled"
}

empty_actions(actions) if actions == null

empty_actions(actions) if {
	is_array(actions)
	count(actions) == 0
}
