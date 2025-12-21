"""Dynamic scenario coverage for Phase 3 integration checks."""

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
JOB_CONFIG_PATH = REPO_ROOT / "jenkins" / "jobs" / "pipeline" / "_seed" / "job-creator" / "job-config.yaml"
DSL_ROOT = REPO_ROOT / "jenkins" / "jobs" / "dsl"
PIPELINE_ROOT = REPO_ROOT / "jenkins" / "jobs" / "pipeline"

EXPECTED_CHOICE_ORDER = "['ec2-fleet-micro', 'ec2-fleet-small', 'ec2-fleet-medium']"

# Category coverage expectations mirrored from the Phase 3 scenario doc.
CATEGORY_EXPECTATIONS = {
    "Admin_Jobs": {
        "admin_backup_config_job",
        "admin_github_webhooks_setting_job",
        "admin_ssm_backup_job",
        "admin_ssm_restore_job",
        "admin_test_github_job",
        "admin_user_management_job",
    },
    "Infrastructure": {
        "infrastructure_ansible_playbook_executor_job",
        "infrastructure_lambda_verification_job",
        "infrastructure_pulumi_dashboard_job",
        "infrastructure_pulumi_stack_action_job",
        "infrastructure_ssm_dashboard_job",
    },
    "Infrastructure_Management": {"infrastructure_shutdown_environment_job"},
    "Code_Quality_Checker": {
        "code_quality_pr_complexity_analyzer_job",
        "code_quality_pr_complexity_analyzer_github_trigger_job",
        "code_quality_rust_code_analysis_check_job",
    },
    "Document_Generator": {
        "docs_generator_auto_insert_doxygen_comment_job",
        "docs_generator_auto_insert_doxygen_comment_test_job",
        "docs_generator_generate_doxygen_html_job",
        "docs_generator_multi_pull_request_comment_builder_job",
        "docs_generator_technical_docs_writer_job",
        "docx_generator_pull_request_comment_builder_job",
        "docx_generator_pull_request_comment_builder_github_trigger_job",
    },
}

# Expected DSL and Jenkinsfile paths for the jobs called out in the scenario document.
EXPECTED_JOB_PATHS = {
    "admin_backup_config_job": {
        "dsl": "jenkins/jobs/dsl/admin/admin_backup_config_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/admin/backup-config/Jenkinsfile",
    },
    "admin_github_webhooks_setting_job": {
        "dsl": "jenkins/jobs/dsl/admin/admin_github_webhooks_setting_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/admin/github-webhooks-setting/Jenkinsfile",
    },
    "admin_ssm_backup_job": {
        "dsl": "jenkins/jobs/dsl/admin/admin_ssm_backup_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/admin/ssm-backup/Jenkinsfile",
    },
    "admin_ssm_restore_job": {
        "dsl": "jenkins/jobs/dsl/admin/admin_ssm_restore_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/admin/ssm-restore/Jenkinsfile",
    },
    "admin_test_github_job": {"dsl": "jenkins/jobs/dsl/admin/admin_test_github_job.groovy"},
    "admin_user_management_job": {
        "dsl": "jenkins/jobs/dsl/admin/admin_user_management_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/admin/user-management/Jenkinsfile",
    },
    "infrastructure_ansible_playbook_executor_job": {
        "dsl": "jenkins/jobs/dsl/infrastructure/infrastructure_ansible_playbook_executor_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/infrastructure/ansible-playbook-executor/Jenkinsfile",
    },
    "infrastructure_lambda_verification_job": {
        "dsl": "jenkins/jobs/dsl/infrastructure/infrastructure_lambda_verification_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/infrastructure/lambda-verification/Jenkinsfile",
    },
    "infrastructure_pulumi_dashboard_job": {
        "dsl": "jenkins/jobs/dsl/infrastructure/infrastructure_pulumi_dashboard_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/infrastructure/pulumi-dashboard/Jenkinsfile",
    },
    "infrastructure_pulumi_stack_action_job": {
        "dsl": "jenkins/jobs/dsl/infrastructure/infrastructure_pulumi_stack_action_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/Jenkinsfile",
    },
    "infrastructure_ssm_dashboard_job": {
        "dsl": "jenkins/jobs/dsl/infrastructure/infrastructure_ssm_dashboard_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/infrastructure/ssm-dashboard/Jenkinsfile",
    },
    "infrastructure_shutdown_environment_job": {
        "dsl": "jenkins/jobs/dsl/infrastructure-management/infrastructure_shutdown_environment_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/infrastructure-management/shutdown-environment/Jenkinsfile",
    },
    "code_quality_pr_complexity_analyzer_job": {
        "dsl": "jenkins/jobs/dsl/code-quality-checker/code_quality_pr_complexity_analyzer_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/code-quality-checker/pr-complexity-analyzer/Jenkinsfile",
    },
    "code_quality_pr_complexity_analyzer_github_trigger_job": {
        "dsl": "jenkins/jobs/dsl/code-quality-checker/code_quality_pr_complexity_analyzer_github_trigger_job.groovy"
    },
    "code_quality_rust_code_analysis_check_job": {
        "dsl": "jenkins/jobs/dsl/code-quality-checker/code_quality_rust_code_analysis_check_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/code-quality-checker/rust-code-analysis-check/Jenkinsfile",
    },
    "docs_generator_auto_insert_doxygen_comment_job": {
        "dsl": "jenkins/jobs/dsl/docs-generator/docs_generator_auto_insert_doxygen_comment_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/docs-generator/auto-insert-doxygen-comment/Jenkinsfile",
    },
    "docs_generator_auto_insert_doxygen_comment_test_job": {
        "dsl": "jenkins/jobs/dsl/docs-generator/docs_generator_auto_insert_doxygen_comment_test_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/docs-generator/auto-insert-doxygen-comment/tests/Jenkinsfile",
    },
    "docs_generator_generate_doxygen_html_job": {
        "dsl": "jenkins/jobs/dsl/docs-generator/docs_generator_generate_doxygen_html_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/docs-generator/generate-doxygen-html/Jenkinsfile",
    },
    "docs_generator_multi_pull_request_comment_builder_job": {
        "dsl": "jenkins/jobs/dsl/docs-generator/docs_generator_multi_pull_request_comment_builder_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/docs-generator/multi-pull-request-comment-builder/Jenkinsfile",
    },
    "docs_generator_technical_docs_writer_job": {
        "dsl": "jenkins/jobs/dsl/docs-generator/docs_generator_technical_docs_writer_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/docs-generator/technical-docs-writer/Jenkinsfile",
    },
    "docx_generator_pull_request_comment_builder_job": {
        "dsl": "jenkins/jobs/dsl/docs-generator/docx_generator_pull_request_comment_builder_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/docs-generator/pull-request-comment-builder/Jenkinsfile",
    },
    "docx_generator_pull_request_comment_builder_github_trigger_job": {
        "dsl": "jenkins/jobs/dsl/docs-generator/docx_generator_pull_request_comment_builder_github_trigger_job.groovy"
    },
}

# Representative jobs used in IT-006 through IT-009.
REPRESENTATIVE_JOBS = {
    "admin_ssm_backup_job": {
        "dsl": "jenkins/jobs/dsl/admin/admin_ssm_backup_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/admin/ssm-backup/Jenkinsfile",
    },
    "infrastructure_ssm_dashboard_job": {
        "dsl": "jenkins/jobs/dsl/infrastructure/infrastructure_ssm_dashboard_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/infrastructure/ssm-dashboard/Jenkinsfile",
    },
    "code_quality_pr_complexity_analyzer_job": {
        "dsl": "jenkins/jobs/dsl/code-quality-checker/code_quality_pr_complexity_analyzer_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/code-quality-checker/pr-complexity-analyzer/Jenkinsfile",
    },
    "docx_generator_pull_request_comment_builder_job": {
        "dsl": "jenkins/jobs/dsl/docs-generator/docx_generator_pull_request_comment_builder_job.groovy",
        "jenkinsfile": "jenkins/jobs/pipeline/docs-generator/pull-request-comment-builder/Jenkinsfile",
    },
}


def load_job_config_jobs():
    """Parse the jenkins-jobs map without external dependencies."""
    jobs = {}
    current_key = None
    current_fields = {}
    in_jobs = False

    for line in JOB_CONFIG_PATH.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("jenkins-jobs:"):
            in_jobs = True
            continue

        if in_jobs and line and not line.startswith(" "):
            if stripped.startswith("#"):
                continue
            break

        if not in_jobs:
            continue

        if not stripped or stripped.startswith("#"):
            continue

        if line.startswith("  ") and not line.startswith("    "):
            if current_key:
                jobs[current_key] = current_fields
            current_key = stripped.rstrip(":")
            current_fields = {}
            continue

        if current_key and line.startswith("    "):
            if ":" not in stripped:
                continue
            key, raw_value = stripped.split(":", 1)
            value = raw_value.strip().strip("'\"")
            current_fields[key.strip()] = value

    if current_key:
        jobs[current_key] = current_fields

    return jobs


class SeedJobDynamicScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jobs = load_job_config_jobs()

    def test_seed_job_definitions_cover_phase3_targets(self):
        """Seed job config should contain all Phase 3 target jobs and their source paths."""
        self.assertGreaterEqual(
            len(self.jobs),
            22,
            msg="Seed job should manage at least the 22 Phase 3 scenario jobs.",
        )

        for category, expected_jobs in CATEGORY_EXPECTATIONS.items():
            missing = expected_jobs - set(self.jobs.keys())
            self.assertFalse(
                missing,
                msg=f"{category} is missing jobs in job-config.yaml: {missing}",
            )

        for job_name, paths in EXPECTED_JOB_PATHS.items():
            config = self.jobs.get(job_name)
            self.assertIsNotNone(config, msg=f"{job_name} is missing from job-config.yaml")

            dsl_path = REPO_ROOT / paths["dsl"]
            self.assertTrue(dsl_path.exists(), msg=f"DSL file missing for {job_name}: {paths['dsl']}")
            self.assertEqual(
                config.get("dslfile"),
                paths["dsl"],
                msg=f"{job_name} should point to DSL {paths['dsl']}",
            )

            jenkinsfile_path = paths.get("jenkinsfile")
            if jenkinsfile_path:
                self.assertEqual(
                    config.get("jenkinsfile"),
                    jenkinsfile_path,
                    msg=f"{job_name} should map to Jenkinsfile {jenkinsfile_path}",
                )
                self.assertTrue(
                    (REPO_ROOT / jenkinsfile_path).exists(),
                    msg=f"Jenkinsfile missing for {job_name}: {jenkinsfile_path}",
                )

    def test_representative_jobs_use_micro_agent_by_default(self):
        """Representative jobs must default to ec2-fleet-micro in DSL and pipelines."""
        fallback_pattern = re.compile(r"label\s+params\.AGENT_LABEL\s*\?:\s*'([^']+)'")

        for job_name, paths in REPRESENTATIVE_JOBS.items():
            dsl_text = (REPO_ROOT / paths["dsl"]).read_text()
            self.assertIn(
                EXPECTED_CHOICE_ORDER,
                dsl_text,
                msg=f"{job_name} should list ec2-fleet-micro first in AGENT_LABEL options",
            )

            pipeline_text = (REPO_ROOT / paths["jenkinsfile"]).read_text()
            fallbacks = set(fallback_pattern.findall(pipeline_text))
            self.assertTrue(
                fallbacks,
                msg=f"{job_name} Jenkinsfile must set an agent label fallback",
            )
            self.assertSetEqual(
                fallbacks,
                {"ec2-fleet-micro"},
                msg=f"{job_name} should default to ec2-fleet-micro but found {fallbacks}",
            )

    def test_freestyle_triggers_present_and_pinned_to_micro(self):
        """Freestyle trigger jobs should exist in the seed config and stay on micro agents."""
        trigger_jobs = {
            "code_quality_pr_complexity_analyzer_github_trigger_job": "pr-complexity-analyzer",
            "docx_generator_pull_request_comment_builder_github_trigger_job": "pull_request_comment_builder",
        }

        for job_name, downstream in trigger_jobs.items():
            config = self.jobs.get(job_name, {})
            self.assertIn(
                "downstreamJob",
                config,
                msg=f"{job_name} should declare downstreamJob in job-config.yaml",
            )
            self.assertEqual(
                config.get("downstreamJob"),
                downstream,
                msg=f"{job_name} should trigger {downstream}",
            )

            dsl_path = REPO_ROOT / EXPECTED_JOB_PATHS[job_name]["dsl"]
            dsl_text = dsl_path.read_text()
            self.assertIn(
                "label('ec2-fleet-micro')",
                dsl_text,
                msg=f"{job_name} should pin to ec2-fleet-micro",
            )

    def test_agent_label_choice_allows_manual_override(self):
        """All AGENT_LABEL choice parameters should expose micro/small/medium options."""
        offenders = []
        for path in DSL_ROOT.rglob("*.groovy"):
            text = path.read_text()
            if "choiceParam('AGENT_LABEL'" in text and EXPECTED_CHOICE_ORDER not in text:
                offenders.append(path.relative_to(DSL_ROOT))

        self.assertFalse(
            offenders,
            msg=f"AGENT_LABEL choiceParam missing expected options in: {offenders}",
        )

    def test_pipelines_use_requested_label_on_agent_blocks(self):
        """Pipelines that expose AGENT_LABEL should honor it in agent label blocks."""
        offenders = []
        label_pattern = re.compile(r"label\s+params\.AGENT_LABEL")

        for path in PIPELINE_ROOT.rglob("Jenkinsfile"):
            contents = path.read_text()
            if "params.AGENT_LABEL" in contents and not label_pattern.search(contents):
                offenders.append(path.relative_to(PIPELINE_ROOT))

        self.assertFalse(
            offenders,
            msg=f"Pipelines using params.AGENT_LABEL should set agent labels: {offenders}",
        )


if __name__ == "__main__":
    unittest.main()
