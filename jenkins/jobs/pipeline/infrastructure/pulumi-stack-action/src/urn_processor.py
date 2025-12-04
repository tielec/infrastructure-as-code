"""
URN/URI processing for Pulumi resources

このモジュールはPulumi URN（Uniform Resource Name）の解析、正規化、
コンポーネント抽出の責務を担当します。

主要機能:
- URNパース: Pulumi URN形式の解析
- URI正規化: URN情報の正規化と整形
- コンポーネント抽出: プロバイダー、モジュール、タイプ、名前の抽出
- ラベル生成: 読みやすいラベルの生成
- リソース判定: スタックリソースの判定

依存関係:
- re: 正規表現処理
- typing: 型ヒント
"""

import re
from typing import Dict


class UrnProcessor:
    """URN（Uniform Resource Name）の解析、正規化、コンポーネント抽出を担当

    このクラスはPulumi URNの処理に特化しており、すべてのメソッドは
    静的メソッドとして実装されています（ステートレス設計）。

    URN形式: urn:pulumi:STACK::PROJECT::PROVIDER:MODULE/TYPE:TYPE::NAME

    例:
        >>> urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket"
        >>> urn_info = UrnProcessor.parse_urn(urn)
        >>> print(urn_info['provider'])  # 'aws'
        >>> print(urn_info['type'])      # 'Bucket'
    """

    @staticmethod
    def parse_urn(urn: str) -> Dict[str, str]:
        """URNをパースして構成要素を抽出

        Pulumi URN形式をパースして、スタック名、プロジェクト名、
        プロバイダー名、モジュール名、リソースタイプ、リソース名を抽出します。

        URN形式: urn:pulumi:STACK::PROJECT::PROVIDER:MODULE/TYPE:TYPE::NAME

        Args:
            urn (str): Pulumi URN文字列

        Returns:
            Dict[str, str]: URN構成要素を含む辞書
                - stack (str): スタック名（例: 'dev'）
                - project (str): プロジェクト名（例: 'myproject'）
                - provider (str): プロバイダー名（例: 'aws', 'azure', 'gcp'）
                - module (str): モジュール名（例: 's3', 'storage'）
                - type (str): リソースタイプ（例: 'Bucket'）
                - name (str): リソース名（例: 'my-bucket'）
                - full_urn (str): 完全なURN文字列

        Examples:
            >>> UrnProcessor.parse_urn("urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket")
            {
                'stack': 'dev',
                'project': 'myproject',
                'provider': 'aws',
                'module': 's3',
                'type': 'Bucket',
                'name': 'my-bucket',
                'full_urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'
            }

            >>> UrnProcessor.parse_urn("invalid-urn")
            {
                'stack': '',
                'project': '',
                'provider': 'unknown',
                'module': '',
                'type': 'unknown',
                'name': 'invalid-urn',
                'full_urn': 'invalid-urn'
            }

        Note:
            不正なURN形式の場合でも例外を投げず、デフォルト値を返します。
            これはPulumi生成データに不正なURNが含まれる可能性があるためです。
        """
        # デフォルト値を設定（不正なURNに対する安全網）
        default_result = {
            'stack': '',
            'project': '',
            'provider': 'unknown',
            'module': '',
            'type': 'unknown',
            'name': urn.split('::')[-1] if '::' in urn else urn,
            'full_urn': urn
        }

        # URNを'::'で分割
        parts = urn.split('::')
        if len(parts) < 4:
            # URN形式が不正な場合、デフォルト値を返す
            return default_result

        # 基本情報を抽出
        result = {
            'stack': parts[0].replace('urn:pulumi:', '') if parts else '',
            'project': parts[1] if len(parts) > 1 else '',
            'name': parts[-1] if parts else 'unknown',
            'full_urn': urn
        }

        # プロバイダーとタイプを解析
        provider_type = parts[2] if len(parts) > 2 else ''
        provider_info = UrnProcessor._parse_provider_type(provider_type)
        result.update(provider_info)

        return result

    @staticmethod
    def _parse_provider_type(provider_type: str) -> Dict[str, str]:
        """プロバイダータイプ文字列を解析

        プロバイダータイプ文字列（例: aws:s3/bucket:Bucket）を解析し、
        プロバイダー名、モジュール名、リソースタイプを抽出します。

        Args:
            provider_type (str): プロバイダータイプ文字列
                例: "aws:s3/bucket:Bucket"
                例: "kubernetes:apps/v1:Deployment"
                例: "pulumi:Stack"（モジュールなし）

        Returns:
            Dict[str, str]: プロバイダー情報を含む辞書
                - provider (str): プロバイダー名（例: 'aws'）
                - module (str): モジュール名（例: 's3'）
                - type (str): リソースタイプ（例: 'Bucket'）

        Note:
            内部ヘルパーメソッド（private）。
            コロンが含まれない場合やモジュールがない場合も安全に処理します。
        """
        # 不正な入力に対するデフォルト値
        if not provider_type or ':' not in provider_type:
            return {
                'provider': 'unknown',
                'module': '',
                'type': provider_type or 'unknown'
            }

        # プロバイダータイプを':'で分割
        provider_parts = provider_type.split(':')
        provider = provider_parts[0]

        # モジュールとタイプを抽出
        module = ''
        if len(provider_parts) > 1 and '/' in provider_parts[1]:
            module_and_type = provider_parts[1]
            module = module_and_type.split('/')[0]

        # タイプ名は最後の':'以降
        resource_type = provider_parts[-1] if len(provider_parts) > 1 else 'unknown'

        return {
            'provider': provider,
            'module': module,
            'type': resource_type
        }

    @staticmethod
    def create_readable_label(urn_info: Dict[str, str]) -> str:
        """URN情報から読みやすいラベルを生成

        URN情報辞書から、DOTグラフ用の読みやすいラベル文字列を生成します。
        ラベルは改行区切り（\\n）で、モジュール名、リソースタイプ、
        リソース名を含みます。

        Args:
            urn_info (Dict[str, str]): URN情報辞書（parse_urn()の戻り値）
                必須キー: 'type', 'name'
                オプションキー: 'module'

        Returns:
            str: 改行区切り（\\n）のラベル文字列

        Examples:
            >>> urn_info = {
            ...     'provider': 'aws',
            ...     'module': 's3',
            ...     'type': 'Bucket',
            ...     'name': 'my-bucket'
            ... }
            >>> UrnProcessor.create_readable_label(urn_info)
            's3\\nBucket\\nmy-bucket'

            >>> urn_info = {
            ...     'provider': 'pulumi',
            ...     'module': '',
            ...     'type': 'Stack',
            ...     'name': 'dev'
            ... }
            >>> UrnProcessor.create_readable_label(urn_info)
            'Stack\\ndev'

        Note:
            - モジュール名がある場合は含めます
            - 長いタイプ名は省略されます（_format_resource_type()を使用）
            - リソース名は全体を表示します
        """
        resource_type = urn_info['type']
        resource_name = urn_info['name']
        module = urn_info.get('module', '')

        # ラベルの構成要素を準備
        label_parts = []

        # 1. モジュール名があれば追加
        if module:
            label_parts.append(module)

        # 2. リソースタイプを処理（長い場合は省略）
        readable_type = UrnProcessor._format_resource_type(resource_type)
        label_parts.append(readable_type)

        # 3. リソース名（全体を表示）
        label_parts.append(resource_name)

        # 改行で結合
        return '\\n'.join(label_parts)

    @staticmethod
    def _format_resource_type(resource_type: str) -> str:
        """リソースタイプを読みやすい形式にフォーマット

        リソースタイプ名が長い場合（30文字以上）、キャメルケースを
        考慮して省略形式に変換します。

        Args:
            resource_type (str): リソースタイプ文字列

        Returns:
            str: フォーマット済みのタイプ名

        Examples:
            >>> UrnProcessor._format_resource_type("Bucket")
            'Bucket'

            >>> UrnProcessor._format_resource_type("VeryLongResourceTypeNameThatExceeds30Characters")
            'VeryLong...Characters'

        Note:
            - 30文字以下の場合はそのまま返します
            - 30文字以上の場合は省略します（例: VeryLongType...Name）
            - キャメルケースを単語に分割して省略します
        """
        # 短いタイプ名はそのまま返す
        if len(resource_type) <= 30:
            return resource_type

        # キャメルケースを単語に分割
        words = re.findall(r'[A-Z][a-z]*', resource_type)

        # 主要な単語のみを残す（先頭2単語 + 末尾1単語）
        if len(words) > 3:
            return f"{words[0]}{words[1]}...{words[-1]}"
        else:
            # 単語が3個以下の場合はそのまま返す
            return resource_type

    @staticmethod
    def is_stack_resource(urn: str) -> bool:
        """スタックリソースかどうかを判定

        URN文字列がPulumiスタックリソースを表しているかを判定します。

        Args:
            urn (str): Pulumi URN文字列

        Returns:
            bool: スタックリソースの場合True、それ以外はFalse

        Examples:
            >>> UrnProcessor.is_stack_resource("urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev")
            True

            >>> UrnProcessor.is_stack_resource("urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket")
            False

            >>> UrnProcessor.is_stack_resource("invalid-urn")
            False

        Note:
            判定条件: URNに'pulumi:pulumi:Stack'を含むか
            不正なURNに対しても安全にFalseを返します。
        """
        return 'pulumi:pulumi:Stack' in urn
