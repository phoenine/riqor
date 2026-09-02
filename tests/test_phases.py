import unittest

from helpers import load_tool

phases = load_tool("phases")


class PhaseNamingTests(unittest.TestCase):
    def test_normalize_intake_alias_for_feature_testing(self):
        self.assertEqual(phases.normalize_phase("intake", "feature-quality"), "Intake")

    def test_normalize_case_insensitive_requirement_specification(self):
        self.assertEqual(
            phases.normalize_phase("requirement specification", "feature-quality"),
            "Requirement Specification",
        )

    def test_normalize_bug_intake_alias(self):
        self.assertEqual(phases.normalize_phase("bug intake", "bug-regression"), "Bug Intake")

    def test_validation_rejects_unknown_phase(self):
        self.assertEqual(
            phases.phase_validation_error("feature-quality", "Mystery Phase"),
            "must be one of: Intake, Requirement Specification, Risk Analysis, Test Design, "
            "Optional Case Sync Or Generation, Optional Case Execute, Optional Bug Report, Optional Test Report",
        )

    def test_validation_accepts_canonical_phase(self):
        self.assertIsNone(phases.phase_validation_error("release-acceptance", "Release Baseline"))


if __name__ == "__main__":
    unittest.main()
