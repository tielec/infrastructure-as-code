"""
UrnProcessor クラスのユニットテスト

テストシナリオ: test-scenario.md の UT-URN-001 ~ UT-URN-012
"""

import pytest
from urn_processor import UrnProcessor


class TestParseUrn:
    """parse_urn() メソッドのテストクラス"""

    def test_parse_urn_standard_format(self, sample_urns):
        """UT-URN-001: parse_urn_標準的なURN形式_正常系

        Given: 標準的なURN形式
        When: parse_urn()を呼び出す
        Then: 各構成要素が正しく抽出される
        """
        # Given
        test_data = sample_urns['valid_urns'][0]
        urn = test_data['urn']
        expected = test_data['expected']

        # When
        result = UrnProcessor.parse_urn(urn)

        # Then
        assert result['stack'] == expected['stack']
        assert result['project'] == expected['project']
        assert result['provider'] == expected['provider']
        assert result['module'] == expected['module']
        assert result['type'] == expected['type']
        assert result['name'] == expected['name']
        assert result['full_urn'] == urn

    def test_parse_urn_with_module(self, sample_urns):
        """UT-URN-002: parse_urn_モジュール名あり_準正常系

        Given: モジュール名を含むURN
        When: parse_urn()を呼び出す
        Then: モジュール名が正しく抽出される
        """
        # Given
        test_data = sample_urns['valid_urns'][1]  # kubernetes:apps/v1:Deployment
        urn = test_data['urn']
        expected = test_data['expected']

        # When
        result = UrnProcessor.parse_urn(urn)

        # Then
        assert result['stack'] == expected['stack']
        assert result['project'] == expected['project']
        assert result['provider'] == expected['provider']
        assert result['module'] == expected['module']
        assert result['type'] == expected['type']
        assert result['name'] == expected['name']

    def test_parse_urn_invalid_format(self):
        """UT-URN-003: parse_urn_不正な形式_異常系

        Given: 不正なURN形式
        When: parse_urn()を呼び出す
        Then: 例外をスローせず、デフォルト値を返す
        """
        # Given
        urn = "invalid-urn-format"

        # When
        result = UrnProcessor.parse_urn(urn)

        # Then
        assert result['stack'] == ''
        assert result['project'] == ''
        assert result['provider'] == 'unknown'
        assert result['module'] == ''
        assert result['type'] == 'unknown'
        assert result['name'] == 'invalid-urn-format'
        assert result['full_urn'] == urn

    def test_parse_urn_empty_string(self):
        """UT-URN-004: parse_urn_空文字列_異常系

        Given: 空文字列
        When: parse_urn()を呼び出す
        Then: デフォルト値を返す
        """
        # Given
        urn = ""

        # When
        result = UrnProcessor.parse_urn(urn)

        # Then
        assert result['stack'] == ''
        assert result['project'] == ''
        assert result['provider'] == 'unknown'
        assert result['module'] == ''
        assert result['type'] == 'unknown'
        assert result['name'] == ''
        assert result['full_urn'] == ''

    def test_parse_urn_none_input(self):
        """UT-URN-005: parse_urn_None入力_異常系

        Given: None が入力される
        When: parse_urn()を呼び出す
        Then: デフォルト値を返す（例外をスローしない）
        """
        # Given
        urn = None

        # When
        result = UrnProcessor.parse_urn(urn)

        # Then
        assert result['stack'] == ''
        assert result['project'] == ''
        assert result['provider'] == 'unknown'
        assert result['module'] == ''
        assert result['type'] == 'unknown'
        assert result['name'] == ''
        assert result['full_urn'] is None

    def test_parse_urn_special_characters(self, sample_urns):
        """UT-URN-006: parse_urn_特殊文字を含むURN_境界値

        Given: ハイフンを含むURN
        When: parse_urn()を呼び出す
        Then: 特殊文字が正しく処理される
        """
        # Given
        urn = "urn:pulumi:dev::my-project::aws:ec2/instance:Instance::web-server-01"

        # When
        result = UrnProcessor.parse_urn(urn)

        # Then
        assert result['stack'] == 'dev'
        assert result['project'] == 'my-project'
        assert result['provider'] == 'aws'
        assert result['module'] == 'ec2'
        assert result['type'] == 'Instance'
        assert result['name'] == 'web-server-01'

    def test_parse_urn_very_long_urn(self, sample_urns):
        """UT-URN-007: parse_urn_非常に長いURN_境界値

        Given: 極端に長いURN（300文字以上）
        When: parse_urn()を呼び出す
        Then: 適切にパースされる
        """
        # Given
        test_data = sample_urns['edge_case_urns'][2]  # 非常に長いURN
        urn = test_data['urn']

        # When
        result = UrnProcessor.parse_urn(urn)

        # Then
        # URNが長くても基本構造は維持される
        assert result['stack'] == 'dev'
        assert result['project'] == 'project-with-very-long-name-that-exceeds-normal-limits'
        assert result['provider'] == 'aws'
        assert result['module'] == 'ec2'
        assert result['type'] == 'Instance'
        assert result['name'] == 'resource-with-extremely-long-name-that-should-be-handled-correctly'

    def test_parse_urn_minimal_structure(self):
        """UT-URN-008: parse_urn_短いURN_境界値

        Given: 最小限の構成要素しかないURN
        When: parse_urn()を呼び出す
        Then: 可能な範囲で構成要素を抽出
        """
        # Given
        urn = "urn:pulumi:dev::project::type::name"

        # When
        result = UrnProcessor.parse_urn(urn)

        # Then
        assert result['stack'] == 'dev'
        assert result['project'] == 'project'
        assert result['name'] == 'name'
        # プロバイダータイプが不正な形式の場合はデフォルト値
        assert 'provider' in result

    @pytest.mark.parametrize("urn,expected_provider,expected_type", [
        ("urn:pulumi:dev::project::aws:s3/bucket:Bucket::my-bucket", "aws", "Bucket"),
        ("urn:pulumi:prod::app::gcp:compute/instance:Instance::vm-1", "gcp", "Instance"),
        ("urn:pulumi:staging::web::azure:network/virtualNetwork:VirtualNetwork::vnet", "azure", "VirtualNetwork"),
        ("urn:pulumi:test::api::kubernetes:apps/v1:Deployment::nginx", "kubernetes", "Deployment"),
    ])
    def test_parse_urn_parameterized(self, urn, expected_provider, expected_type):
        """UT-URN-012: パラメタライズドテスト_複数のURN形式

        Given: 多様なURN形式（複数クラウドプロバイダー）
        When: parse_urn()を呼び出す
        Then: 各URNが正しくパースされる
        """
        # When
        result = UrnProcessor.parse_urn(urn)

        # Then
        assert result['provider'] == expected_provider
        assert result['type'] == expected_type
        assert result['full_urn'] == urn


class TestParseProviderType:
    """_parse_provider_type() メソッドのテストクラス"""

    def test_parse_provider_type_standard(self):
        """UT-URN-009: _parse_provider_type_標準的なプロバイダータイプ_正常系

        Given: 標準的なプロバイダータイプ（aws:ec2/instance:Instance）
        When: _parse_provider_type()を呼び出す
        Then: プロバイダー、モジュール、タイプが正しく抽出される
        """
        # Given
        provider_type = "aws:ec2/instance:Instance"

        # When
        result = UrnProcessor._parse_provider_type(provider_type)

        # Then
        assert result['provider'] == 'aws'
        assert result['module'] == 'ec2'
        assert result['type'] == 'Instance'

    def test_parse_provider_type_without_module(self):
        """UT-URN-010: _parse_provider_type_モジュールなし_準正常系

        Given: モジュール情報がないプロバイダータイプ
        When: _parse_provider_type()を呼び出す
        Then: モジュールは空文字列、他は正しく抽出される
        """
        # Given
        provider_type = "kubernetes:Service"

        # When
        result = UrnProcessor._parse_provider_type(provider_type)

        # Then
        assert result['provider'] == 'kubernetes'
        assert result['module'] == ''
        assert result['type'] == 'Service'

    def test_parse_provider_type_invalid_format(self):
        """UT-URN-011: _parse_provider_type_不正な形式_異常系

        Given: 不正なプロバイダータイプ
        When: _parse_provider_type()を呼び出す
        Then: デフォルト値を返す
        """
        # Given
        provider_type = "invalid"

        # When
        result = UrnProcessor._parse_provider_type(provider_type)

        # Then
        assert result['provider'] == 'unknown'
        assert result['module'] == ''
        assert result['type'] == 'invalid'
