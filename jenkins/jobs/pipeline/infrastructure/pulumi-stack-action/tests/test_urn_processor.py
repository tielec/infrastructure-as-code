"""
urn_processor.py のユニットテスト

UrnProcessorクラスの全公開メソッドを網羅的にテストします。
Phase 2-1: UrnProcessorクラスの抽出に対応するテストコード。
"""
import pytest
import time


# =============================================================================
# TestUrnProcessorParsing - URNパースのテスト
# =============================================================================

class TestUrnProcessorParsing:
    """UrnProcessor - URNパースのテスト"""

    @pytest.mark.unit
    def test_parse_urn_valid_aws(self, urn_processor, sample_urns):
        """正常なAWS URNの解析

        テストシナリオ 2.1.1に対応
        """
        # Given: 正常なAWS URN文字列
        urn = sample_urns['valid_aws_urn']

        # When: UrnProcessor.parse_urn()を呼び出す
        result = urn_processor.parse_urn(urn)

        # Then: 辞書形式で構成要素が正しく抽出される
        assert isinstance(result, dict)
        assert result['stack'] == 'dev'
        assert result['project'] == 'myproject'
        assert result['provider'] == 'aws'
        assert result['module'] == 's3'
        assert result['type'] == 'Bucket'
        assert result['name'] == 'my-bucket'
        assert result['full_urn'] == urn

    @pytest.mark.unit
    def test_parse_urn_valid_azure(self, urn_processor, sample_urns):
        """正常なAzure URNの解析

        テストシナリオ 2.1.2に対応
        """
        # Given: 正常なAzure URN文字列
        urn = sample_urns['valid_azure_urn']

        # When: UrnProcessor.parse_urn()を呼び出す
        result = urn_processor.parse_urn(urn)

        # Then: Azureの構成要素が正しく抽出される
        assert isinstance(result, dict)
        assert result['stack'] == 'dev'
        assert result['project'] == 'myproject'
        assert result['provider'] == 'azure'
        assert result['module'] == 'storage'
        assert result['type'] == 'StorageAccount'
        assert result['name'] == 'mystorage'
        assert result['full_urn'] == urn

    @pytest.mark.unit
    def test_parse_urn_valid_gcp(self, urn_processor, sample_urns):
        """正常なGCP URNの解析

        テストシナリオ 2.1.3に対応
        """
        # Given: 正常なGCP URN文字列
        urn = sample_urns['valid_gcp_urn']

        # When: UrnProcessor.parse_urn()を呼び出す
        result = urn_processor.parse_urn(urn)

        # Then: GCPの構成要素が正しく抽出される
        assert isinstance(result, dict)
        assert result['stack'] == 'dev'
        assert result['project'] == 'myproject'
        assert result['provider'] == 'gcp'
        assert result['module'] == 'storage'
        assert result['type'] == 'Bucket'
        assert result['name'] == 'my-bucket'
        assert result['full_urn'] == urn

    @pytest.mark.unit
    def test_parse_urn_valid_kubernetes(self, urn_processor, sample_urns):
        """正常なKubernetes URNの解析

        テストシナリオ 2.1.4に対応
        """
        # Given: 正常なKubernetes URN文字列
        urn = sample_urns['valid_kubernetes_urn']

        # When: UrnProcessor.parse_urn()を呼び出す
        result = urn_processor.parse_urn(urn)

        # Then: Kubernetesの構成要素が正しく抽出される
        assert isinstance(result, dict)
        assert result['stack'] == 'dev'
        assert result['project'] == 'myproject'
        assert result['provider'] == 'kubernetes'
        assert result['module'] == 'core'
        assert result['type'] == 'Namespace'
        assert result['name'] == 'my-namespace'
        assert result['full_urn'] == urn

    @pytest.mark.unit
    def test_parse_urn_stack_resource(self, urn_processor, sample_urns):
        """スタックリソースURNの解析

        テストシナリオ 2.1.5に対応
        """
        # Given: スタックリソースURN
        urn = sample_urns['stack_urn']

        # When: UrnProcessor.parse_urn()を呼び出す
        result = urn_processor.parse_urn(urn)

        # Then: スタックリソースの構成要素が正しく抽出される
        assert isinstance(result, dict)
        assert result['stack'] == 'dev'
        assert result['project'] == 'myproject'
        assert result['provider'] == 'pulumi'
        assert result['module'] == 'pulumi'
        assert result['type'] == 'Stack'
        assert result['name'] == 'dev'
        assert result['full_urn'] == urn

    @pytest.mark.unit
    def test_parse_urn_invalid_format(self, urn_processor, sample_urns):
        """不正なURN形式（区切り不足）

        テストシナリオ 2.1.6に対応
        """
        # Given: 不正なURN形式
        urn = sample_urns['invalid_urn_no_separator']

        # When: UrnProcessor.parse_urn()を呼び出す
        result = urn_processor.parse_urn(urn)

        # Then: 例外が発生せず、デフォルト値を含む辞書が返される
        assert isinstance(result, dict)
        assert result['stack'] == ''
        assert result['project'] == ''
        assert result['provider'] == 'unknown'
        assert result['module'] == ''
        assert result['type'] == 'unknown'
        assert result['name'] == 'invalid-urn'
        assert result['full_urn'] == urn

    @pytest.mark.unit
    def test_parse_urn_partial_urn(self, urn_processor, sample_urns):
        """部分的なURN

        テストシナリオ 2.1.7に対応
        """
        # Given: 部分的なURN（一部の区切りが不足）
        urn = sample_urns['invalid_urn_partial']

        # When: UrnProcessor.parse_urn()を呼び出す
        result = urn_processor.parse_urn(urn)

        # Then: 例外が発生せず、デフォルト値を含む辞書が返される
        assert isinstance(result, dict)
        # stackとprojectは抽出可能
        assert result['stack'] == 'dev'
        # provider、module、typeはデフォルト値
        assert result['provider'] == 'unknown'
        assert result['module'] == ''
        assert result['type'] == 'unknown'
        assert result['full_urn'] == urn

    @pytest.mark.unit
    def test_parse_urn_empty_string(self, urn_processor, sample_urns):
        """空文字列

        テストシナリオ 2.1.8に対応
        """
        # Given: 空文字列
        urn = sample_urns['empty_urn']

        # When: UrnProcessor.parse_urn()を呼び出す
        result = urn_processor.parse_urn(urn)

        # Then: 例外が発生せず、デフォルト値を含む辞書が返される
        assert isinstance(result, dict)
        assert result['stack'] == ''
        assert result['project'] == ''
        assert result['provider'] == 'unknown'
        assert result['module'] == ''
        assert result['type'] == 'unknown'
        assert result['name'] == ''
        assert result['full_urn'] == ''
        # すべてのキーが存在すること
        assert 'stack' in result
        assert 'project' in result
        assert 'provider' in result
        assert 'module' in result
        assert 'type' in result
        assert 'name' in result
        assert 'full_urn' in result

    @pytest.mark.unit
    def test_parse_urn_extremely_long(self, urn_processor, sample_urns):
        """極端に長いURN

        テストシナリオ 2.1.9に対応
        """
        # Given: 極端に長いURN（1万文字）
        base_urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::"
        long_name = "x" * 10000
        urn = base_urn + long_name

        # When: UrnProcessor.parse_urn()を呼び出す
        start_time = time.time()
        result = urn_processor.parse_urn(urn)
        elapsed_time = time.time() - start_time

        # Then:
        # - 例外が発生しない
        # - 処理が100ms以内に完了する
        # - nameに極端に長い文字列が含まれる
        assert isinstance(result, dict)
        assert elapsed_time < 0.1  # 100ms未満
        assert result['provider'] == 'aws'
        assert result['module'] == 's3'
        assert result['type'] == 'Bucket'
        assert len(result['name']) == 10000

    @pytest.mark.unit
    def test_parse_urn_no_module(self, urn_processor):
        """モジュール名なしのURN

        テストシナリオ 2.1.10に対応
        """
        # Given: モジュール名がないURN（`provider:type`形式）
        urn = "urn:pulumi:dev::myproject::pulumi:Stack::dev"

        # When: UrnProcessor.parse_urn()を呼び出す
        result = urn_processor.parse_urn(urn)

        # Then: moduleが空文字列であり、その他の要素が正しく抽出される
        assert isinstance(result, dict)
        assert result['stack'] == 'dev'
        assert result['project'] == 'myproject'
        assert result['provider'] == 'pulumi'
        assert result['module'] == ''
        assert result['type'] == 'Stack'
        assert result['name'] == 'dev'
        assert result['full_urn'] == urn


# =============================================================================
# TestUrnProcessorLabelCreation - ラベル生成のテスト
# =============================================================================

class TestUrnProcessorLabelCreation:
    """UrnProcessor - ラベル生成のテスト"""

    @pytest.mark.unit
    def test_create_readable_label_basic(self, urn_processor):
        """基本的なラベル生成

        テストシナリオ 2.2.1に対応
        """
        # Given: URN情報辞書
        urn_info = {
            'provider': 'aws',
            'module': 's3',
            'type': 'Bucket',
            'name': 'my-bucket'
        }

        # When: UrnProcessor.create_readable_label()を呼び出す
        result = urn_processor.create_readable_label(urn_info)

        # Then: 改行区切りのラベル文字列が返される
        assert isinstance(result, str)
        assert 's3' in result
        assert 'Bucket' in result
        assert 'my-bucket' in result
        assert '\\n' in result
        # 期待される形式: "s3\nBucket\nmy-bucket"
        assert result == 's3\\nBucket\\nmy-bucket'

    @pytest.mark.unit
    def test_create_readable_label_no_module(self, urn_processor):
        """モジュール名なしの場合

        テストシナリオ 2.2.2に対応
        """
        # Given: モジュール名がないURN情報辞書
        urn_info = {
            'provider': 'pulumi',
            'module': '',
            'type': 'Stack',
            'name': 'dev'
        }

        # When: UrnProcessor.create_readable_label()を呼び出す
        result = urn_processor.create_readable_label(urn_info)

        # Then: モジュール名が省略されたラベルが返される
        assert isinstance(result, str)
        assert 'Stack' in result
        assert 'dev' in result
        assert '\\n' in result
        # 期待される形式: "Stack\ndev"
        assert result == 'Stack\\ndev'

    @pytest.mark.unit
    def test_create_readable_label_long_type(self, urn_processor):
        """長いタイプ名の省略処理

        テストシナリオ 2.2.3に対応
        """
        # Given: 長いタイプ名（30文字以上）
        urn_info = {
            'provider': 'aws',
            'module': 'ecs',
            'type': 'VeryLongResourceTypeNameThatExceeds30Characters',
            'name': 'my-resource'
        }

        # When: UrnProcessor.create_readable_label()を呼び出す
        result = urn_processor.create_readable_label(urn_info)

        # Then: ラベルに省略されたタイプ名が含まれる
        assert isinstance(result, str)
        assert 'ecs' in result
        assert 'my-resource' in result
        assert '\\n' in result
        # タイプ名が省略されること（...を含む）
        assert '...' in result

    @pytest.mark.unit
    def test_format_resource_type_short(self, urn_processor):
        """短いタイプ名（30文字以下）

        テストシナリオ 2.2.4に対応
        """
        # Given: 短いタイプ名
        resource_type = "Bucket"

        # When: UrnProcessor._format_resource_type()を呼び出す
        result = urn_processor._format_resource_type(resource_type)

        # Then: タイプ名が変更されない
        assert result == "Bucket"
        assert len(result) <= 30

    @pytest.mark.unit
    def test_format_resource_type_long(self, urn_processor):
        """長いタイプ名（30文字以上）

        テストシナリオ 2.2.5に対応
        """
        # Given: 長いタイプ名（30文字以上）
        resource_type = "VeryLongResourceTypeNameThatExceeds30Characters"

        # When: UrnProcessor._format_resource_type()を呼び出す
        result = urn_processor._format_resource_type(resource_type)

        # Then: 省略されたタイプ名が返される
        assert isinstance(result, str)
        # 省略記号が含まれる
        assert '...' in result
        # キャメルケースを考慮した省略
        assert 'Very' in result
        assert 'Long' in result
        assert 'Characters' in result

    @pytest.mark.unit
    def test_create_readable_label_special_characters(self, urn_processor):
        """特殊文字を含む名前

        テストシナリオ 2.2.6に対応
        """
        # Given: 特殊文字を含むリソース名
        urn_info = {
            'provider': 'aws',
            'module': 's3',
            'type': 'Bucket',
            'name': 'my-bucket-with-特殊文字'
        }

        # When: UrnProcessor.create_readable_label()を呼び出す
        result = urn_processor.create_readable_label(urn_info)

        # Then: 特殊文字がそのまま含まれる
        assert isinstance(result, str)
        assert '特殊文字' in result
        assert 's3' in result
        assert 'Bucket' in result
        assert 'my-bucket-with-特殊文字' in result


# =============================================================================
# TestUrnProcessorResourceIdentification - リソース判定のテスト
# =============================================================================

class TestUrnProcessorResourceIdentification:
    """UrnProcessor - リソース判定のテスト"""

    @pytest.mark.unit
    def test_is_stack_resource_true(self, urn_processor, sample_urns):
        """スタックリソースの判定

        テストシナリオ 2.3.1に対応
        """
        # Given: スタックリソースURN
        urn = sample_urns['stack_urn']

        # When: UrnProcessor.is_stack_resource()を呼び出す
        result = urn_processor.is_stack_resource(urn)

        # Then: Trueが返される
        assert result is True

    @pytest.mark.unit
    def test_is_stack_resource_false(self, urn_processor, sample_urns):
        """通常リソースの判定

        テストシナリオ 2.3.2に対応
        """
        # Given: 通常リソースURN
        urn = sample_urns['valid_aws_urn']

        # When: UrnProcessor.is_stack_resource()を呼び出す
        result = urn_processor.is_stack_resource(urn)

        # Then: Falseが返される
        assert result is False

    @pytest.mark.unit
    def test_is_stack_resource_invalid_urn(self, urn_processor, sample_urns):
        """不正なURN

        テストシナリオ 2.3.3に対応
        """
        # Given: 不正なURN
        urn = sample_urns['invalid_urn_no_separator']

        # When: UrnProcessor.is_stack_resource()を呼び出す
        result = urn_processor.is_stack_resource(urn)

        # Then: 例外が発生せず、Falseが返される
        assert result is False

    @pytest.mark.unit
    def test_is_stack_resource_empty_string(self, urn_processor, sample_urns):
        """空文字列

        テストシナリオ 2.3.4に対応
        """
        # Given: 空文字列
        urn = sample_urns['empty_urn']

        # When: UrnProcessor.is_stack_resource()を呼び出す
        result = urn_processor.is_stack_resource(urn)

        # Then: 例外が発生せず、Falseが返される
        assert result is False


# =============================================================================
# TestEdgeCases - エッジケースのテスト
# =============================================================================

class TestEdgeCases:
    """エッジケースのテスト"""

    @pytest.mark.edge_case
    def test_extremely_long_urn_10000_chars(self, urn_processor):
        """極端に長いURN（1万文字）

        テストシナリオ 2.4.1に対応
        """
        # Given: 極端に長いURN（1万文字）
        base_urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::"
        long_name = "x" * 10000
        urn = base_urn + long_name

        # When: UrnProcessor.parse_urn()を呼び出す
        start_time = time.time()
        result = urn_processor.parse_urn(urn)
        elapsed_time = time.time() - start_time

        # Then:
        # - 例外が発生しない
        # - 処理が100ms未満である
        # - メモリリークが発生しない
        # - パース結果のnameに極端に長い文字列が含まれる
        assert isinstance(result, dict)
        assert elapsed_time < 0.1  # 100ms未満
        assert result['provider'] == 'aws'
        assert result['module'] == 's3'
        assert result['type'] == 'Bucket'
        assert len(result['name']) == 10000

    @pytest.mark.edge_case
    def test_special_characters_in_urn(self, urn_processor):
        """特殊文字を含むURN

        テストシナリオ 2.4.2に対応
        """
        # Given: 特殊文字（SQLインジェクション文字列等）を含むURN
        urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'; DROP TABLE users;--"

        # When: UrnProcessor.parse_urn()を呼び出す
        result = urn_processor.parse_urn(urn)

        # Then:
        # - 例外が発生しない
        # - エスケープが正しく行われる
        # - コードインジェクションが発生しない
        # - nameに特殊文字が含まれる
        assert isinstance(result, dict)
        assert result['provider'] == 'aws'
        assert result['module'] == 's3'
        assert result['type'] == 'Bucket'
        assert "'; DROP TABLE users;--" in result['name']

    @pytest.mark.edge_case
    def test_unicode_characters_in_urn(self, urn_processor):
        """Unicode文字を含むURN

        テストシナリオ 2.4.3に対応
        """
        # Given: Unicode文字（日本語、絵文字等）を含むURN
        urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::私のバケット🎉"

        # When: UrnProcessor.parse_urn()を呼び出す
        result = urn_processor.parse_urn(urn)

        # Then:
        # - 例外が発生しない
        # - Unicode文字がそのまま保持される
        # - nameにUnicode文字が含まれる
        assert isinstance(result, dict)
        assert result['provider'] == 'aws'
        assert result['module'] == 's3'
        assert result['type'] == 'Bucket'
        assert result['name'] == '私のバケット🎉'

    @pytest.mark.edge_case
    def test_multiple_colons_in_name(self, urn_processor):
        """リソース名に複数のコロンが含まれるURN

        テストシナリオ 2.4.4に対応
        """
        # Given: リソース名に複数のコロンが含まれるURN
        urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my:bucket:with:colons"

        # When: UrnProcessor.parse_urn()を呼び出す
        result = urn_processor.parse_urn(urn)

        # Then:
        # - 例外が発生しない
        # - nameに`my:bucket:with:colons`が含まれる
        # - その他の要素が正しく抽出される
        assert isinstance(result, dict)
        assert result['provider'] == 'aws'
        assert result['module'] == 's3'
        assert result['type'] == 'Bucket'
        assert result['name'] == 'my:bucket:with:colons'
