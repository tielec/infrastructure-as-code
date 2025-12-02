"""
DotFileProcessor クラスの統合テスト

テストシナリオ: test-scenario.md の IT-DOT-001 ~ IT-DOT-012
"""

import time
import pytest
from dot_processor import DotFileProcessor


class TestDotFileProcessorIntegration:
    """DotFileProcessor 統合テストクラス"""

    def test_refactoring_behavior_consistency(self, simple_graph_content):
        """IT-DOT-001: リファクタリング前後の振る舞い同一性_特性テスト

        Given: リファクタリング後のDotFileProcessor
        When: apply_graph_styling()を実行
        Then: グラフが正しく処理される（リファクタリング前との同一性は手動確認が必要）

        注: この特性テストは、リファクタリング前のコードのスナップショットと比較するのが理想だが、
        Phase 5では実装後のコードのみをテストする。リファクタリング前のコードが残っていれば、
        Phase 6で比較テストを実施する。
        """
        # Given
        dot_content = simple_graph_content

        # When
        result = DotFileProcessor.apply_graph_styling(dot_content)

        # Then
        # 基本的な構造が維持されていることを確認
        assert 'strict digraph' in result
        assert 'rankdir' in result
        assert 'node [' in result
        assert 'edge [' in result
        # URNが処理されていることを確認
        assert '->' in result

    def test_urn_processor_integration(self):
        """IT-DOT-002: UrnProcessorとDotFileProcessorの統合_正常系

        Given: DotFileProcessorが内部でUrnProcessorを使用
        When: parse_urn()を呼び出す
        Then: URN情報が正しく解析される
        """
        # Given
        urn = "urn:pulumi:dev::myproject::aws:ec2/instance:Instance::webserver"

        # When
        result = DotFileProcessor.parse_urn(urn)

        # Then
        assert result['stack'] == 'dev'
        assert result['project'] == 'myproject'
        assert result['provider'] == 'aws'
        assert result['module'] == 'ec2'
        assert result['type'] == 'Instance'
        assert result['name'] == 'webserver'

    def test_node_label_generator_integration(self, sample_urn_info):
        """IT-DOT-003: NodeLabelGeneratorとDotFileProcessorの統合_正常系

        Given: DotFileProcessorが内部でNodeLabelGeneratorを使用
        When: create_readable_label()を呼び出す
        Then: 読みやすいラベルが生成される
        """
        # Given
        urn_info = sample_urn_info

        # When
        result = DotFileProcessor.create_readable_label(urn_info)

        # Then
        assert 'ec2' in result
        assert 'Instance' in result
        assert 'webserver' in result

    def test_is_empty_graph_true(self):
        """IT-DOT-004補足: is_empty_graph()が正しく動作する（空グラフ）

        Given: 空のグラフコンテンツ
        When: is_empty_graph()を呼び出す
        Then: Trueが返される
        """
        # Given
        dot_content = "strict digraph {\n    rankdir=\"LR\";\n}\n"

        # When
        result = DotFileProcessor.is_empty_graph(dot_content)

        # Then
        assert result is True

    def test_is_empty_graph_false(self, simple_graph_content):
        """IT-DOT-004補足: is_empty_graph()が正しく動作する（非空グラフ）

        Given: ノードを含むグラフコンテンツ
        When: is_empty_graph()を呼び出す
        Then: Falseが返される
        """
        # Given
        dot_content = simple_graph_content

        # When
        result = DotFileProcessor.is_empty_graph(dot_content)

        # Then
        assert result is False

    def test_end_to_end_simple_graph(self, simple_graph_content):
        """IT-DOT-005: 3つの新規クラスの統合動作_E2Eテスト（単純グラフ）

        Given: 単純なDOTファイル
        When: apply_graph_styling()を実行
        Then: URN解析、ラベル生成、依存関係処理がすべて正しく動作する
        """
        # Given
        dot_content = simple_graph_content

        # When
        result = DotFileProcessor.apply_graph_styling(dot_content)

        # Then
        # 基本構造が維持されていることを確認
        assert 'strict digraph' in result
        # スタックリソースノードが追加されていることを確認（実装により異なる可能性）
        assert 'Stack' in result or 'dev' in result
        # エッジが処理されていることを確認
        assert '->' in result

    def test_end_to_end_complex_graph(self, complex_graph_content):
        """IT-DOT-005補足: E2Eテスト（複雑グラフ）

        Given: 複雑なDOTファイル（複数のリソースと依存関係）
        When: apply_graph_styling()を実行
        Then: すべてのリソースと依存関係が正しく処理される
        """
        # Given
        dot_content = complex_graph_content

        # When
        result = DotFileProcessor.apply_graph_styling(dot_content)

        # Then
        # 複数のノードが処理されていることを確認
        assert result.count('->') >= 10  # 複雑グラフには11のエッジがある
        # VPCリソースが含まれることを確認
        assert 'vpc' in result.lower() or 'Vpc' in result

    def test_performance_processing_time(self, complex_graph_content):
        """IT-DOT-007: パフォーマンステスト_処理時間比較

        Given: 複雑なDOTファイル
        When: apply_graph_styling()を100回実行
        Then: 平均処理時間が許容範囲内（ベースライン測定）

        注: リファクタリング前のコードがないため、ベースラインを測定する。
        Phase 6でリファクタリング前のコードと比較する。
        """
        # Given
        dot_content = complex_graph_content

        # When
        execution_times = []
        for _ in range(100):
            start_time = time.time()
            DotFileProcessor.apply_graph_styling(dot_content)
            elapsed_time = time.time() - start_time
            execution_times.append(elapsed_time)

        # Then
        average_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)

        # 平均処理時間を記録（ベースライン）
        print(f"Average processing time: {average_time:.4f}s")
        print(f"Max processing time: {max_time:.4f}s")

        # 処理時間が合理的な範囲内であることを確認（1秒以内）
        assert average_time < 1.0
        assert max_time < 2.0

    def test_aws_specific_resources(self):
        """IT-DOT-009: 実環境DOTファイルでのE2Eテスト_AWS

        Given: AWS固有のURN
        When: parse_urn()を呼び出す
        Then: AWSリソースタイプが正しく処理される
        """
        # Given
        aws_urns = [
            "urn:pulumi:prod::app::aws:ec2/instance:Instance::web",
            "urn:pulumi:prod::app::aws:s3/bucket:Bucket::data",
            "urn:pulumi:prod::app::aws:lambda/function:Function::api",
        ]

        # When & Then
        for urn in aws_urns:
            result = DotFileProcessor.parse_urn(urn)
            assert result['provider'] == 'aws'
            assert result['name'] in ['web', 'data', 'api']

    def test_kubernetes_specific_resources(self):
        """IT-DOT-010: 実環境DOTファイルでのE2Eテスト_Kubernetes

        Given: Kubernetes固有のURN
        When: parse_urn()を呼び出す
        Then: Kubernetesリソースタイプが正しく処理される
        """
        # Given
        k8s_urns = [
            "urn:pulumi:prod::app::kubernetes:core/v1:Service::api-service",
            "urn:pulumi:prod::app::kubernetes:apps/v1:Deployment::nginx",
        ]

        # When & Then
        for urn in k8s_urns:
            result = DotFileProcessor.parse_urn(urn)
            assert result['provider'] == 'kubernetes'
            assert result['type'] in ['Service', 'Deployment']

    def test_guard_clause_control_flow(self):
        """IT-DOT-011: Guard Clauseパターン適用後の制御フロー_正常系

        Given: 不正な行を含むDOTファイル
        When: apply_graph_styling()を実行
        Then: 不正な行はスキップされ、正常な行のみ処理される

        注: 実装の内部動作を直接テストすることは難しいため、
        不正な入力に対してエラーがスローされないことを確認する。
        """
        # Given - 空行やコメントを含むDOTコンテンツ
        dot_content = """strict digraph {
    rankdir="LR";

    // Comment line

    N0 [label="urn:pulumi:dev::project::aws:ec2/instance:Instance::web"];

    N0 -> N1;
}"""

        # When
        result = DotFileProcessor.apply_graph_styling(dot_content)

        # Then
        # エラーがスローされないことを確認
        assert 'strict digraph' in result
        # 正常な行は処理される
        assert 'web' in result or 'Instance' in result

    def test_regression_public_api_compatibility(self):
        """IT-DOT-012: 回帰テスト_既存の統合テストスイート実行

        Given: DotFileProcessorの公開API
        When: 各メソッドを呼び出す
        Then: すべてのメソッドが正しく動作する（後方互換性の確認）
        """
        # Given & When & Then
        # parse_urn()の動作確認
        urn_result = DotFileProcessor.parse_urn(
            "urn:pulumi:dev::project::aws:ec2/instance:Instance::web"
        )
        assert urn_result['provider'] == 'aws'

        # create_readable_label()の動作確認
        label_result = DotFileProcessor.create_readable_label(urn_result)
        assert 'Instance' in label_result

        # is_empty_graph()の動作確認
        empty_result = DotFileProcessor.is_empty_graph("strict digraph {\n}")
        assert empty_result is True

        # apply_graph_styling()の動作確認
        dot_content = """strict digraph {
    N0 [label="urn:pulumi:dev::project::aws:ec2/instance:Instance::web"];
}"""
        styled_result = DotFileProcessor.apply_graph_styling(dot_content)
        assert 'strict digraph' in styled_result


class TestEdgeCases:
    """エッジケースのテストクラス"""

    def test_malformed_dot_content(self):
        """不正なDOTファイル形式に対するロバスト性

        Given: 不正なDOTファイル形式
        When: apply_graph_styling()を実行
        Then: エラーをスローせず、可能な限り処理を継続する
        """
        # Given
        malformed_content = "This is not a valid DOT file"

        # When & Then
        # エラーがスローされないことを確認（または適切なデフォルト値を返す）
        try:
            result = DotFileProcessor.apply_graph_styling(malformed_content)
            # 何らかの出力が返されることを確認
            assert result is not None
        except Exception as e:
            # 適切な例外処理がされていることを確認
            pytest.fail(f"Unexpected exception: {e}")

    def test_very_large_graph(self):
        """非常に大きなグラフに対するスケーラビリティ

        Given: 100以上のノードを持つDOTファイル
        When: apply_graph_styling()を実行
        Then: 処理が完了する（メモリエラーが発生しない）
        """
        # Given - 100ノードのDOTファイルを生成
        nodes = [f'    N{i} [label="urn:pulumi:dev::project::aws:ec2/instance:Instance::web{i}"];'
                 for i in range(100)]
        edges = [f'    N{i} -> N{i+1};' for i in range(99)]

        dot_content = 'strict digraph {\n    rankdir="LR";\n'
        dot_content += '\n'.join(nodes)
        dot_content += '\n'
        dot_content += '\n'.join(edges)
        dot_content += '\n}\n'

        # When
        start_time = time.time()
        result = DotFileProcessor.apply_graph_styling(dot_content)
        elapsed_time = time.time() - start_time

        # Then
        # 処理が完了することを確認
        assert result is not None
        # 処理時間が合理的な範囲内（5秒以内）
        assert elapsed_time < 5.0
        print(f"Large graph processing time: {elapsed_time:.4f}s")
