"""
Node label generation for DOT graphs

このモジュールは、リソースタイプに応じたラベル生成ロジックを担当します。

主要な機能:
- URN情報から読みやすいラベルを生成
- 長いリソースタイプ名の省略処理
- DOT形式向けのエスケープ処理
"""

import re
from typing import Dict


class NodeLabelGenerator:
    """リソースタイプに応じたラベル生成を担当"""

    @staticmethod
    def create_readable_label(urn_info: Dict[str, str]) -> str:
        """URN情報から読みやすいラベルを生成

        Args:
            urn_info: parse_urn() の戻り値形式の辞書

        Returns:
            改行区切りのラベル文字列（モジュール名\\nリソースタイプ\\nリソース名）

        Examples:
            >>> generator = NodeLabelGenerator()
            >>> urn_info = {'provider': 'aws', 'module': 'ec2', 'type': 'Instance', 'name': 'webserver'}
            >>> label = generator.create_readable_label(urn_info)
            >>> print(label)
            ec2\\nInstance\\nwebserver

            >>> urn_info = {'provider': 'kubernetes', 'module': '', 'type': 'Service', 'name': 'api-service'}
            >>> label = generator.create_readable_label(urn_info)
            >>> print(label)
            Service\\napi-service

        Notes:
            - モジュール名がない場合は省略される
            - 改行はDOT形式用に '\\n' としてエスケープされる
            - 空のurn_infoの場合はデフォルトラベルを返す
        """
        resource_type = urn_info.get('type', 'unknown')
        resource_name = urn_info.get('name', 'unknown')
        module = urn_info.get('module', '')

        # ラベルの構成要素を準備
        label_parts = []

        # 1. モジュール名があれば追加
        if module:
            label_parts.append(module)

        # 2. リソースタイプを処理
        readable_type = NodeLabelGenerator._format_resource_type(resource_type)
        label_parts.append(readable_type)

        # 3. リソース名（全体を表示）
        label_parts.append(resource_name)

        # 改行で結合（DOT形式では\\nとしてエスケープ）
        return '\\n'.join(label_parts)

    @staticmethod
    def _format_resource_type(resource_type: str) -> str:
        """リソースタイプを読みやすい形式にフォーマット

        Args:
            resource_type: リソースタイプ文字列

        Returns:
            フォーマット済みのリソースタイプ

        Examples:
            >>> NodeLabelGenerator._format_resource_type('Instance')
            'Instance'

            >>> NodeLabelGenerator._format_resource_type('VeryLongResourceTypeNameThatExceedsThirtyCharacters')
            'VeryLong...Characters'

            >>> NodeLabelGenerator._format_resource_type('ApplicationLoadBalancerTargetGroup')
            'ApplicationLoad...Group'

        Notes:
            - 30文字以下のタイプ名はそのまま返す
            - 30文字を超える場合、キャメルケースを単語に分割し省略
            - 主要な単語（先頭2語 + 末尾1語）のみを残す
        """
        # 早期リターン: 短いタイプ名はそのまま返す
        if len(resource_type) <= 30:
            return resource_type

        # キャメルケースを単語に分割
        words = re.findall(r'[A-Z][a-z]*', resource_type)

        # 主要な単語のみを残す
        if len(words) > 3:
            return f"{words[0]}{words[1]}...{words[-1]}"

        return resource_type
