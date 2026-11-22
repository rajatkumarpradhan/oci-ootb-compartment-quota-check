"""python -m quota_check.cli EXPORT"""

from __future__ import annotations

import argparse
import sys

from .model import ExportError, load_export
from .rules import exit_code, run_all


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="compartment-quota-check",
        description="Audit an offline export of OCI Compartment Quotas policies for coverage and ordering gaps.",
    )
    p.add_argument("export", help="path to the JSON export")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        compartments, policies = load_export(args.export)
    except ExportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    findings = run_all(compartments, policies)
    n_statements = sum(len(p.statements) + len(p.invalid) for p in policies)
    print(
        f"Compartment quota audit - {len(compartments)} compartment(s), {len(policies)} policy(ies), "
        f"{n_statements} statement(s), {len(findings)} finding(s)"
    )
    for x in findings:
        print(f"[{x.severity:6s}] {x.rule} {x.target}")
        print(f"         {x.detail}")
    code = exit_code(findings)
    print({0: "RESULT: clean", 1: "RESULT: warnings only", 2: "RESULT: HIGH findings present"}[code])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
