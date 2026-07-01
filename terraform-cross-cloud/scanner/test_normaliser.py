
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parser import parse_directory
from normaliser import normalise

# path of testing folders
TEST_DIR = "../terraform_tests/group2_crosscloud"


def separator(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ── Step 1: Show raw parser output ──────────────────────────
separator("RAW PARSER OUTPUT (provider-specific, not comparable)")
raw = parse_directory(TEST_DIR)

for resource_type, instances in raw.items():
    if resource_type in (
        "aws_s3_bucket",
        "azurerm_storage_account",
        "aws_s3_bucket_public_access_block",
        "aws_s3_bucket_versioning",
    ):
        for name, config in instances.items():
            print(f"\n  resource_type : {resource_type}")
            print(f"  name          : {name}")
            print(f"  raw keys      : {list(config.keys())}")


# ── Step 2: Show normalised output ──────────────────────────
separator("NORMALISED OUTPUT (unified model — same keys for AWS and Azure)")
normalised = normalise(raw)

for resource in normalised:
    print(f"\n  provider  : {resource['provider']}")
    print(f"  name      : {resource['name']}")
    print(f"  raw_type  : {resource['raw_type']}")
    print(f"  attributes:")
    for k, v in resource["attributes"].items():
        print(f"    {k:<25} = {v}")


# ── Step 3: Show what cross-cloud comparison is now possible ─
separator("WHAT CROSS-CLOUD COMPARISON IS NOW POSSIBLE")
# With the normalised output, we can now directly compare attributes across clouds.
aws   = [r for r in normalised if r["provider"] == "aws"]
azure = [r for r in normalised if r["provider"] == "azure"]

if aws and azure:
    print("\n  Both AWS and Azure resources found in the same directory.")
    print("  Comparing versioning settings across clouds:\n")

    aws_v   = any(r["attributes"]["versioning_enabled"] for r in aws)
    azure_v = any(r["attributes"]["versioning_enabled"] for r in azure)

    print(f"    AWS versioning enabled   : {aws_v}")
    print(f"    Azure versioning enabled : {azure_v}")

    if aws_v != azure_v:
        print("\n  *** INCONSISTENCY DETECTED ***")
        print("  AWS and Azure have different versioning settings.")
        print("  Checkov and tfsec CANNOT detect this because they")
        print("  run separate rule sets per provider with no shared model.")
    else:
        print(f"\n  Both clouds agree: versioning = {aws_v}")

    print("\n  Comparing public access settings:\n")
    aws_pub   = all(r["attributes"]["public_access_blocked"] for r in aws)
    azure_pub = all(r["attributes"]["public_access_blocked"] for r in azure)

    print(f"    AWS public access blocked   : {aws_pub}")
    print(f"    Azure public access blocked : {azure_pub}")

    if aws_pub != azure_pub:
        print("\n  *** INCONSISTENCY DETECTED ***")
        print("  AWS is correctly locked down but Azure is not.")
        print("  A single-cloud tool scanning only AWS would PASS this file.")
    else:
        print(f"\n  Both clouds agree: public_access_blocked = {aws_pub}")

else:
    print("\n  Only one provider found. No cross-cloud comparison possible.")
    print("  Try running on group2_crosscloud/ to see the comparison.")