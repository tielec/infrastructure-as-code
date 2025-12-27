"""Integration checks that documentation updates align with the Pulumi ECS resources (Issue #540)."""

from pathlib import Path
import unittest


class InfrastructureDocumentationConsistencyTests(unittest.TestCase):
    """Validate ECS documentation content against the Pulumi implementation."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.infrastructure_doc = (
            cls.repo_root / "docs" / "architecture" / "infrastructure.md"
        )
        cls.pulumi_agent = cls.repo_root / "pulumi" / "jenkins-agent" / "index.ts"
        cls.docker_dir = cls.repo_root / "docker" / "jenkins-agent-ecs"
        cls.expected_ssm_params = [
            "/jenkins-infra/{environment}/agent/ecs-cluster-arn",
            "/jenkins-infra/{environment}/agent/ecs-cluster-name",
            "/jenkins-infra/{environment}/agent/ecs-task-definition-arn",
            "/jenkins-infra/{environment}/agent/ecr-repository-url",
            "/jenkins-infra/{environment}/agent/ecs-execution-role-arn",
            "/jenkins-infra/{environment}/agent/ecs-task-role-arn",
            "/jenkins-infra/{environment}/agent/ecs-log-group-name",
        ]

    def test_ecs_resource_sections_exist(self):
        """Ensure the ECS resource subsections that document Pulumi resources exist."""
        doc_text = self.infrastructure_doc.read_text(encoding="utf-8")
        headers = [
            "### ECS Cluster",
            "### ECR Repository",
            "### Task Definition",
            "### IAM Roles",
            "### CloudWatch Logs",
        ]
        for header in headers:
            self.assertIn(
                header,
                doc_text,
                f"{header} section should be present in infrastructure documentation",
            )

    def test_spotfleet_vs_ecs_comparison_and_guidance_present(self):
        """Confirm the SpotFleet vs ECS comparison table and guidance text remain in the doc."""
        doc_text = self.infrastructure_doc.read_text(encoding="utf-8")
        self.assertIn(
            "| 観点 | SpotFleet | ECS Fargate |",
            doc_text,
            "SpotFleet vs ECS Fargate comparison table header should exist",
        )
        self.assertIn(
            "#### 使い分けの指針",
            doc_text,
            "The guidance section should explain when to prefer each agent type",
        )

    def test_docker_agent_ecs_section_matches_artifacts(self):
        """Verify docker/jenkins-agent-ecs documentation describes actual files."""
        doc_text = self.infrastructure_doc.read_text(encoding="utf-8")
        self.assertIn(
            "docker/jenkins-agent-ecs",
            doc_text,
            "The documentation must mention docker/jenkins-agent-ecs directory",
        )
        for filename in ("Dockerfile", "entrypoint.sh"):
            path = self.docker_dir / filename
            self.assertTrue(
                path.is_file(),
                f"{path} should exist as documented in docker/jenkins-agent-ecs",
            )
            self.assertIn(
                filename,
                doc_text,
                f"The documentation should describe {filename} in docker/jenkins-agent-ecs",
            )

    def test_ssm_parameters_are_documented_and_exported(self):
        """Ensure the documented SSM parameters exist both in the doc and Pulumi exports."""
        doc_text = self.infrastructure_doc.read_text(encoding="utf-8")
        pulumi_text = self.pulumi_agent.read_text(encoding="utf-8")
        for param in self.expected_ssm_params:
            self.assertIn(
                param,
                doc_text,
                f"{param} should be listed in the ECS SSM Parameter table",
            )
            param_name = param.split("/")[-1]
            self.assertIn(
                f"agent/{param_name}",
                pulumi_text,
                f"{param_name} should be exported in pulumi/jenkins-agent/index.ts",
            )


if __name__ == "__main__":
    unittest.main()
