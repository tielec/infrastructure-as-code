"""Integration tests for Issue #558 AI coding tools bootstrap updates."""

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency for structural checks
    yaml = None


class BootstrapAiCodingToolsIntegrationTests(unittest.TestCase):
    """Integration checks for AI coding tools bootstrap changes."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.playbook = cls.repo_root / "ansible" / "playbooks" / "bootstrap-setup.yml"
        cls.verify_script = cls.repo_root / "bootstrap" / "verify-installation.sh"
        cls.setup_script = cls.repo_root / "bootstrap" / "setup-bootstrap.sh"
        cls.playbook_text = cls.playbook.read_text(encoding="utf-8")
        cls.verify_text = cls.verify_script.read_text(encoding="utf-8")
        cls.setup_text = cls.setup_script.read_text(encoding="utf-8")

    def test_ansible_playbook_syntax_check(self):
        """INT-558-01: ansible-playbook --syntax-check passes for the updated playbook."""
        # Given: ansible-playbook is available
        ansible = shutil.which("ansible-playbook")
        if not ansible:
            self.skipTest("ansible-playbook is not available")

        # When: running syntax check against the playbook
        result = subprocess.run(
            [ansible, "--syntax-check", str(self.playbook)],
            capture_output=True,
            text=True,
        )

        # Then: syntax check succeeds without errors
        self.assertEqual(
            result.returncode,
            0,
            msg=f"Syntax check failed: {result.stderr or result.stdout}",
        )

    def test_shellcheck_passes_for_updated_scripts(self):
        """INT-558-02: shellcheck passes for verify-installation.sh and setup-bootstrap.sh."""
        # Given: shellcheck is available
        shellcheck = shutil.which("shellcheck")
        if not shellcheck:
            self.skipTest("shellcheck is not available")

        # When: running shellcheck for updated scripts
        result = subprocess.run(
            [shellcheck, str(self.verify_script), str(self.setup_script)],
            capture_output=True,
            text=True,
        )

        # Then: shellcheck reports no errors
        self.assertEqual(
            result.returncode,
            0,
            msg=f"ShellCheck failed: {result.stderr or result.stdout}",
        )

    def test_playbook_includes_ai_coding_tools_block(self):
        """INT-558-03: AI coding tools block includes idempotent checks and npm installs."""
        # Given: the playbook text is loaded
        content = self.playbook_text

        # When: searching for AI coding tools installation details
        # Then: required tasks and guards are present
        self.assertIn("- name: Install AI Coding Tools", content)
        self.assertIn("ignore_errors: yes", content)
        self.assertIn("claude --version", content)
        self.assertIn("codex --version", content)
        self.assertIn("npm install -g @anthropic-ai/claude-code", content)
        self.assertIn("npm install -g @openai/codex", content)
        self.assertIn("when: claude_check.rc != 0", content)
        self.assertIn("when: codex_check.rc != 0", content)

    def test_playbook_ai_tools_block_structure(self):
        """INT-558-03A: AI coding tools block structure is validated via YAML parsing."""
        # Given: PyYAML is available for structural validation
        if yaml is None:
            self.skipTest("PyYAML is not available for YAML structural checks")

        # When: parsing the playbook to inspect task structure
        data = yaml.safe_load(self.playbook_text)

        # Then: the playbook contains the AI tools block with required fields
        self.assertIsInstance(data, list)
        self.assertTrue(data, "Playbook should contain at least one play")
        tasks = data[0].get("tasks", [])
        self.assertTrue(tasks, "Playbook should define tasks")

        ai_task = next((task for task in tasks if task.get("name") == "Install AI Coding Tools"), None)
        self.assertIsNotNone(ai_task, "AI Coding Tools block is missing")
        self.assertEqual(ai_task.get("ignore_errors"), True)
        self.assertIsInstance(ai_task.get("block"), list)

        block_tasks = ai_task.get("block", [])
        task_names = {task.get("name") for task in block_tasks}
        self.assertIn("Check if Claude Code is installed", task_names)
        self.assertIn("Install Claude Code via npm", task_names)
        self.assertIn("Check if Codex CLI is installed", task_names)
        self.assertIn("Install Codex CLI via npm", task_names)

        claude_install = next(
            (task for task in block_tasks if task.get("name") == "Install Claude Code via npm"),
            {},
        )
        codex_install = next(
            (task for task in block_tasks if task.get("name") == "Install Codex CLI via npm"),
            {},
        )
        self.assertEqual(claude_install.get("when"), "claude_check.rc != 0")
        self.assertEqual(codex_install.get("when"), "codex_check.rc != 0")

    def test_playbook_readme_includes_ai_tool_auth_guidance(self):
        """INT-558-04: README.txt template in playbook documents AI tools and login steps."""
        # Given: the playbook text is loaded
        content = self.playbook_text

        # When: validating README.txt content
        # Then: tool names and login guidance are included
        self.assertIn("Claude Code (AI coding assistant)", content)
        self.assertIn("Codex CLI (AI coding assistant)", content)
        self.assertIn("claude login", content)
        self.assertIn("codex login", content)

    def test_playbook_completion_message_mentions_ai_tools(self):
        """INT-558-05: Completion message advertises AI tools and authentication note."""
        # Given: the playbook text is loaded
        content = self.playbook_text

        # When: inspecting the completion message section
        # Then: it mentions the AI tools and login guidance
        self.assertIn("Claude Code (AI coding assistant)", content)
        self.assertIn("Codex CLI (AI coding assistant)", content)
        self.assertIn("AI tools authentication", content)
        self.assertIn("claude login", content)
        self.assertIn("codex login", content)

    def test_verify_installation_ai_tools_section_exists(self):
        """INT-558-06: verify-installation.sh reports AI tools as optional."""
        # Given: verify-installation.sh content is loaded
        content = self.verify_text

        # When: searching for AI tools section
        # Then: optional messaging and version checks are included
        self.assertIn("=== AI Coding Tools ===", content)
        self.assertIn("Claude Code: Not installed (optional)", content)
        self.assertIn("Codex CLI: Not installed (optional)", content)
        self.assertIn("claude --version", content)
        self.assertIn("codex --version", content)

    def test_verify_installation_summary_does_not_count_ai_tools(self):
        """INT-558-07: Summary counter excludes AI tools from critical tools count."""
        # Given: verify-installation.sh content is loaded
        content = self.verify_text

        # When: inspecting summary counters
        # Then: AI tools are not included in total/looped tools
        self.assertIn("total_tools=9", content)
        self.assertIn("for tool in python3 aws ansible pulumi git java node; do", content)

    def test_setup_script_completion_message_lists_ai_tools(self):
        """INT-558-08: setup-bootstrap.sh completion message lists AI tools."""
        # Given: setup-bootstrap.sh content is loaded
        content = self.setup_text

        # When: verifying completion message content
        # Then: AI tools are listed alongside other installed tools
        self.assertIn("Claude Code (AI", content)
        self.assertIn("Codex CLI (AI", content)


if __name__ == "__main__":
    unittest.main()
