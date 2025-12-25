"""PRコメントジェネレーターのエントリポイント兼互換性レイヤー。"""
import os
import sys
import warnings

# このモジュールをパッケージとして扱い、サブモジュールを利用できるようにする
__path__ = [os.path.join(os.path.dirname(__file__), 'pr_comment_generator')]
__package__ = 'pr_comment_generator'
sys.modules.setdefault('pr_comment_generator', sys.modules[__name__])

from pr_comment_generator.cli import create_argument_parser, setup_environment_from_args, main  # noqa: E402
from pr_comment_generator.generator import PRCommentGenerator  # noqa: E402
from pr_comment_generator.openai_client import OpenAIClient  # noqa: E402
from pr_comment_generator.chunk_analyzer import ChunkAnalyzer  # noqa: E402
from pr_comment_generator.models import PRInfo, FileChange  # noqa: E402
from pr_comment_generator.token_estimator import TokenEstimator  # noqa: E402
from pr_comment_generator.prompt_manager import PromptTemplateManager  # noqa: E402
from pr_comment_generator.statistics import PRCommentStatistics  # noqa: E402
from pr_comment_generator.formatter import CommentFormatter  # noqa: E402

warnings.warn(
    "直接 'from pr_comment_generator import ...' でインポートすることは非推奨です。\n"
    "新しいインポートパスを使用してください:\n"
    "  from pr_comment_generator.generator import PRCommentGenerator\n"
    "  from pr_comment_generator.models import PRInfo, FileChange\n"
    "このメッセージは将来のバージョンで削除される予定です。",
    DeprecationWarning,
    stacklevel=3,
)

__all__ = [
    'PRInfo',
    'FileChange',
    'TokenEstimator',
    'PromptTemplateManager',
    'PRCommentStatistics',
    'CommentFormatter',
    'PRCommentGenerator',
    'OpenAIClient',
    'ChunkAnalyzer',
    'create_argument_parser',
    'setup_environment_from_args',
    'main',
]

if __name__ == '__main__':
    main()
