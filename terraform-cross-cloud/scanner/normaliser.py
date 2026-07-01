# normaliser.py
# Converts AWS and Azure Terraform resources into a single common format

''' Algorithm for normalising storage resources:
1. Go through every resource the parser found
2. If it is an AWS S3 bucket:
   a. Look up its public access block (a separate resource)
   b. Look up its versioning setting (another separate resource)
   c. Look up its logging setting (another separate resource)
   d. Combine all of these into one summary card
3. If it is an Azure storage account:
   a. Read the public access settings from the resource itself
   b. Read the versioning setting from inside blob_properties
   c. Read the logging setting from inside blob_properties
   d. Combine all of these into one summary card
4. Every summary card has the SAME four keys regardless of provider
5. Return all the summary cards in a list
'''

def normalise(resources):
    # Start with empty list — we will add one card per storage resource
    result = []

    # Loop through every resource type on the shelf (e.g. "aws_s3_bucket")
    for resource_type, instances in resources.items():

        # Loop through every named resource of that type (e.g. "app_data")
        for name, config in instances.items():

            # If it is an AWS S3 bucket, build an AWS summary card
            if resource_type == "aws_s3_bucket":
                result.append(normalise_aws(name, resources))

            # If it is an Azure Storage Account, build an Azure summary card
            elif resource_type == "azurerm_storage_account":
                result.append(normalise_azure(name, config))

    # Return the list of all summary cards
    return result


def to_bool(value):
    # python-hcl2 sometimes wraps values in a list — unwrap it first
    if isinstance(value, list):
        value = value[0] if value else False

    # If the value is a string like "true" or "false", convert it properly
    if isinstance(value, str):
        return value.lower() == "true"

    # For everything else (actual booleans, None, numbers) use Python's bool()
    return bool(value)


def first_item(value):
    # python-hcl2 wraps blocks in lists — if it is a list, return the first item
    if isinstance(value, list):
        return value[0] if value else {}

    # If it is already a dict, return it as-is
    return value


def normalise_aws(name, resources):
    # Start by assuming all security settings are OFF
    # We only change to True when we find proof they are ON
    public_access_blocked = False
    versioning_enabled = False
    logging_enabled = False

    # --- CHECK PUBLIC ACCESS ---
    # AWS stores public access settings in a separate resource
    public_blocks = resources.get("aws_s3_bucket_public_access_block", {})

    for block in public_blocks.values():
        # Check if this public access block belongs to our bucket
        if name in str(block.get("bucket", "")):
            # All three flags must be True for the bucket to be fully blocked
            public_access_blocked = (
                to_bool(block.get("block_public_acls"))
                and to_bool(block.get("block_public_policy"))
                and to_bool(block.get("restrict_public_buckets"))
            )

    # --- CHECK VERSIONING ---
    # AWS stores versioning in a separate resource
    versioning_resources = resources.get("aws_s3_bucket_versioning", {})

    for version in versioning_resources.values():
        # Check if this versioning block belongs to our bucket
        if name in str(version.get("bucket", "")):
            # versioning_configuration may be wrapped in a list by hcl2
            config = first_item(version.get("versioning_configuration", {}))
            status = config.get("status", "")
            # python-hcl2 may wrap scalar values in a list — unwrap if needed
            if isinstance(status, list):
                status = status[0] if status else ""
            # Versioning is enabled only if status says "Enabled"
            versioning_enabled = str(status).lower() == "enabled"

    # --- CHECK LOGGING ---
    # AWS stores logging in a separate resource
    logging_resources = resources.get("aws_s3_bucket_logging", {})

    for log in logging_resources.values():
        # If a logging resource exists for our bucket, logging is ON
        if name in str(log.get("bucket", "")):
            logging_enabled = True

    # Return the AWS summary card in the unified format
    return {
        "provider": "aws",
        "name": name,
        "raw_type": "aws_s3_bucket",
        "attributes": {
            "public_access_blocked": public_access_blocked,
            "versioning_enabled": versioning_enabled,
            "logging_enabled": logging_enabled,
            "tls_min_version": "TLS1_2"   # AWS does not use this attribute
        }
    }


def normalise_azure(name, config):
    # --- CHECK PUBLIC ACCESS ---
    # Azure uses two settings to control public access
    # Default is True (public allowed) — safest assumption if not specified
    allow_public = config.get("allow_nested_items_to_be_public", True)
    network_access = config.get("public_network_access_enabled", True)

    # Both must be False for the bucket to be fully blocked
    public_access_blocked = (
        not to_bool(allow_public)
        and not to_bool(network_access)
    )

    # --- GET BLOB PROPERTIES SECTION ---
    # All blob settings (versioning, logging) live inside blob_properties
    # Use first_item because hcl2 may wrap it in a list
    blob = first_item(config.get("blob_properties", {}))

    # --- CHECK VERSIONING ---
    versioning_enabled = to_bool(blob.get("versioning_enabled", False))

    # --- CHECK LOGGING ---
    # If the logging block exists and has content, logging is ON
    logging_enabled = bool(blob.get("logging"))

    # --- CHECK TLS VERSION ---
    tls_min_version = config.get("min_tls_version", "TLS1_2")

    # Return the Azure summary card in the unified format
    return {
        "provider": "azure",
        "name": name,
        "raw_type": "azurerm_storage_account",
        "attributes": {
            "public_access_blocked": public_access_blocked,
            "versioning_enabled": versioning_enabled,
            "logging_enabled": logging_enabled,
            "tls_min_version": tls_min_version
        }
    }