"""Integration tests that verify the updated Ansible content stays ansible-lint compliant."""

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path
from typing import Iterable, List


class AnsibleLintIntegrationTests(unittest.TestCase):
    """Runs the lint/syntax verification commands referenced by the test scenario."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.ansible_dir = cls.repo_root / "ansible"
        cls.bootstrap_playbook = cls.ansible_dir / "playbooks" / "bootstrap-setup.yml"
        cls._ensure_tools_available(("ansible-lint", "ansible-playbook"))

    @classmethod
    def _ensure_tools_available(cls, tools: Iterable[str]) -> None:
        """Skip all tests if a required CLI tool is not on PATH."""
        missing = [tool for tool in tools if shutil.which(tool) is None]
        if missing:
            raise unittest.SkipTest(f"Missing tools for integration tests: {', '.join(missing)}")

    def run_command(self, args: List[str], description: str) -> subprocess.CompletedProcess[str]:
        """Run a subprocess with working directory set to the repo root."""
        result = subprocess.run(
            args,
            cwd=self.repo_root,
            text=True,
            capture_output=True,
        )
        self.assertEqual(
            0,
            result.returncode,
            f"{description} failed (exit {result.returncode}).\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return result

    def test_group_vars_all_ansible_lint(self):
        """Run ansible-lint on the group vars file that previously lacked a newline."""
        self.run_command(
            ["ansible-lint", str(self.ansible_dir / "inventory" / "group_vars" / "all.yml")],
            "ansible-lint on ansible/inventory/group_vars/all.yml",
        )

    def test_bootstrap_playbook_syntax_check(self):
        """Verify updated bootstrap playbook passes Ansible syntax check."""
        self.run_command(
            ["ansible-playbook", "--syntax-check", str(self.bootstrap_playbook)],
            "ansible-playbook --syntax-check for bootstrap-setup.yml",
        )
