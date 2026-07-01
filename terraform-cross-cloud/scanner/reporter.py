# reporter.py
# Prints findings in a readable format and saves to CSV

import csv


def print_report(findings, directory):
    """
    Print all findings to the terminal in a clean format.
    Groups findings by severity so the most serious ones appear first.
    """
    print("\n" + "=" * 65)
    print(f"  CCSM Scanner Results — {directory}")
    print("=" * 65)

    if not findings:
        print("\n  No misconfigurations found.\n")
        return

    # Count findings by severity
    high   = [f for f in findings if f["severity"] == "HIGH"]
    medium = [f for f in findings if f["severity"] == "MEDIUM"]
    low    = [f for f in findings if f["severity"] == "LOW"]

    # Count cross-cloud findings separately
    cross_cloud = [f for f in findings if f["provider"] == "cross-cloud"]
    single_cloud = [f for f in findings if f["provider"] != "cross-cloud"]

    print(f"\n  Total findings     : {len(findings)}")
    print(f"  Single-cloud       : {len(single_cloud)}  (same as Checkov/tfsec)")
    print(f"  Cross-cloud        : {len(cross_cloud)}  (only this tool detects these)")
    print(f"  HIGH: {len(high)}   MEDIUM: {len(medium)}   LOW: {len(low)}")

    # Print findings grouped by severity
    for severity_label, group in [("HIGH", high), ("MEDIUM", medium), ("LOW", low)]:
        if not group:
            continue

        print(f"\n  ── {severity_label} ──")

        for finding in group:
            tag = " [CROSS-CLOUD]" if finding["provider"] == "cross-cloud" else ""
            print(f"\n  [{finding['check']}]{tag}")
            print(f"  Resource : {finding['resource']}")
            print(f"  Problem  : {finding['problem']}")
            print(f"  Fix      : {finding['recommendation']}")

    print("\n" + "=" * 65 + "\n")


def save_csv(findings, output_path):
    """
    Save findings to a CSV file.
    This is used to build the comparison table in your dissertation.
    """
    with open(output_path, "w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["check", "severity", "provider", "resource",
                        "problem", "recommendation"]
        )
        writer.writeheader()
        writer.writerows(findings)

    print(f"  Results saved to: {output_path}")