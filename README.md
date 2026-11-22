# oci-ootb-compartment-quota-check

**Category: built-in OCI services project (OOTB).** The custom portfolio project in this
pair is `oci-autonomous-db-config-audit`.

## Which built-in OCI services this wires

- **OCI Compartment Quotas** (`oci_limits_quota`): the built-in quota service. Per the OCI
  docs, quota policies are lists of statements written in a small declarative language -
  `set`, `unset`, `zero` - and **within a policy, a later statement supersedes an earlier
  statement targeting the same resource**. A policy can therefore quietly cancel itself,
  and a missing direct statement is a coverage gap in the supplied export, not proof of
  effective limits.

## Custom code vs native config

- **Native config**: `terraform/` declares one quota policy with correctly ordered
  statements (an allowlist pattern: `zero` the family first, then `set` the exception
  after). Field names follow the oracle/oci provider docs (`oci_limits_quota`).
  **Template only - NOT plan/apply validated** (no live tenancy).
- **Custom code**: `quota_check/` audits an offline JSON export of compartments and quota
  policies: it parses each statement against the documented grammar and cross-references
  targets.

## The rules

| Rule | Severity | Fires when |
| ---- | -------- | ---------- |
| QTA001 | HIGH | A **prod-labeled** compartment is targeted by no quota statement in the export - direct coverage is missing in this export. Inherited or tenancy-wide rules may still apply. |
| QTA002 | MEDIUM | A recorded statement **does not parse** against the documented grammar (`set/unset/zero <family> quota(s) [name] [to N] in tenancy|compartment <name> [where ...]`) - a transcription error or invalid statement as recorded. |
| QTA003 | MEDIUM | Within one policy, a broad `zero <family> quotas` statement appears **after** a `set <family> quota ...` for the same family and target, with neither statement conditional - per the docs the later statement supersedes, silently cancelling the earlier allocation. |
| QTA004 | LOW | A quota policy records **zero statements** - empty scaffolding as far as the export records. |

Exit code: `2` on any HIGH, `1` on MEDIUM/LOW only, `0` when clean.

## Run it

```bash
python -m quota_check.cli samples/quotas_messy.json   # exits 2, all 4 rules fire
python -m quota_check.cli samples/quotas_clean.json   # exits 0
python -m unittest discover -s tests -v               # 27 tests, stdlib only
```

## Honest limits

- **Offline audit**: the JSON export is synthetic; nothing calls the OCI API.
- QTA001 is a review prompt - a prod compartment can be intentionally governed by
  service limits alone, and statements in policies missing from the export are invisible
  to it.
- Grammar and precedence semantics (later statement wins within a policy; most
  restrictive policy wins across policies) are from the OCI quota docs as of Nov 2026;
  verify current behavior before acting.
- Cross-policy interplay (multiple policies targeting the same resource) is out of scope.
- The Terraform template is illustrative and has **not** been plan/apply validated.
- No live tenancy was touched.

## Project status

Built as a daily OOTB project. 27 unit tests, green locally and in CI. Free tier only; no
live cloud calls, no spend.

## Scope and sources

Only offline tests and synthetic demos ran locally and in GitHub Actions. Native quota
configuration is template-only. This is not an effective-permissions engine: ancestor
coverage, full compartment identities, quota-name validation and condition evaluation
are not implemented. QTA003 checks unconditional statements only. Quota policies can
be created in any compartment; the example places one at the tenancy root.

- https://docs.oracle.com/en-us/iaas/Content/Quotas/Concepts/quota_policy_syntax.htm
- https://registry.terraform.io/providers/oracle/oci/latest/docs/resources/limits_quota
