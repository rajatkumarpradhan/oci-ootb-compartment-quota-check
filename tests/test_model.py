import unittest

from quota_check.model import parse_statement


class TestParse(unittest.TestCase):
    def test_set_with_value(self):
        s = parse_statement("set compute-core quota standard-e4-core-count to 240 in compartment webshop-prod")
        self.assertIsNotNone(s)
        self.assertEqual(s.action, "set")
        self.assertEqual(s.family, "compute-core")
        self.assertEqual(s.quota_name, "standard-e4-core-count")
        self.assertEqual(s.value, 240)
        self.assertEqual((s.scope_kind, s.scope_target), ("compartment", "webshop-prod"))

    def test_zero_family_wide(self):
        s = parse_statement("zero compute-core quotas in tenancy")
        self.assertTrue(s.broad_zero)
        self.assertEqual((s.scope_kind, s.scope_target), ("tenancy", ""))

    def test_wildcard_name(self):
        s = parse_statement("set database quota /*exadata*/ to 1 in tenancy")
        self.assertIsNotNone(s)
        self.assertEqual(s.quota_name, "/*exadata*/")

    def test_where_clause(self):
        s = parse_statement("set compute-core quota x to 5 in compartment c where request.region = us-phoenix-1")
        self.assertIsNotNone(s)

    def test_set_without_value_rejected(self):
        self.assertIsNone(parse_statement("set compute-core quota x in compartment c"))

    def test_zero_with_value_rejected(self):
        self.assertIsNone(parse_statement("zero compute-core quotas to 0 in tenancy"))

    def test_typo_keyword_rejected(self):
        self.assertIsNone(parse_statement("set compute-core quotaa x to 5 in compartment c"))

    def test_nested_compartment(self):
        s = parse_statement("set compute-core quota x to 5 in compartment parent:child:grand")
        self.assertEqual(s.scope_target, "parent:child:grand")

    def test_case_insensitive(self):
        s = parse_statement("Zero compute-core quotas in tenancy")
        self.assertEqual(s.action, "zero")


if __name__ == "__main__":
    unittest.main()
