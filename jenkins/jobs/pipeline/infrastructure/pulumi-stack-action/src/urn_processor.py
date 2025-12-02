"""
URN/URI processing for Pulumi resources

このモジュールは、Pulumi URN（Uniform Resource Name）のパース、正規化、
コンポーネント抽出の責務を担当します。

主要な機能:
- URN文字列のパースと構成要素の抽出
- プロバイダータイプの解析
- 不正なURN形式の安全な処理（例外をスローせずデフォルト値を返す）
"""

from typing import Dict


class UrnProcessor:
    """URN/URI のパース、正規化、コンポーネント抽出を担当"""

    @staticmethod
    def parse_urn(urn: str) -> Dict[str, str]:
        """URNをパースして構成要素を抽出

        URN形式: urn:pulumi:STACK::PROJECT::PROVIDER:MODULE/TYPE:TYPE::NAME

        Args:
            urn: Pulumi URN文字列

        Returns:
            URN構成要素の辞書
            {
                'stack': str,        # スタック名
                'project': str,      # プロジェクト名
                'provider': str,     # プロバイダー名（aws, gcp等）
                'module': str,       # モジュール名（ec2, s3等）
                'type': str,         # リソースタイプ（Instance, Bucket等）
                'name': str,         # リソース名
                'full_urn': str      # 元のURN文字列
            }

        Examples:
            >>> processor = UrnProcessor()
            >>> result = processor.parse_urn('urn:pulumi:dev::myproject::aws:ec2/instance:Instance::webserver')
            >>> result['stack']
            'dev'
            >>> result['provider']
            'aws'
            >>> result['name']
            'webserver'

        Notes:
            - 不正なURN形式の場合も例外をスローせず、デフォルト値を含む辞書を返す
            - 空文字列やNoneが入力された場合も安全に処理される
        """
        # デフォルト値を設定
        default_result = {
            'stack': '',
            'project': '',
            'provider': 'unknown',
            'module': '',
            'type': 'unknown',
            'name': urn.split('::')[-1] if urn and '::' in urn else (urn or ''),
            'full_urn': urn if urn is not None else ''
        }

        # 早期リターン: URN形式でない場合
        if not urn or '::' not in urn:
            return default_result

        parts = urn.split('::')
        if len(parts) < 4:
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

        Args:
            provider_type: プロバイダータイプ文字列（例: aws:ec2/instance:Instance）

        Returns:
            プロバイダー情報の辞書 {'provider': str, 'module': str, 'type': str}

        Examples:
            >>> UrnProcessor._parse_provider_type('aws:ec2/instance:Instance')
            {'provider': 'aws', 'module': 'ec2', 'type': 'Instance'}

            >>> UrnProcessor._parse_provider_type('kubernetes:Service')
            {'provider': 'kubernetes', 'module': '', 'type': 'Service'}

        Notes:
            - 不正な形式の場合もデフォルト値を返す（例外をスローしない）
            - モジュール名がない場合は空文字列を返す
        """
        # 早期リターン: 不正な形式
        if not provider_type or ':' not in provider_type:
            return {
                'provider': 'unknown',
                'module': '',
                'type': provider_type or 'unknown'
            }

        provider_parts = provider_type.split(':')
        provider = provider_parts[0]

        # モジュールとタイプを抽出
        module = ''
        if len(provider_parts) > 1 and '/' in provider_parts[1]:
            module_and_type = provider_parts[1]
            module = module_and_type.split('/')[0]

        # タイプ名は最後の:以降
        resource_type = provider_parts[-1] if len(provider_parts) > 1 else 'unknown'

        return {
            'provider': provider,
            'module': module,
            'type': resource_type
        }
