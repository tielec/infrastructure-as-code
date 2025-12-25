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
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.phase3_script = (
            cls.repo_root
            / "scripts"
            / "jenkins"
            / "shell"
            / "phase3_shutdown_scheduler_flow.sh"
        )

    def _read_dsl(self) -> str:
        return self.dsl_path.read_text()

    def _read_phase3_script(self) -> str:
        return self.phase3_script.read_text()

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

    def test_phase3_cli_script_captures_state_and_schedule(self):
        """Phase 3 Step 1/4: the CLI helper captures disabled state and the nightly cron spec."""
        self.assertTrue(
            self.phase3_script.exists(),
            "Phase 3 script must exist so CLI instructions can be rerun in Jenkins environments",
        )
        script = self._read_phase3_script()
        self.assertIn(
            'TARGET_JOB="Infrastructure_Management/Shutdown-Environment-Scheduler"',
            script,
            "The script must point at the scheduler job that is being disabled",
        )
        self.assertIn(
            'run_cli get-job "$TARGET_JOB" | grep -i disabled',
            script,
            "Baseline CLI checks should verify the disabled flag via Jenkins CLI",
        )
        self.assertIn(
            "run_cli get-job \"$TARGET_JOB\" | grep -o '<spec>H 15 \\* \\* \\*</spec>'",
            script,
            "The nightly cron spec must remain in the job definition after the seed job runs",
        )
        self.assertIn(
            'run_cli get-job "$TARGET_JOB" | grep "<disabled>true</disabled>"',
            script,
            "The helper should confirm the scheduler is marked as disabled in the XML",
        )
        self.assertIn(
            'run_cli get-job "$TARGET_JOB" | grep -A5 -B5 "TimerTrigger"',
            script,
            "The script also reads adjacent TimerTrigger lines to ensure schedule suppression persists",
        )

    def test_phase3_cli_script_drives_seed_and_manual_flows(self):
        """Phase 3 Step 3/5: the helper executes the seed job and the DRY_RUN manual run."""
        script = self._read_phase3_script()
        self.assertIn(
            'run_cli build "$SEED_JOB" -s',
            script,
            "Seeding Jenkins with the updated DSL is required before verifying the disable flow",
        )
        self.assertIn(
            'run_cli build "$TARGET_JOB" -s -p DRY_RUN=true',
            script,
            "Manual execution must be triggered in DRY_RUN mode so human operators can verify behavior",
        )
        self.assertIn(
            'run_cli console "$TARGET_JOB" "$manual_build"',
            script,
            "The helper fetches the console log of the DRY_RUN build to check downstream logs",
        )

    def test_phase3_cli_script_regression_checks_other_jobs(self):
        """Phase 3 Step 6: the helper inspects sibling jobs and the downstream shutdown job."""
        script = self._read_phase3_script()
        self.assertIn(
            'run_cli list-jobs Infrastructure_Management/',
            script,
            "Regression checks exercise the Infrastructure_Management folder listing via CLI",
        )
        self.assertIn(
            'run_cli get-job "$DOWNSTREAM_JOB" | grep -q "<disabled>true</disabled>"',
            script,
            "The helper fails fast if the downstream shutdown job is disabled unexpectedly",
        )


if __name__ == "__main__":
    unittest.main()
