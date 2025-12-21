"""Integration-style checks for Job DSL agent label defaults."""

from pathlib import Path
import unittest


DSL_ROOT = Path(__file__).resolve().parents[2] / "jenkins" / "jobs" / "dsl"

# Jobs that should default AGENT_LABEL to ec2-fleet-micro by listing it first.
MICRO_FIRST_TARGETS = {
    "admin/admin_backup_config_job.groovy",
    "admin/admin_github_webhooks_setting_job.groovy",
    "admin/admin_ssm_backup_job.groovy",
    "admin/admin_ssm_restore_job.groovy",
    "admin/admin_test_github_job.groovy",
    "admin/admin_user_management_job.groovy",
    "code-quality-checker/code_quality_pr_complexity_analyzer_job.groovy",
    "code-quality-checker/code_quality_rust_code_analysis_check_job.groovy",
    "docs-generator/docs_generator_auto_insert_doxygen_comment_job.groovy",
    "docs-generator/docs_generator_auto_insert_doxygen_comment_test_job.groovy",
    "docs-generator/docs_generator_generate_doxygen_html_job.groovy",
    "docs-generator/docs_generator_multi_pull_request_comment_builder_job.groovy",
    "docs-generator/docs_generator_technical_docs_writer_job.groovy",
    "docs-generator/docx_generator_pull_request_comment_builder_job.groovy",
    "infrastructure-management/infrastructure_shutdown_environment_job.groovy",
    "infrastructure/infrastructure_ansible_playbook_executor_job.groovy",
    "infrastructure/infrastructure_lambda_verification_job.groovy",
    "infrastructure/infrastructure_pulumi_dashboard_job.groovy",
    "infrastructure/infrastructure_pulumi_stack_action_job.groovy",
    "infrastructure/infrastructure_ssm_dashboard_job.groovy",
}

FREESTYLE_LABEL_TARGETS = {
    "code-quality-checker/code_quality_pr_complexity_analyzer_github_trigger_job.groovy",
    "docs-generator/docx_generator_pull_request_comment_builder_github_trigger_job.groovy",
}

EXPECTED_CHOICE_ORDER = "['ec2-fleet-micro', 'ec2-fleet-small', 'ec2-fleet-medium']"


class JobDslAgentLabelTests(unittest.TestCase):
    def test_choice_param_defaults_to_micro_first(self):
        """Ensure AGENT_LABEL choiceParam defaults to micro for targeted DSL jobs."""
        for rel_path in MICRO_FIRST_TARGETS:
            path = DSL_ROOT / rel_path
            contents = path.read_text()
            self.assertIn(
                "choiceParam('AGENT_LABEL'",
                contents,
                msg=f"{rel_path} must expose AGENT_LABEL as a choice parameter",
            )
            self.assertIn(
                EXPECTED_CHOICE_ORDER,
                contents,
                msg=f"{rel_path} should list ec2-fleet-micro first in AGENT_LABEL options",
            )

    def test_freestyle_jobs_use_micro_label(self):
        """Freestyle trigger jobs must pin to ec2-fleet-micro."""
        for rel_path in FREESTYLE_LABEL_TARGETS:
            contents = (DSL_ROOT / rel_path).read_text()
            self.assertIn(
                "label('ec2-fleet-micro')",
                contents,
                msg=f"{rel_path} should pin to ec2-fleet-micro",
            )
            self.assertNotIn(
                "label('ec2-fleet')",
                contents,
                msg=f"{rel_path} should no longer reference the generic ec2-fleet label",
            )


if __name__ == "__main__":
    unittest.main()
