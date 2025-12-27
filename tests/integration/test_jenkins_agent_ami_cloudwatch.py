"""Integration tests for Issue #544: CloudWatch Agent CPU metrics on Jenkins Agent AMI."""

import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path


class JenkinsAgentAmiCloudWatchTests(unittest.TestCase):
    """INTEGRATION_ONLY checks for Image Builder components and CloudWatch Agent config."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.ami_dir = cls.repo_root / "pulumi" / "jenkins-agent-ami"
        cls.helper_script = cls.repo_root / "tests" / "integration" / "helpers" / "render_jenkins_agent_ami_components.js"
        cls.compiled_index = cls.ami_dir / "bin" / "index.js"
        cls._install_node_dependencies()
        cls._build_typescript()
        cls._ensure_pulumi_assets_in_bin()
        cls.preview = cls._render_components()

    @classmethod
    def _install_node_dependencies(cls):
        subprocess.run(
            ["npm", "--silent", "install"],
            cwd=cls.ami_dir,
            check=True,
        )

    @classmethod
    def _build_typescript(cls):
        env = {**os.environ, "NODE_OPTIONS": "--max-old-space-size=4096"}
        subprocess.run(
            ["npm", "--silent", "run", "build"],
            cwd=cls.ami_dir,
            check=True,
            env=env,
        )
        if not cls.compiled_index.exists():
            raise AssertionError("TypeScript build did not produce bin/index.js")

    @classmethod
    def _ensure_pulumi_assets_in_bin(cls):
        """Copy CloudWatch template and component YAMLs next to the compiled index for synthesis."""
        assets = [
            (
                cls.ami_dir / "templates" / "cloudwatch-agent-config.json",
                cls.compiled_index.parent / "templates" / "cloudwatch-agent-config.json",
            ),
            (cls.ami_dir / "component-arm.yml", cls.compiled_index.parent / "component-arm.yml"),
            (cls.ami_dir / "component-x86.yml", cls.compiled_index.parent / "component-x86.yml"),
        ]
        for source, destination in assets:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    @classmethod
    def _render_components(cls) -> dict:
        env = {**os.environ, "NODE_OPTIONS": "--max-old-space-size=4096"}
        result = subprocess.run(
            ["node", str(cls.helper_script)],
            cwd=cls.repo_root,
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        return json.loads(result.stdout)

    def _component_map(self):
        components = self.preview.get("components", [])
        self.assertGreaterEqual(len(components), 2, "Both ARM/x86 components should be synthesized")
        return {c["name"]: c for c in components}

    def _extract_cloudwatch_config(self, component_data: str) -> dict:
        self.assertNotIn("__CWAGENT_CONFIG__", component_data, "Template placeholder must be replaced")
        # Pull the CloudWatch Agent heredoc body out of the component YAML for JSON decoding.
        match = re.search(
            r"amazon-cloudwatch-agent\.json << 'EOF'\n(?P<body>.*?)\n\s*EOF",
            component_data,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "CloudWatch Agent config heredoc should be embedded in component data")
        try:
            return json.loads(match.group("body").strip())
        except json.JSONDecodeError as exc:
            self.fail(f"Embedded CloudWatch Agent config is not valid JSON: {exc}")

    def test_cloudwatch_agent_config_is_embedded_and_equal_between_architectures(self):
        """IT-544-01: ARM/x86 components should share identical CloudWatch Agent CPU/Mem config."""
        components = self._component_map()
        self.assertSetEqual(set(components.keys()), {"agent-component-x86", "agent-component-arm"})

        configs = {name: self._extract_cloudwatch_config(comp["data"]) for name, comp in components.items()}
        self.assertEqual(
            configs["agent-component-x86"],
            configs["agent-component-arm"],
            "CloudWatch Agent config must be identical between architectures",
        )

        cpu_measurements = [
            item["name"] for item in configs["agent-component-x86"]["metrics"]["metrics_collected"]["cpu"]["measurement"]
        ]
        self.assertCountEqual(
            cpu_measurements,
            ["cpu_usage_active", "cpu_usage_user", "cpu_usage_system", "cpu_usage_iowait"],
            "CPU measurements should cover active/user/system/iowait",
        )
        cpu_interval = configs["agent-component-x86"]["metrics"]["metrics_collected"]["cpu"]["metrics_collection_interval"]
        mem_interval = configs["agent-component-x86"]["metrics"]["metrics_collected"]["mem"]["metrics_collection_interval"]
        self.assertEqual(60, cpu_interval)
        self.assertEqual(60, mem_interval)

    def test_cloudwatch_agent_config_uses_autoscaling_dimensions(self):
        """IT-544-02: Metrics must aggregate on AutoScalingGroupName for dashboards/alarms."""
        config = self._extract_cloudwatch_config(self._component_map()["agent-component-x86"]["data"])
        append_dims = config["metrics"]["append_dimensions"]
        agg_dims = config["metrics"]["aggregation_dimensions"]
        self.assertEqual(
            {"AutoScalingGroupName": "${aws:AutoScalingGroupName}"},
            append_dims,
            "ASG append dimension should be present for per-ASG dashboards",
        )
        self.assertEqual([["AutoScalingGroupName"]], agg_dims)
        self.assertEqual("CWAgent", config["metrics"]["namespace"])

    def test_translator_validation_step_present_in_components(self):
        """IT-544-03: Components should run amazon-cloudwatch-agent-config-translator to fail fast."""
        for name, comp in self._component_map().items():
            data = comp["data"]
            self.assertIn("ValidateCloudWatchAgentConfig", data, f"{name} should validate the agent config")
            self.assertIn("amazon-cloudwatch-agent-config-translator", data)
            self.assertIn("-input /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json", data)
            self.assertIn("-output /tmp/cwagent.translated.json", data)
            self.assertIn("Translator not found", data, "Translator presence check should protect the build")

    def test_pulumi_preview_diff_is_constrained(self):
        """IT-544-04: Pulumi preview (mocked) should surface only expected resources/exports."""
        expected_exports = {
            "imagePipelineX86Arn",
            "imagePipelineArmArn",
            "imageBuilderRoleArn",
            "jenkinsAgentComponentX86Arn",
            "jenkinsAgentComponentArmArn",
            "customAmiX86ParameterName",
            "customAmiArmParameterName",
            "currentComponentVersion",
            "currentRecipeVersion",
        }
        self.assertEqual(
            21,
            self.preview.get("resourceCount"),
            "Preview should only synthesize the known Image Builder resources after CPU metric addition",
        )
        self.assertSetEqual(expected_exports, set(self.preview.get("exports", [])))

    def test_dashboard_and_alarm_guidance_is_documented(self):
        """IT-544-05: CPU dashboard/alarm initial values should be recorded for ops handoff."""
        doc_path = self.repo_root / "docs" / "operations" / "jenkins-agent-cloudwatch.md"
        self.assertTrue(doc_path.exists(), "Operations doc for CPU dashboards/alarms must exist")
        content = doc_path.read_text(encoding="utf-8")
        self.assertIn("AutoScalingGroupName", content, "ASG dimension must be documented for dashboards/alarms")
        self.assertRegex(content, r"(CPU.*80%|80%.*CPU)", "CPU high-usage threshold guidance should be present")
        self.assertRegex(content, r"(5 ?minutes|5\\s*分)", "Sustained high-usage period guidance should be present")
        self.assertIn("adjust", content.lower(), "Operators should be instructed that thresholds are tunable")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
