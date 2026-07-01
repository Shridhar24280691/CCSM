# main.py
# Runs the CCSM scanner on every test file in both test groups
# and prints plus saves all the findings.
#
# This works no matter which folder you run "python main.py" from,
# because it locates folders using this file's own location on disk.

import sys
import os
from pathlib import Path
import csv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

from parser import parse_file
from normaliser import normalise
from detector import detect

GROUP1_DIR = SCRIPT_DIR.parent / "terraform_tests" / "group1_individual"
GROUP2_DIR = SCRIPT_DIR.parent / "terraform_tests" / "group2_crosscloud"
RESULTS_DIR = SCRIPT_DIR.parent / "results"


def run_on_each_file():
    all_findings = []
    total_files = 0

    for test_dir in [GROUP1_DIR, GROUP2_DIR]:
        if not test_dir.exists():
            print(f"\n  WARNING: folder not found: {test_dir}")
            continue

        tf_files = sorted(test_dir.glob("*.tf"))
        total_files += len(tf_files)

        for tf_file in tf_files:
            print(f"\n  -- Scanning: {tf_file.name} --")

            resources = parse_file(str(tf_file))
            normalised = normalise(resources)

            if not normalised:
                print(f"  No storage resources found in {tf_file.name}")
                continue

            findings = detect(normalised)

            for finding in findings:
                finding["file"] = tf_file.name

            for finding in findings:
                tag = " [CROSS-CLOUD]" if finding["provider"] == "cross-cloud" else ""
                print(f"    [{finding['severity']}] {finding['check']}{tag}")
                print(f"    Problem: {finding['problem']}")
                print(f"    Fix:     {finding['recommendation']}")
                print()

            all_findings = all_findings + findings

    cross_cloud = [f for f in all_findings if f["provider"] == "cross-cloud"]
    single_cloud = [f for f in all_findings if f["provider"] != "cross-cloud"]

    print("=" * 65)
    print("  SUMMARY ACROSS ALL FILES")
    print("=" * 65)
    print(f"  Total findings     : {len(all_findings)}")
    print(f"  Single-cloud       : {len(single_cloud)}")
    print(f"  Cross-cloud        : {len(cross_cloud)}  (novel contribution)")
    print(f"  Files scanned      : {total_files}")
    print("=" * 65)

    save_results(all_findings)
    return all_findings


def save_results(findings):
    RESULTS_DIR.mkdir(exist_ok=True)
    csv_path = RESULTS_DIR / "ccsm_results.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["file", "check", "severity", "provider",
                        "resource", "problem", "recommendation"]
        )
        writer.writeheader()
        writer.writerows(findings)

    print(f"\n  Results saved to: {csv_path}")


if __name__ == "__main__":
    run_on_each_file()
