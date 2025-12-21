"""Integration checks for AGENT_LABEL parameterization across Jenkinsfiles."""

import re
import subprocess
import unittest
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[2] / "jenkins" / "jobs" / "pipeline"

# Expected fallback values aligned with the DSL defaults per category.
AGENT_FALLBACKS = {
    "admin/backup-config/Jenkinsfile": "ec2-fleet-small",
    "admin/github-webhooks-setting/Jenkinsfile": "ec2-fleet-small",
    "admin/ssm-backup/Jenkinsfile": "ec2-fleet-small",
    "admin/ssm-restore/Jenkinsfile": "ec2-fleet-small",
    "admin/user-management/Jenkinsfile": "ec2-fleet-small",
    "account-setup/user-self-activation/Jenkinsfile": "ec2-fleet-small",
    "code-quality-checker/pr-complexity-analyzer/Jenkinsfile": "ec2-fleet-small",
    "code-quality-checker/rust-code-analysis-check/Jenkinsfile": "ec2-fleet-small",
    "docs-generator/auto-insert-doxygen-comment/Jenkinsfile": "ec2-fleet-small",
    "docs-generator/auto-insert-doxygen-comment/tests/Jenkinsfile": "ec2-fleet-small",
    "docs-generator/diagram-generator/Jenkinsfile": "ec2-fleet-small",
    "docs-generator/generate-doxygen-html/Jenkinsfile": "ec2-fleet-small",
    "docs-generator/mermaid-generator/Jenkinsfile": "ec2-fleet-small",
    "docs-generator/multi-pull-request-comment-builder/Jenkinsfile": "ec2-fleet-small",
    "docs-generator/pull-request-comment-builder/Jenkinsfile": "ec2-fleet-small",
    "docs-generator/technical-docs-writer/Jenkinsfile": "ec2-fleet-small",
    "infrastructure/ansible-playbook-executor/Jenkinsfile": "ec2-fleet-small",
    "infrastructure/lambda-verification/Jenkinsfile": "ec2-fleet-small",
    "infrastructure/pulumi-dashboard/Jenkinsfile": "ec2-fleet-medium",
    "infrastructure/ssm-dashboard/Jenkinsfile": "ec2-fleet-small",
    "shared-library/test-aws-utils/sqs-check-operation/Jenkinsfile": "ec2-fleet-micro",
    "shared-library/test-git-utils/deploykeys-operation/Jenkinsfile": "ec2-fleet-micro",
    "shared-library/test-git-utils/github-apps-basic-operation/Jenkinsfile": "ec2-fleet-micro",
    "shared-library/test-git-utils/webhook-operation/Jenkinsfile": "ec2-fleet-micro",
    "shared-library/test-jenkins-utils/credentials-operation/Jenkinsfile": "ec2-fleet-micro",
    "shared-library/test-ssm-parameter/Jenkinsfile": "ec2-fleet-micro",
    "infrastructure/pulumi-stack-action/Jenkinsfile": "ec2-fleet-medium",
}

# Files intentionally left on built-in to ensure controller-executed jobs stay untouched.
BUILT_IN_JOBS = {
    "_seed/job-creator/Jenkinsfile",
    "admin/restore-config/Jenkinsfile",
    "infrastructure-management/shutdown-environment/Jenkinsfile",
}


class AgentLabelParameterizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jenkinsfiles = list(PIPELINE_ROOT.rglob("Jenkinsfile"))

    def test_ec2_fleet_label_removed(self):
        """Static guard: old ec2-fleet label must be fully removed."""
        result = subprocess.run(
            ["grep", "-R", "label 'ec2-fleet'", str(PIPELINE_ROOT)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            1,
            msg=f"Found legacy ec2-fleet labels:\n{result.stdout}{result.stderr}",
        )

    def test_params_agent_label_present_on_expected_files(self):
        agent_label_files = {
            path
            for path in self.jenkinsfiles
            if "params.AGENT_LABEL" in path.read_text()
        }
        expected_paths = {PIPELINE_ROOT / rel for rel in AGENT_FALLBACKS}

        self.assertGreaterEqual(
            len(agent_label_files),
            27,
            "At least 27 Jenkinsfiles should use params.AGENT_LABEL (26 updated + existing pulumi-stack-action).",
        )
        self.assertTrue(
            expected_paths.issubset(agent_label_files),
            msg="Some target Jenkinsfiles are missing params.AGENT_LABEL.",
        )

    def test_agent_label_always_has_fallback(self):
        """Ensure every params.AGENT_LABEL usage keeps the Elvis operator fallback."""
        pattern = re.compile(r"params\.AGENT_LABEL\s*\?:\s*'([^']+)'")

        for rel_path, expected_fallback in AGENT_FALLBACKS.items():
            path = PIPELINE_ROOT / rel_path
            contents = path.read_text()
            matches = set(pattern.findall(contents))
            self.assertTrue(
                matches,
                msg=f"No Elvis fallback found in {rel_path}",
            )
            self.assertSetEqual(
                matches,
                {expected_fallback},
                msg=f"{rel_path} should use fallback '{expected_fallback}' but found {matches}",
            )

    def test_no_agent_label_without_elvis_operator(self):
        """Guard against params.AGENT_LABEL being used without ?: fallback."""
        pattern = re.compile(r"params\.AGENT_LABEL(?!\s*\?:)")
        offenders = []
        for path in self.jenkinsfiles:
            text = path.read_text()
            if pattern.search(text):
                offenders.append(path.relative_to(PIPELINE_ROOT))

        self.assertFalse(
            offenders,
            msg=f"Found params.AGENT_LABEL without Elvis fallback in: {offenders}",
        )

    def test_built_in_label_jobs_are_unchanged(self):
        for rel_path in BUILT_IN_JOBS:
            path = PIPELINE_ROOT / rel_path
            contents = path.read_text()
            self.assertIn("label 'built-in'", contents, f"{rel_path} should remain on built-in")
            self.assertNotIn("params.AGENT_LABEL", contents, f"{rel_path} must not be parameterized")


if __name__ == "__main__":
    unittest.main()
