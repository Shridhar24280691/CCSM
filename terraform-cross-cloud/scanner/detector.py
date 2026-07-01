# detector.py
# Checks normalised resources for security problems
# Two types of checks: per-resource and cross-cloud


def detect(normalised_resources):
    """
    Run all security checks on the normalised resource list.
    Returns a list of findings. Each finding is a dictionary
    describing one security problem found.
    """
    findings = []

    # ── Type 1: Check each resource on its own ──────────────
    for resource in normalised_resources:
        findings = findings + check_single_resource(resource)

    # ── Type 2: Compare AWS and Azure against each other ────
    aws_list   = [r for r in normalised_resources if r["provider"] == "aws"]
    azure_list = [r for r in normalised_resources if r["provider"] == "azure"]

    # Only run cross-cloud checks if both providers are present
    if aws_list and azure_list:
        findings = findings + check_cross_cloud(aws_list, azure_list)

    return findings


def check_single_resource(resource):
    """
    Check one resource for common misconfigurations.
    These are the same checks that Checkov and tfsec perform.
    We include them so we can do a fair comparison.
    """
    findings = []
    attrs = resource["attributes"]
    provider = resource["provider"].upper()
    name = resource["name"]
    location = f"{provider} / {resource['raw_type']} / {name}"

    # Check 1: Is public access blocked?
    if not attrs["public_access_blocked"]:
        findings.append({
            "check":          "PUBLIC_ACCESS_NOT_BLOCKED",
            "severity":       "HIGH",
            "provider":       resource["provider"],
            "resource":       location,
            "problem":        "Public access is not blocked on this storage resource.",
            "recommendation": "Block public access on this resource."
        })

    # Check 2: Is versioning enabled?
    if not attrs["versioning_enabled"]:
        findings.append({
            "check":          "VERSIONING_DISABLED",
            "severity":       "MEDIUM",
            "provider":       resource["provider"],
            "resource":       location,
            "problem":        "Versioning is not enabled.",
            "recommendation": "Enable versioning to protect against accidental deletion."
        })

    # Check 3: Is logging enabled?
    if not attrs["logging_enabled"]:
        findings.append({
            "check":          "LOGGING_DISABLED",
            "severity":       "MEDIUM",
            "provider":       resource["provider"],
            "resource":       location,
            "problem":        "Access logging is not enabled.",
            "recommendation": "Enable access logging on this resource."
        })

    # Check 4: Is TLS version too low? (Azure only)
    tls = attrs.get("tls_min_version", "TLS1_2")
    if isinstance(tls, list):
        tls = tls[0] if tls else "TLS1_2"
    if str(tls) in ("TLS1_0", "TLS1_1"):
        findings.append({
            "check":          "TLS_VERSION_LOW",
            "severity":       "HIGH",
            "provider":       resource["provider"],
            "resource":       location,
            "problem":        f"TLS version is {tls}. Minimum should be TLS1_2.",
            "recommendation": "Set minimum TLS version to TLS1_2."
        })

    return findings


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
    findings = []

    aws_versioning   = any(r["attributes"]["versioning_enabled"] for r in aws_list)
    azure_versioning = any(r["attributes"]["versioning_enabled"] for r in azure_list)

    aws_logging  = any(r["attributes"]["logging_enabled"] for r in aws_list)
    azure_logging = any(r["attributes"]["logging_enabled"] for r in azure_list)

    aws_public_blocked  = all(r["attributes"]["public_access_blocked"] for r in aws_list)
    azure_public_blocked = all(r["attributes"]["public_access_blocked"] for r in azure_list)

    # ── Cross-cloud check 1: Versioning gap (MEDIUM) ────────
    if aws_versioning != azure_versioning:
        if aws_versioning and not azure_versioning:
            problem = (
                "Versioning is enabled on AWS but not on Azure. "
                "A single-cloud tool scanning only AWS would report no problem."
            )
            fix = "Enable versioning on Azure storage account."
        else:
            problem = (
                "Versioning is enabled on Azure but not on AWS. "
                "A single-cloud tool scanning only Azure would report no problem."
            )
            fix = "Add aws_s3_bucket_versioning resource with status Enabled."

        findings.append({
            "check":          "CROSS_CLOUD_VERSIONING_GAP",
            "severity":       "MEDIUM",
            "provider":       "cross-cloud",
            "resource":       "AWS S3 vs Azure Storage",
            "problem":        problem,
            "recommendation": fix
        })

    # ── Cross-cloud check 2: Logging gap (LOW) ──────────────
    if aws_logging != azure_logging:
        if aws_logging and not azure_logging:
            problem = (
                "Logging is enabled on AWS but not on Azure. "
                "A single-cloud tool cannot detect this gap."
            )
            fix = "Enable logging in blob_properties on Azure storage account."
        else:
            problem = (
                "Logging is enabled on Azure but not on AWS. "
                "A single-cloud tool cannot detect this gap."
            )
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
    if aws_public_blocked != azure_public_blocked:
        if aws_public_blocked and not azure_public_blocked:
            problem = (
                "Public access is blocked on AWS but not on Azure. "
                "A single-cloud tool scanning only AWS would pass this entirely."
            )
            fix = "Set allow_nested_items_to_be_public to false on Azure."
        else:
            problem = (
                "Public access is blocked on Azure but not on AWS. "
                "A single-cloud tool scanning only Azure would pass this entirely."
            )
            fix = "Add aws_s3_bucket_public_access_block with all flags set to true."

        findings.append({
            "check":          "CROSS_CLOUD_PUBLIC_ACCESS_GAP",
            "severity":       "HIGH",
            "provider":       "cross-cloud",
            "resource":       "AWS S3 vs Azure Storage",
            "problem":        problem,
            "recommendation": fix
        })

    return findings