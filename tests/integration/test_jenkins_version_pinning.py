"""Issue #576 の Jenkins バージョン固定と Runbook 導線を検証する統合テスト。"""

import os
from pathlib import Path
import re
import subprocess
import unittest


class JenkinsVersionPinningIntegrationTests(unittest.TestCase):
    """SSM パラメータ、Runbook、導線、検証スクリプトを静的に検証する。"""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.ssm_init = cls.repo_root / "pulumi" / "jenkins-ssm-init" / "index.ts"
        cls.controller_install = cls.repo_root / "scripts" / "jenkins" / "shell" / "controller-install.sh"
        cls.runbook = cls.repo_root / "docs" / "jenkins-upgrade-runbook.md"
        cls.jenkins_readme = cls.repo_root / "jenkins" / "README.md"
        cls.claude_md = cls.repo_root / "CLAUDE.md"
        cls.jenkins_management = cls.repo_root / "docs" / "operations" / "jenkins-management.md"
        cls.verify_version_script = cls.repo_root / "tests" / "issue-576" / "verify-version-format.sh"
        cls.verify_docs_script = cls.repo_root / "tests" / "issue-576" / "verify-docs-integrity.sh"
        cls.ssm_init_dir = cls.repo_root / "pulumi" / "jenkins-ssm-init"
        cls.typescript_candidates = [
            cls.ssm_init_dir / "node_modules" / ".bin" / "tsc",
            cls.ssm_init_dir / "node_modules" / "typescript" / "bin" / "tsc",
            cls.repo_root / "pulumi" / "components" / "node_modules" / ".bin" / "tsc",
            cls.repo_root / "pulumi" / "components" / "node_modules" / "typescript" / "bin" / "tsc",
        ]

        cls.ssm_init_text = cls.ssm_init.read_text(encoding="utf-8")
        cls.controller_install_text = cls.controller_install.read_text(encoding="utf-8")
        cls.runbook_text = cls.runbook.read_text(encoding="utf-8")
        cls.jenkins_readme_text = cls.jenkins_readme.read_text(encoding="utf-8")
        cls.claude_text = cls.claude_md.read_text(encoding="utf-8")
        cls.jenkins_management_text = cls.jenkins_management.read_text(encoding="utf-8")

    @classmethod
    def _extract_ssm_parameter_block(cls, logical_name: str) -> str:
        """指定した SSM パラメータ定義ブロックだけを返す。"""
        marker = f"const {logical_name} = new aws.ssm.Parameter("
        start = cls.ssm_init_text.find(marker)
        if start == -1:
            raise AssertionError(f"{logical_name} の定義が必要です")
        end = cls.ssm_init_text.find("});", start)
        if end == -1:
            raise AssertionError(f"{logical_name} の定義終端が必要です")
        return cls.ssm_init_text[start : end + 3]

    @classmethod
    def _extract_runbook_section(cls, title: str) -> str:
        """指定した見出し配下のセクション本文を抽出する。"""
        pattern = rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)"
        match = re.search(pattern, cls.runbook_text, flags=re.MULTILINE | re.DOTALL)
        if match is None:
            raise AssertionError(f"Runbook に '{title}' セクションが必要です")
        return match.group(1)

    @staticmethod
    def _extract_markdown_link(document_text: str, target_path: str) -> re.Match[str]:
        """指定パスを向く Markdown リンクを抽出する。"""
        pattern = rf"\[([^\]]+)\]\(({re.escape(target_path)})\)"
        match = re.search(pattern, document_text)
        if match is None:
            raise AssertionError(f"{target_path} を指す Markdown リンクが必要です")
        return match

    @staticmethod
    def _assert_resolved_path_exists(base_file: Path, relative_path: str):
        """相対パスのリンク先ファイルが実在することを確認する。"""
        resolved_path = (base_file.parent / relative_path).resolve()
        if not resolved_path.is_file():
            raise AssertionError(f"リンク先ファイルが存在しません: {relative_path} -> {resolved_path}")

    @staticmethod
    def _assert_process_succeeds(result: subprocess.CompletedProcess[str]):
        """シェルスクリプト実行結果の終了コードと PASS 表示を確認する。"""
        if result.returncode != 0:
            raise AssertionError(
                f"終了コード {result.returncode} で失敗しました\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        if "FAIL" in result.stdout or "FAIL" in result.stderr:
            raise AssertionError(
                f"スクリプト出力に FAIL が含まれています\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        if "PASS" not in result.stdout:
            raise AssertionError(f"スクリプト出力に PASS が含まれていません\n{result.stdout}")

    def test_jenkins_version_is_pinned_to_semver(self):
        """Given jenkins-version 定義を確認するとき、When value を抽出すると、Then latest ではなく X.Y.Z 形式であること。"""
        block = self._extract_ssm_parameter_block("jenkinsVersionParam")
        self.assertIn('name: `${ssmPrefix}/config/jenkins-version`', block)
        self.assertNotIn('value: "latest"', block)
        match = re.search(r'value: "([0-9]+\.[0-9]+\.[0-9]+)"', block)
        self.assertIsNotNone(match, "Jenkins バージョンは X.Y.Z 形式で定義されている必要があります")

    def test_jenkins_version_comment_references_issue_and_runbook(self):
        """Given jenkins-version 付近のコメントを見るとき、When 運用ガイドを確認すると、Then Issue 番号と Runbook パスが記載されていること。"""
        block = self._extract_ssm_parameter_block("jenkinsVersionParam")
        context_start = max(0, self.ssm_init_text.find(block) - 220)
        context = self.ssm_init_text[context_start : self.ssm_init_text.find(block) + len(block)]
        self.assertIn("Issue #576", context)
        self.assertIn("docs/jenkins-upgrade-runbook.md", context)

    def test_jenkins_version_metadata_is_preserved(self):
        """Given jenkins-version 定義を見るとき、When 主要属性を確認すると、Then 値以外のメタデータが維持されること。"""
        block = self._extract_ssm_parameter_block("jenkinsVersionParam")
        required_lines = [
            'type: "String",',
            "overwrite: true,",
            'description: "Jenkins version to install",',
            "Environment: environment,",
            'ManagedBy: "pulumi",',
            'Component: "config",',
        ]
        for line in required_lines:
            self.assertIn(line, block)

    def test_other_representative_ssm_parameters_remain_expected(self):
        """Given 変更スコープを確認するとき、When 他の代表値を見ると、Then 既存値が維持されること。"""
        expected_values = [
            'value: "blue"',
            'value: "false"',
            'value: "none"',
            'value: "t4g.large"',
            'value: "t4g.medium"',
        ]
        for value in expected_values:
            self.assertIn(value, self.ssm_init_text)

        parameter_names = [
            "jenkins-version",
            "jenkins-color",
            "jenkins-recovery-mode",
            "key-name",
            "controller-instance-type",
            "agent-instance-type",
        ]
        for parameter_name in parameter_names:
            self.assertEqual(
                1,
                self.ssm_init_text.count(f'"{parameter_name}"'),
                f"{parameter_name} の定義は 1 回だけ存在する必要があります",
            )

    def test_controller_install_version_branching_logic_is_preserved(self):
        """Given controller-install.sh を確認するとき、When Jenkins のインストール分岐を読むと、Then latest 判定と両方の install コマンドが維持されていること。"""
        self.assertTrue(self.controller_install.is_file())
        for expected_line in [
            'if [ "${JENKINS_VERSION}" != "latest" ]; then',
            'dnf install -y jenkins-${JENKINS_VERSION}',
            "dnf install -y jenkins",
        ]:
            self.assertIn(expected_line, self.controller_install_text)

    def test_runbook_contains_required_sections_and_checklists(self):
        """Given Runbook を確認するとき、When 必須見出しとチェックリストを数えると、Then 要件の骨格を満たすこと。"""
        required_sections = [
            "## 事前準備",
            "## dev環境での検証",
            "## staging環境への展開",
            "## prod環境への展開",
            "## ロールバック手順",
            "## CVE対応の特例",
            "## 運用方針",
        ]
        for section in required_sections:
            self.assertIn(section, self.runbook_text)
        self.assertGreaterEqual(
            self.runbook_text.count("- [ ]"),
            10,
            "Runbook には十分なチェックリスト項目が必要です",
        )
        for section_title in [
            "事前準備",
            "dev環境での検証",
            "staging環境への展開",
            "prod環境への展開",
            "ロールバック手順",
            "CVE対応の特例",
            "運用方針",
        ]:
            self.assertIn("- [ ]", self._extract_runbook_section(section_title))

    def test_runbook_sections_cover_phase3_requirements(self):
        """Given Runbook をセクション単位で確認するとき、When Phase 3 の要件を照合すると、Then 個別要件が各セクション内で満たされること。"""
        precheck = self._extract_runbook_section("事前準備")
        for keyword in ["バージョン", "Upgrade Guide", "Changelog", "プラグイン", "JCasC"]:
            self.assertIn(keyword, precheck)

        dev_section = self._extract_runbook_section("dev環境での検証")
        for keyword in [
            "deploy_jenkins_ssm_init.yml",
            "deploy_jenkins_application.yml",
            "Jenkins UI",
            "JCasC",
            "EC2 Fleet",
            "ECS Fargate",
            "/monitoring",
            "CloudWatch",
        ]:
            self.assertIn(keyword, dev_section)
        self.assertRegex(dev_section, r"1\s*週間")

        staging_section = self._extract_runbook_section("staging環境への展開")
        self.assertRegex(staging_section, r"3[〜-]5\s*日")

        prod_section = self._extract_runbook_section("prod環境への展開")
        self.assertRegex(prod_section, r"24\s*時間")

        rollback_section = self._extract_runbook_section("ロールバック手順")
        for keyword in ["SSM", "deploy_jenkins_application.yml", "プラグイン"]:
            self.assertIn(keyword, rollback_section)

        cve_section = self._extract_runbook_section("CVE対応の特例")
        for keyword in ["Critical", "High", "最低限", "24 時間"]:
            self.assertIn(keyword, cve_section)

        policy_section = self._extract_runbook_section("運用方針")
        for keyword in ["LTS 固定", "月 1 回", "四半期"]:
            self.assertIn(keyword, policy_section)
        self.assertIn("dev環境での検証", self.runbook_text)
        self.assertIn("staging環境への展開", self.runbook_text)
        self.assertIn("prod環境への展開", self.runbook_text)

    def test_runbook_contains_commands_and_japanese_text(self):
        """Given Runbook の記述品質を見るとき、When コマンド例と日本語量を確認すると、Then 運用手順書として必要な体裁を満たすこと。"""
        for keyword in [
            "deploy_jenkins_ssm_init.yml",
            "deploy_jenkins_application.yml",
            "https://www.jenkins.io/doc/upgrade-guide/",
            "https://www.jenkins.io/changelog-stable/",
        ]:
            self.assertIn(keyword, self.runbook_text)
        self.assertIn("```bash", self.runbook_text)
        self.assertRegex(self.runbook_text.splitlines()[0], r"[一-龯ぁ-んァ-ヶ]")
        japanese_characters = re.findall(r"[ぁ-んァ-ヶ一-龯]", self.runbook_text)
        self.assertGreaterEqual(len(japanese_characters), 50)

    def test_documentation_links_point_to_runbook_with_valid_relative_paths(self):
        """Given 関連ドキュメントを確認するとき、When Runbook 導線をたどると、Then 書式と相対パスが要件どおりであること。"""
        readme_link = self._extract_markdown_link(self.jenkins_readme_text, "../docs/jenkins-upgrade-runbook.md")
        self.assertTrue(readme_link.group(1))
        self._assert_resolved_path_exists(self.jenkins_readme, readme_link.group(2))

        self.assertIn("docs/jenkins-upgrade-runbook.md", self.claude_text)
        self._assert_resolved_path_exists(self.claude_md, "docs/jenkins-upgrade-runbook.md")
        self.assertIn("latest", self.claude_text)
        self.assertIn("LTS 固定バージョン", self.claude_text)

        management_link = self._extract_markdown_link(self.jenkins_management_text, "../jenkins-upgrade-runbook.md")
        self._assert_resolved_path_exists(self.jenkins_management, management_link.group(2))
        management_row = next(
            (line for line in self.jenkins_management_text.splitlines() if "Jenkinsバージョン更新" in line),
            "",
        )
        self.assertIn("Runbook", management_row)
        self.assertIn("jenkins-upgrade-runbook.md", management_row)

    def test_verify_version_script_exists_and_is_executable(self):
        """Given バージョン検証スクリプトを確認するとき、When 配置状態を見ると、Then ファイルが存在し execute bit が付与されていること。"""
        self.assertTrue(self.verify_version_script.is_file())
        self.assertTrue(
            os.access(self.verify_version_script, os.X_OK),
            "verify-version-format.sh には実行権限が必要です",
        )

    def test_verify_version_script_succeeds(self):
        """Given バージョン検証スクリプトを実行するとき、When 現在の実装を検査すると、Then PASS で完了すること。"""
        result = subprocess.run(
            ["bash", str(self.verify_version_script)],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self._assert_process_succeeds(result)

    def test_verify_docs_script_succeeds(self):
        """Given ドキュメント整合性スクリプトを実行するとき、When 現在の文書群を検査すると、Then PASS で完了すること。"""
        result = subprocess.run(
            ["bash", str(self.verify_docs_script)],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self._assert_process_succeeds(result)

    def test_typescript_build_succeeds_when_compiler_is_available(self):
        """Given TypeScript コンパイラが存在するとき、When jenkins-ssm-init をビルドすると、Then 正常終了すること。"""
        compiler = next((path for path in self.typescript_candidates if path.exists()), None)
        if compiler is None:
            self.skipTest("TypeScript コンパイラがリポジトリ内に存在しないためスキップします")

        env = {**os.environ, "NODE_OPTIONS": "--max-old-space-size=4096"}
        result = subprocess.run(
            ["node", str(compiler), "--project", "tsconfig.json"],
            cwd=self.ssm_init_dir,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        if result.returncode != 0 and "../lib/tsc.js" in result.stderr:
            self.skipTest("TypeScript ツールチェーンが不完全なためスキップします")

        self.assertEqual(
            0,
            result.returncode,
            f"TypeScript ビルドが失敗しました\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
        )
        self.assertTrue(
            (self.ssm_init_dir / "bin" / "index.js").is_file(),
            "TypeScript ビルド後に bin/index.js が生成される必要があります",
        )


if __name__ == "__main__":
    unittest.main()
