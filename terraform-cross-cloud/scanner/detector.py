# detector.py
# Checks normalised resources for security problems
# Two types of checks: per-resource and cross-cloud


def detect(normalised_resources):
    findings = []# Initialises an empty list to collect all security findings that will be returned.

    # Type 1: Check each resource on its own
    for resource in normalised_resources:# Iterates over every normalised resource dictionary in the input list.
        findings = findings + check_single_resource(resource) # Calls `check_single_resource` for the current resource and appends any findings it returns to the `findings` list.

    # Type 2: Compare AWS and Azure against each other
    aws_list   = [r for r in normalised_resources if r["provider"] == "aws"] # Builds a list of all resources whose "provider" field is "aws".
    azure_list = [r for r in normalised_resources if r["provider"] == "azure"]  #  Builds a list of all resources whose "provider" field is "azure".

    # Only run cross-cloud checks if both providers are present
    if aws_list and azure_list:  # Checks that both `aws_list` and `azure_list` are non-empty (i.e., both clouds are represented).
        findings = findings + check_cross_cloud(aws_list, azure_list) # Calls `check_cross_cloud` with the AWS and Azure resource lists and appends any cross-cloud findings to `findings`.

    return findings


def check_single_resource(resource):
    findings = [] # Initialises an empty list to hold findings specific to this one resource.
    attrs = resource["attributes"] # Extracts the "attributes" dictionary from the resource for easier access to fields like logging, versioning, etc.
    provider = resource["provider"].upper()  # Gets the provider name (e.g., "aws", "azure") and converts it to uppercase for display purposes.
    name = resource["name"] # Extracts the resource's name (e.g., bucket name, storage account name).
    location = f"{provider} / {resource['raw_type']} / {name}" # Builds a human-readable identifier for the resource, e.g. "AWS / s3_bucket / my-bucket", used in findings.

    # Check 1: Is public access blocked?
    if not attrs["public_access_blocked"]: # Checks if the "public_access_blocked" attribute is False (i.e., public access is NOT blocked).
        findings.append({ # If public access is not blocked, appends a new finding dictionary to the `findings` list.
            "check":          "PUBLIC_ACCESS_NOT_BLOCKED",
            "severity":       "HIGH",
            "provider":       resource["provider"],
            "resource":       location,
            "problem":        "Public access is not blocked on this storage resource.",
            "recommendation": "Block public access on this resource."
        })

    # Check 2: Is versioning enabled?
    if not attrs["versioning_enabled"]: # Checks if the "versioning_enabled" attribute is False (i.e., versioning is NOT enabled).
        findings.append({ # If versioning is not enabled, appends a new finding dictionary to the `findings` list.
            "check":          "VERSIONING_DISABLED",
            "severity":       "MEDIUM",
            "provider":       resource["provider"],
            "resource":       location,
            "problem":        "Versioning is not enabled.",
            "recommendation": "Enable versioning to protect against accidental deletion."
        })

    # Check 3: Is logging enabled?
    if not attrs["logging_enabled"]: # Checks if the "logging_enabled" attribute is False (i.e., logging is NOT enabled).
        findings.append({ # If logging is not enabled, appends a new finding dictionary to the `findings` list.
            "check":          "LOGGING_DISABLED",
            "severity":       "MEDIUM",
            "provider":       resource["provider"],
            "resource":       location,
            "problem":        "Access logging is not enabled.",
            "recommendation": "Enable access logging on this resource."
        })

    # Check 4: Is TLS version too low? (Azure only)
    tls = attrs.get("tls_min_version", "TLS1_2") # Safely gets the "tls_min_version" attribute; defaults to "TLS1_2" if not present.
    if isinstance(tls, list):
        tls = tls[0] if tls else "TLS1_2" # If the list is non-empty, take the first element; otherwise default to "TLS1_2".
    if str(tls) in ("TLS1_0", "TLS1_1"):
        findings.append({ # If TLS is too low, appends a new finding.
            "check":          "TLS_VERSION_LOW",
            "severity":       "HIGH",
            "provider":       resource["provider"],
            "resource":       location,
            "problem":        f"TLS version is {tls}. Minimum should be TLS1_2.",
            "recommendation": "Set minimum TLS version to TLS1_2."
        })

    return findings # Returns the list of findings for this single resource to the caller (`detect`).


def check_cross_cloud(aws_list, azure_list):
    """
    Compare AWS and Azure resources for security policy inconsistencies.

    THIS IS THE NOVEL CONTRIBUTION.
    Checkov and tfsec cannot do this because they have no shared model.
    This function only works because the normaliser already converted
    both clouds into the same attribute names.

    Severity levels for cross-cloud checks:
      HIGH   - public access gap (data exposed to the internet)
      MEDIUM - versioning gap (inconsistent data protection)
      LOW    - logging gap (inconsistent audit trail)
    """
    findings = [] # Initialises an empty list to hold cross-cloud findings.

    aws_versioning   = any(r["attributes"]["versioning_enabled"] for r in aws_list) # Computes a boolean: True if ANY AWS resource has versioning enabled.
    azure_versioning = any(r["attributes"]["versioning_enabled"] for r in azure_list)  # Computes a boolean: True if ANY Azure resource has versioning enabled.

    aws_logging  = any(r["attributes"]["logging_enabled"] for r in aws_list) # Computes a boolean: True if ANY AWS resource has logging enabled.
    azure_logging = any(r["attributes"]["logging_enabled"] for r in azure_list) # Computes a boolean: True if ANY Azure resource has logging enabled.

    aws_public_blocked  = all(r["attributes"]["public_access_blocked"] for r in aws_list) # Computes a boolean: True if ALL AWS resources have public access blocked.
    azure_public_blocked = all(r["attributes"]["public_access_blocked"] for r in azure_list) # Computes a boolean: True if ALL Azure resources have public access blocked.

    # Type 1: Cross-cloud check 1: Versioning gap (MEDIUM)
    if aws_versioning != azure_versioning: # Checks whether versioning enablement differs between AWS and Azure.
        if aws_versioning and not azure_versioning: # Case: versioning is enabled on AWS but not on Azure.
            problem = (
                "Versioning is enabled on AWS but not on Azure. "
                "A single-cloud tool scanning only AWS would report no problem."
            ) # Describes the inconsistency and why a single-cloud scanner would miss it.
            fix = "Enable versioning on Azure storage account."
        else:# Case: versioning is enabled on Azure but not on AWS.
            problem = (
                "Versioning is enabled on Azure but not on AWS. "
                "A single-cloud tool scanning only Azure would report no problem."
            ) # Describes the inconsistency from the other direction.
            fix = "Add aws_s3_bucket_versioning resource with status Enabled."

        findings.append({
            "check":          "CROSS_CLOUD_VERSIONING_GAP",
            "severity":       "MEDIUM",
            "provider":       "cross-cloud",
            "resource":       "AWS S3 vs Azure Storage",
            "problem":        problem,
            "recommendation": fix
        })

    # Type 2: Cross-cloud check 2: Logging gap (LOW) ──────────────
    if aws_logging != azure_logging: # Checks whether logging enablement differs between AWS and Azure.
        if aws_logging and not azure_logging: # Case: logging is enabled on AWS but not on Azure.
            problem = (
                "Logging is enabled on AWS but not on Azure. "
                "A single-cloud tool cannot detect this gap."
            )# Describes the inconsistency and limitation of single-cloud tools.
            fix = "Enable logging in blob_properties on Azure storage account."
        else: # Case: logging enabled on Azure but not on AWS.
            problem = (
                "Logging is enabled on Azure but not on AWS. "
                "A single-cloud tool cannot detect this gap."
            ) # Describes the inconsistency from the other direction.
            fix = "Add aws_s3_bucket_logging resource for the S3 bucket."

        findings.append({
            "check":          "CROSS_CLOUD_LOGGING_GAP",
            "severity":       "LOW",
            "provider":       "cross-cloud",
            "resource":       "AWS S3 vs Azure Storage",
            "problem":        problem,
            "recommendation": fix
        })

    # ── Cross-cloud check 3: Public access gap (HIGH) ───────
    if aws_public_blocked != azure_public_blocked: # Checks whether public access blocking differs between AWS and Azure.
        if aws_public_blocked and not azure_public_blocked: # Case: public access is blocked on AWS but not on Azure.
            problem = ( 
                "Public access is blocked on AWS but not on Azure. "
                "A single-cloud tool scanning only AWS would pass this entirely."
            ) # Describes the risk and why a single-cloud AWS scan would miss it.
            fix = "Set allow_nested_items_to_be_public to false on Azure."
        else:
            problem = (
                "Public access is blocked on Azure but not on AWS. "
                "A single-cloud tool scanning only Azure would pass this entirely."
            ) # Describes the risk and why a single-cloud Azure scan would miss it.
            fix = "Add aws_s3_bucket_public_access_block with all flags set to true."

        findings.append({ # Appends a cross-cloud finding for the public access gap.
            "check":          "CROSS_CLOUD_PUBLIC_ACCESS_GAP",
            "severity":       "HIGH",
            "provider":       "cross-cloud",
            "resource":       "AWS S3 vs Azure Storage",
            "problem":        problem,
            "recommendation": fix
        })

    return findings # Returns the list of cross-cloud findings to the caller (`detect`).