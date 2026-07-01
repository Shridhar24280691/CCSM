# run_comparison.py
# Runs CCSM, Checkov, and tfsec on every test file in both groups
# and builds a visual HTML comparison report.
#
# This works no matter which folder you run "python run_comparison.py"
# from, because it locates folders using this file's own location.

import sys
import os
import subprocess
import json
from pathlib import Path

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


def run_ccsm_on_file(filepath):
    resources = parse_file(filepath)
    normalised = normalise(resources)
    if not normalised:
        return []
    return detect(normalised)


def run_checkov_on_file(filepath):
    try:
        result = subprocess.run(
            f'checkov -f "{filepath}" --framework terraform -o json --quiet --compact',
            capture_output=True, text=True, timeout=120, shell=True
        )
        output = result.stdout.strip()
        if not output:
            return {"total": 0, "aws": 0, "azure": 0}

        json_start = output.find("{")
        if json_start == -1:
            return {"total": 0, "aws": 0, "azure": 0}
        output = output[json_start:]

        # Checkov sometimes prints two JSON objects back to back.
        # Count braces to cut off after the first complete object.
        data = None
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            depth = 0
            end_pos = 0
            for i, char in enumerate(output):
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        end_pos = i + 1
                        break
            if end_pos > 0:
                try:
                    data = json.loads(output[:end_pos])
                except json.JSONDecodeError:
                    return {"total": 0, "aws": 0, "azure": 0}

        if data is None:
            return {"total": 0, "aws": 0, "azure": 0}

        results_list = data if isinstance(data, list) else [data]

        failed_checks = []
        aws_count = 0
        azure_count = 0
        for block in results_list:
            failed = block.get("results", {}).get("failed_checks", [])
            for check in failed:
                check_id = check.get("check_id", "")
                failed_checks.append(check_id)
                if "aws" in check_id.lower():
                    aws_count += 1
                elif "azure" in check_id.lower():
                    azure_count += 1

        return {"total": len(failed_checks), "aws": aws_count, "azure": azure_count}

    except Exception as e:
        print(f"    Checkov error: {e}")
        return {"total": 0, "aws": 0, "azure": 0}


def run_tfsec_on_file(filepath):
    try:
        # tfsec scans a directory, not a single file, so we scan the
        # parent folder and then keep only results for this filename.
        file_dir = str(Path(filepath).parent)
        result = subprocess.run(
            f'tfsec "{file_dir}" --format json --no-colour',
            capture_output=True, text=True, timeout=120, shell=True
        )
        output = result.stdout.strip() or result.stderr.strip()
        if not output:
            return {"total": 0, "aws": 0, "azure": 0}

        json_start = output.find("{")
        json_end = output.rfind("}")
        if json_start == -1 or json_end == -1:
            return {"total": 0, "aws": 0, "azure": 0}

        data = json.loads(output[json_start:json_end + 1])
        results = data.get("results") or []

        filename = Path(filepath).name
        aws_count = 0
        azure_count = 0
        file_results = []
        for r in results:
            result_file = r.get("location", {}).get("filename", "")
            if filename not in result_file:
                continue
            rule_id = r.get("rule_id", "")
            file_results.append(rule_id)
            if "aws" in rule_id.lower():
                aws_count += 1
            elif "azure" in rule_id.lower():
                azure_count += 1

        return {"total": len(file_results), "aws": aws_count, "azure": azure_count}

    except Exception as e:
        print(f"    tfsec error: {e}")
        return {"total": 0, "aws": 0, "azure": 0}


def collect_all_results():
    all_results = {}

    for group_name, test_dir in [("Group 1", GROUP1_DIR), ("Group 2", GROUP2_DIR)]:
        if not test_dir.exists():
            print(f"\n  WARNING: folder not found: {test_dir}")
            continue

        tf_files = sorted(test_dir.glob("*.tf"))

        for tf_file in tf_files:
            filename = tf_file.name
            filepath = str(tf_file)

            print(f"\n  Scanning: {filename}")

            print("    Running CCSM...")
            ccsm_findings = run_ccsm_on_file(filepath)
            ccsm_single = [f for f in ccsm_findings if f["provider"] != "cross-cloud"]
            ccsm_cross = [f for f in ccsm_findings if f["provider"] == "cross-cloud"]

            print("    Running Checkov...")
            checkov = run_checkov_on_file(filepath)

            print("    Running tfsec...")
            tfsec = run_tfsec_on_file(filepath)

            all_results[filename] = {
                "group": group_name,
                "ccsm_single": len(ccsm_single),
                "ccsm_cross": len(ccsm_cross),
                "ccsm_total": len(ccsm_findings),
                "ccsm_findings": ccsm_findings,
                "checkov_total": checkov["total"],
                "tfsec_total": tfsec["total"],
            }

            print(f"    CCSM: {len(ccsm_single)} single + {len(ccsm_cross)} cross-cloud")
            print(f"    Checkov: {checkov['total']} findings")
            print(f"    tfsec: {tfsec['total']} findings")

    return all_results


def severity_badge_colors(severity):
    """Returns (background_color, text_color) for a given severity level."""
    if severity == "HIGH":
        return "#ffebee", "#c62828"
    elif severity == "MEDIUM":
        return "#fff3e0", "#e65100"
    else:
        return "#fffde7", "#f57f17"


def build_html(all_results):
    files = sorted(all_results.keys())

    total_checkov = sum(r["checkov_total"] for r in all_results.values())
    total_tfsec = sum(r["tfsec_total"] for r in all_results.values())
    total_ccsm_single = sum(r["ccsm_single"] for r in all_results.values())
    total_ccsm_cross = sum(r["ccsm_cross"] for r in all_results.values())
    total_ccsm = sum(r["ccsm_total"] for r in all_results.values())

    table_rows = ""
    for filename in files:
        r = all_results[filename]
        short = filename.replace(".tf", "").replace("_", " ")
        cross_bg = "#e8f5e9" if r["ccsm_cross"] > 0 else "#fff"
        cross_color = "#2e7d32" if r["ccsm_cross"] > 0 else "#333"

        table_rows += f"""
        <tr>
            <td style="text-align:left; padding:8px 12px; font-size:11px; color:#888;">{r['group']}</td>
            <td style="text-align:left; padding:8px 12px; font-weight:500;">{short}</td>
            <td style="padding:8px 12px;">{r['checkov_total']}</td>
            <td style="padding:8px 12px;">{r['tfsec_total']}</td>
            <td style="padding:8px 12px;">{r['ccsm_single']}</td>
            <td style="padding:8px 12px; background:{cross_bg}; color:{cross_color}; font-weight:600;">{r['ccsm_cross']}</td>
        </tr>"""

    # Cross-cloud finding cards, each badge reads the REAL severity
    finding_cards = ""
    for filename in files:
        r = all_results[filename]
        for f in r["ccsm_findings"]:
            if f["provider"] == "cross-cloud":
                severity = f.get("severity", "HIGH")
                sev_bg, sev_color = severity_badge_colors(severity)
                finding_cards += f"""
    <div style="background:white; border-left:4px solid #2e7d32; padding:16px; margin:12px 0;
                border-radius:0 8px 8px 0; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <span style="background:{sev_bg}; color:{sev_color}; padding:2px 8px; border-radius:4px;
                     font-size:11px; font-weight:600;">{severity}</span>
        <span style="background:#e8f5e9; color:#2e7d32; padding:2px 8px; border-radius:4px;
                     font-size:11px; font-weight:600; margin-left:4px;">CROSS-CLOUD</span>
        <strong style="margin-left:8px;">{f['check']}</strong>
        <br><span style="color:#666; font-size:13px;">File: {filename}</span>
        <br><br>
        <strong>Problem:</strong> {f['problem']}<br>
        <strong>Fix:</strong> {f['recommendation']}
    </div>"""

    if not finding_cards:
        finding_cards = "<p>No cross-cloud findings.</p>"

    max_val = max(total_checkov, total_tfsec, total_ccsm, 1)
    checkov_width = int(total_checkov / max_val * 100)
    tfsec_width = int(total_tfsec / max_val * 100)
    ccsm_single_width = int(total_ccsm_single / max_val * 100)
    ccsm_cross_width = max(int(total_ccsm_cross / max_val * 100), 8)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>CCSM Scanner - Comparison Report</title>
<style>
body {{ font-family: -apple-system, Arial, sans-serif; max-width:1100px; margin:40px auto; padding:0 20px; background:#fafafa; color:#333; }}
h1 {{ font-size:24px; font-weight:600; border-bottom:2px solid #1976d2; padding-bottom:10px; }}
h2 {{ font-size:18px; font-weight:600; margin-top:40px; color:#1976d2; }}
.grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin:24px 0; }}
.card {{ background:white; border-radius:8px; padding:20px; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.1); }}
.card .num {{ font-size:36px; font-weight:700; margin:8px 0; }}
.card .lbl {{ font-size:13px; color:#666; }}
table {{ width:100%; border-collapse:collapse; background:white; border-radius:8px; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,0.1); margin:20px 0; }}
th {{ background:#1976d2; color:white; padding:10px 12px; text-align:center; font-weight:500; font-size:12px; }}
td {{ text-align:center; border-bottom:1px solid #eee; font-size:13px; }}
.bar-row {{ display:flex; align-items:center; gap:12px; margin:8px 0; }}
.bar-lbl {{ width:120px; text-align:right; font-size:13px; font-weight:500; }}
.bar-track {{ flex:1; height:28px; background:#eee; border-radius:4px; }}
.bar-fill {{ height:100%; border-radius:4px; display:flex; align-items:center; padding-left:8px; font-size:12px; font-weight:600; color:white; min-width:30px; }}
.keybox {{ background:#e3f2fd; border-radius:8px; padding:16px 20px; margin:20px 0; font-size:14px; line-height:1.6; }}
.section {{ background:white; padding:24px; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.1); margin:20px 0; }}
</style>
</head>
<body>

<h1>Cross-Cloud Storage Misconfiguration Scanner - Results</h1>
<p>Comparison of Checkov, tfsec, and CCSM across {len(files)} Terraform test files (Group 1: single-cloud, Group 2: cross-cloud).</p>

<h2>Summary</h2>
<div class="grid">
    <div class="card"><div class="lbl">Files scanned</div><div class="num" style="color:#333;">{len(files)}</div><div class="lbl">total test files</div></div>
    <div class="card"><div class="lbl">CCSM cross-cloud findings</div><div class="num" style="color:#2e7d32;">{total_ccsm_cross}</div><div class="lbl">only this tool detects these</div></div>
    <div class="card"><div class="lbl">Checkov cross-cloud</div><div class="num" style="color:#c62828;">0</div><div class="lbl">cannot detect</div></div>
    <div class="card"><div class="lbl">tfsec cross-cloud</div><div class="num" style="color:#c62828;">0</div><div class="lbl">cannot detect</div></div>
</div>

<div class="keybox">
    <strong>Key finding:</strong> Checkov produced {total_checkov} findings and tfsec produced {total_tfsec} findings
    across all test files. Every one of those findings checks a single cloud provider in isolation. The CCSM scanner
    found {total_ccsm_cross} cross-cloud inconsistencies that neither Checkov nor tfsec can detect, because neither
    has a shared semantic model between AWS and Azure.
</div>

<h2>Results per file</h2>
<table>
    <tr><th>Group</th><th style="text-align:left;">Test file</th><th>Checkov</th><th>tfsec</th><th>CCSM single-cloud</th><th>CCSM cross-cloud</th></tr>
    {table_rows}
</table>

<h2>Cross-cloud findings (only CCSM detects these)</h2>
{finding_cards}

<h2>Total findings comparison</h2>
<div class="section">
    <div class="bar-row"><div class="bar-lbl">Checkov</div><div class="bar-track"><div class="bar-fill" style="width:{checkov_width}%; background:#1976d2;">{total_checkov} findings</div></div></div>
    <div class="bar-row"><div class="bar-lbl">tfsec</div><div class="bar-track"><div class="bar-fill" style="width:{tfsec_width}%; background:#7b1fa2;">{total_tfsec} findings</div></div></div>
    <div class="bar-row"><div class="bar-lbl">CCSM single</div><div class="bar-track"><div class="bar-fill" style="width:{ccsm_single_width}%; background:#0288d1;">{total_ccsm_single} single-cloud</div></div></div>
    <div class="bar-row"><div class="bar-lbl">CCSM cross-cloud</div><div class="bar-track"><div class="bar-fill" style="width:{ccsm_cross_width}%; background:#2e7d32;">{total_ccsm_cross} cross-cloud (unique to CCSM)</div></div></div>
</div>

</body>
</html>"""
    return html


print("=" * 60)
print("  CCSM Comparison Report Generator")
print("=" * 60)

all_results = collect_all_results()

print("\n\nGenerating HTML report...")
html = build_html(all_results)

RESULTS_DIR.mkdir(exist_ok=True)
report_path = RESULTS_DIR / "comparison_report.html"
with open(report_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\nReport saved to: {report_path}")

total_checkov = sum(r["checkov_total"] for r in all_results.values())
total_tfsec = sum(r["tfsec_total"] for r in all_results.values())
total_cross = sum(r["ccsm_cross"] for r in all_results.values())

print("\n" + "=" * 60)
print("  QUICK SUMMARY")
print("=" * 60)
print(f"  Checkov total findings      : {total_checkov}")
print(f"  tfsec total findings        : {total_tfsec}")
print(f"  CCSM cross-cloud findings   : {total_cross}")
print(f"  Files scanned               : {len(all_results)}")
print("=" * 60)
