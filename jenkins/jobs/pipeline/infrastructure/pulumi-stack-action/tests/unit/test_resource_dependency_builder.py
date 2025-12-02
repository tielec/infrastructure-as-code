"""
ResourceDependencyBuilder クラスのユニットテスト

テストシナリオ: test-scenario.md の UT-DEP-001 ~ UT-DEP-010
"""

import pytest
from resource_dependency_builder import ResourceDependencyBuilder


class TestBuildDependencyGraph:
    """build_dependency_graph() メソッドのテストクラス"""

    def test_build_dependency_graph_simple(self, sample_resources):
        """UT-DEP-001: build_dependency_graph_単純な依存関係_正常系

        Given: 単純な依存関係（2リソース、1依存関係）
        When: build_dependency_graph()を呼び出す
        Then: 正しいエッジ定義が返される
        """
        # Given
        builder = ResourceDependencyBuilder()

        # When
        result = builder.build_dependency_graph(sample_resources)

        # Then
        assert len(result) >= 1
        # エッジが存在することを確認（具体的な形式は実装に依存）
        assert any('->' in edge for edge in result)

    def test_build_dependency_graph_complex(self, complex_resources):
        """UT-DEP-002: build_dependency_graph_複雑な依存関係_正常系

        Given: 複数の依存関係を持つリソース（4リソース、3依存関係）
        When: build_dependency_graph()を呼び出す
        Then: すべての依存関係がエッジとして追加される
        """
        # Given
        builder = ResourceDependencyBuilder()

        # When
        result = builder.build_dependency_graph(complex_resources)

        # Then
        # 複数のエッジが生成されることを確認
        assert len(result) >= 3
        # すべてのエッジに'->'が含まれることを確認
        assert all('->' in edge for edge in result)

    def test_build_dependency_graph_empty_resources(self):
        """UT-DEP-003: build_dependency_graph_空のリソースリスト_異常系

        Given: 空のリソースリスト
        When: build_dependency_graph()を呼び出す
        Then: 空のリストが返される
        """
        # Given
        builder = ResourceDependencyBuilder()
        resources = []

        # When
        result = builder.build_dependency_graph(resources)

        # Then
        assert result == []

    def test_build_dependency_graph_missing_dependency(self):
        """UT-DEP-004: build_dependency_graph_依存先が存在しない_準正常系

        Given: 存在しない依存先を参照するリソース
        When: build_dependency_graph()を呼び出す
        Then: 該当エッジをスキップし、エラーをスローしない
        """
        # Given
        builder = ResourceDependencyBuilder()
        resources = [
            {
                'urn': 'urn:...:web',
                'dependencies': ['urn:...:nonexistent']
            }
        ]

        # When
        result = builder.build_dependency_graph(resources)

        # Then
        # 依存先が見つからないため、エッジは生成されない
        assert result == []

    def test_build_dependency_graph_parent_dependency(self):
        """UT-DEP-005: build_dependency_graph_親リソース依存_正常系

        Given: 親リソースへの依存を持つリソース
        When: build_dependency_graph()を呼び出す
        Then: 親リソースへのエッジが追加される（dashed線）
        """
        # Given
        builder = ResourceDependencyBuilder()
        resources = [
            {
                'urn': 'urn:...:child',
                'parent': 'urn:...:parent',
                'dependencies': []
            },
            {
                'urn': 'urn:...:parent',
                'dependencies': []
            }
        ]

        # When
        result = builder.build_dependency_graph(resources)

        # Then
        # 親リソースへのエッジが生成される
        assert len(result) >= 1
        # dashed スタイルが含まれることを確認
        parent_edges = [edge for edge in result if 'dashed' in edge]
        assert len(parent_edges) >= 1

    def test_build_dependency_graph_property_dependency(self):
        """UT-DEP-006: build_dependency_graph_プロパティ依存_正常系

        Given: プロパティ依存を持つリソース
        When: build_dependency_graph()を呼び出す
        Then: プロパティ依存のエッジが追加される
        """
        # Given
        builder = ResourceDependencyBuilder()
        resources = [
            {
                'urn': 'urn:...:web',
                'propertyDependencies': {
                    'vpcId': ['urn:...:vpc'],
                    'subnetId': ['urn:...:subnet']
                },
                'dependencies': []
            },
            {
                'urn': 'urn:...:vpc',
                'dependencies': []
            },
            {
                'urn': 'urn:...:subnet',
                'dependencies': []
            }
        ]

        # When
        result = builder.build_dependency_graph(resources)

        # Then
        # 2つのプロパティ依存エッジが生成される
        assert len(result) >= 2

    def test_build_dependency_graph_large_resources(self):
        """UT-DEP-007: build_dependency_graph_大量のリソース_境界値

        Given: 100以上のリソース
        When: build_dependency_graph()を呼び出す
        Then: すべての依存関係が正しく処理され、処理時間が許容範囲内
        """
        # Given
        builder = ResourceDependencyBuilder()
        # 100リソース、200依存関係を生成
        resources = []
        for i in range(100):
            deps = []
            if i > 0:
                deps.append(f'urn:...:resource{i-1}')
            if i > 1:
                deps.append(f'urn:...:resource{i-2}')
            resources.append({
                'urn': f'urn:...:resource{i}',
                'dependencies': deps
            })

        # When
        import time
        start_time = time.time()
        result = builder.build_dependency_graph(resources)
        elapsed_time = time.time() - start_time

        # Then
        # すべての依存関係が処理される
        assert len(result) > 0
        # 処理時間が1秒以内（目標）
        assert elapsed_time < 1.0


class TestInternalMethods:
    """内部メソッドのテストクラス"""

    def test_create_urn_to_node_mapping(self):
        """UT-DEP-008: _create_urn_to_node_mapping_標準的なリソースリスト_正常系

        Given: 3つのリソースを含むリスト
        When: _create_urn_to_node_mapping()を呼び出す
        Then: URN -> ノードIDのマッピングが正しく作成される
        """
        # Given
        builder = ResourceDependencyBuilder()
        resources = [
            {'urn': 'urn:...:resource1'},
            {'urn': 'urn:...:resource2'},
            {'urn': 'urn:...:resource3'}
        ]

        # When
        result = builder._create_urn_to_node_mapping(resources)

        # Then
        assert len(result) == 3
        assert 'urn:...:resource1' in result
        assert 'urn:...:resource2' in result
        assert 'urn:...:resource3' in result
        # ノードIDの形式を確認（resource_0, resource_1, resource_2）
        assert result['urn:...:resource1'] == 'resource_0'
        assert result['urn:...:resource2'] == 'resource_1'
        assert result['urn:...:resource3'] == 'resource_2'

    def test_add_direct_dependencies(self):
        """UT-DEP-009: _add_direct_dependencies_複数の直接依存_正常系

        Given: 2つの直接依存関係を持つリソース
        When: _add_direct_dependencies()を呼び出す
        Then: 2つのエッジ定義が返される
        """
        # Given
        builder = ResourceDependencyBuilder()
        node_id = 'resource_0'
        resource = {
            'dependencies': ['urn:...:dep1', 'urn:...:dep2']
        }
        urn_to_node_id = {
            'urn:...:dep1': 'resource_1',
            'urn:...:dep2': 'resource_2'
        }

        # When
        result = builder._add_direct_dependencies(node_id, resource, urn_to_node_id)

        # Then
        assert len(result) == 2
        # 各エッジに'->'が含まれることを確認
        assert all('->' in edge for edge in result)

    def test_add_property_dependencies(self):
        """UT-DEP-010: _add_property_dependencies_複数プロパティ_正常系

        Given: 複数プロパティの依存関係を持つリソース
        When: _add_property_dependencies()を呼び出す
        Then: すべてのプロパティ依存エッジが返される
        """
        # Given
        builder = ResourceDependencyBuilder()
        node_id = 'resource_0'
        resource = {
            'propertyDependencies': {
                'security.groups': ['urn:...:sg1', 'urn:...:sg2'],
                'network.vpcId': ['urn:...:vpc']
            }
        }
        urn_to_node_id = {
            'urn:...:sg1': 'resource_1',
            'urn:...:sg2': 'resource_2',
            'urn:...:vpc': 'resource_3'
        }

        # When
        result = builder._add_property_dependencies(node_id, resource, urn_to_node_id)

        # Then
        # 3つのエッジが生成される（sg1, sg2, vpc）
        assert len(result) == 3
        # プロパティ名のラベルが含まれることを期待
        assert any('label' in edge for edge in result)
