"""Integration checks for CPU credit Unlimited settings (Issue #542)."""

from pathlib import Path
import unittest


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
