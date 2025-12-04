"""
node_label_generator.py のユニットテスト

NodeLabelGeneratorクラスの全公開メソッドを網羅的にテストします。
Phase 2-2: NodeLabelGeneratorクラスの抽出に対応するテストコード。
"""
import pytest
import time


# =============================================================================
# TestGenerateNodeLabel - ノード属性生成の振り分けテスト
# =============================================================================

class TestGenerateNodeLabel:
    """NodeLabelGenerator.generate_node_label() - ノード属性生成の振り分けテスト"""

    @pytest.mark.unit
    def test_generate_node_label_stack_resource(self, node_label_generator, sample_urns):
        """スタックリソースの振り分け（正常系）

        テストシナリオ 2.1.1に対応
        """
        # Given: スタックリソースURNとURN情報
        from urn_processor import UrnProcessor
        urn = sample_urns['stack_urn']
        urn_info = UrnProcessor.parse_urn(urn)

        # When: generate_node_label()を呼び出す
        result = node_label_generator.generate_node_label(urn, urn_info)

        # Then: スタックノード用のラベルが返される
        assert isinstance(result, str)
        assert 'label="Stack\\ndev"' in result
        assert 'fillcolor="#D1C4E9"' in result
        assert 'color="#512DA8"' in result
        assert 'shape=ellipse' in result
        assert 'fontsize="14"' in result

    @pytest.mark.unit
    def test_generate_node_label_aws_resource(self, node_label_generator, sample_urns):
        """通常リソース（AWS）の振り分け（正常系）

        テストシナリオ 2.1.2に対応
        """
        # Given: AWS S3 BucketのURNとURN情報
        from urn_processor import UrnProcessor
        urn = sample_urns['valid_aws_urn']
        urn_info = UrnProcessor.parse_urn(urn)

        # When: generate_node_label()を呼び出す
        result = node_label_generator.generate_node_label(urn, urn_info)

        # Then: AWSリソース用のラベルが返される
        assert isinstance(result, str)
        assert 'label=' in result
        assert 'fillcolor="#FFF3E0"' in result  # AWS color
        assert 'color="#EF6C00"' in result  # AWS color
        assert 'shape=box' in result
        assert 'fontsize="11"' in result

    @pytest.mark.unit
    def test_generate_node_label_azure_resource(self, node_label_generator, sample_urns):
        """通常リソース（Azure）の振り分け（正常系）

        テストシナリオ 2.1.3に対応
        """
        # Given: Azure Storage AccountのURNとURN情報
        from urn_processor import UrnProcessor
        urn = sample_urns['valid_azure_urn']
        urn_info = UrnProcessor.parse_urn(urn)

        # When: generate_node_label()を呼び出す
        result = node_label_generator.generate_node_label(urn, urn_info)

        # Then: Azureリソース用のラベルが返される
        assert isinstance(result, str)
        assert 'label=' in result
        assert 'fillcolor="#E3F2FD"' in result  # Azure color
        assert 'color="#0078D4"' in result  # Azure color
        assert 'shape=box' in result
        assert 'fontsize="11"' in result

    @pytest.mark.unit
    def test_generate_node_label_gcp_resource(self, node_label_generator, sample_urns):
        """通常リソース（GCP）の振り分け（正常系）

        テストシナリオ 2.1.4に対応
        """
        # Given: GCP Storage BucketのURNとURN情報
        from urn_processor import UrnProcessor
        urn = sample_urns['valid_gcp_urn']
        urn_info = UrnProcessor.parse_urn(urn)

        # When: generate_node_label()を呼び出す
        result = node_label_generator.generate_node_label(urn, urn_info)

        # Then: GCPリソース用のラベルが返される
        assert isinstance(result, str)
        assert 'label=' in result
        assert 'fillcolor="#E8F5E9"' in result  # GCP color
        assert 'color="#4285F4"' in result  # GCP color
        assert 'shape=box' in result
        assert 'fontsize="11"' in result


# =============================================================================
# TestGenerateStackNodeLabel - スタックノードラベル生成テスト
# =============================================================================

class TestGenerateStackNodeLabel:
    """NodeLabelGenerator.generate_stack_node_label() - スタックノードラベル生成テスト"""

    @pytest.mark.unit
    def test_generate_stack_node_label_basic(self, node_label_generator):
        """基本的なスタックラベル生成（正常系）

        テストシナリオ 2.2.1に対応
        """
        # Given: スタック名を含むURN情報
        urn_info = {
            'stack': 'dev',
            'project': 'myproject',
            'provider': 'pulumi',
            'module': 'pulumi',
            'type': 'Stack',
            'name': 'dev'
        }

        # When: generate_stack_node_label()を呼び出す
        result = node_label_generator.generate_stack_node_label(urn_info)

        # Then: 期待されるスタックラベルが返される
        expected = 'label="Stack\\ndev", fillcolor="#D1C4E9", color="#512DA8", shape=ellipse, fontsize="14"'
        assert result == expected

    @pytest.mark.unit
    def test_generate_stack_node_label_long_name(self, node_label_generator):
        """長いスタック名（正常系）

        テストシナリオ 2.2.2に対応
        """
        # Given: 長いスタック名
        urn_info = {
            'stack': 'production-environment-v2-with-very-long-name',
            'project': 'myproject',
            'provider': 'pulumi',
            'module': 'pulumi',
            'type': 'Stack',
            'name': 'production-environment-v2-with-very-long-name'
        }

        # When: generate_stack_node_label()を呼び出す
        result = node_label_generator.generate_stack_node_label(urn_info)

        # Then: スタック名全体が含まれる（省略なし）
        assert 'label="Stack\\nproduction-environment-v2-with-very-long-name"' in result
        assert 'fillcolor="#D1C4E9"' in result
        assert 'color="#512DA8"' in result
        assert 'shape=ellipse' in result

    @pytest.mark.unit
    def test_generate_stack_node_label_special_characters(self, node_label_generator):
        """特殊文字を含むスタック名（エッジケース）

        テストシナリオ 2.2.3に対応
        """
        # Given: 特殊文字を含むスタック名
        urn_info = {
            'stack': 'dev-stack-with-"quotes"',
            'project': 'myproject',
            'provider': 'pulumi',
            'module': 'pulumi',
            'type': 'Stack',
            'name': 'dev-stack-with-"quotes"'
        }

        # When: generate_stack_node_label()を呼び出す
        result = node_label_generator.generate_stack_node_label(urn_info)

        # Then: 特殊文字がそのまま含まれる
        assert isinstance(result, str)
        assert 'dev-stack-with-"quotes"' in result
        assert 'fillcolor="#D1C4E9"' in result

    @pytest.mark.unit
    def test_generate_stack_node_label_empty_string(self, node_label_generator):
        """空文字列のスタック名（異常系）

        テストシナリオ 2.2.4に対応
        """
        # Given: 空文字列のスタック名
        urn_info = {
            'stack': '',
            'project': 'myproject',
            'provider': 'pulumi',
            'module': 'pulumi',
            'type': 'Stack',
            'name': ''
        }

        # When: generate_stack_node_label()を呼び出す
        result = node_label_generator.generate_stack_node_label(urn_info)

        # Then: 例外が発生せず、有効なラベルが返される
        assert isinstance(result, str)
        assert 'label="Stack\\n"' in result
        assert 'fillcolor="#D1C4E9"' in result


# =============================================================================
# TestGenerateResourceNodeLabel - リソースノードラベル生成テスト
# =============================================================================

class TestGenerateResourceNodeLabel:
    """NodeLabelGenerator.generate_resource_node_label() - リソースノードラベル生成テスト"""

    @pytest.mark.unit
    def test_generate_resource_node_label_aws(self, node_label_generator):
        """AWSリソースラベル生成（正常系）

        テストシナリオ 2.3.1に対応
        """
        # Given: AWS S3 BucketのURN情報
        urn_info = {
            'stack': 'dev',
            'project': 'myproject',
            'provider': 'aws',
            'module': 's3',
            'type': 'Bucket',
            'name': 'my-bucket'
        }

        # When: generate_resource_node_label()を呼び出す
        result = node_label_generator.generate_resource_node_label(urn_info)

        # Then: AWS固有の色設定が適用される
        assert 'label="s3\\nBucket\\nmy-bucket"' in result
        assert 'fillcolor="#FFF3E0"' in result
        assert 'color="#EF6C00"' in result
        assert 'shape=box' in result
        assert 'fontsize="11"' in result

    @pytest.mark.unit
    def test_generate_resource_node_label_azure(self, node_label_generator):
        """Azureリソースラベル生成（正常系）

        テストシナリオ 2.3.2に対応
        """
        # Given: Azure Storage AccountのURN情報
        urn_info = {
            'stack': 'dev',
            'project': 'myproject',
            'provider': 'azure',
            'module': 'storage',
            'type': 'StorageAccount',
            'name': 'mystorage'
        }

        # When: generate_resource_node_label()を呼び出す
        result = node_label_generator.generate_resource_node_label(urn_info)

        # Then: Azure固有の色設定が適用される
        assert 'label="storage\\nStorageAccount\\nmystorage"' in result
        assert 'fillcolor="#E3F2FD"' in result
        assert 'color="#0078D4"' in result
        assert 'shape=box' in result

    @pytest.mark.unit
    def test_generate_resource_node_label_gcp(self, node_label_generator):
        """GCPリソースラベル生成（正常系）

        テストシナリオ 2.3.3に対応
        """
        # Given: GCP Storage BucketのURN情報
        urn_info = {
            'stack': 'dev',
            'project': 'myproject',
            'provider': 'gcp',
            'module': 'storage',
            'type': 'Bucket',
            'name': 'my-bucket'
        }

        # When: generate_resource_node_label()を呼び出す
        result = node_label_generator.generate_resource_node_label(urn_info)

        # Then: GCP固有の色設定が適用される
        assert 'label="storage\\nBucket\\nmy-bucket"' in result
        assert 'fillcolor="#E8F5E9"' in result
        assert 'color="#4285F4"' in result
        assert 'shape=box' in result

    @pytest.mark.unit
    def test_generate_resource_node_label_kubernetes(self, node_label_generator):
        """Kubernetesリソースラベル生成（正常系）

        テストシナリオ 2.3.4に対応
        """
        # Given: Kubernetes NamespaceのURN情報
        urn_info = {
            'stack': 'dev',
            'project': 'myproject',
            'provider': 'kubernetes',
            'module': 'core',
            'type': 'Namespace',
            'name': 'my-namespace'
        }

        # When: generate_resource_node_label()を呼び出す
        result = node_label_generator.generate_resource_node_label(urn_info)

        # Then: Kubernetes固有の色設定が適用される
        assert 'label="core\\nNamespace\\nmy-namespace"' in result
        assert 'fillcolor="#E8EAF6"' in result
        assert 'color="#326DE6"' in result
        assert 'shape=box' in result

    @pytest.mark.unit
    def test_generate_resource_node_label_unknown_provider(self, node_label_generator):
        """未定義プロバイダーのデフォルト色設定（正常系）

        テストシナリオ 2.3.5に対応
        """
        # Given: 未定義プロバイダーのURN情報
        urn_info = {
            'stack': 'dev',
            'project': 'myproject',
            'provider': 'unknown-provider',
            'module': 'module',
            'type': 'Resource',
            'name': 'my-resource'
        }

        # When: generate_resource_node_label()を呼び出す
        result = node_label_generator.generate_resource_node_label(urn_info)

        # Then: デフォルト色設定が適用される
        assert isinstance(result, str)
        assert 'fillcolor="#E3F2FD"' in result
        assert 'color="#1565C0"' in result
        assert 'shape=box' in result

    @pytest.mark.unit
    def test_generate_resource_node_label_no_module(self, node_label_generator):
        """モジュール名なしのリソース（正常系）

        テストシナリオ 2.3.6に対応
        """
        # Given: モジュール名がないURN情報
        urn_info = {
            'stack': 'dev',
            'project': 'myproject',
            'provider': 'pulumi',
            'module': '',
            'type': 'Stack',
            'name': 'dev'
        }

        # When: generate_resource_node_label()を呼び出す
        result = node_label_generator.generate_resource_node_label(urn_info)

        # Then: 例外が発生せず、ラベルが生成される
        assert isinstance(result, str)
        assert 'label="Stack\\ndev"' in result
        assert 'shape=box' in result

    @pytest.mark.unit
    def test_generate_resource_node_label_long_name(self, node_label_generator):
        """長いリソース名（正常系）

        テストシナリオ 2.3.7に対応
        """
        # Given: 長いリソース名
        long_name = 'my-very-long-bucket-name-that-exceeds-standard-length-limits-x' * 2
        urn_info = {
            'stack': 'dev',
            'project': 'myproject',
            'provider': 'aws',
            'module': 's3',
            'type': 'Bucket',
            'name': long_name
        }

        # When: generate_resource_node_label()を呼び出す
        result = node_label_generator.generate_resource_node_label(urn_info)

        # Then: 例外が発生せず、ラベルが生成される
        assert isinstance(result, str)
        assert 'fillcolor="#FFF3E0"' in result
        assert 'color="#EF6C00"' in result
        assert 'shape=box' in result

    @pytest.mark.unit
    def test_generate_resource_node_label_special_characters(self, node_label_generator):
        """特殊文字を含むリソース名（エッジケース）

        テストシナリオ 2.3.8に対応
        """
        # Given: 特殊文字を含むリソース名
        urn_info = {
            'stack': 'dev',
            'project': 'myproject',
            'provider': 'aws',
            'module': 's3',
            'type': 'Bucket',
            'name': 'my-bucket-with-"quotes"'
        }

        # When: generate_resource_node_label()を呼び出す
        result = node_label_generator.generate_resource_node_label(urn_info)

        # Then: 例外が発生せず、ラベルが生成される
        assert isinstance(result, str)
        assert 'my-bucket-with-"quotes"' in result
        assert 'fillcolor="#FFF3E0"' in result

    @pytest.mark.unit
    def test_generate_resource_node_label_unicode(self, node_label_generator):
        """Unicode文字を含むリソース名（エッジケース）

        テストシナリオ 2.3.9に対応
        """
        # Given: Unicode文字（日本語、絵文字）を含むリソース名
        urn_info = {
            'stack': 'dev',
            'project': 'myproject',
            'provider': 'aws',
            'module': 's3',
            'type': 'Bucket',
            'name': '私のバケット🎉'
        }

        # When: generate_resource_node_label()を呼び出す
        result = node_label_generator.generate_resource_node_label(urn_info)

        # Then: 例外が発生せず、Unicode文字が含まれる
        assert isinstance(result, str)
        assert '私のバケット🎉' in result
        assert 'fillcolor="#FFF3E0"' in result

    @pytest.mark.unit
    def test_generate_resource_node_label_case_insensitive_provider(self, node_label_generator):
        """大文字小文字の混在したプロバイダー名（正常系）

        テストシナリオ 2.3.10に対応
        """
        # Given: 大文字のプロバイダー名
        urn_info = {
            'stack': 'dev',
            'project': 'myproject',
            'provider': 'AWS',
            'module': 's3',
            'type': 'Bucket',
            'name': 'my-bucket'
        }

        # When: generate_resource_node_label()を呼び出す
        result = node_label_generator.generate_resource_node_label(urn_info)

        # Then: AWS固有の色設定が適用される（大文字小文字を無視）
        assert 'fillcolor="#FFF3E0"' in result
        assert 'color="#EF6C00"' in result


# =============================================================================
# TestFormatLabel - ラベルフォーマットテスト
# =============================================================================

class TestFormatLabel:
    """NodeLabelGenerator._format_label() - ラベルフォーマットテスト（内部ヘルパー）"""

    @pytest.mark.unit
    def test_format_label_short(self, node_label_generator):
        """短いラベル（正常系）

        テストシナリオ 2.4.1に対応
        """
        # Given: 短いラベル（40文字以下）
        label = "s3\\nBucket\\nmy-bucket"

        # When: _format_label()を呼び出す
        result = node_label_generator._format_label(label, max_length=40)

        # Then: ラベルが変更されない
        assert result == label
        assert '...' not in result

    @pytest.mark.unit
    def test_format_label_long(self, node_label_generator):
        """長いラベル（正常系）

        テストシナリオ 2.4.2に対応
        """
        # Given: 長いラベル（40文字以上）
        label = "very-long-module-name\\nVeryLongResourceTypeName\\nvery-long-resource-name-that-exceeds-40-chars"

        # When: _format_label()を呼び出す
        result = node_label_generator._format_label(label, max_length=40)

        # Then: ラベルが省略される
        assert len(result) == 40
        assert '...' in result
        assert result.endswith('...')

    @pytest.mark.unit
    def test_format_label_custom_max_length(self, node_label_generator):
        """カスタムmax_length（正常系）

        テストシナリオ 2.4.3に対応
        """
        # Given: カスタムmax_length
        label = "s3\\nBucket\\nmy-bucket-with-a-longer-name"

        # When: _format_label()を呼び出す（max_length=20）
        result = node_label_generator._format_label(label, max_length=20)

        # Then: 20文字以下に省略される
        assert len(result) == 20
        assert '...' in result

    @pytest.mark.unit
    def test_format_label_empty_string(self, node_label_generator):
        """空文字列（異常系）

        テストシナリオ 2.4.4に対応
        """
        # Given: 空文字列
        label = ""

        # When: _format_label()を呼び出す
        result = node_label_generator._format_label(label, max_length=40)

        # Then: 空文字列のまま返される
        assert result == ""

    @pytest.mark.unit
    def test_format_label_extremely_long(self, node_label_generator):
        """極端に長いラベル（エッジケース）

        テストシナリオ 2.4.5に対応
        """
        # Given: 極端に長いラベル（1000文字）
        label = "x" * 1000

        # When: _format_label()を呼び出す
        start_time = time.time()
        result = node_label_generator._format_label(label, max_length=40)
        elapsed_time = time.time() - start_time

        # Then: 省略されて40文字以下になる
        assert len(result) == 40
        assert '...' in result
        assert elapsed_time < 0.1  # 100ms未満


# =============================================================================
# TestProviderColors - プロバイダー別色設定テスト
# =============================================================================

class TestProviderColors:
    """プロバイダー別色設定のテスト"""

    @pytest.mark.unit
    def test_all_defined_providers(self, node_label_generator):
        """全定義済みプロバイダーの色設定検証

        テストシナリオ 2.5.1に対応
        """
        # Given: 全定義済みプロバイダー
        providers = [
            ('aws', '#FFF3E0', '#EF6C00'),
            ('azure', '#E3F2FD', '#0078D4'),
            ('azuread', '#E8F5E9', '#0078D4'),
            ('gcp', '#E8F5E9', '#4285F4'),
            ('google', '#E8F5E9', '#4285F4'),
            ('kubernetes', '#E8EAF6', '#326DE6'),
            ('docker', '#E3F2FD', '#2496ED'),
            ('pulumi', '#F3E5F5', '#6A1B9A'),
            ('random', '#FFF9C4', '#FBC02D'),
            ('tls', '#FFEBEE', '#D32F2F'),
            ('github', '#F5F5F5', '#24292E'),
            ('cloudflare', '#FFF8E1', '#F48120'),
            ('datadog', '#F3E5F5', '#632CA6'),
            ('postgresql', '#E8F5E9', '#336791'),
            ('mysql', '#E3F2FD', '#00758F'),
            ('vault', '#F5F5F5', '#000000'),
        ]

        # When/Then: 各プロバイダーで正しい色設定が適用される
        for provider, expected_fillcolor, expected_color in providers:
            urn_info = {
                'stack': 'dev',
                'project': 'myproject',
                'provider': provider,
                'module': 'module',
                'type': 'Resource',
                'name': 'resource'
            }
            result = node_label_generator.generate_resource_node_label(urn_info)
            assert f'fillcolor="{expected_fillcolor}"' in result, f"Provider {provider} fillcolor mismatch"
            assert f'color="{expected_color}"' in result, f"Provider {provider} color mismatch"


# =============================================================================
# TestEdgeCases - エッジケース・異常系テスト
# =============================================================================

class TestEdgeCases:
    """エッジケース・異常系のテスト"""

    @pytest.mark.edge_case
    def test_urn_info_incomplete(self, node_label_generator):
        """urn_infoが不完全な場合（異常系）

        テストシナリオ 2.6.1に対応
        """
        # Given: 必須キーが欠落したurn_info
        urn_info = {'stack': 'dev'}

        # When/Then: KeyErrorが発生する（または適切にハンドリングされる）
        with pytest.raises(KeyError):
            node_label_generator.generate_resource_node_label(urn_info)

    @pytest.mark.edge_case
    def test_urn_with_multiple_colons(self, node_label_generator):
        """URNにコロンが多数含まれる場合（エッジケース）

        テストシナリオ 2.6.3に対応
        """
        # Given: リソース名に複数のコロンが含まれるURN
        from urn_processor import UrnProcessor
        urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my:bucket:with:colons"
        urn_info = UrnProcessor.parse_urn(urn)

        # When: generate_resource_node_label()を呼び出す
        result = node_label_generator.generate_resource_node_label(urn_info)

        # Then: 例外が発生せず、ラベルが生成される
        assert isinstance(result, str)
        assert 'my:bucket:with:colons' in result

    @pytest.mark.edge_case
    def test_sql_injection_string(self, node_label_generator):
        """SQLインジェクション文字列を含む場合（セキュリティ）

        テストシナリオ 2.6.4に対応
        """
        # Given: SQLインジェクション文字列を含むリソース名
        urn_info = {
            'stack': 'dev',
            'project': 'myproject',
            'provider': 'aws',
            'module': 's3',
            'type': 'Bucket',
            'name': "my-bucket'; DROP TABLE users;--"
        }

        # When: generate_resource_node_label()を呼び出す
        result = node_label_generator.generate_resource_node_label(urn_info)

        # Then: 例外が発生せず、ラベルが生成される（コードインジェクションが発生しない）
        assert isinstance(result, str)
        assert "my-bucket'; DROP TABLE users;--" in result
        assert 'fillcolor=' in result


# =============================================================================
# TestPerformance - パフォーマンステスト
# =============================================================================

class TestPerformance:
    """パフォーマンステスト"""

    @pytest.mark.performance
    def test_1000_resources_label_generation(self, node_label_generator):
        """1000リソースのラベル生成パフォーマンス

        テストシナリオ 2.7.1に対応
        """
        # Given: 1000個のURN情報
        urn_infos = []
        for i in range(1000):
            urn_infos.append({
                'stack': 'dev',
                'project': 'myproject',
                'provider': ['aws', 'azure', 'gcp'][i % 3],
                'module': 's3',
                'type': 'Bucket',
                'name': f'bucket-{i}'
            })

        # When: 1000個のラベル生成を実行
        start_time = time.time()
        for urn_info in urn_infos:
            node_label_generator.generate_resource_node_label(urn_info)
        elapsed_time = time.time() - start_time

        # Then: 10秒以内に完了する
        assert elapsed_time < 10, f"Processing took {elapsed_time:.2f}s, expected < 10s"

    @pytest.mark.performance
    def test_single_resource_label_generation_performance(self, node_label_generator):
        """単一リソースのラベル生成パフォーマンス

        テストシナリオ 2.7.2に対応
        """
        # Given: 単一のURN情報
        urn_info = {
            'stack': 'dev',
            'project': 'myproject',
            'provider': 'aws',
            'module': 's3',
            'type': 'Bucket',
            'name': 'my-bucket'
        }

        # When: ラベル生成を実行
        start_time = time.time()
        node_label_generator.generate_resource_node_label(urn_info)
        elapsed_time = time.time() - start_time

        # Then: 10ミリ秒以内に完了する
        assert elapsed_time < 0.01, f"Processing took {elapsed_time*1000:.2f}ms, expected < 10ms"
