"""Integration tests for Issue #547: CloudWatch Agent validation on Jenkins Agent AMI."""

import json
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
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

    def _extract_cloudwatch_config(self, component_data: str, component_name: str) -> dict:
        self.assertNotIn("__CWAGENT_CONFIG__", component_data, "Template placeholder must be replaced")
        # Pull the CloudWatch Agent heredoc body out of the component YAML for JSON decoding.
        match = re.search(
            r"amazon-cloudwatch-agent\.json << 'EOF'\n(?P<body>.*?)\n\s*EOF",
            component_data,
            re.DOTALL,
        )
        self.assertIsNotNone(
            match, f"CloudWatch Agent config heredoc should be embedded in component data ({component_name})"
        )
        try:
            return json.loads(match.group("body").strip())
        except json.JSONDecodeError as exc:
            self.fail(f"[{component_name}] Embedded CloudWatch Agent config is not valid JSON: {exc}")

    def _extract_validation_script(self, component_data: str, config_path: Path) -> str:
        match = re.search(
            r"- name: ValidateCloudWatchAgentConfig[\s\S]*?- \|\n(?P<body>[\s\S]*?)\n\s*- cat /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json",
            component_data,
        )
        self.assertIsNotNone(match, "Validation script block should be present in component YAML")
        script = textwrap.dedent(match.group("body")).strip()
        return script.replace("/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json", str(config_path))

    def _run_validation_step(self, *, config_body: str | None, component_name: str = "agent-component-x86"):
        component_data = self._component_map()[component_name]["data"]
        with tempfile.TemporaryDirectory() as tempdir:
            config_path = Path(tempdir) / "amazon-cloudwatch-agent.json"
            if config_body is not None:
                config_path.write_text(config_body)
            script = self._extract_validation_script(component_data, config_path)
            command = f'echo "Validating CloudWatch Agent configuration..."\n{script}'
            if config_body is not None:
                command += f'\ncat "{config_path}"'
            result = subprocess.run(
                ["bash", "-eo", "pipefail", "-c", command],
                capture_output=True,
                text=True,
            )
            output = (result.stdout or "") + (result.stderr or "")
            return result.returncode, output

    def _run_enable_step(self, *, component_name: str):
        component_data = self._component_map()[component_name]["data"]
        match = re.search(
            r"- name: EnableCloudWatchAgent[\s\S]*?commands:\s*(?P<body>(?:\s*- .*\n)+?)(?:\n\s*- name:|\Z)",
            component_data,
        )
        self.assertIsNotNone(match, "EnableCloudWatchAgent step should be present in component YAML")
        lines = []
        for line in match.group("body").strip().splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                lines.append(stripped[2:])
        script = "\n".join(lines)
        with tempfile.TemporaryDirectory() as tempdir:
            shim = Path(tempdir) / "systemctl"
            shim.write_text("#!/usr/bin/env bash\necho \"systemctl $@\"\nexit 0\n")
            shim.chmod(0o755)
            env = {**os.environ, "PATH": f"{tempdir}:{os.environ.get('PATH', '')}", "SYSTEMD_COLORS": "0"}
            result = subprocess.run(
                ["bash", "-eo", "pipefail", "-c", script],
                capture_output=True,
                text=True,
                env=env,
            )
            output = (result.stdout or "") + (result.stderr or "")
            return result.returncode, output

    def test_cloudwatch_agent_config_is_embedded_and_equal_between_architectures(self):
        """IT-544-01: ARM/x86 components should share identical CloudWatch Agent CPU/Mem config."""
        components = self._component_map()
        self.assertSetEqual(set(components.keys()), {"agent-component-x86", "agent-component-arm"})

        configs = {name: self._extract_cloudwatch_config(comp["data"], name) for name, comp in components.items()}
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
        config = self._extract_cloudwatch_config(self._component_map()["agent-component-x86"]["data"], "agent-component-x86")
        append_dims = config["metrics"]["append_dimensions"]
        agg_dims = config["metrics"]["aggregation_dimensions"]
        self.assertEqual(
            {"AutoScalingGroupName": "${aws:AutoScalingGroupName}"},
            append_dims,
            "ASG append dimension should be present for per-ASG dashboards",
        )
        self.assertEqual([["AutoScalingGroupName"]], agg_dims)
        self.assertEqual("CWAgent", config["metrics"]["namespace"])

    def test_validation_step_uses_jq_and_rejects_translator_dependency(self):
        """IT-547-03: Components should validate CloudWatch Agent config with jq instead of the translator binary."""
        required_snippets = [
            "ValidateCloudWatchAgentConfig",
            'CONFIG_PATH="/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"',
            "jq empty \"$CONFIG_PATH\"",
            "Invalid JSON syntax",
            "'metrics' section not found in configuration",
            "CloudWatch Agent configuration validation passed.",
            "set -e",
        ]
        for name, comp in self._component_map().items():
            data = comp["data"]
            for snippet in required_snippets:
                self.assertIn(snippet, data, f"{name} validation step should include '{snippet}'")
            self.assertNotIn(
                "amazon-cloudwatch-agent-config-translator",
                data,
                f"{name} must not rely on the deprecated translator binary",
            )

    def test_validation_step_succeeds_with_valid_config_on_both_architectures(self):
        """IT-547-06: Simulated Image Builder validation succeeds for valid config on x86 and arm."""
        valid_config = (self.ami_dir / "templates" / "cloudwatch-agent-config.json").read_text()
        for component_name in ("agent-component-x86", "agent-component-arm"):
            code, output = self._run_validation_step(config_body=valid_config, component_name=component_name)
            self.assertEqual(0, code, f"{component_name} validation should exit successfully")
            self.assertIn("Validating CloudWatch Agent configuration...", output)
            self.assertIn("Checking JSON syntax...", output)
            self.assertIn("CloudWatch Agent configuration validation passed.", output)

    def test_validation_step_errors_when_config_missing(self):
        """IT-547-07: Missing CloudWatch Agent config should fail validation with an error."""
        code, output = self._run_validation_step(config_body=None)
        self.assertNotEqual(0, code, "Validation must fail when the config file is absent")
        self.assertIn("Configuration file not found", output)
        self.assertNotIn("CloudWatch Agent configuration validation passed.", output)

    def test_validation_step_errors_on_invalid_json(self):
        """IT-547-08: Invalid JSON should raise a fatal error during validation."""
        invalid_config = '{"metrics": {"namespace": "CWAgent", "metrics_collected": {"cpu": {"resources": ["*"]}}'
        code, output = self._run_validation_step(config_body=invalid_config)
        self.assertNotEqual(0, code, "Validation must fail on malformed JSON")
        self.assertIn("Invalid JSON syntax", output)
        self.assertRegex(output, r"parse error|Invalid JSON", "jq should report parsing failure details")

    def test_validation_step_warns_when_metrics_section_absent(self):
        """IT-547-09: Missing metrics section should emit warning but continue."""
        no_metrics_config = json.dumps({"logs": {"logs_collected": {"files": {"collect_list": []}}}})
        code, output = self._run_validation_step(config_body=no_metrics_config)
        self.assertEqual(0, code, "Validation should succeed even when metrics are absent")
        self.assertIn("WARNING: 'metrics' section not found in configuration", output)
        self.assertIn("CloudWatch Agent configuration validation passed.", output)

    def test_enable_step_can_run_with_systemctl_shim(self):
        """IT-547-10: EnableCloudWatchAgent should trigger service enablement when validation passes."""
        for component_name in ("agent-component-x86", "agent-component-arm"):
            code, output = self._run_enable_step(component_name=component_name)
            self.assertEqual(0, code, f"{component_name} enable step should succeed with stub systemctl")
            self.assertIn("Enabling CloudWatch Agent service...", output)
            self.assertIn("systemctl enable amazon-cloudwatch-agent", output)
            self.assertIn("CloudWatch Agent will start automatically on instance boot", output)

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
