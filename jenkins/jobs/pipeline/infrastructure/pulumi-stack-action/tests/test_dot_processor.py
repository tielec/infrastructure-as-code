"""
dot_processor.py の特性テスト（Characterization Test）

このテストは、既存のdot_processor.pyの振る舞いを記録し、
将来のリファクタリング時に振る舞いが維持されていることを検証します。
"""
import pytest
from typing import List, Dict


# =============================================================================
# DotFileGenerator クラスのテスト
# =============================================================================

class TestDotFileGeneratorEscaping:
    """DotFileGenerator - エスケープ処理のテスト"""

    @pytest.mark.characterization
    def test_escape_dot_string_with_double_quotes(self, dot_file_generator):
        """ダブルクォートのエスケープ"""
        # Given: ダブルクォートを含む文字列
        input_str = 'test "value" here'

        # When: escape_dot_string()を呼び出す
        result = dot_file_generator.escape_dot_string(input_str)

        # Then: エスケープされた文字列が返される
        assert result == 'test \\"value\\" here'

    @pytest.mark.characterization
    def test_escape_dot_string_with_backslash(self, dot_file_generator):
        """バックスラッシュのエスケープ"""
        # Given: バックスラッシュを含む文字列
        input_str = 'test\\path'

        # When: escape_dot_string()を呼び出す
        result = dot_file_generator.escape_dot_string(input_str)

        # Then: バックスラッシュがエスケープされる
        assert result == 'test\\\\path'

    @pytest.mark.characterization
    def test_escape_dot_string_with_newline(self, dot_file_generator):
        """改行のエスケープ"""
        # Given: 改行を含む文字列
        input_str = 'line1\nline2'

        # When: escape_dot_string()を呼び出す
        result = dot_file_generator.escape_dot_string(input_str)

        # Then: 改行がエスケープされる
        assert result == 'line1\\nline2'

    @pytest.mark.characterization
    def test_escape_dot_string_with_tab(self, dot_file_generator):
        """タブのエスケープ"""
        # Given: タブを含む文字列
        input_str = 'col1\tcol2'

        # When: escape_dot_string()を呼び出す
        result = dot_file_generator.escape_dot_string(input_str)

        # Then: タブがエスケープされる
        assert result == 'col1\\tcol2'

    @pytest.mark.characterization
    def test_escape_dot_string_with_carriage_return(self, dot_file_generator):
        """キャリッジリターンの除去"""
        # Given: キャリッジリターンを含む文字列
        input_str = 'line1\r\nline2'

        # When: escape_dot_string()を呼び出す
        result = dot_file_generator.escape_dot_string(input_str)

        # Then: \rが削除され、\nがエスケープされる
        assert result == 'line1\\nline2'

    @pytest.mark.characterization
    def test_escape_dot_string_with_empty_string(self, dot_file_generator):
        """空文字列の処理"""
        # Given: 空文字列
        input_str = ''

        # When: escape_dot_string()を呼び出す
        result = dot_file_generator.escape_dot_string(input_str)

        # Then: 空文字列がそのまま返される（エラーが発生しない）
        assert result == ''

    @pytest.mark.characterization
    def test_escape_dot_string_with_none(self, dot_file_generator):
        """None値の処理"""
        # Given: None値
        input_str = None

        # When: escape_dot_string()を呼び出す
        result = dot_file_generator.escape_dot_string(input_str)

        # Then: Noneがそのまま返される
        assert result is None

    @pytest.mark.characterization
    def test_escape_dot_string_with_unicode(self, dot_file_generator):
        """Unicode文字の処理"""
        # Given: Unicode文字を含む文字列
        input_str = 'テスト🚀データ'

        # When: escape_dot_string()を呼び出す
        result = dot_file_generator.escape_dot_string(input_str)

        # Then: エスケープされずにそのまま返される
        assert result == 'テスト🚀データ'

    @pytest.mark.characterization
    def test_escape_dot_string_with_multiple_escapes(self, dot_file_generator):
        """複合エスケープ"""
        # Given: 複数の特殊文字を含む文字列
        input_str = 'test "value"\nwith\\backslash\tand\ttabs'

        # When: escape_dot_string()を呼び出す
        result = dot_file_generator.escape_dot_string(input_str)

        # Then: すべての特殊文字が正しくエスケープされる
        assert result == 'test \\"value\\"\\nwith\\\\backslash\\tand\\ttabs'


class TestDotFileGeneratorCreation:
    """DotFileGenerator - DOTファイル生成のテスト"""

    @pytest.mark.characterization
    def test_create_dot_file_basic(self, dot_file_generator, sample_resources):
        """基本的なDOTファイル生成"""
        # Given: サンプルのスタック名、リソース、プロバイダー情報
        stack_name = 'dev'
        resources = [sample_resources['basic_resource']]
        resource_providers = {'aws': 1}

        # When: create_dot_file()を呼び出す
        result = dot_file_generator.create_dot_file(stack_name, resources, resource_providers)

        # Then: 有効なDOT形式の文字列リストが返される
        assert isinstance(result, list)
        assert len(result) > 0
        # digraph G {で開始
        assert 'digraph G {' in result[0]
        # }で終了
        assert result[-1].strip() == '}'
        # Stackノードが存在
        assert any('Stack' in line for line in result)
        # プロバイダーノードが存在
        assert any('provider_aws' in line for line in result)

    @pytest.mark.characterization
    def test_create_dot_file_with_empty_resources(self, dot_file_generator):
        """空リソースの処理"""
        # Given: 空リソース
        stack_name = 'dev'
        resources = []
        resource_providers = {}

        # When: create_dot_file()を呼び出す
        result = dot_file_generator.create_dot_file(stack_name, resources, resource_providers)

        # Then: 有効なDOT形式が生成される
        assert isinstance(result, list)
        assert 'digraph G {' in result[0]
        assert result[-1].strip() == '}'
        # Stackノードが含まれる
        assert any('Stack' in line for line in result)
        # プロバイダーノードは含まれない
        assert not any('provider_' in line for line in result)

    @pytest.mark.characterization
    def test_create_dot_file_with_20_resources(self, dot_file_generator):
        """最大20リソースの処理"""
        # Given: ちょうど20個のリソース
        stack_name = 'dev'
        resources = []
        for i in range(20):
            resources.append({
                'type': 'aws:s3/bucket:Bucket',
                'urn': f'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-{i}',
                'dependencies': [],
                'parent': None,
                'propertyDependencies': {}
            })
        resource_providers = {'aws': 20}

        # When: create_dot_file()を呼び出す
        result = dot_file_generator.create_dot_file(stack_name, resources, resource_providers)

        # Then: 20個全てのリソースノードが生成される
        resource_nodes = [line for line in result if 'resource_' in line and '[label=' in line]
        assert len(resource_nodes) == 20

    @pytest.mark.characterization
    def test_create_dot_file_with_21_resources(self, dot_file_generator):
        """21リソース以上の処理（最初の20個のみ）"""
        # Given: 25個のリソース
        stack_name = 'dev'
        resources = []
        for i in range(25):
            resources.append({
                'type': 'aws:s3/bucket:Bucket',
                'urn': f'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-{i}',
                'dependencies': [],
                'parent': None,
                'propertyDependencies': {}
            })
        resource_providers = {'aws': 25}

        # When: create_dot_file()を呼び出す
        result = dot_file_generator.create_dot_file(stack_name, resources, resource_providers)

        # Then: 最初の20個のみが処理される
        resource_nodes = [line for line in result if 'resource_' in line and '[label=' in line]
        assert len(resource_nodes) == 20
        # resource_19が存在する
        assert any('resource_19' in line for line in result)
        # resource_20は存在しない
        assert not any('resource_20' in line for line in result)

    @pytest.mark.characterization
    def test_create_dot_file_provider_colors_aws(self, dot_file_generator):
        """AWSプロバイダーの色設定"""
        # Given: AWSリソース
        stack_name = 'dev'
        resources = [{
            'type': 'aws:s3/bucket:Bucket',
            'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket',
            'dependencies': [],
            'parent': None,
            'propertyDependencies': {}
        }]
        resource_providers = {'aws': 1}

        # When: create_dot_file()を呼び出す
        result = dot_file_generator.create_dot_file(stack_name, resources, resource_providers)

        # Then: AWSの色設定が適用される
        result_str = '\n'.join(result)
        assert '#FFF3E0' in result_str  # AWS fillcolor
        assert '#EF6C00' in result_str  # AWS color

    @pytest.mark.characterization
    def test_create_dot_file_provider_colors_azure(self, dot_file_generator):
        """Azureプロバイダーの色設定"""
        # Given: Azureリソース
        stack_name = 'dev'
        resources = [{
            'type': 'azure:storage/storageAccount:StorageAccount',
            'urn': 'urn:pulumi:dev::myproject::azure:storage/storageAccount:StorageAccount::mystorage',
            'dependencies': [],
            'parent': None,
            'propertyDependencies': {}
        }]
        resource_providers = {'azure': 1}

        # When: create_dot_file()を呼び出す
        result = dot_file_generator.create_dot_file(stack_name, resources, resource_providers)

        # Then: Azureの色設定が適用される
        result_str = '\n'.join(result)
        assert '#E3F2FD' in result_str  # Azure fillcolor
        assert '#0078D4' in result_str  # Azure color

    @pytest.mark.characterization
    def test_create_dot_file_provider_colors_unknown(self, dot_file_generator):
        """未定義プロバイダーのデフォルト色設定"""
        # Given: 未定義プロバイダー
        stack_name = 'dev'
        resources = [{
            'type': 'custom:resource:CustomResource',
            'urn': 'urn:pulumi:dev::myproject::custom:resource:CustomResource::my-resource',
            'dependencies': [],
            'parent': None,
            'propertyDependencies': {}
        }]
        resource_providers = {'custom': 1}

        # When: create_dot_file()を呼び出す
        result = dot_file_generator.create_dot_file(stack_name, resources, resource_providers)

        # Then: デフォルト色が適用される
        result_str = '\n'.join(result)
        assert '#E3F2FD' in result_str  # デフォルト fillcolor
        assert '#1565C0' in result_str  # デフォルト color

    @pytest.mark.characterization
    def test_create_dot_file_multiple_providers(self, dot_file_generator, sample_resources):
        """複数プロバイダーの処理"""
        # Given: 複数プロバイダーのリソース
        stack_name = 'dev'
        resources = [
            sample_resources['basic_resource'],
            sample_resources['gcp_resource']
        ]
        resource_providers = {'aws': 1, 'gcp': 1}

        # When: create_dot_file()を呼び出す
        result = dot_file_generator.create_dot_file(stack_name, resources, resource_providers)

        # Then: 両方のプロバイダーノードが存在する
        result_str = '\n'.join(result)
        assert 'provider_aws' in result_str
        assert 'provider_gcp' in result_str

    @pytest.mark.characterization
    def test_create_dot_file_resource_dependencies(self, dot_file_generator, sample_resources):
        """リソース間の依存関係の生成"""
        # Given: 依存関係を持つリソース
        stack_name = 'dev'
        resources = [
            sample_resources['basic_resource'],
            sample_resources['resource_with_dependencies']
        ]
        resource_providers = {'aws': 2}

        # When: create_dot_file()を呼び出す
        result = dot_file_generator.create_dot_file(stack_name, resources, resource_providers)

        # Then: 依存関係のエッジが生成される
        result_str = '\n'.join(result)
        # resource_1 -> resource_0 の依存エッジが存在
        assert 'resource_1' in result_str
        assert 'resource_0' in result_str
        assert '->' in result_str

    @pytest.mark.characterization
    def test_create_dot_file_long_resource_name(self, dot_file_generator):
        """長いリソース名の省略"""
        # Given: 長いリソース名
        stack_name = 'dev'
        long_name = 'a' * 50
        resources = [{
            'type': 'aws:s3/bucket:Bucket',
            'urn': f'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::{long_name}',
            'dependencies': [],
            'parent': None,
            'propertyDependencies': {}
        }]
        resource_providers = {'aws': 1}

        # When: create_dot_file()を呼び出す
        result = dot_file_generator.create_dot_file(stack_name, resources, resource_providers)

        # Then: リソース名が省略される
        result_str = '\n'.join(result)
        # 省略記号が含まれる
        assert '...' in result_str


# =============================================================================
# DotFileProcessor クラスのテスト
# =============================================================================

class TestDotFileProcessorUrnParsing:
    """DotFileProcessor - URN解析のテスト"""

    @pytest.mark.characterization
    def test_parse_urn_valid_aws(self, dot_file_processor, sample_urns):
        """正常なAWS URNの解析"""
        # Given: 正しいURN形式の文字列
        urn = sample_urns['valid_aws_urn']

        # When: parse_urn()を呼び出す
        result = dot_file_processor.parse_urn(urn)

        # Then: 辞書形式で構成要素が返される
        assert isinstance(result, dict)
        assert result['stack'] == 'dev'
        assert result['project'] == 'myproject'
        assert result['provider'] == 'aws'
        assert result['module'] == 's3'
        assert result['type'] == 'Bucket'
        assert result['name'] == 'my-bucket'
        assert result['full_urn'] == urn

    @pytest.mark.characterization
    def test_parse_urn_valid_azure(self, dot_file_processor, sample_urns):
        """正常なAzure URNの解析"""
        # Given: 正しいAzure URN
        urn = sample_urns['valid_azure_urn']

        # When: parse_urn()を呼び出す
        result = dot_file_processor.parse_urn(urn)

        # Then: Azure URNが正しく解析される
        assert result['stack'] == 'dev'
        assert result['project'] == 'myproject'
        assert result['provider'] == 'azure'
        assert result['module'] == 'storage'
        assert result['type'] == 'StorageAccount'
        assert result['name'] == 'mystorage'

    @pytest.mark.characterization
    def test_parse_urn_valid_gcp(self, dot_file_processor, sample_urns):
        """正常なGCP URNの解析"""
        # Given: 正しいGCP URN
        urn = sample_urns['valid_gcp_urn']

        # When: parse_urn()を呼び出す
        result = dot_file_processor.parse_urn(urn)

        # Then: GCP URNが正しく解析される
        assert result['stack'] == 'dev'
        assert result['project'] == 'myproject'
        assert result['provider'] == 'gcp'
        assert result['module'] == 'storage'
        assert result['type'] == 'Bucket'
        assert result['name'] == 'my-bucket'

    @pytest.mark.characterization
    def test_parse_urn_valid_kubernetes(self, dot_file_processor, sample_urns):
        """正常なKubernetes URNの解析"""
        # Given: 正しいKubernetes URN
        urn = sample_urns['valid_kubernetes_urn']

        # When: parse_urn()を呼び出す
        result = dot_file_processor.parse_urn(urn)

        # Then: Kubernetes URNが正しく解析される
        assert result['stack'] == 'dev'
        assert result['project'] == 'myproject'
        assert result['provider'] == 'kubernetes'
        assert result['module'] == 'core'
        assert result['type'] == 'Namespace'
        assert result['name'] == 'my-namespace'

    @pytest.mark.characterization
    def test_parse_urn_stack_resource(self, dot_file_processor, sample_urns):
        """スタックリソースURNの解析"""
        # Given: スタックリソースURN
        urn = sample_urns['stack_urn']

        # When: parse_urn()を呼び出す
        result = dot_file_processor.parse_urn(urn)

        # Then: スタックURNが正しく解析される
        assert result['stack'] == 'dev'
        assert result['project'] == 'myproject'
        assert result['provider'] == 'pulumi'
        assert result['type'] == 'Stack'
        assert result['name'] == 'dev'

    @pytest.mark.characterization
    def test_parse_urn_invalid_format(self, dot_file_processor, sample_urns):
        """不正なURN形式（区切り不足）"""
        # Given: 不正なURN形式
        urn = sample_urns['invalid_urn_no_separator']

        # When: parse_urn()を呼び出す
        result = dot_file_processor.parse_urn(urn)

        # Then: デフォルト値が返される（エラーが発生しない）
        assert isinstance(result, dict)
        assert result['stack'] == ''
        assert result['project'] == ''
        assert result['provider'] == 'unknown'
        assert result['module'] == ''
        assert result['type'] == 'unknown'
        assert result['name'] == 'invalid-urn'
        assert result['full_urn'] == urn

    @pytest.mark.characterization
    def test_parse_urn_partial_urn(self, dot_file_processor, sample_urns):
        """部分的なURN"""
        # Given: 部分的なURN
        urn = sample_urns['invalid_urn_partial']

        # When: parse_urn()を呼び出す
        result = dot_file_processor.parse_urn(urn)

        # Then: デフォルト値が返される
        assert isinstance(result, dict)
        assert result['provider'] == 'unknown'
        assert result['full_urn'] == urn

    @pytest.mark.characterization
    def test_parse_urn_empty_string(self, dot_file_processor, sample_urns):
        """空文字列"""
        # Given: 空文字列
        urn = sample_urns['empty_urn']

        # When: parse_urn()を呼び出す
        result = dot_file_processor.parse_urn(urn)

        # Then: デフォルト値が返される（エラーが発生しない）
        assert isinstance(result, dict)
        assert result['stack'] == ''
        assert result['project'] == ''
        assert result['provider'] == 'unknown'
        assert result['name'] == ''

    @pytest.mark.characterization
    def test_parse_urn_extremely_long(self, dot_file_processor, sample_urns):
        """極端に長いURN"""
        # Given: 極端に長いURN（100文字以上）
        urn = sample_urns['long_urn']

        # When: parse_urn()を呼び出す
        result = dot_file_processor.parse_urn(urn)

        # Then: パース処理が正常に完了する
        assert isinstance(result, dict)
        assert result['provider'] == 'aws'
        assert len(result['name']) == 100


class TestDotFileProcessorGraphStyling:
    """DotFileProcessor - グラフスタイル適用のテスト"""

    @pytest.mark.characterization
    def test_apply_graph_styling_pulumi_generated(self, dot_file_processor, sample_dot_strings):
        """Pulumi生成グラフ（strict digraph）の処理"""
        # Given: Pulumi生成のDOT文字列
        dot_content = sample_dot_strings['pulumi_generated_graph']

        # When: apply_graph_styling()を呼び出す
        result = dot_file_processor.apply_graph_styling(dot_content)

        # Then: スタイル拡張されたDOT文字列が返される
        assert isinstance(result, str)
        assert 'strict digraph' in result
        # グラフ属性が追加される
        assert 'graph [' in result or 'rankdir=' in result

    @pytest.mark.characterization
    def test_apply_graph_styling_custom_generated(self, dot_file_processor, sample_dot_strings):
        """自前生成グラフ（digraph G）の処理"""
        # Given: 自前生成のDOT文字列
        dot_content = sample_dot_strings['custom_generated_graph']

        # When: apply_graph_styling()を呼び出す
        result = dot_file_processor.apply_graph_styling(dot_content)

        # Then: スタイル設定が適用される
        assert isinstance(result, str)
        assert 'digraph G {' in result or 'graph [' in result

    @pytest.mark.characterization
    def test_apply_graph_styling_empty_graph(self, dot_file_processor, sample_dot_strings):
        """空グラフの処理"""
        # Given: 空グラフ
        dot_content = sample_dot_strings['empty_graph']

        # When: apply_graph_styling()を呼び出す
        result = dot_file_processor.apply_graph_styling(dot_content)

        # Then: 処理が正常に完了する
        assert isinstance(result, str)


class TestDotFileProcessorGraphValidation:
    """DotFileProcessor - グラフ検証のテスト"""

    @pytest.mark.characterization
    def test_is_empty_graph_empty(self, dot_file_processor, sample_dot_strings):
        """空グラフの判定"""
        # Given: 空グラフの文字列
        dot_content = sample_dot_strings['empty_graph']

        # When: is_empty_graph()を呼び出す
        result = dot_file_processor.is_empty_graph(dot_content)

        # Then: Trueが返される
        assert result is True

    @pytest.mark.characterization
    def test_is_empty_graph_minimal(self, dot_file_processor, sample_dot_strings):
        """最小グラフ（30文字未満）の判定"""
        # Given: 最小グラフ
        dot_content = sample_dot_strings['minimal_graph']

        # When: is_empty_graph()を呼び出す
        result = dot_file_processor.is_empty_graph(dot_content)

        # Then: Trueが返される（30文字未満）
        assert result is True

    @pytest.mark.characterization
    def test_is_empty_graph_non_empty(self, dot_file_processor, sample_dot_strings):
        """非空グラフの判定"""
        # Given: 十分な内容を持つグラフ
        dot_content = sample_dot_strings['custom_generated_graph']

        # When: is_empty_graph()を呼び出す
        result = dot_file_processor.is_empty_graph(dot_content)

        # Then: Falseが返される
        assert result is False

    @pytest.mark.characterization
    def test_is_empty_graph_boundary_30(self, dot_file_processor):
        """ちょうど30文字のグラフ"""
        # Given: ちょうど30文字のグラフ文字列
        dot_content = 'digraph G { a -> b; }'  # 21文字
        dot_content += ' ' * 9  # 合計30文字

        # When: is_empty_graph()を呼び出す
        result = dot_file_processor.is_empty_graph(dot_content)

        # Then: Falseが返される（30文字以上）
        assert result is False


class TestDotFileProcessorLabelCreation:
    """DotFileProcessor - ラベル生成のテスト"""

    @pytest.mark.characterization
    def test_create_readable_label_basic(self, dot_file_processor):
        """基本的なラベル生成"""
        # Given: URN情報辞書
        urn_info = {
            'provider': 'aws',
            'module': 's3',
            'type': 'Bucket',
            'name': 'my-bucket'
        }

        # When: create_readable_label()を呼び出す
        result = dot_file_processor.create_readable_label(urn_info)

        # Then: 改行区切りの読みやすいラベル文字列が返される
        assert isinstance(result, str)
        assert 's3' in result
        assert 'Bucket' in result
        assert 'my-bucket' in result
        assert '\\n' in result

    @pytest.mark.characterization
    def test_create_readable_label_no_module(self, dot_file_processor):
        """モジュール名なしの場合"""
        # Given: モジュール名がないURN情報
        urn_info = {
            'provider': 'pulumi',
            'module': '',
            'type': 'Stack',
            'name': 'dev'
        }

        # When: create_readable_label()を呼び出す
        result = dot_file_processor.create_readable_label(urn_info)

        # Then: モジュール名が省略される
        assert isinstance(result, str)
        assert 'Stack' in result
        assert 'dev' in result

    @pytest.mark.characterization
    def test_create_readable_label_long_type(self, dot_file_processor):
        """長いタイプ名の省略処理"""
        # Given: 長いタイプ名
        urn_info = {
            'provider': 'aws',
            'module': 'ec2',
            'type': 'VeryLongResourceTypeNameThatExceeds30Characters',
            'name': 'my-resource'
        }

        # When: create_readable_label()を呼び出す
        result = dot_file_processor.create_readable_label(urn_info)

        # Then: ラベルが生成される
        assert isinstance(result, str)
        assert 'my-resource' in result


class TestDotFileProcessorResourceIdentification:
    """DotFileProcessor - リソース識別のテスト"""

    @pytest.mark.characterization
    def test_is_stack_resource_true(self, dot_file_processor, sample_urns):
        """スタックリソースの判定"""
        # Given: スタックリソースURN
        urn = sample_urns['stack_urn']

        # When: is_stack_resource()を呼び出す
        result = dot_file_processor.is_stack_resource(urn)

        # Then: Trueが返される
        assert result is True

    @pytest.mark.characterization
    def test_is_stack_resource_false(self, dot_file_processor, sample_urns):
        """通常リソースの判定"""
        # Given: 通常リソースURN
        urn = sample_urns['valid_aws_urn']

        # When: is_stack_resource()を呼び出す
        result = dot_file_processor.is_stack_resource(urn)

        # Then: Falseが返される
        assert result is False

    @pytest.mark.characterization
    def test_is_stack_resource_invalid_urn(self, dot_file_processor, sample_urns):
        """不正なURN"""
        # Given: 不正なURN
        urn = sample_urns['invalid_urn_no_separator']

        # When: is_stack_resource()を呼び出す
        result = dot_file_processor.is_stack_resource(urn)

        # Then: Falseが返される
        assert result is False


# =============================================================================
# エッジケースのテスト
# =============================================================================

class TestEdgeCases:
    """エッジケースのテスト"""

    @pytest.mark.edge_case
    def test_extreme_long_resource_name(self, dot_file_generator):
        """極端に長いリソース名"""
        # Given: 極端に長いリソース名（1000文字）
        stack_name = 'dev'
        long_name = 'a' * 1000
        resources = [{
            'type': 'aws:s3/bucket:Bucket',
            'urn': f'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::{long_name}',
            'dependencies': [],
            'parent': None,
            'propertyDependencies': {}
        }]
        resource_providers = {'aws': 1}

        # When: create_dot_file()を呼び出す
        result = dot_file_generator.create_dot_file(stack_name, resources, resource_providers)

        # Then: エラーが発生しない
        assert isinstance(result, list)
        # リソース名が適切に省略される
        result_str = '\n'.join(result)
        assert '...' in result_str

    @pytest.mark.edge_case
    def test_special_characters_in_resource_name(self, dot_file_generator):
        """リソース名に特殊文字を含む場合"""
        # Given: 特殊文字を含むリソース名
        stack_name = 'dev'
        resources = [{
            'type': 'aws:s3/bucket:Bucket',
            'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-"special"-bucket',
            'dependencies': [],
            'parent': None,
            'propertyDependencies': {}
        }]
        resource_providers = {'aws': 1}

        # When: create_dot_file()を呼び出す
        result = dot_file_generator.create_dot_file(stack_name, resources, resource_providers)

        # Then: ダブルクォートが正しくエスケープされる
        result_str = '\n'.join(result)
        assert '\\"special\\"' in result_str

    @pytest.mark.edge_case
    def test_provider_name_case_sensitivity(self, dot_file_generator):
        """プロバイダー名の大文字小文字"""
        # Given: 大文字のAWS
        stack_name = 'dev'
        resources = [{
            'type': 'AWS:s3/bucket:Bucket',
            'urn': 'urn:pulumi:dev::myproject::AWS:s3/bucket:Bucket::my-bucket',
            'dependencies': [],
            'parent': None,
            'propertyDependencies': {}
        }]
        resource_providers = {'AWS': 1}

        # When: create_dot_file()を呼び出す
        result = dot_file_generator.create_dot_file(stack_name, resources, resource_providers)

        # Then: 処理が正常に完了する
        assert isinstance(result, list)
        result_str = '\n'.join(result)
        assert 'provider_AWS' in result_str

    @pytest.mark.edge_case
    def test_circular_dependencies(self, dot_file_generator):
        """循環依存の処理"""
        # Given: 循環依存を持つリソース
        stack_name = 'dev'
        resources = [
            {
                'type': 'aws:s3/bucket:Bucket',
                'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',
                'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b'],
                'parent': None,
                'propertyDependencies': {}
            },
            {
                'type': 'aws:s3/bucket:Bucket',
                'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b',
                'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a'],
                'parent': None,
                'propertyDependencies': {}
            }
        ]
        resource_providers = {'aws': 2}

        # When: create_dot_file()を呼び出す
        result = dot_file_generator.create_dot_file(stack_name, resources, resource_providers)

        # Then: エラーが発生しない
        assert isinstance(result, list)
        # 両方の依存関係エッジが生成される
        result_str = '\n'.join(result)
        assert 'resource_0' in result_str
        assert 'resource_1' in result_str

    @pytest.mark.edge_case
    def test_empty_provider_dict(self, dot_file_generator):
        """空のプロバイダー辞書"""
        # Given: 空のプロバイダー辞書
        stack_name = 'dev'
        resources = []
        resource_providers = {}

        # When: create_dot_file()を呼び出す
        result = dot_file_generator.create_dot_file(stack_name, resources, resource_providers)

        # Then: エラーが発生しない
        assert isinstance(result, list)
        # スタックノードのみのDOTファイルが生成される
        result_str = '\n'.join(result)
        assert 'Stack' in result_str
        assert 'digraph G {' in result_str[0]
