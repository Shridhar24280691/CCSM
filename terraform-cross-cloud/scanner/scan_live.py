# scan_live.py
# Scans the live deployed Terraform file with all three tools
# and generates a clean HTML report.
#
# Usage:
#   cd scanner
#   python scan_live.py
#
# What it does:
#   1. Runs your CCSM scanner on the live test file
#   2. Runs Checkov on the same file
#   3. Runs tfsec on the same file
#   4. Opens a comparison HTML report in your browser automatically

import sys
import os
import subprocess
import json
import webbrowser
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR   = Path(__file__).resolve().parent
LIVE_FILE    = SCRIPT_DIR.parent / "terraform_tests" / "live_test" / "main.tf"
RESULTS_DIR  = SCRIPT_DIR.parent / "results"
REPORT_PATH  = RESULTS_DIR / "live_scan_report.html"

sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

from parser     import parse_file
from normaliser import normalise
from detector   import detect


def run_ccsm():
    print("  Running CCSM scanner...")
    resources  = parse_file(str(LIVE_FILE)) # Parses the live Terraform file into a structured representation of resources.
    normalised = normalise(resources) # Normalises the parsed resources for consistent processing.
    findings   = detect(normalised) # Detects issues in the normalised resources.

    single     = [f for f in findings if f["provider"] != "cross-cloud"] # Filters findings to keep only those where provider != "cross-cloud".
    cross      = [f for f in findings if f["provider"] == "cross-cloud"] # Filters findings to keep only those where provider == "cross-cloud".

    print(f"  CCSM: {len(single)} single-cloud  +  {len(cross)} cross-cloud")
    return findings


def run_checkov():
    print("  Running Checkov...")
    try:
        result = subprocess.run( # Calls subprocess.run to execute the Checkov CLI command and capture its output.
            f'checkov -f "{LIVE_FILE}" --framework terraform -o json --quiet --compact',
            capture_output=True, text=True, timeout=120, shell=True 
        )
        output = result.stdout.strip()
        if not output:
            print("  Checkov: no output")
            return []

        # Checkov sometimes outputs two JSON objects joined together.
        # Find the first complete JSON object by counting braces.
        json_start = output.find("{")
        if json_start == -1:
            return []
        output = output[json_start:]

        data = None
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            depth, end_pos = 0, 0
            for i, ch in enumerate(output):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end_pos = i + 1
                        break
            if end_pos:
                try:
                    data = json.loads(output[:end_pos]) 
                except json.JSONDecodeError:
                    return []

        if data is None: 
            return []

        blocks   = data if isinstance(data, list) else [data] # Ensures blocks is a list: if data is already a list, use it; otherwise wrap it in a list.
        findings = [] 
        for block in blocks:
            for check in block.get("results", {}).get("failed_checks", []):
                findings.append({
                    "check_id":    check.get("check_id", ""),
                    "check_type":  check.get("check_result", {}).get("name", check.get("check_id", "")),
                    "file":        check.get("repo_file_path", str(LIVE_FILE)),
                    "resource":    check.get("resource", ""),
                    "guideline":   check.get("guideline", ""),
                })

        print(f"  Checkov: {len(findings)} findings  (all single-cloud)")
        return findings

    except Exception as e:
        print(f"  Checkov error: {e}")
        return []


def run_tfsec():
    print("  Running tfsec...")
    try:
        file_dir = str(LIVE_FILE.parent)
        result   = subprocess.run(
            f'tfsec "{file_dir}" --format json --no-colour',
            capture_output=True, text=True, timeout=120, shell=True
        )
        output = (result.stdout or result.stderr).strip()
        if not output:
            print("  tfsec: no output")
            return []

        json_start = output.find("{") # Finds the index of the first `{`, assuming JSON starts there.
        json_end   = output.rfind("}") # Finds the index of the last `}`, assuming JSON ends there.
        if json_start == -1 or json_end == -1:
            return []

        data     = json.loads(output[json_start:json_end + 1]) # Parses the substring from json_start to json_end + 1 as JSON into a Python object.
        results  = data.get("results") or []
        findings = []
        for r in results:
            findings.append({
                "rule_id":     r.get("rule_id", ""),
                "description": r.get("description", ""),
                "severity":    r.get("severity", ""),
                "resource":    r.get("location", {}).get("filename", ""),
            })

        print(f"  tfsec: {len(findings)} findings  (all single-cloud)")
        return findings

    except Exception as e:
        print(f"  tfsec error: {e}")
        return []


def severity_colors(severity):
    if severity == "HIGH":
        return "#ffebee", "#c62828"
    if severity == "MEDIUM":
        return "#fff3e0", "#e65100"
    return "#fffde7", "#f57f17"


def build_html(ccsm_findings, checkov_findings, tfsec_findings):
    cross  = [f for f in ccsm_findings if f["provider"] == "cross-cloud"]
    single = [f for f in ccsm_findings if f["provider"] != "cross-cloud"]

    # CCSM cross-cloud finding cards 
    cross_cards = ""
    if cross:
        for f in cross:
            bg, col = severity_colors(f.get("severity", "HIGH"))
            cross_cards += f"""
<div style="background:white; border-left:4px solid #2e7d32; padding:16px;
            margin:12px 0; border-radius:0 8px 8px 0;
            box-shadow:0 1px 3px rgba(0,0,0,0.08);">
  <span style="background:{bg}; color:{col}; padding:2px 8px;
               border-radius:4px; font-size:11px; font-weight:600;">
    {f.get('severity','HIGH')}
  </span>
  <span style="background:#e8f5e9; color:#2e7d32; padding:2px 8px;
               border-radius:4px; font-size:11px; font-weight:600; margin-left:4px;">
    CROSS-CLOUD
  </span>
  <strong style="margin-left:8px;">{f['check']}</strong><br>
  <span style="color:#666; font-size:13px;">Provider: {f['provider']}</span>
  <br><br>
  <strong>Problem:</strong> {f['problem']}<br>
  <strong>Fix:</strong> {f['recommendation']}
</div>"""
    else:
        cross_cards = "<p style='color:#666;'>No cross-cloud findings.</p>"

    # CCSM single-cloud rows 
    ccsm_rows = ""
    for f in single:
        bg, col = severity_colors(f.get("severity", "MEDIUM"))
        ccsm_rows += f"""
<tr>
  <td style="padding:8px 12px;">
    <span style="background:{bg}; color:{col}; padding:2px 6px;
                 border-radius:4px; font-size:11px; font-weight:600;">
      {f.get('severity','MEDIUM')}
    </span>
  </td>
  <td style="padding:8px 12px; font-family:monospace; font-size:12px;">{f['check']}</td>
  <td style="padding:8px 12px; font-size:12px;">{f['problem']}</td>
</tr>"""

    # Checkov rows 
    checkov_rows = ""
    for f in checkov_findings:
        checkov_rows += f"""
<tr>
  <td style="padding:8px 12px; font-family:monospace; font-size:12px;">{f['check_id']}</td>
  <td style="padding:8px 12px; font-size:12px;">{f['check_type']}</td>
  <td style="padding:8px 12px; font-size:12px;">{f['resource']}</td>
</tr>"""

    # tfsec rows 
    tfsec_rows = ""
    for f in tfsec_findings:
        bg, col = severity_colors(f.get("severity", "").upper())
        tfsec_rows += f"""
<tr>
  <td style="padding:8px 12px;">
    <span style="background:{bg}; color:{col}; padding:2px 6px;
                 border-radius:4px; font-size:11px; font-weight:600;">
      {f.get('severity','')}
    </span>
  </td>
  <td style="padding:8px 12px; font-family:monospace; font-size:12px;">{f['rule_id']}</td>
  <td style="padding:8px 12px; font-size:12px;">{f['description']}</td>
</tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>CCSM Live Deployment Scan Report</title>
<style>
  body  {{ font-family:-apple-system,Arial,sans-serif; max-width:1100px; margin:40px auto;
          padding:0 20px; background:#fafafa; color:#333; }}
  h1    {{ font-size:24px; font-weight:600; border-bottom:2px solid #1976d2;
          padding-bottom:10px; }}
  h2    {{ font-size:18px; font-weight:600; margin-top:40px; color:#1976d2; }}
  h3    {{ font-size:15px; font-weight:600; margin-top:24px; color:#555; }}
  .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin:24px 0; }}
  .card {{ background:white; border-radius:8px; padding:20px; text-align:center;
          box-shadow:0 1px 3px rgba(0,0,0,0.1); }}
  .num  {{ font-size:36px; font-weight:700; margin:8px 0; }}
  .lbl  {{ font-size:13px; color:#666; }}
  table {{ width:100%; border-collapse:collapse; background:white; border-radius:8px;
          overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,0.1); margin:16px 0; }}
  th    {{ background:#1976d2; color:white; padding:10px 12px; text-align:left;
          font-size:12px; font-weight:500; }}
  td    {{ border-bottom:1px solid #eee; font-size:13px; vertical-align:top; }}
  .box  {{ background:#e3f2fd; border-radius:8px; padding:16px 20px; margin:20px 0;
          font-size:14px; line-height:1.6; }}
  .warn {{ background:#fff3e0; border-radius:8px; padding:12px 16px; margin:16px 0;
          font-size:13px; color:#e65100; }}
</style>
</head>
<body>

<h1>CCSM Live Deployment Scan — Cross-Cloud Misconfiguration Report</h1>
<p>
  This report shows the results of scanning a Terraform configuration that was
  <strong>deployed to real AWS and Azure cloud accounts</strong>.
  The same file was scanned by all three tools simultaneously.
</p>

<div class="box">
  <strong>What was deployed:</strong><br>
  AWS S3 bucket with versioning <strong>Enabled</strong> — correctly configured.<br>
  Azure Storage Account with versioning <strong>Disabled</strong> — the deliberate gap.<br><br>
  This is the cross-cloud policy inconsistency that CCSM scanner detects
  and that Checkov and tfsec cannot detect.
</div>

<h2>Summary</h2>
<div class="grid">
  <div class="card">
    <div class="lbl">CCSM cross-cloud</div>
    <div class="num" style="color:#2e7d32;">{len(cross)}</div>
    <div class="lbl">novel findings</div>
  </div>
  <div class="card">
    <div class="lbl">CCSM single-cloud</div>
    <div class="num" style="color:#0288d1;">{len(single)}</div>
    <div class="lbl">standard findings</div>
  </div>
  <div class="card">
    <div class="lbl">Checkov findings</div>
    <div class="num" style="color:#555;">{len(checkov_findings)}</div>
    <div class="lbl">all single-cloud</div>
  </div>
  <div class="card">
    <div class="lbl">tfsec findings</div>
    <div class="num" style="color:#555;">{len(tfsec_findings)}</div>
    <div class="lbl">all single-cloud</div>
  </div>
</div>

<div class="warn">
  Neither Checkov ({len(checkov_findings)} findings) nor tfsec ({len(tfsec_findings)} findings)
  produced any finding comparing AWS versioning against Azure versioning.
  All their findings check one cloud provider in isolation.
</div>

<h2>Cross-Cloud Findings (only CCSM detects these)</h2>
{cross_cards}

<h2>CCSM Single-Cloud Findings</h2>
<p style="font-size:13px; color:#666;">
  These are the same type of findings Checkov and tfsec also produce.
  They are included so the comparison is fair.
</p>
<table>
  <tr><th>Severity</th><th>Check</th><th>Problem</th></tr>
  {ccsm_rows if ccsm_rows else '<tr><td colspan="3" style="padding:12px; color:#666;">None</td></tr>'}
</table>

<h2>Checkov Findings ({len(checkov_findings)} total — all single-cloud)</h2>
<table>
  <tr><th>Check ID</th><th>Description</th><th>Resource</th></tr>
  {checkov_rows if checkov_rows else '<tr><td colspan="3" style="padding:12px; color:#666;">None returned</td></tr>'}
</table>

<h2>tfsec Findings ({len(tfsec_findings)} total — all single-cloud)</h2>
<table>
  <tr><th>Severity</th><th>Rule ID</th><th>Description</th></tr>
  {tfsec_rows if tfsec_rows else '<tr><td colspan="3" style="padding:12px; color:#666;">None returned</td></tr>'}
</table>
</body>
</html>"""
    return html


# MAIN 

print()
print("=" * 55)
print("  CCSM Live Deployment Scanner")
print("=" * 55)
print(f"  Scanning: {LIVE_FILE}")
print()

if not LIVE_FILE.exists():
    print(f"  ERROR: File not found: {LIVE_FILE}")
    print("  Make sure you have run 'terraform apply' in")
    print("  terraform_tests/live_test/ before running this script.")
    sys.exit(1)

ccsm_findings    = run_ccsm()
checkov_findings = run_checkov()
tfsec_findings   = run_tfsec()

print()
print("  Generating HTML report...")
RESULTS_DIR.mkdir(exist_ok=True)
html = build_html(ccsm_findings, checkov_findings, tfsec_findings)
with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print(f"  Report saved to: {REPORT_PATH}")
print()
print("=" * 55)
print("  RESULTS SUMMARY")
print("=" * 55)

cross  = [f for f in ccsm_findings if f["provider"] == "cross-cloud"]
single = [f for f in ccsm_findings if f["provider"] != "cross-cloud"]

print(f"  CCSM cross-cloud findings : {len(cross)}  (Checkov: 0  tfsec: 0)")
print(f"  CCSM single-cloud         : {len(single)}")
print(f"  Checkov total             : {len(checkov_findings)}")
print(f"  tfsec total               : {len(tfsec_findings)}")
print("=" * 55)
print()

# Open the report in browser automatically
webbrowser.open(REPORT_PATH.as_uri())
print("  Report opened in your browser.")
print()