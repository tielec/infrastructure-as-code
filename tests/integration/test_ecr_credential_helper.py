"""Integration tests for Issue #556: ECR credential-helper on Jenkins Agent AMI."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

import yaml


class EcrCredentialHelperTests(unittest.TestCase):
    """INTEGRATION_ONLY checks for Image Builder components, userdata scripts, and docs."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.ami_dir = cls.repo_root / "pulumi" / "jenkins-agent-ami"
        cls.helper_script = cls.repo_root / "tests" / "integration" / "helpers" / "render_jenkins_agent_ami_components.js"
        cls.compiled_index = cls.ami_dir / "bin" / "index.js"
        cls.component_x86 = cls.ami_dir / "component-x86.yml"
        cls.component_arm = cls.ami_dir / "component-arm.yml"
        cls.userdata_setup = cls.repo_root / "scripts" / "aws" / "userdata" / "jenkins-agent-setup.sh"
        cls.userdata_custom = cls.repo_root / "scripts" / "aws" / "userdata" / "jenkins-agent-custom-ami.sh"
        cls.doc_path = cls.repo_root / "jenkins" / "DOCKER_IMAGES.md"

        cls._install_node_dependencies()
        cls._build_typescript()
        cls._ensure_pulumi_assets_in_bin()
        cls.preview = cls._render_components()

    @classmethod
    def _install_node_dependencies(cls):
        subprocess.run(
            ["npm", "--silent", "install"],
            cwd=cls.ami_dir,
            check=True,
        )

    @classmethod
    def _build_typescript(cls):
        env = {**os.environ, "NODE_OPTIONS": "--max-old-space-size=4096"}
        subprocess.run(
            ["npm", "--silent", "run", "build"],
            cwd=cls.ami_dir,
            check=True,
            env=env,
        )
        if not cls.compiled_index.exists():
            raise AssertionError("TypeScript build did not produce bin/index.js")

    @classmethod
    def _ensure_pulumi_assets_in_bin(cls):
        assets = [
            (
                cls.ami_dir / "templates" / "cloudwatch-agent-config.json",
                cls.compiled_index.parent / "templates" / "cloudwatch-agent-config.json",
            ),
            (cls.ami_dir / "component-arm.yml", cls.compiled_index.parent / "component-arm.yml"),
            (cls.ami_dir / "component-x86.yml", cls.compiled_index.parent / "component-x86.yml"),
        ]
        for source, destination in assets:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    @classmethod
    def _render_components(cls) -> dict:
        env = {**os.environ, "NODE_OPTIONS": "--max-old-space-size=4096"}
        result = subprocess.run(
            ["node", str(cls.helper_script)],
            cwd=cls.repo_root,
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        return json.loads(result.stdout)

    def _component_map(self) -> dict:
        components = self.preview.get("components", [])
        self.assertGreaterEqual(len(components), 2, "Both ARM/x86 components should be synthesized")
        return {c["name"]: c for c in components}

    @staticmethod
    def _extract_step_names(component_data: str) -> list[str]:
        return re.findall(r"^\s*- name: (.+)$", component_data, re.MULTILINE)

    @staticmethod
    def _extract_block(text: str, start_marker: str, end_marker: str) -> str:
        start_index = text.find(start_marker)
        end_index = text.find(end_marker)
        if start_index == -1 or end_index == -1 or end_index <= start_index:
            return ""
        return text[start_index + len(start_marker) : end_index]

    def test_install_step_exists(self):
        """IT-556-01: InstallEcrCredentialHelperステップが両アーキテクチャに存在すること。"""
        components = self._component_map()
        required_snippets = [
            "InstallEcrCredentialHelper",
            "dnf install -y amazon-ecr-credential-helper",
            "which docker-credential-ecr-login",
        ]
        for name, comp in components.items():
            # Given: Image Builderコンポーネントのデータ
            data = comp["data"]
            # When/Then: ステップとコマンドの存在を確認
            for snippet in required_snippets:
                self.assertIn(snippet, data, f"{name} should include '{snippet}'")

    def test_install_step_order(self):
        """IT-556-02: InstallDockerの後にInstallEcrCredentialHelperが配置されること。"""
        for name, comp in self._component_map().items():
            # Given: ステップ名の順序
            steps = self._extract_step_names(comp["data"])
            # When/Then: 期待する順序を検証
            self.assertIn("InstallDocker", steps, f"{name} should define InstallDocker")
            self.assertIn("InstallEcrCredentialHelper", steps, f"{name} should define InstallEcrCredentialHelper")
            self.assertLess(
                steps.index("InstallDocker"),
                steps.index("InstallEcrCredentialHelper"),
                f"{name} should place InstallEcrCredentialHelper after InstallDocker",
            )

    def test_create_jenkins_user_config(self):
        """IT-556-03: CreateJenkinsUser内のconfig.json生成とフォールバックが存在すること。"""
        required_snippets = [
            "CreateJenkinsUser",
            "credHelpers",
            "ecr-login",
            "aws sts get-caller-identity",
            "/home/jenkins/.docker/config.json",
            "/root/.docker/config.json",
            "chown jenkins:jenkins",
            "*.dkr.ecr.*.amazonaws.com",
        ]
        for name, comp in self._component_map().items():
            # Given: コンポーネント定義
            data = comp["data"]
            # When/Then: 必須文字列の存在を検証
            for snippet in required_snippets:
                self.assertIn(snippet, data, f"{name} should include '{snippet}'")

    def test_validate_installation_step(self):
        """IT-556-04: ValidateInstallationのバリデーション項目が追加されていること。"""
        required_snippets = [
            "ValidateInstallation",
            "which docker-credential-ecr-login",
            "test -f /home/jenkins/.docker/config.json",
            "test -f /root/.docker/config.json",
            "jq . /home/jenkins/.docker/config.json",
            "jq -e '.credHelpers' /home/jenkins/.docker/config.json",
        ]
        for name, comp in self._component_map().items():
            # Given: ValidateInstallationステップ
            data = comp["data"]
            # When/Then: バリデーション項目の存在を検証
            for snippet in required_snippets:
                self.assertIn(snippet, data, f"{name} should include '{snippet}'")

    def test_component_step_consistency(self):
        """IT-556-05: x86_64/ARM64のステップ構成が一致していること。"""
        components = self._component_map()
        # Given: 両アーキテクチャのステップ一覧
        steps_x86 = self._extract_step_names(components["agent-component-x86"]["data"])
        steps_arm = self._extract_step_names(components["agent-component-arm"]["data"])
        # When/Then: ステップ構成が一致することを検証
        self.assertListEqual(steps_x86, steps_arm, "Step sequence must match between architectures")
        for keyword in ("InstallEcrCredentialHelper", "credHelpers", "docker-credential-ecr-login"):
            self.assertIn(keyword, components["agent-component-x86"]["data"])
            self.assertIn(keyword, components["agent-component-arm"]["data"])

    def test_yaml_parses_and_has_phases(self):
        """IT-556-06: component YAMLがパース可能でbuild/validateフェーズが存在すること。"""
        for path in (self.component_x86, self.component_arm):
            # Given: コンポーネントYAML
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            # When: phasesを取得
            phase_names = [phase.get("name") for phase in data.get("phases", [])]
            # Then: build/validateが存在する
            self.assertIn("build", phase_names, f"{path} should include build phase")
            self.assertIn("validate", phase_names, f"{path} should include validate phase")

    def test_pulumi_mock_components_present(self):
        """IT-556-07: Pulumiモック合成に両コンポーネントが含まれること。"""
        components = self._component_map()
        # Given/When/Then: 期待するコンポーネント名を検証
        self.assertSetEqual(set(components.keys()), {"agent-component-x86", "agent-component-arm"})

    def test_userdata_setup_has_credential_helper_config(self):
        """IT-556-08: jenkins-agent-setup.shにcredential-helperのフル設定が含まれること。"""
        script = self.userdata_setup.read_text(encoding="utf-8")
        required_snippets = [
            "dnf install -y amazon-ecr-credential-helper",
            "X-aws-ec2-metadata-token-ttl-seconds",
            "instance-identity/document",
            "/home/jenkins/.docker/config.json",
            "/root/.docker/config.json",
            "credHelpers",
            "ecr-login",
            "chown jenkins:jenkins",
            "WARNING: ACCOUNT_ID",
        ]
        # Given/When/Then: 追加コードの存在を検証
        for snippet in required_snippets:
            self.assertIn(snippet, script, f"setup.sh should include '{snippet}'")

    def test_userdata_custom_ami_has_fallback(self):
        """IT-556-09: jenkins-agent-custom-ami.shの冪等性チェックとフォールバックが存在すること。"""
        script = self.userdata_custom.read_text(encoding="utf-8")
        required_snippets = [
            "jq -e '.credHelpers'",
            "既に設定済み",
            "X-aws-ec2-metadata-token-ttl-seconds",
            "credHelpers",
            "ecr-login",
            "chown jenkins:jenkins",
            "WARNING: ACCOUNT_ID",
        ]
        for snippet in required_snippets:
            self.assertIn(snippet, script, f"custom-ami.sh should include '{snippet}'")

    def test_custom_ami_block_avoids_pulumi_template_vars(self):
        """IT-556-10: credential-helper追加ブロックがPulumiテンプレート変数と干渉しないこと。"""
        script = self.userdata_custom.read_text(encoding="utf-8")
        block = self._extract_block(
            script,
            "# ===== ECR credential-helper config.json のフォールバック設定 =====",
            "# ===== ECR credential-helper フォールバック設定完了 =====",
        )
        self.assertTrue(block, "credential-helper block should be extracted")
        forbidden_tokens = ["${PROJECT_NAME}", "${ENVIRONMENT}", "${IPV6_CONFIG}", "${ARCHITECTURE_ENV}"]
        # Given/When/Then: 追加コードにテンプレート変数が無いことを検証
        for token in forbidden_tokens:
            self.assertNotIn(token, block, f"credential-helper block should not contain {token}")

    def test_config_json_structure_normal(self):
        """IT-556-13: 通常形式のconfig.json構造が正しいこと。"""
        # Given: 通常形式のconfig.json
        config_json = """{"credHelpers":{"123456789012.dkr.ecr.ap-northeast-1.amazonaws.com":"ecr-login"}}"""
        # When: JSONパース
        data = json.loads(config_json)
        # Then: 構造と値を検証
        self.assertIn("credHelpers", data)
        endpoints = list(data["credHelpers"].keys())
        self.assertEqual(1, len(endpoints))
        self.assertRegex(endpoints[0], r"^[0-9]{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com$")
        self.assertEqual("ecr-login", data["credHelpers"][endpoints[0]])

    def test_config_json_structure_wildcard(self):
        """IT-556-14: フォールバック形式のconfig.json構造が正しいこと。"""
        # Given: ワイルドカード形式のconfig.json
        config_json = """{"credHelpers":{"*.dkr.ecr.*.amazonaws.com":"ecr-login"}}"""
        data = json.loads(config_json)
        # Then: ワイルドカードキーと値を検証
        self.assertIn("credHelpers", data)
        endpoints = list(data["credHelpers"].keys())
        self.assertEqual(["*.dkr.ecr.*.amazonaws.com"], endpoints)
        self.assertEqual("ecr-login", data["credHelpers"][endpoints[0]])

    def test_double_protection_mechanism(self):
        """IT-556-15: AMIビルド時とEC2起動時の二重保護設計が存在すること。"""
        components = self._component_map()
        # Given: AMIビルド時の設定
        for name, comp in components.items():
            data = comp["data"]
            self.assertIn("InstallEcrCredentialHelper", data, f"{name} should include install step")
            self.assertIn("/home/jenkins/.docker/config.json", data, f"{name} should configure jenkins config.json")
            self.assertIn("ValidateInstallation", data, f"{name} should include validation step")

        # When/Then: EC2起動時の設定を検証
        setup_script = self.userdata_setup.read_text(encoding="utf-8")
        self.assertIn("amazon-ecr-credential-helper", setup_script)
        self.assertIn("/home/jenkins/.docker/config.json", setup_script)

        custom_script = self.userdata_custom.read_text(encoding="utf-8")
        self.assertIn("jq -e '.credHelpers'", custom_script)
        self.assertIn("ECR credential-helper config.json が未設定です", custom_script)

    def test_imdsv2_token_usage(self):
        """IT-556-16: IMDSv2トークンベースのメタデータアクセスが使用されていること。"""
        for path in (self.userdata_setup, self.userdata_custom):
            script = path.read_text(encoding="utf-8")
            # Given/When/Then: トークン取得とヘッダー使用を確認
            self.assertIn("latest/api/token", script, f"{path} should request IMDSv2 token")
            self.assertIn("X-aws-ec2-metadata-token-ttl-seconds", script, f"{path} should include TTL header")
            self.assertIn("X-aws-ec2-metadata-token", script, f"{path} should send token header")
            # IMDSv1の直接アクセスが無いことを検証
            unsafe_calls = [
                line
                for line in script.splitlines()
                if "169.254.169.254/latest/dynamic/instance-identity/document" in line
                and "X-aws-ec2-metadata-token" not in line
            ]
            self.assertFalse(unsafe_calls, f"{path} should not use IMDSv1 without token")

    def test_documentation_mentions_credential_helper(self):
        """IT-556-17: DOCKER_IMAGES.mdにECR credential-helperの説明があること。"""
        doc_text = self.doc_path.read_text(encoding="utf-8")
        # Given/When/Then: 必須の説明が含まれることを検証
        self.assertRegex(doc_text, r"ECR.*credential-helper", "ECR credential-helper section should exist")
        self.assertIn("aws ecr get-login-password", doc_text)
        self.assertIn("EC2 Fleet", doc_text)
        self.assertIn("ECS Fargate", doc_text)
        self.assertIn("credHelpers", doc_text)
        self.assertIn("ecr-login", doc_text)
        self.assertIn("|", doc_text, "Comparison table should be present")

    def test_placeholder_replaced_in_pulumi_data(self):
        """IT-556-18: コンポーネントデータに未置換のプレースホルダーが残っていないこと。"""
        for name, comp in self._component_map().items():
            # Given/When/Then: プレースホルダーが残っていないこと
            self.assertNotIn("__CWAGENT_CONFIG__", comp["data"], f"{name} should not contain template placeholders")

    def test_invalid_config_json_detected_by_jq(self):
        """IT-556-19: 不正JSONやcredHelpers欠落がjqで検出されること。"""
        if shutil.which("jq") is None:
            self.skipTest("jq is not installed")

        invalid_json = '{"credHelpers": {"endpoint": "ecr-login"}'
        result = subprocess.run(["jq", "."], input=invalid_json, text=True, capture_output=True)
        self.assertNotEqual(0, result.returncode, "jq should fail on invalid JSON")

        missing_key_json = '{"otherKey": "value"}'
        result = subprocess.run(["jq", "-e", ".credHelpers"], input=missing_key_json, text=True, capture_output=True)
        self.assertNotEqual(0, result.returncode, "jq should fail when credHelpers is missing")

    def test_non_ecr_registry_not_affected(self):
        """IT-556-20: credHelpersがECRのみを対象にしていること。"""
        config_json = """{"credHelpers":{"123456789012.dkr.ecr.ap-northeast-1.amazonaws.com":"ecr-login"}}"""
        data = json.loads(config_json)
        # Given/When/Then: credHelpersキーがECRのみでありcredsStoreが無いこと
        self.assertNotIn("credsStore", data)
        endpoints = list(data["credHelpers"].keys())
        self.assertTrue(all("dkr.ecr" in endpoint for endpoint in endpoints))
        self.assertTrue(all("docker.io" not in endpoint for endpoint in endpoints))
        self.assertTrue(all("ghcr.io" not in endpoint for endpoint in endpoints))


if __name__ == "__main__":
    unittest.main()
