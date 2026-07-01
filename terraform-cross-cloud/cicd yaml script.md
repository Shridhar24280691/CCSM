terraform-cross-cloud/
    .github/
        workflows/
            ccsm_scan.yml


# ccsm_scan.yml
# This file tells GitHub to automatically run the CCSM scanner
# every time someone pushes new Terraform files to the repository.
# If cross-cloud misconfigurations are found, the pipeline fails
# and the developer is notified before the code reaches production.

name: CCSM Cross-Cloud Security Scan

on:
  push:
    paths:
      - '**.tf'          # run whenever any .tf file changes
  pull_request:
    paths:
      - '**.tf'

jobs:
  security-scan:
    runs-on: ubuntu-latest

    steps:
      - name: Check out the code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install python-hcl2

      - name: Run CCSM Scanner
        run: |
          cd scanner
          python main.py

      - name: Upload results as artifact
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: ccsm-scan-results
          path: results/ccsm_results.csv

# Steps to be followed by developers
Developer writes Terraform file
         |
         v
Git push to GitHub
         |
         v
GitHub Actions triggers automatically
         |
         v
    ┌─────────────────────────────────────┐
    │  CCSM Scanner runs                  │
    │  parser.py   → reads .tf files      │
    │  normaliser  → unifies AWS + Azure  │
    │  detector    → finds cross-cloud    │
    │               gaps                  │
    └─────────────────────────────────────┘
         |
    ┌────┴────┐
    │         │
No gaps   Gaps found
found         |
    │    Pipeline FAILS
Pipeline  Developer notified
PASSES    Must fix before
    │     code is merged
    v
Terraform files safe to apply
to real cloud accounts