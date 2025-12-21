"""Integration tests for ec2-fleet legacy removal (Issue #508)."""

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = ROOT / "scripts" / "jenkins" / "casc" / "jenkins.yaml.template"
SCRIPT_PATH = ROOT / "scripts" / "jenkins" / "shell" / "application-configure-with-casc.sh"
JOBS_ROOT = ROOT / "jenkins" / "jobs"


class Ec2FleetRemovalIntegrationTests(unittest.TestCase):
    """Covers Phase 3 integration scenarios for removing legacy ec2-fleet config."""

    @classmethod
    def setUpClass(cls):
        cls.template_text = TEMPLATE_PATH.read_text()
        cls.script_text = SCRIPT_PATH.read_text()
        cls.envsubst_variables = cls._extract_envsubst_variables(cls.script_text)

    @staticmethod
    def _extract_envsubst_variables(script_text: str) -> set[str]:
        match = re.search(r"envsubst '([^']+)' <", script_text)
        if not match:
            return set()
        tokens = match.group(1).split()
        return {token.lstrip("$") for token in tokens if token.startswith("$")}

    def test_yaml_template_parses_with_pyyaml(self):
        """IT-001: YAML syntax should remain valid after legacy removal."""
        if yaml is None:
            self.skipTest("PyYAML is required for this check; install pyyaml to run it.")

        parsed = yaml.safe_load(self.template_text)
        self.assertIsInstance(parsed, dict, "Template should parse into a mapping")

    def test_shell_script_passes_bash_syntax_check(self):
        """IT-003: Bash should accept the script without syntax errors."""
        result = subprocess.run(
            ["bash", "-n", str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"Bash syntax check failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
        )

    def test_shellcheck_reports_no_errors(self):
        """IT-002: shellcheck should not report errors (warnings allowed)."""
        shellcheck = shutil.which("shellcheck")
        if not shellcheck:
            self.skipTest("shellcheck is not available in PATH.")

        result = subprocess.run(
            [shellcheck, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertIn(
            result.returncode,
            (0, 1),  # 1 indicates warnings only
            f"shellcheck reported errors (exit code {result.returncode}).\nSTDERR:\n{result.stderr}",
        )

    def test_template_drops_legacy_ec2_fleet_blocks(self):
        """IT-004: Legacy ec2-fleet block and variables must be absent."""
        legacy_vars = [
            "EC2_FLEET_ID",
            "EC2_IDLE_MINUTES",
            "EC2_MIN_SIZE",
            "EC2_MAX_SIZE",
            "EC2_NUM_EXECUTORS",
        ]
        self.assertIsNone(
            re.search(r'name:\s*"ec2-fleet"(?!-)', self.template_text),
            "Plain ec2-fleet cloud should be removed",
        )
        for var in legacy_vars:
            self.assertIsNone(
                re.search(rf"\$\{{{var}\}}", self.template_text),
                f"{var} should not be referenced in the template",
            )
        self.assertNotIn("後方互換性のため既存のec2-fleet設定を維持", self.template_text)

    def test_template_keeps_expected_cloud_definitions(self):
        """IT-005: Size-specific fleets and other clouds must remain."""
        expected_snippets = [
            'name: "ec2-fleet-medium"',
            'name: "ec2-fleet-small"',
            'name: "ec2-fleet-micro"',
            'name: "ecs-fargate"',
            'name: "bootstrap-workterminal"',
            "${EC2_FLEET_MEDIUM_ID}",
            "${EC2_FLEET_SMALL_ID}",
            "${EC2_FLEET_MICRO_ID}",
        ]
        for snippet in expected_snippets:
            self.assertIn(snippet, self.template_text, f"Missing expected snippet: {snippet}")

    def test_shell_script_excludes_legacy_variables(self):
        """IT-006: Legacy env vars and messages should be gone from the script."""
        forbidden_patterns = [
            r"\bEC2_FLEET_ID\b",
            r"\bEC2_MIN_SIZE\b",
            r"\bEC2_MAX_SIZE\b",
            r"\bEC2_NUM_EXECUTORS\b",
            r"\bEC2_IDLE_MINUTES\b",
            r"/agent/spotFleetRequestId\"(?!-)",
            r"/config/agent-min-capacity\"",
            r"/config/agent-max-capacity\"",
            r"\(legacy\)",
        ]
        for pattern in forbidden_patterns:
            self.assertIsNone(
                re.search(pattern, self.script_text),
                f"Found legacy pattern that should be removed: {pattern}",
            )

    def test_shell_script_keeps_size_specific_exports(self):
        """IT-007: Size-specific variables must still be exported."""
        expected_exports = [
            "export EC2_FLEET_MEDIUM_ID",
            "export EC2_FLEET_SMALL_ID",
            "export EC2_FLEET_MICRO_ID",
            "export EC2_FLEET_MEDIUM_MIN_SIZE",
            "export EC2_FLEET_MEDIUM_MAX_SIZE",
            "export EC2_FLEET_SMALL_MIN_SIZE",
            "export EC2_FLEET_SMALL_MAX_SIZE",
            "export EC2_FLEET_MICRO_MIN_SIZE",
            "export EC2_FLEET_MICRO_MAX_SIZE",
            "export EC2_FLEET_MEDIUM_NUM_EXECUTORS",
            "export EC2_FLEET_SMALL_NUM_EXECUTORS",
            "export EC2_FLEET_MICRO_NUM_EXECUTORS",
            "export EC2_FLEET_MEDIUM_IDLE_MINUTES",
            "export EC2_FLEET_SMALL_IDLE_MINUTES",
            "export EC2_FLEET_MICRO_IDLE_MINUTES",
        ]
        for export_stmt in expected_exports:
            self.assertIn(export_stmt, self.script_text, f"Missing export: {export_stmt}")

    def test_envsubst_variables_cover_template_usage(self):
        """IT-008: envsubst list should cover template vars and omit legacy ones."""
        template_vars = set(re.findall(r"\$\{([A-Z0-9_]+)\}", self.template_text))
        missing = template_vars - self.envsubst_variables
        self.assertFalse(missing, f"envsubst is missing variables: {sorted(missing)}")

        forbidden = {"EC2_FLEET_ID", "EC2_IDLE_MINUTES", "EC2_MIN_SIZE", "EC2_MAX_SIZE", "EC2_NUM_EXECUTORS"}
        overlap = forbidden & self.envsubst_variables
        self.assertFalse(overlap, f"envsubst should not include legacy vars: {sorted(overlap)}")

    def test_envsubst_rendering_produces_filled_yaml(self):
        """IT-009: Rendering should substitute every variable and stay parseable."""
        envsubst = shutil.which("envsubst")
        if not envsubst:
            self.skipTest("envsubst is not available in PATH.")
        if yaml is None:
            self.skipTest("PyYAML is required to validate rendered YAML.")

        with tempfile.TemporaryDirectory() as tmpdir:
            rendered_path = Path(tmpdir) / "jenkins.yaml"
            env = os.environ.copy()
            for var in self.envsubst_variables:
                env[var] = env.get(var, f"test-{var.lower()}")
            with rendered_path.open("w") as handle:
                subprocess.run(
                    [envsubst],
                    input=self.template_text,
                    text=True,
                    check=True,
                    capture_output=False,
                    env=env,
                    stdout=handle,
                )
            rendered_text = rendered_path.read_text()
            self.assertNotRegex(rendered_text, r"\$\{[^}]+\}", "Rendered YAML should not contain placeholders")
            parsed = yaml.safe_load(rendered_text)
            self.assertIsInstance(parsed, dict, "Rendered YAML should parse after substitution")

    def test_jobs_do_not_reference_plain_ec2_fleet_label(self):
        """IT-010: Jenkins jobs should not use the legacy ec2-fleet label."""
        pattern = re.compile(r"ec2-fleet(?!-[a-zA-Z0-9])")
        offending_files: list[Path] = []
        for path in JOBS_ROOT.rglob("*"):
            if path.is_dir():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if pattern.search(text):
                offending_files.append(path.relative_to(ROOT))
        self.assertFalse(offending_files, f"Legacy ec2-fleet label found in: {offending_files}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
