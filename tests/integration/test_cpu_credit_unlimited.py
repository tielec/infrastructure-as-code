"""Integration checks for CPU credit Unlimited settings (Issue #542)."""

import json
import os
import subprocess
from pathlib import Path
import unittest


class PulumiScenarioTests(unittest.TestCase):
    """Automate Phase 3 scenarios with Pulumi mocks and build steps."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.agent_dir = cls.repo_root / "pulumi" / "jenkins-agent"
        cls.helper_script = cls.repo_root / "tests" / "integration" / "helpers" / "render_launch_templates.js"
        cls.compiled_index = cls.agent_dir / "bin" / "index.js"
        cls._install_node_dependencies()
        cls._build_typescript()
        cls.preview = cls._render_launch_templates()

    @classmethod
    def _install_node_dependencies(cls):
        subprocess.run(
            ["npm", "--silent", "install"],
            cwd=cls.agent_dir,
            check=True,
        )

    @classmethod
    def _build_typescript(cls):
        env = {**os.environ, "NODE_OPTIONS": "--max-old-space-size=4096"}
        subprocess.run(
            ["npm", "--silent", "run", "build"],
            cwd=cls.agent_dir,
            check=True,
            env=env,
        )
        if not cls.compiled_index.exists():
            raise AssertionError("TypeScript build did not produce bin/index.js")

    @classmethod
    def _render_launch_templates(cls) -> dict:
        result = subprocess.run(
            ["node", str(cls.helper_script)],
            cwd=cls.repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_typescript_compiles_cleanly(self):
        """IT-001: TypeScript sources build without errors (tsc --noEmit equivalent)."""
        self.assertTrue(self.compiled_index.exists(), "compiled index.js must exist after build")

    def test_launch_templates_report_unlimited_credits(self):
        """IT-002/IT-003: Preview shows unlimited CPU credits for both LaunchTemplates."""
        templates = self.preview.get("launchTemplates", [])
        self.assertEqual(2, len(templates), "Exactly two LaunchTemplates should be synthesized")
        names = {lt["name"] for lt in templates}
        self.assertSetEqual(names, {"agent-lt", "agent-lt-arm"})
        for lt in templates:
            credits = lt.get("creditSpecification", {})
            self.assertEqual(
                "unlimited",
                credits.get("cpuCredits"),
                f"{lt.get('name')} must request unlimited CPU credits",
            )

    def test_launch_templates_keep_expected_network_and_storage_settings(self):
        """IT-004: Preview indicates only intended changes; safety-critical settings remain intact."""
        templates = self.preview.get("launchTemplates", [])
        self.assertGreaterEqual(len(templates), 2, "LaunchTemplates should be captured for both architectures")
        for lt in templates:
            # Network safeguards
            nic = lt.get("networkInterfaces", [{}])[0]
            self.assertEqual("false", nic.get("associatePublicIpAddress"), "No public IPs should be assigned")
            self.assertEqual(1, nic.get("ipv6AddressCount"), "IPv6 address should be allocated")
            self.assertTrue(nic.get("securityGroups"), "Security group must be attached")

            # Metadata hardening
            metadata = lt.get("metadataOptions", {})
            self.assertEqual("enabled", metadata.get("httpEndpoint"))
            self.assertEqual("required", metadata.get("httpTokens"))

            # Storage expectations
            block = lt.get("blockDeviceMappings", [{}])[0].get("ebs", {})
            self.assertEqual("true", block.get("encrypted"))
            self.assertEqual("gp3", block.get("volumeType"))
            volume_size = int(block.get("volumeSize", 0))
            self.assertGreaterEqual(volume_size, 30)

            # Tag coverage for visibility in console checks
            tags = (lt.get("tagSpecifications", [{}])[0] or {}).get("tags", {})
            self.assertEqual("jenkins-agent", tags.get("Role"))
            self.assertEqual("true", tags.get("IPv6Enabled"))

    def test_stack_exports_expose_launch_template_ids(self):
        """IT-005: Pulumi stack exports provide LaunchTemplate identifiers after synthesis."""
        exports = set(self.preview.get("exports", []))
        expected_exports = {
            "launchTemplateId",
            "launchTemplateArmId",
            "launchTemplateLatestVersion",
            "launchTemplateArmLatestVersion",
        }
        self.assertTrue(
            expected_exports.issubset(exports),
            f"Stack outputs should include LaunchTemplate identifiers: {expected_exports}",
        )


class CpuCreditUnlimitedIntegrationTests(unittest.TestCase):
    """Validate creditSpecification additions and documentation notes."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.pulumi_agent = cls.repo_root / "pulumi" / "jenkins-agent" / "index.ts"
        cls.infrastructure_doc = cls.repo_root / "docs" / "architecture" / "infrastructure.md"
        cls.agent_source = cls.pulumi_agent.read_text(encoding="utf-8")
        cls.doc_text = cls.infrastructure_doc.read_text(encoding="utf-8")

    def _extract_template_block(self, template_name: str) -> str:
        """Return the slice of the source starting at the template up to the next const declaration."""
        marker = f"const {template_name} "
        start = self.agent_source.find(marker)
        self.assertNotEqual(start, -1, f"LaunchTemplate {template_name} should exist in index.ts")
        next_const = self.agent_source.find("const ", start + len(marker))
        end = next_const if next_const != -1 else len(self.agent_source)
        return self.agent_source[start:end]

    def test_x86_launch_template_has_unlimited_credit_spec(self):
        """IT-002: agentLaunchTemplate must set creditSpecification.cpuCredits to unlimited."""
        block = self._extract_template_block("agentLaunchTemplate")
        self.assertIn("creditSpecification", block, "x86_64 LaunchTemplate should define creditSpecification")
        self.assertIn(
            'cpuCredits: "unlimited"',
            block,
            "x86_64 LaunchTemplate should request unlimited CPU credits",
        )

    def test_arm_launch_template_has_unlimited_credit_spec(self):
        """IT-003: agentLaunchTemplateArm must set creditSpecification.cpuCredits to unlimited."""
        block = self._extract_template_block("agentLaunchTemplateArm")
        self.assertIn("creditSpecification", block, "ARM64 LaunchTemplate should define creditSpecification")
        self.assertIn(
            'cpuCredits: "unlimited"',
            block,
            "ARM64 LaunchTemplate should request unlimited CPU credits",
        )

    def test_documentation_describes_unlimited_settings(self):
        """IT-004: infrastructure documentation should mention Unlimited mode and covered templates."""
        self.assertIn(
            "CPUクレジット設定",
            self.doc_text,
            "Documentation should include the CPU credit section header",
        )
        self.assertIn(
            '| creditSpecification.cpuCredits | "unlimited" |',
            self.doc_text,
            "Documentation should describe the unlimited cpuCredits value",
        )
        for template in ("agent-lt (x86_64)", "agent-lt-arm (ARM64)"):
            self.assertIn(
                template,
                self.doc_text,
                f"Documentation should list {template} as covered by Unlimited mode",
            )
        self.assertIn(
            "CPUSurplusCreditBalance",
            self.doc_text,
            "Documentation should note the cost monitoring metric for Unlimited mode",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
