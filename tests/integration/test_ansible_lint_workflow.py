"""Integration tests for the Ansible lint GitHub Actions workflow (Issue #522)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except Exception:  # pragma: no cover - optional dependency
    yaml = None


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "ansible-lint.yml"
ANSIBLE_LINT_CONFIG_PATH = ROOT / ".ansible-lint"
YAMLLINT_CONFIG_PATH = ROOT / ".yamllint"
README_PATH = ROOT / "README.md"


def _load_yaml_if_available(path: Path) -> Optional[Dict[str, Any]]:
    """Load YAML when PyYAML is present; otherwise return None so text-based assertions can run."""
    if yaml is None:
        return None
    try:
        return yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:  # type: ignore[attr-defined]
        raise AssertionError(f"Failed to parse YAML from {path}: {exc}") from exc


class AnsibleLintWorkflowIntegrationTests(unittest.TestCase):
    """Covers Phase 3 integration scenarios for the ansible-lint GitHub Actions workflow."""

    @classmethod
    def setUpClass(cls):
        cls.workflow_text = WORKFLOW_PATH.read_text()
        cls.workflow_data = _load_yaml_if_available(WORKFLOW_PATH)
        cls.ansible_lint_text = ANSIBLE_LINT_CONFIG_PATH.read_text()
        cls.ansible_lint_data = _load_yaml_if_available(ANSIBLE_LINT_CONFIG_PATH)
        cls.yamllint_text = YAMLLINT_CONFIG_PATH.read_text()
        cls.yamllint_data = _load_yaml_if_available(YAMLLINT_CONFIG_PATH)
        cls.readme_text = README_PATH.read_text()

    def test_workflow_paths_cover_ansible_changes(self):
        """IT-001/IT-006: Workflow should trigger on Ansible-related changes only."""
        expected_paths = {
            "ansible/**/*.yml",
            "ansible/**/*.yaml",
            ".ansible-lint",
            ".yamllint",
        }

        if self.workflow_data:
            pull_request = self.workflow_data.get("on", {}).get("pull_request", {})
            self.assertIsInstance(pull_request, dict)
            paths = set(pull_request.get("paths", []))
            self.assertTrue(expected_paths.issubset(paths), f"Missing paths: {expected_paths - paths}")
        else:
            for path in expected_paths:
                self.assertIn(path, self.workflow_text)
            self.assertRegex(self.workflow_text, r"on:\s*\n\s*pull_request:", "pull_request trigger is required")

    def test_workflow_sets_python_and_runs_linters(self):
        """IT-002/IT-003/IT-008: Workflow should set Python 3.11 and run ansible-lint and yamllint."""
        if self.workflow_data:
            job = self.workflow_data.get("jobs", {}).get("ansible-lint", {})
            steps = job.get("steps", [])
            python_step = next((step for step in steps if "setup-python" in str(step.get("uses", ""))), None)
            self.assertIsNotNone(python_step, "Python setup step is missing")
            self.assertEqual(
                str(python_step.get("with", {}).get("python-version")),
                "3.11",
                "Workflow must use Python 3.11",
            )

            install_step = next((step for step in steps if "pip install ansible-lint yamllint" in str(step.get("run", ""))), None)
            self.assertIsNotNone(install_step, "Install lint tools step is missing")

            ansible_step = next((step for step in steps if step.get("run") == "ansible-lint ansible/"), None)
            self.assertIsNotNone(ansible_step, "ansible-lint execution step is missing or altered")

            yamllint_step = next((step for step in steps if step.get("run") == "yamllint ansible/"), None)
            self.assertIsNotNone(yamllint_step, "yamllint execution step is missing or altered")
        else:
            self.assertRegex(self.workflow_text, r"python-version:\s*['\"]?3\.11", "Python 3.11 must be configured")
            self.assertIn("pip install ansible-lint yamllint", self.workflow_text)
            self.assertIn("ansible-lint ansible/", self.workflow_text)
            self.assertIn("yamllint ansible/", self.workflow_text)

    def test_ansible_lint_config_matches_requirements(self):
        """IT-002/IT-004/IT-005: ansible-lint settings should align with requirements."""
        expected_excludes = {".cache/", ".github/", ".git/", ".ai-workflow/"}

        if self.ansible_lint_data:
            self.assertEqual("moderate", self.ansible_lint_data.get("profile"))
            excludes = set(self.ansible_lint_data.get("exclude_paths", []))
            self.assertTrue(expected_excludes.issubset(excludes), f"Missing exclude paths: {expected_excludes - excludes}")
            skip_list = set(self.ansible_lint_data.get("skip_list", []))
            self.assertIn("yaml[line-length]", skip_list)
            self.assertFalse(self.ansible_lint_data.get("strict", False), "strict should be false for gradual adoption")
            self.assertFalse(self.ansible_lint_data.get("offline", False), "offline should remain false for PyPI access")
        else:
            self.assertIn("profile: moderate", self.ansible_lint_text)
            for path in expected_excludes:
                self.assertIn(path, self.ansible_lint_text)
            self.assertIn("yaml[line-length]", self.ansible_lint_text)
            self.assertRegex(self.ansible_lint_text, r"strict:\s*false")
            self.assertRegex(self.ansible_lint_text, r"offline:\s*false")

    def test_yamllint_config_enforces_line_length_and_indentation(self):
        """IT-003: yamllint rules should enforce 120-char lines and 2-space indentation."""
        if self.yamllint_data:
            self.assertEqual("default", self.yamllint_data.get("extends"))
            rules = self.yamllint_data.get("rules", {})
            line_length = rules.get("line-length", {})
            self.assertEqual(120, line_length.get("max"))
            self.assertTrue(line_length.get("allow-non-breakable-words"))
            indentation = rules.get("indentation", {})
            self.assertEqual(2, indentation.get("spaces"))
            self.assertTrue(indentation.get("indent-sequences"))
            self.assertFalse(indentation.get("check-multi-line-strings"))
            self.assertEqual("disable", rules.get("document-end"))
        else:
            self.assertIn("extends: default", self.yamllint_text)
            self.assertRegex(self.yamllint_text, r"line-length:\s*\n\s*max:\s*120")
            self.assertRegex(self.yamllint_text, r"indentation:\s*\n\s*spaces:\s*2")
            self.assertIn("document-end: disable", self.yamllint_text)

    def test_readme_contains_ansible_lint_badge(self):
        """IT-007: README should display the Ansible Lint status badge."""
        badge_pattern = re.compile(
            r"\[!\[Ansible Lint\]\(https://github.com/.+?/actions/workflows/ansible-lint.yml/badge.svg\)\]"
        )
        self.assertRegex(self.readme_text, badge_pattern, "README must include the Ansible Lint CI badge")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
