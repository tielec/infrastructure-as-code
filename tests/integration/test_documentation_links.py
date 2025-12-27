"""Integration tests validating documentation navigation and link integrity for Issue #538."""

import contextlib
import unittest
from pathlib import Path
from urllib import error, request


class DocumentationIntegrationTests(unittest.TestCase):
    """Integration checks for the README refactor and docs split."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.readme = cls.repo_root / "README.md"
        cls.docs_dir = cls.repo_root / "docs"
        cls.expected_docs = {
            cls.docs_dir / "changelog.md": "../README.md",
            cls.docs_dir / "troubleshooting.md": "../README.md",
            cls.docs_dir / "setup" / "prerequisites.md": "../../README.md",
            cls.docs_dir / "setup" / "bootstrap.md": "../../README.md",
            cls.docs_dir / "setup" / "pulumi-backend.md": "../../README.md",
            cls.docs_dir / "operations" / "jenkins-deploy.md": "../../README.md",
            cls.docs_dir / "operations" / "jenkins-management.md": "../../README.md",
            cls.docs_dir / "operations" / "bootstrap-management.md": "../../README.md",
            cls.docs_dir / "operations" / "infrastructure-teardown.md": "../../README.md",
            cls.docs_dir / "operations" / "parameters.md": "../../README.md",
            cls.docs_dir / "architecture" / "infrastructure.md": "../../README.md",
            cls.docs_dir / "development" / "extension.md": "../../README.md",
        }
        cls.quick_nav_links = [
            "docs/setup/prerequisites.md",
            "docs/setup/bootstrap.md",
            "docs/setup/pulumi-backend.md",
            "docs/operations/jenkins-deploy.md",
            "docs/operations/jenkins-management.md",
            "docs/operations/bootstrap-management.md",
            "docs/operations/infrastructure-teardown.md",
            "docs/operations/parameters.md",
            "docs/architecture/infrastructure.md",
            "docs/development/extension.md",
            "docs/troubleshooting.md",
            "docs/changelog.md",
        ]
        cls.external_links = [
            "https://github.com/tielec/infrastructure-as-code/issues/411",
            "https://github.com/tielec/infrastructure-as-code/issues/415",
            "https://platform.openai.com/api-keys",
            "https://github.com/settings/apps",
        ]

    def test_docs_directories_exist(self):
        """INT-006: Expected documentation directories are present."""
        expected_dirs = [
            self.docs_dir,
            self.docs_dir / "setup",
            self.docs_dir / "operations",
            self.docs_dir / "architecture",
            self.docs_dir / "development",
            self.docs_dir / "issues",
        ]
        for directory in expected_dirs:
            self.assertTrue(directory.is_dir(), f"Missing directory: {directory}")

    def test_split_documents_exist_and_link_back_to_readme(self):
        """INT-001 / INT-002: Split docs exist and include the correct parent link."""
        for doc_path, parent_link in self.expected_docs.items():
            self.assertTrue(doc_path.is_file(), f"Missing document: {doc_path}")
            content = doc_path.read_text(encoding="utf-8")
            self.assertTrue(
                content.lstrip().startswith("# "),
                f"{doc_path} should start with an H1 heading",
            )
            self.assertIn(
                parent_link,
                content,
                f"{doc_path} should link back to README via {parent_link}",
            )

    def test_readme_contains_navigation_links(self):
        """INT-001 / INT-004 / INT-009: README keeps quick navigation and important doc links."""
        readme_text = self.readme.read_text(encoding="utf-8")
        for link in self.quick_nav_links:
            self.assertIn(f"({link})", readme_text, f"README should link to {link}")
        for critical in ("ARCHITECTURE.md", "CLAUDE.md", "CONTRIBUTION.md"):
            self.assertIn(f"({critical})", readme_text, f"README should link to {critical}")

    def test_readme_line_count_is_small(self):
        """INT-010: README stays concise after refactor."""
        line_count = len(self.readme.read_text(encoding="utf-8").splitlines())
        self.assertLessEqual(line_count, 120, f"README should be <=120 lines, got {line_count}")

    def test_claude_mentions_readme_and_docs_split(self):
        """INT-003: CLAUDE.md guidance references README and docs structure."""
        claude_text = (self.repo_root / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("README.md", claude_text, "CLAUDE.md should reference README.md")
        leading_section = "\n".join(claude_text.splitlines()[:80])
        self.assertIn("docs/", leading_section, "CLAUDE.md should mention docs/ split near the top")

    def test_external_links_are_reachable(self):
        """INT-005: External references respond successfully."""
        for url in self.external_links:
            status = self._fetch_status(url)
            self.assertLess(
                status,
                400,
                f"{url} should be reachable (HTTP < 400), got {status}",
            )

    def test_markdown_titles_present_in_all_documents(self):
        """INT-007: Ensure Markdown files start with a top-level heading."""
        markdown_files = [self.readme, *self.expected_docs.keys()]
        for path in markdown_files:
            content = path.read_text(encoding="utf-8").lstrip()
            self.assertTrue(
                content.startswith("#"),
                f"{path} should start with a Markdown heading",
            )

    def _fetch_status(self, url: str) -> int:
        """Return HTTP status code for the given URL, falling back from HEAD to GET."""
        for method in ("HEAD", "GET"):
            req = request.Request(url, method=method)
            try:
                with contextlib.closing(request.urlopen(req, timeout=5)) as resp:
                    return resp.getcode() or 0
            except error.HTTPError as exc:
                if exc.code == 405 and method == "HEAD":
                    continue
                return exc.code
            except Exception as exc:  # pragma: no cover - defensive fallback
                self.fail(f"{url} request via {method} failed: {exc}")
        return 599


if __name__ == "__main__":
    unittest.main()
