"""Issue #568 の Jenkins Controller 変更を検証する統合テスト。"""

import os
from pathlib import Path
import re
import subprocess
import unittest


class JenkinsControllerMonitoringIntegrationTests(unittest.TestCase):
    """t4g.large 化、monitoring 追加、README 反映、検証スクリプトを静的に検証する。"""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.ssm_init = cls.repo_root / "pulumi" / "jenkins-ssm-init" / "index.ts"
        cls.controller = cls.repo_root / "pulumi" / "jenkins-controller" / "index.ts"
        cls.ssm_init_dir = cls.repo_root / "pulumi" / "jenkins-ssm-init"
        cls.typescript_cli = (
            cls.repo_root
            / "pulumi"
            / "components"
            / "node_modules"
            / "typescript"
            / "bin"
            / "tsc"
        )
        cls.plugins = (
            cls.repo_root / "scripts" / "jenkins" / "groovy" / "install-plugins.groovy"
        )
        cls.readme = cls.repo_root / "jenkins" / "README.md"
        cls.pulumi_readme = cls.repo_root / "pulumi" / "README.md"
        cls.scripts_readme = cls.repo_root / "scripts" / "README.md"
        cls.verify_instance_script = cls.repo_root / "tests" / "issue-568" / "verify-instance-type.sh"
        cls.verify_plugins_script = cls.repo_root / "tests" / "issue-568" / "verify-plugins.sh"
        cls.application_playbook = (
            cls.repo_root
            / "ansible"
            / "playbooks"
            / "jenkins"
            / "deploy"
            / "deploy_jenkins_application.yml"
        )
        cls.ssm_init_playbook = (
            cls.repo_root
            / "ansible"
            / "playbooks"
            / "jenkins"
            / "deploy"
            / "deploy_jenkins_ssm_init.yml"
        )
        cls.controller_playbook = (
            cls.repo_root
            / "ansible"
            / "playbooks"
            / "jenkins"
            / "deploy"
            / "deploy_jenkins_controller.yml"
        )

        cls.ssm_init_text = cls.ssm_init.read_text(encoding="utf-8")
        cls.controller_text = cls.controller.read_text(encoding="utf-8")
        cls.plugins_text = cls.plugins.read_text(encoding="utf-8")
        cls.readme_text = cls.readme.read_text(encoding="utf-8")
        cls.pulumi_readme_text = cls.pulumi_readme.read_text(encoding="utf-8")
        cls.scripts_readme_text = cls.scripts_readme.read_text(encoding="utf-8")
        cls.plugin_entries = re.findall(r'"([^"]+)"', cls._extract_plugins_block())
        cls._build_typescript()

    @classmethod
    def _extract_plugins_block(cls) -> str:
        """Groovy の plugins 配列部分だけを切り出す。"""
        match = re.search(r"def plugins = \[(.*?)\n\]", cls.plugins_text, re.DOTALL)
        if match is None:
            raise AssertionError("install-plugins.groovy の plugins 配列を抽出できません")
        return match.group(1)

    @classmethod
    def _build_typescript(cls):
        """jenkins-ssm-init の TypeScript がエラーなくビルドできることを確認する。"""
        env = {**os.environ, "NODE_OPTIONS": "--max-old-space-size=4096"}
        subprocess.run(
            ["node", str(cls.typescript_cli), "--project", "tsconfig.json"],
            cwd=cls.ssm_init_dir,
            check=True,
            env=env,
        )

    @classmethod
    def _extract_ssm_parameter_block(cls, logical_name: str) -> str:
        """指定した SSM パラメータ定義ブロックだけを返す。"""
        marker = f'const {logical_name} = new aws.ssm.Parameter("'
        start = cls.ssm_init_text.find(marker)
        if start == -1:
            raise AssertionError(f"{logical_name} の定義が必要です")
        end = cls.ssm_init_text.find("});", start)
        if end == -1:
            raise AssertionError(f"{logical_name} の定義終端が必要です")
        return cls.ssm_init_text[start:end]

    @staticmethod
    def _assert_process_succeeds(result: subprocess.CompletedProcess[str]):
        """シェルスクリプト実行結果の終了コードと PASS 表示を確認する。"""
        if result.returncode != 0:
            raise AssertionError(
                f"終了コード {result.returncode} で失敗しました\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        if "FAIL" in result.stdout:
            raise AssertionError(f"スクリプト出力に FAIL が含まれています\n{result.stdout}")
        if "PASS" not in result.stdout:
            raise AssertionError(f"スクリプト出力に PASS が含まれていません\n{result.stdout}")

    def test_controller_instance_type_is_t4g_large(self):
        """Given SSM 定義を確認するとき、When controller の型を見ると、Then t4g.large であること。"""
        self.assertIn(
            'name: `${ssmPrefix}/config/controller-instance-type`',
            self.ssm_init_text,
        )
        self.assertIn(
            'value: "t4g.large",  // ARM64 instance type',
            self.ssm_init_text,
        )
        self.assertNotIn(
            'value: "t4g.medium",  // ARM64 instance type',
            self._extract_ssm_parameter_block("controllerInstanceTypeParam"),
        )

    def test_agent_instance_type_remains_t4g_medium(self):
        """Given 変更範囲を確認するとき、When agent 側を見ると、Then t4g.medium のままであること。"""
        self.assertIn(
            'value: "t4g.medium",  // ARM64 instance type',
            self._extract_ssm_parameter_block("agentInstanceTypeParam"),
        )

    def test_controller_instance_type_keeps_expected_metadata(self):
        """Given controller の SSM 定義を見るとき、When 属性を確認すると、Then 値以外の主要メタデータが維持されること。"""
        block = self._extract_ssm_parameter_block("controllerInstanceTypeParam")
        required_lines = [
            'name: `${ssmPrefix}/config/controller-instance-type`',
            'type: "String",',
            'overwrite: true,',
            'description: "Jenkins controller EC2 instance type",',
            "Environment: environment,",
            'ManagedBy: "pulumi",',
            'Component: "config",',
        ]
        for line in required_lines:
            self.assertIn(line, block)

    def test_other_ssm_parameters_remain_expected(self):
        """Given 変更スコープを確認するとき、When 代表的な他パラメータを見ると、Then 既存値が維持されること。"""
        expected_values = [
            'value: "latest",',
            'value: "blue",',
            'value: "false",',
            'value: "none",  // EC2キーペア名',
            'value: "t4g.nano",  // ARM64ベースの最小インスタンス（コスト最適化）',
        ]
        for value in expected_values:
            self.assertIn(value, self.ssm_init_text)

        parameter_names = [
            "project-name",
            "vpc-cidr",
            "ipv6-enabled",
            "use-egress-only-gateway",
            "nat-high-availability",
            "nat-instance-type",
            "jenkins-version",
            "jenkins-color",
            "jenkins-recovery-mode",
            "key-name",
            "controller-instance-type",
            "agent-instance-type",
            "agent-min-capacity",
            "agent-max-capacity",
            "agent-medium-min-capacity",
            "agent-medium-max-capacity",
            "agent-small-min-capacity",
            "agent-small-max-capacity",
        ]
        for parameter_name in parameter_names:
            self.assertEqual(
                1,
                self.ssm_init_text.count(f'"{parameter_name}"'),
                f"{parameter_name} の定義は 1 回だけ存在する必要があります",
            )

    def test_controller_instance_type_keeps_t4g_family_for_arm64(self):
        """Given controller の型を抽出するとき、When 値を評価すると、Then t4g ファミリーを維持すること。"""
        block = self._extract_ssm_parameter_block("controllerInstanceTypeParam")
        match = re.search(r'value: "(t4g\.[^"]+)"', block)
        self.assertIsNotNone(match, "controller-instance-type の値を抽出できる必要があります")
        self.assertTrue(
            match.group(1).startswith("t4g."),
            "controller-instance-type は ARM64 前提の t4g ファミリーを維持する必要があります",
        )

    def test_controller_stack_reads_matching_ssm_parameter(self):
        """Given 両スタックを比較するとき、When SSM 名を確認すると、Then 定義と参照が一致すること。"""
        expected_name = 'name: `${ssmPrefix}/config/controller-instance-type`'
        self.assertIn(expected_name, self.ssm_init_text)
        self.assertIn(expected_name, self.controller_text)
        self.assertIn("const instanceTypeParam = aws.ssm.getParameter({", self.controller_text)
        self.assertIn(
            "const instanceType = pulumi.output(instanceTypeParam).apply(p => p.value);",
            self.controller_text,
        )

    def test_monitoring_plugin_is_added_with_japanese_comment(self):
        """Given plugins 配列を確認するとき、When monitoring を探すと、Then 日本語コメント付きで存在すること。"""
        self.assertIn(
            '// モニタリングプラグイン（JavaMelody: CPU/メモリ監視）',
            self.plugins_text,
        )
        self.assertIn('"monitoring"', self.plugins_text)
        self.assertEqual(
            1,
            self.plugins_text.count('"monitoring"'),
            "monitoring プラグインは 1 回だけ定義されるべきです",
        )

    def test_plugin_list_has_valid_tail_syntax(self):
        """Given Groovy 配列末尾を確認するとき、When 末尾 2 要素を見ると、Then カンマ位置が正しいこと。"""
        plugins_block = self._extract_plugins_block()
        self.assertIn('"file-parameters",', plugins_block)
        self.assertRegex(
            plugins_block,
            r'"file-parameters",\s*\n\s*// モニタリングプラグイン（JavaMelody: CPU/メモリ監視）\s*\n\s*"monitoring"\s*$',
        )
        self.assertIn("\n]\n", self.plugins_text, "plugins 配列の閉じ括弧が必要です")

    def test_plugin_list_entries_are_unique(self):
        """Given plugins 配列を列挙するとき、When 重複を調べると、Then すべて一意であること。"""
        self.assertGreater(len(self.plugin_entries), 0, "plugins 配列は空であってはいけません")
        self.assertEqual(
            len(self.plugin_entries),
            len(set(self.plugin_entries)),
            "plugins 配列に重複エントリがあってはいけません",
        )

    def test_typescript_build_succeeds_for_ssm_init_stack(self):
        """Given jenkins-ssm-init をビルドするとき、When テストを実行すると、Then bin/index.js が生成されること。"""
        compiled_index = self.ssm_init_dir / "bin" / "index.js"
        self.assertTrue(compiled_index.exists(), "TypeScript build 後に bin/index.js が存在する必要があります")

    def test_readme_documents_javamelody_section_details(self):
        """Given README を確認するとき、When JavaMelody セクションを見ると、Then 必須情報が日本語で揃っていること。"""
        required_snippets = [
            "## JavaMelodyモニタリング",
            "`monitoring` プラグイン（JavaMelody）",
            "https://<jenkins-url>/monitoring",
            "管理者権限を持つユーザー",
            "CPU 使用率",
            "メモリ使用量",
            "GC の実行回数",
            "スレッド情報",
            "$JENKINS_HOME/monitoring/",
        ]
        for snippet in required_snippets:
            self.assertIn(snippet, self.readme_text)

        monitoring_index = self.readme_text.index("## JavaMelodyモニタリング")
        troubleshooting_index = self.readme_text.index("## トラブルシューティング")
        self.assertLess(
            monitoring_index,
            troubleshooting_index,
            "JavaMelody セクションはトラブルシューティングより前に配置される必要があります",
        )

    def test_readme_preserves_existing_sections_and_troubleshooting_table(self):
        """Given README を確認するとき、When 既存セクションを見ると、Then 主要セクションと表が保全されていること。"""
        required_sections = [
            "## トラブルシューティング",
            "## 開発者向け情報",
            "## 関連ドキュメント",
        ]
        for section in required_sections:
            self.assertIn(section, self.readme_text)

        required_table_rows = [
            "| 問題 | 原因 | 解決方法 |",
            "| ジョブが見つからない | Job DSLが未反映 | Admin_Jobs > job-creator を実行 |",
            "| プラグインエラー | プラグイン未インストール | Plugin Managerから必要なプラグインをインストール |",
        ]
        for row in required_table_rows:
            self.assertIn(row, self.readme_text)

    def test_readme_documents_deploy_order_and_commands(self):
        """Given README を確認するとき、When 手順とコマンドを見ると、Then 反映順序が明記されていること。"""
        required_snippets = [
            "### 反映手順",
            "deploy_jenkins_application.yml",
            "deploy_jenkins_ssm_init.yml",
            "deploy_jenkins_controller.yml",
            'ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_application.yml -e "env=dev"',
            'ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_ssm_init.yml -e "env=dev"',
            'ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_controller.yml -e "env=dev"',
            "/jenkins-infra/<env>/config/controller-instance-type",
            "https://<jenkins-url>/monitoring",
        ]
        for snippet in required_snippets:
            self.assertIn(snippet, self.readme_text)

        application_index = self.readme_text.index("deploy_jenkins_application.yml")
        ssm_index = self.readme_text.index("deploy_jenkins_ssm_init.yml")
        controller_index = self.readme_text.index("deploy_jenkins_controller.yml")
        self.assertLess(application_index, ssm_index)
        self.assertLess(ssm_index, controller_index)

    def test_related_ansible_playbooks_exist(self):
        """Given README に手順を書くとき、When playbook を参照すると、Then 実ファイルが存在すること。"""
        for path in (
            self.application_playbook,
            self.ssm_init_playbook,
            self.controller_playbook,
        ):
            self.assertTrue(path.is_file(), f"Missing playbook: {path}")

    def test_pulumi_readme_does_not_require_instance_type_update(self):
        """Given pulumi/README.md を確認するとき、When 具体的な型名を探すと、Then 更新不要と判断できること。"""
        self.assertNotIn("t4g.medium", self.pulumi_readme_text)
        self.assertNotIn("t4g.large", self.pulumi_readme_text)
        self.assertNotIn("controller-instance-type", self.pulumi_readme_text)

    def test_scripts_readme_does_not_list_individual_plugin_names(self):
        """Given scripts/README.md を確認するとき、When 個別プラグイン名を探すと、Then 更新不要と判断できること。"""
        self.assertNotIn('"monitoring"', self.scripts_readme_text)
        self.assertNotIn('"copyartifact"', self.scripts_readme_text)
        self.assertNotIn('"file-parameters"', self.scripts_readme_text)
        self.assertNotIn("monitoring プラグイン", self.scripts_readme_text)

    def test_verify_instance_type_script_succeeds(self):
        """Given 検証スクリプトを実行するとき、When verify-instance-type.sh を流すと、Then 期待した PASS で完了すること。"""
        self.assertTrue(self.verify_instance_script.is_file(), "verify-instance-type.sh が必要です")
        result = subprocess.run(
            ["bash", str(self.verify_instance_script)],
            cwd=self.verify_instance_script.parent,
            check=False,
            text=True,
            capture_output=True,
        )
        self._assert_process_succeeds(result)

    def test_verify_plugins_script_succeeds(self):
        """Given 検証スクリプトを実行するとき、When verify-plugins.sh を流すと、Then 期待した PASS で完了すること。"""
        self.assertTrue(self.verify_plugins_script.is_file(), "verify-plugins.sh が必要です")
        result = subprocess.run(
            ["bash", str(self.verify_plugins_script)],
            cwd=self.verify_plugins_script.parent,
            check=False,
            text=True,
            capture_output=True,
        )
        self._assert_process_succeeds(result)


if __name__ == "__main__":
    unittest.main()
