"""Integration tests that verify the updated Ansible content stays ansible-lint compliant."""

from __future__ import annotations

import os
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
        cls.tools_dir = cls.repo_root / "tools" / "bin"
        cls._ensure_tools_available(("ansible-lint", "ansible-playbook"))

    @classmethod
    def _ensure_tools_available(cls, tools: Iterable[str]) -> None:
        """Skip all tests if a required CLI tool is not on PATH."""
        missing = [tool for tool in tools if shutil.which(tool) is None]
        if missing:
            raise unittest.SkipTest(f"Missing tools for integration tests: {', '.join(missing)}")

    def run_command(self, args: List[str], description: str) -> subprocess.CompletedProcess[str]:
        """Run a subprocess with working directory set to the repo root."""
        env = os.environ.copy()
        env["ANSIBLE_CONFIG"] = str(self.ansible_dir / "ansible.cfg")
        tools_path = getattr(self, "tools_dir", None)
        if tools_path:
            env["PATH"] = f"{tools_path}{os.pathsep}{env.get('PATH', os.defpath)}"
        result = subprocess.run(
            args,
            cwd=self.repo_root,
            text=True,
            capture_output=True,
            env=env,
        )
        self.assertEqual(
            0,
            result.returncode,
            f"{description} failed (exit {result.returncode}).\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return result

    def _run_ansible_lint(self, target: Path | str) -> subprocess.CompletedProcess[str]:
        """Run ansible-lint against the requested target."""
        target_path = Path(target) if isinstance(target, (str, Path)) else target
        description = f"ansible-lint on {target_path}"
        return self.run_command(["ansible-lint", str(target_path)], description)

    def _run_playbook(self, playbook: Path, extra_args: List[str], description: str) -> subprocess.CompletedProcess[str]:
        """Execute the provided playbook with the given ansible-playbook arguments."""
        command = ["ansible-playbook", *extra_args, str(playbook)]
        return self.run_command(command, description)

    def test_ansible_directory_ansible_lint(self):
        """Scenario 1: Ensure ansible-lint passes across the entire ansible/ tree."""
        self._run_ansible_lint(self.ansible_dir)

    def test_bootstrap_playbook_ansible_lint(self):
        """Scenario 1: Run ansible-lint specifically on bootstrap-setup.yml."""
        self._run_ansible_lint(self.bootstrap_playbook)

    def test_group_vars_all_ansible_lint(self):
        """Run ansible-lint on the group vars file that previously lacked a newline."""
        self._run_ansible_lint(self.ansible_dir / "inventory" / "group_vars" / "all.yml")

    def test_bootstrap_playbook_syntax_check(self):
        """Verify updated bootstrap playbook passes Ansible syntax check."""
        self._run_playbook(
            self.bootstrap_playbook,
            ["--syntax-check"],
            "ansible-playbook --syntax-check for bootstrap-setup.yml",
        )

    def test_bootstrap_playbook_syntax_check_with_jenkins_roles(self):
        """Scenario 2: Syntax check when Jenkins roles are referenced via extra vars."""
        self._run_playbook(
            self.bootstrap_playbook,
            ["--syntax-check", "--extra-vars", "check_jenkins_roles=true"],
            "ansible-playbook --syntax-check bootstrap-setup.yml --extra-vars check_jenkins_roles=true",
        )

    def test_all_playbooks_syntax_check(self):
        """Scenario 2: Run syntax check on every playbook under ansible/playbooks."""
        playbook_dir = self.ansible_dir / "playbooks"
        playbooks = sorted(playbook_dir.rglob("*.yml"))
        for playbook in playbooks:
            self._run_playbook(
                playbook,
                ["--syntax-check"],
                f"ansible-playbook --syntax-check {playbook}",
            )

    def test_jenkins_roles_ansible_lint(self):
        """Scenario 1: Lint the Jenkins roles that include the updated Jinja2 fragments."""
        roles = ("jenkins_cleanup_agent_amis", "jenkins_agent_ami")
        for role in roles:
            role_path = self.ansible_dir / "roles" / role
            self._run_ansible_lint(role_path)

    def test_bootstrap_playbook_dry_run_modes(self):
        """Scenario 3: Execute the bootstrap playbook in dry-run/check modes to surface runtime issues."""
        dry_run_variants = [
            (["--check", "--diff"], "ansible-playbook --check --diff bootstrap-setup.yml"),
            (["--check", "--tags", "debug,facts"], "ansible-playbook --check --tags debug,facts bootstrap-setup.yml"),
            (["--check", "--diff", "--extra-vars", "debug_mode=true"], "ansible-playbook --check --diff bootstrap-setup.yml --extra-vars debug_mode=true"),
        ]
        for args, description in dry_run_variants:
            self._run_playbook(self.bootstrap_playbook, args, description)
