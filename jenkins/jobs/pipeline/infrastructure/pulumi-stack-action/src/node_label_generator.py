"""
Node label generation for Pulumi dependency graphs

このモジュールはPulumiリソースのノードラベル生成の責務を担当します。

主要機能:
- スタックノードラベル生成: Pulumiスタックリソース用のDOT属性
- リソースノードラベル生成: クラウドリソース用のDOT属性
- プロバイダー別色設定: AWS、Azure、GCP等のプロバイダー固有の色適用

設計方針:
- すべてのメソッドは静的メソッド（ステートレス設計）
- UrnProcessor、DotFileGeneratorへの依存
- Single Responsibility Principle（ラベル生成のみ）

依存関係:
- UrnProcessor: URN解析、ラベル生成補助
- DotFileGenerator: エスケープ処理、PROVIDER_COLORS参照
"""

from typing import Dict
from urn_processor import UrnProcessor


class NodeLabelGenerator:
    """ノードラベル生成の責務を担当

    リソースタイプに応じたDOT形式のノード属性文字列を生成します。
    スタックノードとリソースノードで異なるフォーマットを適用します。

    設計方針:
    - すべてのメソッドは静的メソッド（ステートレス設計）
    - UrnProcessor、DotFileGeneratorへの依存
    - 拡張可能な設計（カスタムラベル対応）

    依存関係:
    - UrnProcessor: URN解析、ラベル生成補助
    - DotFileGenerator: PROVIDER_COLORS参照（循環参照を避けるため遅延インポート）

    Examples:
        >>> from urn_processor import UrnProcessor
        >>> urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket"
        >>> urn_info = UrnProcessor.parse_urn(urn)
        >>> label = NodeLabelGenerator.generate_node_label(urn, urn_info)
        >>> print(label)
        'label="s3\\nBucket\\nmy-bucket", fillcolor="#FFF3E0", color="#EF6C00", shape=box, fontsize="11"'
    """

    @staticmethod
    def generate_node_label(urn: str, urn_info: Dict[str, str]) -> str:
        """URNとURN情報からノード属性文字列を生成

        URNの種類（スタック/リソース）を判定し、適切なラベル生成メソッドに
        振り分けます。

        Args:
            urn (str): 完全なURN文字列
            urn_info (Dict[str, str]): UrnProcessor.parse_urn()の戻り値

        Returns:
            str: DOT形式のノード属性文字列
                例: 'label="Stack\\ndev", fillcolor="#D1C4E9", color="#512DA8", shape=ellipse, fontsize="14"'

        Examples:
            >>> urn = "urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev"
            >>> urn_info = UrnProcessor.parse_urn(urn)
            >>> NodeLabelGenerator.generate_node_label(urn, urn_info)
            'label="Stack\\ndev", fillcolor="#D1C4E9", color="#512DA8", shape=ellipse, fontsize="14"'
        """
        if UrnProcessor.is_stack_resource(urn):
            return NodeLabelGenerator.generate_stack_node_label(urn_info)
        else:
            return NodeLabelGenerator.generate_resource_node_label(urn_info)

    @staticmethod
    def generate_stack_node_label(urn_info: Dict[str, str]) -> str:
        """スタックノードのラベル属性を生成

        Pulumiスタックリソース用のDOT形式ノード属性文字列を生成します。
        固定色（#D1C4E9, #512DA8）と楕円形状を使用します。

        Args:
            urn_info (Dict[str, str]): URN情報辞書
                必須キー: 'stack' - スタック名

        Returns:
            str: スタック用のDOT形式ノード属性文字列

        Examples:
            >>> urn_info = {'stack': 'dev', 'project': 'myproject'}
            >>> NodeLabelGenerator.generate_stack_node_label(urn_info)
            'label="Stack\\ndev", fillcolor="#D1C4E9", color="#512DA8", shape=ellipse, fontsize="14"'
        """
        new_label = f"Stack\\n{urn_info['stack']}"
        return f'label="{new_label}", fillcolor="#D1C4E9", color="#512DA8", shape=ellipse, fontsize="14"'

    @staticmethod
    def generate_resource_node_label(urn_info: Dict[str, str]) -> str:
        """リソースノードのラベル属性を生成

        クラウドリソース（AWS、Azure、GCP等）用のDOT形式ノード属性文字列を
        生成します。プロバイダー別の色設定を適用します。

        Args:
            urn_info (Dict[str, str]): URN情報辞書
                必須キー: 'provider' - プロバイダー名
                オプションキー: 'module', 'type', 'name'

        Returns:
            str: リソース用のDOT形式ノード属性文字列

        Examples:
            >>> urn_info = {
            ...     'provider': 'aws',
            ...     'module': 's3',
            ...     'type': 'Bucket',
            ...     'name': 'my-bucket'
            ... }
            >>> NodeLabelGenerator.generate_resource_node_label(urn_info)
            'label="s3\\nBucket\\nmy-bucket", fillcolor="#FFF3E0", color="#EF6C00", shape=box, fontsize="11"'

        Note:
            - プロバイダー名の大文字小文字は無視されます（.lower()で統一）
            - 未定義プロバイダーの場合はデフォルト色（#E3F2FD, #1565C0）が使用されます
            - ラベルはUrnProcessor.create_readable_label()で生成されます
        """
        # 循環参照を避けるため、遅延インポート
        from dot_processor import DotFileGenerator

        # UrnProcessorで読みやすいラベルを生成
        new_label = UrnProcessor.create_readable_label(urn_info)

        # プロバイダー別色設定を取得
        provider_colors = DotFileGenerator.PROVIDER_COLORS.get(
            urn_info['provider'].lower(),
            DotFileGenerator.DEFAULT_COLORS
        )
        fillcolor = provider_colors[0]
        color = provider_colors[1]

        return f'label="{new_label}", fillcolor="{fillcolor}", color="{color}", shape=box, fontsize="11"'

    @staticmethod
    def _format_label(label: str, max_length: int = 40) -> str:
        """ラベル文字列をフォーマット（長い場合は省略）

        長いラベルを省略記号付きで短縮します（将来の拡張用）。
        現在は内部ヘルパーメソッドとして定義されていますが、
        必要に応じて公開メソッドに変更可能です。

        Args:
            label (str): 元のラベル文字列
            max_length (int): 最大文字数（デフォルト: 40）

        Returns:
            str: フォーマット済みラベル文字列

        Examples:
            >>> NodeLabelGenerator._format_label("short", 40)
            'short'

            >>> NodeLabelGenerator._format_label("very-long-label-that-exceeds-40-chars", 40)
            'very-long-label-that-exceeds-40-ch...'

        Note:
            - max_lengthを超える場合は省略記号（...）を追加
            - 空文字列の場合はそのまま返します
            - 将来的なカスタムラベルフォーマット対応のための拡張ポイント
        """
        if not label:
            return label

        if len(label) > max_length:
            return label[:max_length - 3] + '...'

        return label
