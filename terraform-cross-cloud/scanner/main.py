# main.py
# Runs the CCSM scanner on every test file in both test groups
# and prints plus saves all the findings.
# This works no matter which folder you run "python main.py" from,

import sys
import os
from pathlib import Path
import csv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent # Resolves the absolute path of this script file (`__file__`), then takes its parent directory.
sys.path.insert(0, str(SCRIPT_DIR)) 
sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

from parser import parse_file
from normaliser import normalise
from detector import detect

GROUP1_DIR = SCRIPT_DIR.parent / "terraform_tests" / "group1_individual" # Builds an absolute path to the first test group directory
GROUP2_DIR = SCRIPT_DIR.parent / "terraform_tests" / "group2_crosscloud" # Builds an absolute path to the second test group directory
RESULTS_DIR = SCRIPT_DIR.parent / "results" # Builds an absolute path to the results directory


def run_on_each_file(): # Defines the main function that orchestrates scanning all Terraform test files.
    all_findings = [] # Initialises an empty list to collect all findings from all files.
    total_files = 0 # Initialises a counter to keep track of the total number of Terraform files scanned.

    for test_dir in [GROUP1_DIR, GROUP2_DIR]: # Iterates over the two test group directories.
        if not test_dir.exists(): # Checks if the current test directory does not exist on the filesystem.
            print(f"\n  WARNING: folder not found: {test_dir}") 
            continue

        tf_files = sorted(test_dir.glob("*.tf")) # Uses `glob` to find all `.tf` files in the current test directory, then sorts them alphabetically for deterministic ordering.
        total_files += len(tf_files) # Adds the number of Terraform files found in this directory to the running total.

        for tf_file in tf_files: # Iterates over each Terraform file in the sorted list.
            print(f"\n  -- Scanning: {tf_file.name} --")

            resources = parse_file(str(tf_file)) # Calls `parse_file` on the current `.tf` file path to extract raw resource data.
            normalised = normalise(resources) # Calls `normalise` to convert the raw resource data into a standardised format suitable for cross-cloud analysis.

            if not normalised: 
                print(f"  No storage resources found in {tf_file.name}")
                continue

            findings = detect(normalised) # Call the `detect` function on the normalised resources to get security findings.

            for finding in findings: # Iterates over each finding dictionary returned by `detect`.
                finding["file"] = tf_file.name # Adds the filename to each finding dictionary for context.

            for finding in findings: 
                tag = " [CROSS-CLOUD]" if finding["provider"] == "cross-cloud" else "" # Creates a tag string " [CROSS-CLOUD]" if the finding is from the cross-cloud checker, else an empty string for single-cloud findings.
                print(f"    [{finding['severity']}] {finding['check']}{tag}")
                print(f"    Problem: {finding['problem']}")
                print(f"    Fix:     {finding['recommendation']}")
                print()

            all_findings = all_findings + findings # Appends this file's findings to the overall `all_findings` list.

    cross_cloud = [f for f in all_findings if f["provider"] == "cross-cloud"] # Filters `all_findings` to keep only those where provider == "cross-cloud".
    single_cloud = [f for f in all_findings if f["provider"] != "cross-cloud"] # Filters `all_findings` to keep only those where provider != "cross-cloud".

    print("=" * 65)
    print("  SUMMARY ACROSS ALL FILES")
    print("=" * 65)
    print(f"  Total findings     : {len(all_findings)}")
    print(f"  Single-cloud       : {len(single_cloud)}")
    print(f"  Cross-cloud        : {len(cross_cloud)}  (novel contribution)")
    print(f"  Files scanned      : {total_files}")
    print("=" * 65)

    save_results(all_findings) # Call `save_results` to write all findings to a CSV file in the results directory.
    return all_findings 


def save_results(findings):
    RESULTS_DIR.mkdir(exist_ok=True) # Ensures the `RESULTS_DIR` directory exists; `exist_ok=True` means "don't error if it already exists".
    csv_path = RESULTS_DIR / "ccsm_results.csv" # Constructs the full path to the CSV file where results will be saved.

    with open(csv_path, "w", newline="", encoding="utf-8") as f: 
        writer = csv.DictWriter( # Creates a `DictWriter` object that writes dictionaries as CSV rows.
            f,    # The file object to write to.
            fieldnames=["file", "check", "severity", "provider",
                        "resource", "problem", "recommendation"] 
        ) # Specifies the CSV column order and names, matching the keys in each finding dict.
        writer.writeheader()
        writer.writerows(findings)

    print(f"\n  Results saved to: {csv_path}")


if __name__ == "__main__":
    run_on_each_file()
