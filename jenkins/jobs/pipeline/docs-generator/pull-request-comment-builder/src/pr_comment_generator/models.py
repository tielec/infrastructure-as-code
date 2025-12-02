# jenkins/jobs/pipeline/docs-generator/pull-request-comment-builder/src/pr_comment_generator/models.py
"""
データモデル定義

このモジュールは、PRコメント生成に使用するデータクラスを定義します。

主要なクラス:
- PRInfo: PRの基本情報を保持するデータクラス
- FileChange: ファイルの変更内容を保持するデータクラス
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PRInfo:
    """PRの基本情報を保持するデータクラス"""
    title: str
    number: int
    body: Optional[str]
    author: str
    base_branch: str
    head_branch: str
    base_sha: str
    head_sha: str

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'PRInfo':
        """JSONデータからPRInfoを作成する

        Args:
            data: PR情報を含むJSON辞書

        Returns:
            PRInfo: 生成されたPRInfoインスタンス
        """
        return cls(
            title=data.get('title', ''),
            number=data.get('number', 0),
            body=data.get('body') or '',
            author=data.get('user', {}).get('login', ''),
            base_branch=data.get('base', {}).get('ref', ''),
            head_branch=data.get('head', {}).get('ref', ''),
            base_sha=data.get('base', {}).get('sha', ''),
            head_sha=data.get('head', {}).get('sha', '')
        )


@dataclass
class FileChange:
    """ファイルの変更内容を保持するデータクラス"""
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: Optional[str] = None
    content_before: Optional[str] = None  # 変更前のファイル内容
    content_after: Optional[str] = None   # 変更後のファイル内容
    context_diff: Optional[Dict[str, Any]] = field(default_factory=dict)  # 変更箇所の前後のコンテキスト

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'FileChange':
        """JSONデータからFileChangeを作成する

        Args:
            data: ファイル変更情報を含むJSON辞書

        Returns:
            FileChange: 生成されたFileChangeインスタンス
        """
        return cls(
            filename=data.get('filename', ''),
            status=data.get('status', ''),
            additions=data.get('additions', 0),
            deletions=data.get('deletions', 0),
            changes=data.get('changes', 0),
            patch=data.get('patch')
        )
