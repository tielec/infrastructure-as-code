"""Integration tests verifying the Jenkins job-config YAML changes."""

import ast
import unittest
from pathlib import Path
from typing import Any, Dict, Tuple


def parse_job_config_yaml(path: Path) -> Dict[str, Any]:
    """Parse the job-config.yaml file into a nested dictionary using indentation."""
    root: Dict[str, Any] = {}
    stack: list[Tuple[int, Dict[str, Any]]] = [(-1, root)]

    for raw_line in path.read_text().splitlines():
        sanitized = raw_line.split("#", 1)[0].rstrip()
        if not sanitized.strip():
            continue

        indent = len(sanitized) - len(sanitized.lstrip(" "))
        content = sanitized.lstrip(" ")
        if ":" not in content:
            continue

        key, remainder = content.split(":", 1)
        key = key.strip()
        value_part = remainder.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if not value_part:
            node: Dict[str, Any] = {}
            parent[key] = node
            stack.append((indent, node))
        else:
            parent[key] = _literal_value(value_part)

    return root


def _literal_value(value: str) -> Any:
    """Convert a scalar value to its Python equivalent when possible."""
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return value


class JobConfigYamlTests(unittest.TestCase):
    """Integration tests that cover pulumi-projects configuration."""

    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]
        cls.root = root
        cls.config = parse_job_config_yaml(
            root / "jenkins" / "jobs" / "pipeline" / "_seed" / "job-creator" / "job-config.yaml"
        )
        # Re-use nested sections for scenario-specific checks.
        cls.projects = (
            cls.config["pulumi-projects"]["infrastructure-as-code"]["projects"]
        )
        cls.ansible_playbooks = (
            cls.config["ansible-playbooks"]["infrastructure-as-code"]["playbooks"]
        )

    def test_pulumi_projects_structure_exists(self):
        pulumi_projects = self.config.get("pulumi-projects")
        self.assertIsInstance(pulumi_projects, dict, "pulumi-projects section must exist")

        infra = pulumi_projects.get("infrastructure-as-code")
        self.assertIsInstance(infra, dict, "infrastructure-as-code section must exist")

        projects = infra.get("projects")
        self.assertIsInstance(projects, dict, "projects section must exist")
        self.assertIn("jenkins_agent", projects)
        self.assertIn("jenkins_agent_ami", projects)

    def test_jenkins_agent_project_has_expected_values(self):
        projects = (
            self.config["pulumi-projects"]["infrastructure-as-code"]["projects"]
        )
        agent = projects["jenkins_agent"]
        self.assertEqual(agent.get("project_path"), "pulumi/jenkins-agent")
        self.assertEqual(agent.get("display_name"), "Jenkins Agent")
        self.assertEqual(agent.get("project_type"), "nodejs")
        self.assertEqual(agent.get("description"), "Jenkins Agent Infrastructure (Spot Fleet)")
        self.assertListEqual(agent.get("environments"), ["dev"], "jenkins_agent must target dev only")

    def test_jenkins_agent_ami_project_has_expected_values(self):
        projects = (
            self.config["pulumi-projects"]["infrastructure-as-code"]["projects"]
        )
        ami = projects["jenkins_agent_ami"]
        self.assertEqual(ami.get("project_path"), "pulumi/jenkins-agent-ami")
        self.assertEqual(ami.get("display_name"), "Jenkins Agent AMI")
        self.assertEqual(ami.get("project_type"), "nodejs")
        self.assertEqual(
            ami.get("description"), "Jenkins Agent AMI builder using EC2 Image Builder"
        )
        self.assertListEqual(ami.get("environments"), ["dev"], "jenkins_agent_ami must target dev only")

    def test_projects_parse_without_errors(self):
        # sanity check: parsing should produce more than just the new entries.
        self.assertGreaterEqual(
            len(self.config), 3, "job-config.yaml should contain multiple top-level sections"
        )

    def test_job_dsl_receives_pulumi_projects_configuration(self):
        """Scenario 3.2: Jenkins DSL seed job should pass pulumi-projects data to downstream scripts."""
        jenkinsfile = (
            self.root
            / "jenkins"
            / "jobs"
            / "pipeline"
            / "_seed"
            / "job-creator"
            / "Jenkinsfile"
        ).read_text()
        self.assertIn(
            "additionalParams['pulumi_projects'] = jobConfig['pulumi-projects']",
            jenkinsfile,
            "Seed job must forward pulumi-projects config to Job DSL",
        )
        self.assertIn(
            "echo \"Pulumi projects: ${jobConfig['pulumi-projects'].size()}\"",
            jenkinsfile,
            "Seed job should log the number of pulumi projects to demonstrate visibility",
        )

    def test_pulumi_dashboard_job_mentions_new_projects(self):
        """Scenario 3.3: Pulumi dashboard job should advertise project selection controls."""
        dashboard_script = (
            self.root
            / "jenkins"
            / "jobs"
            / "dsl"
            / "infrastructure"
            / "infrastructure_pulumi_dashboard_job.groovy"
        ).read_text()
        self.assertIn(
            "Pulumi Projects Dashboard",
            dashboard_script,
            "Dashboard DSL should show the human-friendly dashboard title",
        )
        self.assertIn(
            "choiceParam('PROJECT_FILTER'",
            dashboard_script,
            "Dashboard job must allow filtering projects for display (new entries should be selectable)",
        )
        self.assertIn(
            "choiceParam('AWS_REGION'",
            dashboard_script,
            "Dashboard job must expose AWS region choice so stacks for dev/prod remain reachable",
        )
        self.assertIn(
            "stringParam('PROJECT_FILTER'",
            dashboard_script,
            "Dashboard job should allow users to type project filters, covering both Jenkins Agent entries",
        )

    def test_existing_lambda_and_ssm_entries_remain_intact(self):
        """Scenario 3.5: Verify that lambda/ssm-related configuration is unaffected."""
        lambda_keys = [
            "lambda_ssm_init",
            "lambda_shipment_s3",
            "lambda_network",
            "lambda_security",
            "lambda_nat",
            "lambda_vpce",
            "lambda_functions",
            "lambda_api_gateway",
        ]
        for key in lambda_keys:
            project = self.projects.get(key)
            self.assertIsNotNone(project, f"Expected existing lambda project '{key}' to still exist")
            envs = project.get("environments", [])
            self.assertIn("dev", envs, f"Lambda project '{key}' should still target dev")
            self.assertIn("prod", envs, f"Lambda project '{key}' should still target prod")

        expect_ssm_playbooks = [
            "update_jenkins_ami_ssm",
            "cleanup_image_builder_amis",
            "lambda_ssm_init_deploy",
            "lambda_ssm_init_remove",
        ]
        for key in expect_ssm_playbooks:
            self.assertIn(
                key,
                self.ansible_playbooks,
                f"Playbook '{key}' should remain to demonstrate SSM feature continuity",
            )


if __name__ == "__main__":
    unittest.main()
