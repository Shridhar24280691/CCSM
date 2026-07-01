# parser.py
# Reads .tf files and organises resources into a clean dictionary

import hcl2
from pathlib import Path


def parse_file(filepath):
    # Convert the filepath string into a Path object for safer handling
    path = Path(filepath)

    # Stop if the file does not exist
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    # Stop if it is not a .tf file
    if path.suffix != ".tf":
        raise ValueError(f"Expected a .tf file, got: {filepath}")

    # Open the file and use hcl2 to convert it into a Python dictionary
    with open(path, "r") as f:
        raw = hcl2.load(f)

    # Merge the resource list into a flat dictionary
    # Same logic as parse_directory but for a single file
    merged = {}
    resource_list = raw.get("resource", [])

    for block in resource_list:
        for resource_type, instances in block.items():
            if resource_type not in merged:
                merged[resource_type] = {}
            merged[resource_type].update(instances)

    return merged

def parse_directory(directory):
    # Find all .tf files inside the folder
    folder = Path(directory)
    tf_files = list(folder.glob("*.tf")) # glob returns a generator, so we convert it to a list for easier handling

    # Stop if no .tf files are found
    if not tf_files:
        raise FileNotFoundError(f"No .tf files found in: {directory}")

    # Start with an empty shelf
    merged = {}

    # Read each file and merge into one dictionary
    for tf_file in tf_files:
        with open(tf_file, "r") as f:
            raw = hcl2.load(f)
        # Get the resource list from this file
        resource_list = raw.get("resource", [])

        ''' Example from the resource list in the raw output of a file might look like this:
        [
            {"aws_s3_bucket": {"app_data": {"bucket": ["my-bucket"]}}},
            {"aws_s3_bucket_public_access_block": {"app_data": {"block_public_acls": [True]}}}
        ]'''

        # Loop through each item in the list
        for block in resource_list:
            # Each block has one key (the type) and one value (the instances)
            for resource_type, instances in block.items():

                # Create a new shelf section if this type is new
                if resource_type not in merged:
                    merged[resource_type] = {}

                # Add the instances to the correct shelf section
                merged[resource_type].update(instances)

    return merged

''' Example of the merged output after parsing multiple files might look like this:
{
    "aws_s3_bucket": {
        "app_data": {"bucket": ["g2-05-app-data-aws"]}
    },
    "aws_s3_bucket_public_access_block": {
        "app_data": {
            "block_public_acls": [True],
            "block_public_policy": [True],
            "restrict_public_buckets": [True]
        }
    },
    "azurerm_storage_account": {
        "app_data": {
            "allow_nested_items_to_be_public": [True],
            "blob_properties": [{"versioning_enabled": [True]}]
        }
    }
}
'''