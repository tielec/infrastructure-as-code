"""
Resource dependency graph building

このモジュールは、依存関係グラフの構築と検証の責務を担当します。

主要な機能:
- リソースリストから依存関係グラフを構築
- URNからノードIDへのマッピング管理
- 通常の依存関係、親リソース依存、プロパティ依存の処理
"""

from typing import Dict, List


class ResourceDependencyBuilder:
    """依存関係グラフの構築と検証を担当"""

    def __init__(self):
        """コンストラクタ

        Attributes:
            node_urn_map: ノードID → URN情報のマッピング（将来的な拡張用）
        """
        self.node_urn_map: Dict[str, Dict[str, str]] = {}

    def build_dependency_graph(self, resources: List[Dict]) -> List[str]:
        """リソースリストから依存関係グラフを構築

        Args:
            resources: リソース情報のリスト

        Returns:
            DOT形式のエッジ定義のリスト

        Examples:
            >>> builder = ResourceDependencyBuilder()
            >>> resources = [
            ...     {'urn': 'urn:...:resource1', 'dependencies': ['urn:...:resource2']},
            ...     {'urn': 'urn:...:resource2', 'dependencies': []}
            ... ]
            >>> edges = builder.build_dependency_graph(resources)
            >>> print(edges[0])
            "resource_0" -> "resource_1" [style=solid, color="#9C27B0", fontsize="10"];

        Notes:
            - 空のリソースリストの場合は空のリストを返す
            - 依存先が存在しない場合、該当するエッジはスキップされる
            - 3種類の依存関係を処理: 直接依存、親リソース依存、プロパティ依存
        """
        # 早期リターン: リソースが空
        if not resources:
            return []

        edges = []

        # URNからノードIDへのマッピングを作成
        urn_to_node_id = self._create_urn_to_node_mapping(resources)

        # 各リソースの依存関係を処理
        for i, resource in enumerate(resources):
            resource_edges = self._add_dependencies_for_resource(
                i, resource, urn_to_node_id
            )
            edges.extend(resource_edges)

        return edges

    def _create_urn_to_node_mapping(self, resources: List[Dict]) -> Dict[str, str]:
        """URNからノードIDへのマッピングを作成

        Args:
            resources: リソース情報のリスト

        Returns:
            URN -> ノードID のマッピング

        Examples:
            >>> builder = ResourceDependencyBuilder()
            >>> resources = [
            ...     {'urn': 'urn:...:resource1'},
            ...     {'urn': 'urn:...:resource2'}
            ... ]
            >>> mapping = builder._create_urn_to_node_mapping(resources)
            >>> mapping['urn:...:resource1']
            'resource_0'

        Notes:
            - ノードIDは 'resource_{index}' 形式で生成される
            - URNが空の場合はマッピングに追加されない
        """
        mapping = {}
        for i, resource in enumerate(resources):
            urn = resource.get('urn', '')
            if urn:
                mapping[urn] = f'resource_{i}'
        return mapping

    def _add_dependencies_for_resource(self, resource_index: int,
                                      resource: Dict,
                                      urn_to_node_id: Dict[str, str]) -> List[str]:
        """単一リソースの依存関係を追加

        Args:
            resource_index: リソースのインデックス
            resource: リソース情報
            urn_to_node_id: URN -> ノードID のマッピング

        Returns:
            DOT形式のエッジ定義のリスト

        Notes:
            - 直接依存関係、親リソース依存、プロパティ依存を統合して処理
        """
        edges = []
        node_id = f'resource_{resource_index}'

        # 通常の依存関係を追加
        edges.extend(self._add_direct_dependencies(node_id, resource, urn_to_node_id))

        # 親リソースへの依存を追加
        parent_edge = self._add_parent_dependency(node_id, resource, urn_to_node_id)
        if parent_edge:
            edges.append(parent_edge)

        # プロパティ依存を追加
        edges.extend(self._add_property_dependencies(node_id, resource, urn_to_node_id))

        return edges

    def _add_direct_dependencies(self, node_id: str, resource: Dict,
                                urn_to_node_id: Dict[str, str]) -> List[str]:
        """直接的な依存関係を追加

        Args:
            node_id: 現在のノードID
            resource: リソース情報
            urn_to_node_id: URN -> ノードID のマッピング

        Returns:
            直接依存関係のエッジ定義のリスト

        Notes:
            - resource['dependencies'] に含まれるURNに対してエッジを生成
            - 依存先が存在しない場合はスキップ
            - スタイル: solid線、色: #9C27B0（紫色）
        """
        edges = []
        dependencies = resource.get('dependencies', [])

        for dep_urn in dependencies:
            if dep_urn in urn_to_node_id:
                dep_node_id = urn_to_node_id[dep_urn]
                edge = (
                    f'    "{node_id}" -> "{dep_node_id}" '
                    f'[style=solid, color="#9C27B0", fontsize="10"];'
                )
                edges.append(edge)

        return edges

    def _add_parent_dependency(self, node_id: str, resource: Dict,
                              urn_to_node_id: Dict[str, str]) -> str:
        """親リソースへの依存を追加

        Args:
            node_id: 現在のノードID
            resource: リソース情報
            urn_to_node_id: URN -> ノードID のマッピング

        Returns:
            親リソース依存のエッジ定義（存在しない場合は空文字列）

        Notes:
            - resource['parent'] に親URNが含まれる場合にエッジを生成
            - スタイル: dashed線、色: #2196F3（青色）、ラベル: "parent"
        """
        parent = resource.get('parent')
        if not parent or parent not in urn_to_node_id:
            return ''

        parent_node_id = urn_to_node_id[parent]
        return (
            f'    "{node_id}" -> "{parent_node_id}" '
            f'[style=dashed, color="#2196F3", label="parent", fontsize="10"];'
        )

    def _add_property_dependencies(self, node_id: str, resource: Dict,
                                  urn_to_node_id: Dict[str, str]) -> List[str]:
        """プロパティ依存を追加

        Args:
            node_id: 現在のノードID
            resource: リソース情報
            urn_to_node_id: URN -> ノードID のマッピング

        Returns:
            プロパティ依存のエッジ定義のリスト

        Notes:
            - resource['propertyDependencies'] に含まれる依存関係を処理
            - プロパティ名が長い場合は最後の部分のみを表示（例: 'security.groups' -> 'groups'）
            - スタイル: dotted線、色: #FF5722（オレンジ色）、ラベル: プロパティ名
        """
        edges = []
        prop_deps = resource.get('propertyDependencies', {})

        for prop_name, dep_urns in prop_deps.items():
            for dep_urn in dep_urns:
                if dep_urn in urn_to_node_id:
                    dep_node_id = urn_to_node_id[dep_urn]
                    # 短いプロパティ名を表示
                    short_prop = prop_name.split('.')[-1] if '.' in prop_name else prop_name
                    edge = (
                        f'    "{node_id}" -> "{dep_node_id}" '
                        f'[style=dotted, color="#FF5722", label="{short_prop}", fontsize="9"];'
                    )
                    edges.append(edge)

        return edges
