import unittest

from quota_check.model import Compartment, Policy, parse_statement
from quota_check.rules import (
    exit_code,
    rule_empty_policy,
    rule_invalid_statement,
    rule_prod_without_quota,
    rule_zero_overrides_set,
    run_all,
)


def comp(name="c", labels=("prod",)):
    return Compartment(name=name, labels=tuple(labels))


def pol(name="p", raws=(), invalid=()):
    return Policy(name=name,
                  statements=tuple(s for s in (parse_statement(r) for r in raws) if s),
                  invalid=tuple(invalid))


class TestQta001(unittest.TestCase):
    def test_fires_prod_untargeted(self):
        out = rule_prod_without_quota((comp(),), ())
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].severity, "HIGH")

    def test_quiet_prod_targeted(self):
        p = pol(raws=("set compute-core quota x to 5 in compartment c",))
        self.assertEqual(rule_prod_without_quota((comp(),), (p,)), [])

    def test_quiet_dev_untargeted(self):
        self.assertEqual(rule_prod_without_quota((comp(labels=("dev",)),), ()), [])

    def test_nested_path_matches_leaf(self):
        p = pol(raws=("set compute-core quota x to 5 in compartment parent:c",))
        self.assertEqual(rule_prod_without_quota((comp(),), (p,)), [])


class TestQta002(unittest.TestCase):
    def test_fires_invalid(self):
        out = rule_invalid_statement((), (pol(invalid=("garbage statement",)),))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].severity, "MEDIUM")

    def test_quiet_all_valid(self):
        self.assertEqual(rule_invalid_statement((), (pol(raws=("zero x quotas in tenancy",)),)), [])


class TestQta003(unittest.TestCase):
    def test_fires_zero_after_set(self):
        p = pol(raws=("set compute-core quota x to 240 in tenancy",
                      "zero compute-core quotas in tenancy"))
        out = rule_zero_overrides_set((), (p,))
        self.assertEqual(len(out), 1)

    def test_quiet_zero_before_set(self):
        p = pol(raws=("zero compute-core quotas in tenancy",
                      "set compute-core quota x to 240 in tenancy"))
        self.assertEqual(rule_zero_overrides_set((), (p,)), [])

    def test_quiet_different_family(self):
        p = pol(raws=("set compute-core quota x to 240 in tenancy",
                      "zero database quotas in tenancy"))
        self.assertEqual(rule_zero_overrides_set((), (p,)), [])

    def test_quiet_different_target(self):
        p = pol(raws=("set compute-core quota x to 240 in compartment a",
                      "zero compute-core quotas in compartment b"))
        self.assertEqual(rule_zero_overrides_set((), (p,)), [])


class TestQta004(unittest.TestCase):
    def test_fires_empty(self):
        out = rule_empty_policy((), (pol(),))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].severity, "LOW")

    def test_quiet_nonempty(self):
        self.assertEqual(rule_empty_policy((), (pol(raws=("zero x quotas in tenancy",)),)), [])


class TestAggregation(unittest.TestCase):
    def test_exit_2_on_high(self):
        self.assertEqual(exit_code(run_all((comp(),), ())), 2)

    def test_exit_1_medium_only(self):
        self.assertEqual(exit_code(run_all((), (pol(invalid=("junk",)),))), 1)

    def test_exit_0_clean(self):
        p = pol(raws=("set compute-core quota x to 5 in compartment c",))
        self.assertEqual(exit_code(run_all((comp(),), (p,))), 0)


if __name__ == "__main__":
    unittest.main()
