"""Integration checks for the shutdown scheduler job DSL."""

from pathlib import Path
import unittest


class InfrastructureShutdownSchedulerJobTests(unittest.TestCase):
    """Verify the DSL defines a disabled scheduler but keeps its cron trigger."""

    @classmethod
    def setUpClass(cls):
        cls.dsl_path = (
            Path(__file__).resolve().parents[2]
            / "jenkins"
            / "jobs"
            / "dsl"
            / "infrastructure-management"
            / "infrastructure_shutdown_scheduler_job.groovy"
        )

    def _read_dsl(self) -> str:
        return self.dsl_path.read_text()

    def test_scheduler_job_is_disabled(self):
        """The scheduler job must set disabled(true) so cron triggers never run."""
        contents = self._read_dsl()
        self.assertIn(
            "disabled(true)",
            contents,
            "Failing to mark the job as disabled would keep the cron trigger active",
        )
        self.assertGreater(
            contents.index("triggers {"),
            contents.index("disabled(true)"),
            "The disabled flag should be declared before the trigger section",
        )

    def test_cron_trigger_remains_defined(self):
        """The cron trigger stays defined even when the job is disabled."""
        contents = self._read_dsl()
        self.assertIn(
            "cron('H 15 * * *')",
            contents,
            "The scheduler must keep its nightly cron definition for future re-enablement",
        )

    def test_manual_execution_chain_is_preserved(self):
        """Phase 3 manual-run checklist: the downstream shutdown job remains triggerable with DRY_RUN."""
        contents = self._read_dsl()
        self.assertIn(
            "trigger('Infrastructure_Management/Shutdown_Jenkins_Environment')",
            contents,
            "The scheduler must still trigger the downstream shutdown job even while disabled",
        )
        self.assertIn(
            "booleanParam('DRY_RUN', false)",
            contents,
            "DRY_RUN must still exist so manual execution can be safely invoked via parameter",
        )
        self.assertIn(
            "booleanParam('CONFIRM_SHUTDOWN', true)",
            contents,
            "Manual execution relies on a confirmation flag that must remain enabled",
        )
        self.assertIn(
            "predefinedProp('ENVIRONMENT', 'dev')",
            contents,
            "Environment targeting must stay pinned to 'dev' for integration sanity checks",
        )
        self.assertIn(
            "triggerWithNoParameters(false)",
            contents,
            "The downstream trigger should keep waiting behavior aligned with CLI expectations",
        )

    def test_only_scheduler_job_is_disabled(self):
        """Phase 3 regression check: no other jobs are disabled when the scheduler is suppressed."""
        contents = self._read_dsl()
        self.assertEqual(
            contents.count("disabled(true)"),
            1,
            "Only the scheduler job should be disabled so other Infrastructure_Management jobs stay active",
        )


if __name__ == "__main__":
    unittest.main()
