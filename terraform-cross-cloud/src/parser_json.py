"""
parser_json.py - Terraform Plan JSON Parser

Reads Terraform plan JSON output (from `terraform show -json`) and extracts
AWS S3 bucket and Azure Storage Account resource configurations.

This module handles the second input mode of the tool: Terraform plan JSON.
This enables CI/CD pipeline integration where plan output is available.
"""

import json
import os


def parse_plan_json(filepath):
    """
    Parse a Terraform plan JSON file and extract all resource blocks.

    The JSON output from `terraform show -json` contains planned resource
    configurations under planned_values.root_module.resources.

    Args:
        filepath (str): Path to the JSON file.

    Returns:
        dict: A dictionary with resource types as keys and lists of
              resource configurations as values.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        plan = json.load(f)

    resources = {}

    # Navigate to the planned resources
    planned_values = plan.get("planned_values", {})
    root_module = planned_values.get("root_module", {})
    resource_list = root_module.get("resources", [])

    # Also check for child modules (modules can nest resources)
    child_modules = root_module.get("child_modules", [])
    for child in child_modules:
        resource_list.extend(child.get("resources", []))

    for resource in resource_list:
        resource_type = resource.get("type", "")
        resource_name = resource.get("name", "unknown")
        values = resource.get("values", {})

        entry = dict(values)
        entry["__name__"] = resource_name
        entry["__type__"] = resource_type

        if resource_type not in resources:
            resources[resource_type] = []
        resources[resource_type].append(entry)

    return resources


def extract_aws_s3_from_plan(resources):
    """
    Extract and group AWS S3 bucket resources from Terraform plan JSON.

    The plan JSON has the same resource structure as HCL but with resolved
    values, making extraction simpler.

    Args:
        resources (dict): Parsed resources from parse_plan_json.

    Returns:
        list: List of S3 bucket configurations with all settings merged.
    """
    buckets = {}

    # Step 1: Identify all base S3 buckets
    for bucket in resources.get("aws_s3_bucket", []):
        name = bucket.get("__name__", "unknown")
        buckets[name] = {
            "resource_name": name,
            "provider": "aws",
            "bucket_name": bucket.get("bucket", ""),
            "public_access_block": None,
            "encryption": None,
            "logging": None,
            "versioning": None,
        }

    # Step 2: Attach public access block
    for pab in resources.get("aws_s3_bucket_public_access_block", []):
        name = pab.get("__name__", "unknown")
        if name in buckets:
            buckets[name]["public_access_block"] = {
                "block_public_acls": pab.get("block_public_acls", False),
                "block_public_policy": pab.get("block_public_policy", False),
                "ignore_public_acls": pab.get("ignore_public_acls", False),
                "restrict_public_buckets": pab.get("restrict_public_buckets", False),
            }

    # Step 3: Attach encryption settings
    for enc in resources.get("aws_s3_bucket_server_side_encryption_configuration", []):
        name = enc.get("__name__", "unknown")
        if name in buckets:
            rules = enc.get("rule", [])
            if rules:
                rule = rules[0] if isinstance(rules, list) else rules
                default_enc = rule.get("apply_server_side_encryption_by_default", {})
                if isinstance(default_enc, list) and default_enc:
                    default_enc = default_enc[0]
                buckets[name]["encryption"] = {
                    "sse_algorithm": default_enc.get("sse_algorithm", "") if default_enc else "",
                }

    # Step 4: Attach logging settings
    for log in resources.get("aws_s3_bucket_logging", []):
        name = log.get("__name__", "unknown")
        if name in buckets:
            buckets[name]["logging"] = {
                "target_bucket": log.get("target_bucket", ""),
                "target_prefix": log.get("target_prefix", ""),
            }

    # Step 5: Attach versioning settings
    for ver in resources.get("aws_s3_bucket_versioning", []):
        name = ver.get("__name__", "unknown")
        if name in buckets:
            ver_config = ver.get("versioning_configuration", [])
            if ver_config:
                vc = ver_config[0] if isinstance(ver_config, list) else ver_config
                buckets[name]["versioning"] = {
                    "status": vc.get("status", "Disabled"),
                }

    return list(buckets.values())


def extract_azure_storage_from_plan(resources):
    """
    Extract Azure Storage Account resources from Terraform plan JSON.

    Args:
        resources (dict): Parsed resources from parse_plan_json.

    Returns:
        list: List of Azure storage account configurations.
    """
    accounts = []

    for account in resources.get("azurerm_storage_account", []):
        name = account.get("__name__", "unknown")

        # Extract blob_properties
        blob_props = account.get("blob_properties", [])
        if isinstance(blob_props, list) and blob_props:
            blob_props = blob_props[0]
        elif not isinstance(blob_props, dict):
            blob_props = {}

        # Extract logging
        logging_config = blob_props.get("logging", [])
        if isinstance(logging_config, list) and logging_config:
            logging_config = logging_config[0]
        elif not isinstance(logging_config, dict):
            logging_config = None

        # Extract versioning
        versioning_enabled = blob_props.get("versioning_enabled", False)

        accounts.append({
            "resource_name": name,
            "provider": "azure",
            "account_name": account.get("name", ""),
            "public_access": account.get("allow_nested_items_to_be_public", True),
            "min_tls_version": account.get("min_tls_version", None),
            "infrastructure_encryption": account.get("infrastructure_encryption_enabled", None),
            "logging": logging_config,
            "versioning_enabled": versioning_enabled,
        })

    return accounts


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python parser_json.py <path_to_plan_json>")
        sys.exit(1)

    filepath = sys.argv[1]
    resources = parse_plan_json(filepath)

    print("\n=== Parsed Resources (from plan JSON) ===")
    print(json.dumps(resources, indent=2, default=str))

    print("\n=== AWS S3 Resources ===")
    aws_resources = extract_aws_s3_from_plan(resources)
    print(json.dumps(aws_resources, indent=2, default=str))

    print("\n=== Azure Storage Resources ===")
    azure_resources = extract_azure_storage_from_plan(resources)
    print(json.dumps(azure_resources, indent=2, default=str))
