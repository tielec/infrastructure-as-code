"""Integration tests for Issue #544: CloudWatch Agent CPU metrics on Jenkins Agent AMI."""

import json
import os
import re
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
    def _render_components(cls) -> dict:
        result = subprocess.run(
            ["node", str(cls.helper_script)],
            cwd=cls.repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def _component_map(self):
        components = self.preview.get("components", [])
        self.assertGreaterEqual(len(components), 2, "Both ARM/x86 components should be synthesized")
        return {c["name"]: c for c in components}

    def _extract_cloudwatch_config(self, component_data: str) -> dict:
        self.assertNotIn("__CWAGENT_CONFIG__", component_data, "Template placeholder must be replaced")
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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
