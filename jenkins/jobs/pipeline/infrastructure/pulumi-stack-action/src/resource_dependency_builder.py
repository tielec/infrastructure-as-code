"""
Resource dependency graph builder for Pulumi DOT files

このモジュールはPulumiリソース間の依存関係グラフ構築の責務を担当します。

主要機能:
- URNマッピング作成: リソースURNからノードIDへのマッピング
- 依存関係追加: 直接、親、プロパティの3種類の依存関係
- エッジ生成: DOT形式の依存関係エッジ文字列生成

設計方針:
- すべてのメソッドは静的メソッド（ステートレス設計）
- 他のクラスに依存しない（疎結合）
- 拡張可能な設計（新しい依存関係タイプ追加が容易）

依存関係:
- typing: 型ヒント（List, Dict）のみ
"""

from typing import Dict, List


class ResourceDependencyBuilder:
    """リソース依存関係グラフ構築の責務を担当

    Pulumiリソース間の依存関係を解析し、DOT形式のエッジ定義を生成します。
    3種類の依存関係（直接、親、プロパティ）をサポートします。

    設計方針:
    - すべてのメソッドは静的メソッド（ステートレス設計）
    - 破壊的更新: dot_linesリストを直接変更
    - エラー安全: 不正なURNや存在しないURNを安全に処理

    Examples:
        >>> resources = [
        ...     {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',
        ...      'dependencies': [], 'parent': None, 'propertyDependencies': {}},
        ...     {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b',
        ...      'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a'],
        ...      'parent': None, 'propertyDependencies': {}}
        ... ]
        >>> dot_lines = []
        >>> ResourceDependencyBuilder.add_resource_dependencies(resources, dot_lines)
        >>> print(dot_lines)
        ['', '    // リソース間の依存関係', '    "resource_1" -> "resource_0" [style=solid, ...]']
    """

    # 依存関係スタイル定数（DOT形式）
    DIRECT_DEPENDENCY_STYLE = 'style=solid, color="#9C27B0", fontsize="10"'
    PARENT_DEPENDENCY_STYLE = 'style=dashed, color="#2196F3", label="parent", fontsize="10"'
    PROPERTY_DEPENDENCY_STYLE = 'style=dotted, color="#FF5722", fontsize="9"'

    @staticmethod
    def add_resource_dependencies(resources: List[Dict], dot_lines: List[str]) -> None:
        """リソース間の依存関係をDOT形式で追加（エントリーポイント）

        リソースリストから依存関係を解析し、DOT形式のエッジ定義を
        dot_linesリストに破壊的に追加します。

        Args:
            resources (List[Dict]): リソースリスト（最大20個）
                各リソースは以下のキーを持つ辞書:
                - urn (str): リソースURN
                - dependencies (List[str]): 依存URNリスト
                - parent (str | None): 親リソースURN
                - propertyDependencies (Dict[str, List[str]]): プロパティ依存辞書
            dot_lines (List[str]): DOT形式文字列リスト（破壊的更新）

        Returns:
            None: dot_linesを直接変更

        Examples:
            >>> resources = [
            ...     {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',
            ...      'dependencies': [], 'parent': None, 'propertyDependencies': {}},
            ...     {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b',
            ...      'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a'],
            ...      'parent': None, 'propertyDependencies': {}}
            ... ]
            >>> dot_lines = []
            >>> ResourceDependencyBuilder.add_resource_dependencies(resources, dot_lines)
            >>> len(dot_lines) > 0
            True

        Note:
            - リソースが1個以下の場合は何もしない
            - 最大20リソースまで処理（仕様）
            - 不正なURNや存在しないURNは安全にスキップ
        """
        if len(resources) <= 1:
            return

        dot_lines.extend(['', '    // リソース間の依存関係'])

        # リソースのURNからIDへのマッピングを作成
        urn_to_node_id = ResourceDependencyBuilder.create_urn_to_node_mapping(resources)

        # 各リソースの依存関係を処理
        for i, resource in enumerate(resources):
            ResourceDependencyBuilder._add_dependencies_for_resource(
                i, resource, urn_to_node_id, dot_lines
            )

    @staticmethod
    def create_urn_to_node_mapping(resources: List[Dict]) -> Dict[str, str]:
        """URNからノードIDへのマッピングを作成

        リソースリストからURN文字列をキー、ノードID（`resource_{i}`形式）を
        値とする辞書を作成します。

        Args:
            resources (List[Dict]): リソースリスト
                各リソースは'urn'キーを持つ辞書

        Returns:
            Dict[str, str]: URN → ノードIDのマッピング辞書
                例: {'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket': 'resource_0'}

        Examples:
            >>> resources = [
            ...     {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a'},
            ...     {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b'}
            ... ]
            >>> mapping = ResourceDependencyBuilder.create_urn_to_node_mapping(resources)
            >>> mapping['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a']
            'resource_0'
            >>> mapping['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b']
            'resource_1'

        Note:
            - 空リストの場合は空の辞書を返す
            - 重複URNの場合は最後のリソースのノードIDを使用
            - 'urn'キーが存在しないリソースは空文字列をキーとして扱う
        """
        mapping = {}
        for i, resource in enumerate(resources):
            urn = resource.get('urn', '')
            mapping[urn] = f'resource_{i}'
        return mapping

    @staticmethod
    def _add_dependencies_for_resource(
        resource_index: int,
        resource: Dict,
        urn_to_node_id: Dict[str, str],
        dot_lines: List[str]
    ) -> None:
        """単一リソースの全依存関係を追加（プライベート）

        単一リソースの直接依存、親依存、プロパティ依存の3種類を
        順次処理します。

        Args:
            resource_index (int): リソースのインデックス（0始まり）
            resource (Dict): リソース辞書
            urn_to_node_id (Dict[str, str]): URNマッピング
            dot_lines (List[str]): DOT形式文字列リスト（破壊的更新）

        Returns:
            None: dot_linesを直接変更

        Note:
            - プライベートメソッド（_プレフィックス）
            - 処理順序: 直接 → 親 → プロパティ
        """
        node_id = f'resource_{resource_index}'

        # 通常の依存関係を追加
        ResourceDependencyBuilder._add_direct_dependencies(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # 親リソースへの依存を追加
        ResourceDependencyBuilder._add_parent_dependency(
            node_id, resource, urn_to_node_id, dot_lines
        )

        # プロパティ依存を追加
        ResourceDependencyBuilder._add_property_dependencies(
            node_id, resource, urn_to_node_id, dot_lines
        )

    @staticmethod
    def _add_direct_dependencies(
        node_id: str,
        resource: Dict,
        urn_to_node_id: Dict[str, str],
        dot_lines: List[str]
    ) -> None:
        """直接的な依存関係を追加（プライベート）

        リソースの'dependencies'フィールドから直接依存関係を抽出し、
        DOT形式のエッジ定義を生成します。

        Args:
            node_id (str): ノードID（例: 'resource_0'）
            resource (Dict): リソース辞書
                - dependencies (List[str]): 依存URNリスト
            urn_to_node_id (Dict[str, str]): URNマッピング
            dot_lines (List[str]): DOT形式文字列リスト（破壊的更新）

        Returns:
            None: dot_linesを直接変更

        Examples:
            >>> node_id = 'resource_1'
            >>> resource = {
            ...     'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a']
            ... }
            >>> urn_to_node_id = {
            ...     'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a': 'resource_0'
            ... }
            >>> dot_lines = []
            >>> ResourceDependencyBuilder._add_direct_dependencies(
            ...     node_id, resource, urn_to_node_id, dot_lines
            ... )
            >>> dot_lines[0]
            '    "resource_1" -> "resource_0" [style=solid, color="#9C27B0", fontsize="10"];'

        Note:
            - 'dependencies'フィールドが存在しない場合は何もしない
            - URNマッピングに存在しないURNはスキップ
            - スタイル: solid, color="#9C27B0"
        """
        dependencies = resource.get('dependencies', [])
        for dep_urn in dependencies:
            if dep_urn in urn_to_node_id:
                dep_node_id = urn_to_node_id[dep_urn]
                dot_lines.append(
                    f'    "{node_id}" -> "{dep_node_id}" '
                    f'[{ResourceDependencyBuilder.DIRECT_DEPENDENCY_STYLE}];'
                )

    @staticmethod
    def _add_parent_dependency(
        node_id: str,
        resource: Dict,
        urn_to_node_id: Dict[str, str],
        dot_lines: List[str]
    ) -> None:
        """親リソースへの依存を追加（プライベート）

        リソースの'parent'フィールドから親依存関係を抽出し、
        DOT形式のエッジ定義を生成します。

        Args:
            node_id (str): ノードID（例: 'resource_0'）
            resource (Dict): リソース辞書
                - parent (str | None): 親リソースURN
            urn_to_node_id (Dict[str, str]): URNマッピング
            dot_lines (List[str]): DOT形式文字列リスト（破壊的更新）

        Returns:
            None: dot_linesを直接変更

        Examples:
            >>> node_id = 'resource_1'
            >>> resource = {
            ...     'parent': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a'
            ... }
            >>> urn_to_node_id = {
            ...     'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a': 'resource_0'
            ... }
            >>> dot_lines = []
            >>> ResourceDependencyBuilder._add_parent_dependency(
            ...     node_id, resource, urn_to_node_id, dot_lines
            ... )
            >>> dot_lines[0]
            '    "resource_1" -> "resource_0" [style=dashed, color="#2196F3", label="parent", fontsize="10"];'

        Note:
            - 'parent'がNoneまたは空文字列の場合は何もしない
            - URNマッピングに存在しないURNはスキップ
            - スタイル: dashed, color="#2196F3", label="parent"
        """
        parent = resource.get('parent')
        if parent and parent in urn_to_node_id:
            parent_node_id = urn_to_node_id[parent]
            dot_lines.append(
                f'    "{node_id}" -> "{parent_node_id}" '
                f'[{ResourceDependencyBuilder.PARENT_DEPENDENCY_STYLE}];'
            )

    @staticmethod
    def _add_property_dependencies(
        node_id: str,
        resource: Dict,
        urn_to_node_id: Dict[str, str],
        dot_lines: List[str]
    ) -> None:
        """プロパティ依存を追加（プライベート）

        リソースの'propertyDependencies'フィールドからプロパティ依存関係を
        抽出し、DOT形式のエッジ定義を生成します。

        Args:
            node_id (str): ノードID（例: 'resource_0'）
            resource (Dict): リソース辞書
                - propertyDependencies (Dict[str, List[str]]): プロパティ依存辞書
                    キー: プロパティ名（例: 'vpc.id'）
                    値: 依存URNリスト
            urn_to_node_id (Dict[str, str]): URNマッピング
            dot_lines (List[str]): DOT形式文字列リスト（破壊的更新）

        Returns:
            None: dot_linesを直接変更

        Examples:
            >>> node_id = 'resource_1'
            >>> resource = {
            ...     'propertyDependencies': {
            ...         'vpc.id': ['urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc']
            ...     }
            ... }
            >>> urn_to_node_id = {
            ...     'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc': 'resource_0'
            ... }
            >>> dot_lines = []
            >>> ResourceDependencyBuilder._add_property_dependencies(
            ...     node_id, resource, urn_to_node_id, dot_lines
            ... )
            >>> dot_lines[0]
            '    "resource_1" -> "resource_0" [style=dotted, color="#FF5722", label="id", fontsize="9"];'

        Note:
            - 'propertyDependencies'が存在しない場合は何もしない
            - プロパティ名が長い場合は末尾のみを使用（例: 'vpc.id' → 'id'）
            - URNマッピングに存在しないURNはスキップ
            - スタイル: dotted, color="#FF5722"
        """
        prop_deps = resource.get('propertyDependencies', {})
        for prop_name, dep_urns in prop_deps.items():
            for dep_urn in dep_urns:
                if dep_urn in urn_to_node_id:
                    dep_node_id = urn_to_node_id[dep_urn]
                    # 短いプロパティ名を表示
                    short_prop = prop_name.split('.')[-1] if '.' in prop_name else prop_name
                    dot_lines.append(
                        f'    "{node_id}" -> "{dep_node_id}" '
                        f'[style=dotted, color="#FF5722", label="{short_prop}", fontsize="9"];'
                    )
