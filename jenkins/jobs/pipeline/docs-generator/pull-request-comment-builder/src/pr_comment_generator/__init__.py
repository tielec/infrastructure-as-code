# jenkins/jobs/pipeline/docs-generator/pull-request-comment-builder/src/pr_comment_generator/__init__.py
"""
PRコメント生成パッケージ

このパッケージは、Pull Requestのコメントを自動生成する機能を提供します。
互換性レイヤーとして、旧インポートパスをサポートします。

非推奨警告: 直接このパッケージからインポートすることは非推奨です。
新しいインポートパスを使用してください：
  from pr_comment_generator.generator import PRCommentGenerator
  from pr_comment_generator.models import PRInfo, FileChange
"""

import warnings

# 新しいモジュールから再エクスポート
from .models import PRInfo, FileChange
from .token_estimator import TokenEstimator
from .prompt_manager import PromptTemplateManager
from .statistics import PRCommentStatistics
from .formatter import CommentFormatter
from .openai_client import OpenAIClient
from .generator import PRCommentGenerator
from .chunk_analyzer import ChunkAnalyzer
from .cli import create_argument_parser, setup_environment_from_args, main

# 非推奨警告を表示
def _show_deprecation_warning():
    """非推奨警告を表示する"""
    warnings.warn(
        "直接 'from pr_comment_generator import ...' でインポートすることは非推奨です。\n"
        "新しいインポートパスを使用してください:\n"
        "  from pr_comment_generator.generator import PRCommentGenerator\n"
        "  from pr_comment_generator.openai_client import OpenAIClient\n"
        "  from pr_comment_generator.chunk_analyzer import ChunkAnalyzer\n"
        "  from pr_comment_generator.models import PRInfo, FileChange\n"
        "このメッセージは将来のバージョンで削除される予定です。",
        DeprecationWarning,
        stacklevel=3
    )

# 旧インポートパス使用時に警告を表示
_show_deprecation_warning()

# 公開するAPI
__all__ = [
    'PRInfo',
    'FileChange',
    'TokenEstimator',
    'PromptTemplateManager',
    'PRCommentStatistics',
    'CommentFormatter',
    'OpenAIClient',
    'PRCommentGenerator',
    'ChunkAnalyzer',
    'create_argument_parser',
    'setup_environment_from_args',
    'main',
]

# バージョン情報
__version__ = '2.0.0'
