import unittest
from scripts.send_telegram_result import _format_mission, _truth_state


class ReportingIntegrityTests(unittest.TestCase):
    def test_execution_success_does_not_imply_requested_outcome_verified(self):
        result = {
            "mission_id": "m1",
            "status": "SUCCEEDED",
            "plan_summary": "Inspect repository and latest workflow",
            "actions": ["github.get_repository", "github.get_workflow_runs"],
            "evidence": {"name": "FALCON"},
            "verification": {"ok": True, "execution_ok": True},
        }
        self.assertEqual(_truth_state(result), ("SUCCEEDED", "NOT_VERIFIED"))
        text = _format_mission(result)
        self.assertIn("Execution status: SUCCEEDED", text)
        self.assertIn("Requested outcome verified: NOT_VERIFIED", text)
        self.assertIn("Do not treat this as full task success", text)

    def test_only_explicit_reporting_verification_can_claim_verified(self):
        result = {"mission_id": "m2", "status": "SUCCEEDED", "reporting_verified": True}
        self.assertEqual(_truth_state(result), ("SUCCEEDED", "VERIFIED"))
        self.assertIn("Requested outcome verified: VERIFIED", _format_mission(result))

    def test_failure_never_claims_requested_outcome_verified(self):
        result = {"mission_id": "m3", "status": "FAILED", "reporting_verified": True}
        self.assertEqual(_truth_state(result), ("FAILED", "NOT_VERIFIED"))


if __name__ == "__main__":
    unittest.main()
