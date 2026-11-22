"""Data model, statement parser + export loading for the quota audit."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional


class ExportError(ValueError):
    """Raised when an export file is malformed."""


PROD_LABELS = ("prod", "production")

# set|unset|zero <family> quota(s) [<name>] [to <N>] in tenancy|compartment <name> [where ...]
_STATEMENT_RE = re.compile(
    r"^\s*(set|unset|zero)\s+"
    r"(?P<family>\S+)\s+quotas?"
    r"(?:\s+(?P<name>[^/\s][^\s]*|/\S+/))?"
    r"(?:\s+to\s+(?P<value>\d+))?"
    r"\s+in\s+(?P<scope>tenancy|compartment\s+.+?)"
    r"(?:\s+where\s+.+)?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Statement:
    raw: str
    action: str          # set | unset | zero
    family: str
    quota_name: str      # "" when the statement covers the whole family
    value: Optional[int]
    scope_kind: str      # tenancy | compartment
    scope_target: str    # compartment path, "" for tenancy

    @property
    def broad_zero(self) -> bool:
        return self.action == "zero" and not self.quota_name


def parse_statement(raw: str) -> Optional[Statement]:
    m = _STATEMENT_RE.match(raw)
    if not m:
        return None
    action = m.group(1).lower()
    value = m.group("value")
    name = (m.group("name") or "").strip()
    # 'set' needs both a quota name and a value; 'zero'/'unset' must not carry a value.
    if action == "set" and (not name or value is None):
        return None
    if action in ("zero", "unset") and value is not None:
        return None
    scope = m.group("scope").strip()
    if scope.lower() == "tenancy":
        kind, target = "tenancy", ""
    elif scope.lower().startswith("compartment"):
        kind = "compartment"
        target = scope[len("compartment"):].strip()
        if not target:
            return None
    else:
        return None
    return Statement(raw=raw, action=action, family=m.group("family").lower(),
                     quota_name=name.lower(), value=int(value) if value is not None else None,
                     scope_kind=kind, scope_target=target.lower())


@dataclass(frozen=True)
class Compartment:
    name: str
    labels: tuple = ()

    def is_prod(self) -> bool:
        return any(c in x.lower() for x in self.labels for c in PROD_LABELS)


@dataclass(frozen=True)
class Policy:
    name: str
    statements: tuple = ()  # tuple[Statement]
    invalid: tuple = ()     # raw strings that did not parse


def load_export(path: str) -> tuple:
    with open(path, "r", encoding="utf-8") as fh:
        try:
            raw = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ExportError(f"{path}: not valid JSON: {exc}") from exc
    if not isinstance(raw, dict) or "compartments" not in raw or "quota_policies" not in raw:
        raise ExportError(f"{path}: top level must hold 'compartments' and 'quota_policies' lists")
    compartments = []
    for i, c in enumerate(raw["compartments"]):
        where = f"compartments[{i}]"
        if "name" not in c:
            raise ExportError(f"{where}: missing required field 'name'")
        compartments.append(Compartment(name=c["name"], labels=tuple(c.get("labels", []))))
    policies = []
    for j, p in enumerate(raw["quota_policies"]):
        where = f"quota_policies[{j}]"
        if "name" not in p:
            raise ExportError(f"{where}: missing required field 'name'")
        stmts, invalid = [], []
        for k, s in enumerate(p.get("statements", [])):
            if not isinstance(s, str):
                raise ExportError(f"{where}.statements[{k}]: must be a string")
            parsed = parse_statement(s)
            (stmts if parsed else invalid).append(parsed if parsed else s)
        policies.append(Policy(name=p["name"], statements=tuple(stmts), invalid=tuple(invalid)))
    return tuple(compartments), tuple(policies)
