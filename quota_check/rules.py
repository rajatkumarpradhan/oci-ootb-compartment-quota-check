"""QTA001-QTA004 rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str  # HIGH | MEDIUM | LOW
    target: str
    detail: str


def rule_prod_without_quota(compartments: tuple, policies: tuple) -> list:
    """QTA001 HIGH: prod-labeled compartment targeted by no quota statement."""
    targeted = set()
    for p in policies:
        for s in p.statements:
            if s.scope_kind == "compartment":
                targeted.add(s.scope_target.split(":")[-1])
    out = []
    for c in compartments:
        if c.is_prod() and c.name.lower() not in targeted:
            out.append(
                Finding("QTA001", "HIGH", c.name,
                        "prod-labeled compartment is targeted by no quota statement in this export; "
                        "resource creation there is bounded only by service limits - review flag")
            )
    return out


def rule_invalid_statement(compartments: tuple, policies: tuple) -> list:
    """QTA002 MEDIUM: recorded statement does not match the documented grammar."""
    del compartments
    out = []
    for p in policies:
        for raw in p.invalid:
            out.append(
                Finding("QTA002", "MEDIUM", p.name,
                        f"statement {raw!r} does not parse against the documented quota grammar; "
                        f"a transcription error or invalid statement as recorded")
            )
    return out


def rule_zero_overrides_set(compartments: tuple, policies: tuple) -> list:
    """QTA003 MEDIUM: a later broad 'zero' supersedes an earlier 'set' for the same family+target."""
    del compartments
    out = []
    for p in policies:
        for idx, s in enumerate(p.statements):
            if not s.broad_zero:
                continue
            for earlier in p.statements[:idx]:
                if (earlier.action == "set" and earlier.family == s.family
                        and earlier.scope_kind == s.scope_kind
                        and earlier.scope_target == s.scope_target):
                    out.append(
                        Finding("QTA003", "MEDIUM", p.name,
                                f"broad statement {s.raw!r} appears after {earlier.raw!r} for family "
                                f"{s.family!r} on the same target; per OCI docs the later statement "
                                f"supersedes, silently cancelling the earlier allocation")
                    )
                    break
    return out


def rule_empty_policy(compartments: tuple, policies: tuple) -> list:
    """QTA004 LOW: policy with zero statements recorded."""
    del compartments
    return [
        Finding("QTA004", "LOW", p.name,
                "quota policy records zero statements; empty scaffolding as far as this export records")
        for p in policies if not p.statements and not p.invalid
    ]


ALL_RULES = (
    rule_prod_without_quota,
    rule_invalid_statement,
    rule_zero_overrides_set,
    rule_empty_policy,
)

_SEVERITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def run_all(compartments: tuple, policies: tuple) -> list:
    findings = []
    for rule in ALL_RULES:
        findings.extend(rule(compartments, policies))
    findings.sort(key=lambda x: (_SEVERITY_RANK[x.severity], x.rule, x.target))
    return findings


def exit_code(findings: list) -> int:
    if any(f.severity == "HIGH" for f in findings):
        return 2
    if findings:
        return 1
    return 0
