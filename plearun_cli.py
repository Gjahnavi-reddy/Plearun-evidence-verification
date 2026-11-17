#!/usr/bin/env python3
"""Verified Findings: Evidence Verification CLI.

Usage:
    python3 plearun_cli.py REPORT RECORDS_DIR > findings.json
"""
import sys
from pathlib import Path

from plearun_pipeline.pipeline import VerificationPipeline


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python3 plearun_cli.py REPORT RECORDS_DIR", file=sys.stderr)
        return 1

    report_path = Path(sys.argv[1])
    records_dir = Path(sys.argv[2])

    if not report_path.exists():
        print(f"Error: Report file does not exist: {report_path}", file=sys.stderr)
        return 1

    if not records_dir.exists() or not records_dir.is_dir():
        print(f"Error: Records directory does not exist or is not a directory: {records_dir}", file=sys.stderr)
        return 1

    try:
        pipeline = VerificationPipeline(report_path, records_dir)
        json_output = pipeline.run_to_json(indent=2)
        print(json_output)
        return 0
    except Exception as e:
        print(f"Error running evidence verification: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
