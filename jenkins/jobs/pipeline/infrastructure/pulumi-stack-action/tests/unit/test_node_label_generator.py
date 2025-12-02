"""
NodeLabelGenerator クラスのユニットテスト

テストシナリオ: test-scenario.md の UT-LABEL-001 ~ UT-LABEL-010
"""

import pytest
from node_label_generator import NodeLabelGenerator


class TestCreateReadableLabel:
    """create_readable_label() メソッドのテストクラス"""

    def test_create_readable_label_standard(self, sample_urn_info):
        """UT-LABEL-001: create_readable_label_標準的なURN情報_正常系

        Given: 標準的なURN情報（モジュール名あり）
        When: create_readable_label()を呼び出す
        Then: モジュール名\\nリソースタイプ\\nリソース名の形式でラベルが生成される
        """
        # Given
        urn_info = sample_urn_info

        # When
        result = NodeLabelGenerator.create_readable_label(urn_info)

        # Then
        assert result == "ec2\\nInstance\\nwebserver"

    def test_create_readable_label_without_module(self):
        """UT-LABEL-002: create_readable_label_モジュール名なし_準正常系

        Given: モジュール名がないURN情報
        When: create_readable_label()を呼び出す
        Then: リソースタイプ\\nリソース名の形式でラベルが生成される
        """
        # Given
        urn_info = {
            'provider': 'kubernetes',
            'module': '',
            'type': 'Service',
            'name': 'api-service'
        }

        # When
        result = NodeLabelGenerator.create_readable_label(urn_info)

        # Then
        assert result == "Service\\napi-service"

    def test_create_readable_label_long_resource_type(self):
        """UT-LABEL-003: create_readable_label_長いリソースタイプ名_境界値

        Given: 30文字を超える長いリソースタイプ名
        When: create_readable_label()を呼び出す
        Then: リソースタイプが適切に省略される
        """
        # Given
        urn_info = {
            'provider': 'aws',
            'module': 'ec2',
            'type': 'VeryLongResourceTypeNameThatExceedsThirtyCharacters',
            'name': 'resource'
        }

        # When
        result = NodeLabelGenerator.create_readable_label(urn_info)

        # Then
        # リソースタイプが省略されていることを確認
        lines = result.split('\\n')
        assert lines[0] == 'ec2'
        assert len(lines[1]) < len('VeryLongResourceTypeNameThatExceedsThirtyCharacters')
        assert lines[2] == 'resource'

    def test_create_readable_label_special_characters(self):
        """UT-LABEL-004: create_readable_label_特殊文字を含む名前_境界値

        Given: ハイフンを含むリソース名
        When: create_readable_label()を呼び出す
        Then: 特殊文字がそのまま含まれる（DOT形式に適合）
        """
        # Given
        urn_info = {
            'provider': 'aws',
            'module': 's3',
            'type': 'Bucket',
            'name': 'my-bucket-2024'
        }

        # When
        result = NodeLabelGenerator.create_readable_label(urn_info)

        # Then
        assert result == "s3\\nBucket\\nmy-bucket-2024"

    def test_create_readable_label_empty_urn_info(self):
        """UT-LABEL-005: create_readable_label_空のurn_info_異常系

        Given: 空の辞書
        When: create_readable_label()を呼び出す
        Then: 例外をスローせず、デフォルトラベルを返す
        """
        # Given
        urn_info = {}

        # When
        result = NodeLabelGenerator.create_readable_label(urn_info)

        # Then
        # デフォルト値（unknown）が含まれることを確認
        assert 'unknown' in result

    def test_create_readable_label_incomplete_urn_info(self):
        """UT-LABEL-006: create_readable_label_不完全なurn_info_異常系

        Given: 必要なキーが不足しているURN情報
        When: create_readable_label()を呼び出す
        Then: 適切に処理され、存在するキーのみを使用
        """
        # Given
        urn_info = {
            'provider': 'aws',
            'type': 'Instance'
            # module と name が不足
        }

        # When
        result = NodeLabelGenerator.create_readable_label(urn_info)

        # Then
        # タイプは存在するので含まれる
        assert 'Instance' in result
        # 不足しているキーのデフォルト値が使用される
        lines = result.split('\\n')
        assert len(lines) >= 2

    @pytest.mark.parametrize("urn_info,expected_lines", [
        (
            {'provider': 'aws', 'module': 'ec2', 'type': 'Instance', 'name': 'web'},
            ['ec2', 'Instance', 'web']
        ),
        (
            {'provider': 'gcp', 'module': 'compute', 'type': 'Instance', 'name': 'vm-1'},
            ['compute', 'Instance', 'vm-1']
        ),
        (
            {'provider': 'azure', 'module': 'network', 'type': 'VirtualNetwork', 'name': 'vnet'},
            ['network', 'VirtualNetwork', 'vnet']
        ),
        (
            {'provider': 'kubernetes', 'module': 'apps/v1', 'type': 'Deployment', 'name': 'nginx'},
            ['apps/v1', 'Deployment', 'nginx']
        ),
    ])
    def test_create_readable_label_parameterized(self, urn_info, expected_lines):
        """UT-LABEL-010: パラメタライズドテスト_複数のラベル生成

        Given: 多様なURN情報（複数クラウドプロバイダー）
        When: create_readable_label()を呼び出す
        Then: 各URN情報に対して正しいラベルが生成される
        """
        # When
        result = NodeLabelGenerator.create_readable_label(urn_info)

        # Then
        lines = result.split('\\n')
        assert lines == expected_lines


class TestFormatResourceType:
    """_format_resource_type() メソッドのテストクラス"""

    def test_format_resource_type_standard(self):
        """UT-LABEL-007: _format_resource_type_標準的なリソースタイプ_正常系

        Given: 短いリソースタイプ名（30文字以下）
        When: _format_resource_type()を呼び出す
        Then: そのまま返される
        """
        # Given
        resource_type = "Instance"

        # When
        result = NodeLabelGenerator._format_resource_type(resource_type)

        # Then
        assert result == "Instance"

    def test_format_resource_type_long_name(self):
        """UT-LABEL-008: _format_resource_type_長いリソースタイプ_境界値

        Given: 30文字を超えるリソースタイプ
        When: _format_resource_type()を呼び出す
        Then: 適切に省略される
        """
        # Given
        resource_type = "ApplicationLoadBalancerTargetGroup"

        # When
        result = NodeLabelGenerator._format_resource_type(resource_type)

        # Then
        # 省略されることを確認（元の長さより短くなる）
        assert len(result) < len(resource_type)
        # 最初と最後の単語が残ることを期待（実装により異なる可能性あり）

    def test_format_resource_type_camel_case_split(self):
        """UT-LABEL-009: _format_resource_type_キャメルケース分割_正常系

        Given: 複数単語のキャメルケース
        When: _format_resource_type()を呼び出す
        Then: 単語に分割され、適切に処理される
        """
        # Given
        resource_type = "VirtualMachineScaleSet"

        # When
        result = NodeLabelGenerator._format_resource_type(resource_type)

        # Then
        # 30文字以下なのでそのまま返される
        assert result == "VirtualMachineScaleSet"
