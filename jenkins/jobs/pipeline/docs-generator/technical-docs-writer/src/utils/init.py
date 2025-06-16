"""!
ユーティリティパッケージ

ファイル操作、ロギング、Markdown処理などの共通機能を提供します。
"""

from .logger import logger, setup_logging
from .file_utils import (
    read_file, write_file, read_json, write_json, 
    ensure_directory, file_exists, get_files_in_directory
)
from .markdown_utils import (
    merge_markdown_documents, adjust_heading_levels, 
    inject_toc, replace_mermaid_diagrams
)

__all__ = [
    'logger', 'setup_logging',
    'read_file', 'write_file', 'read_json', 'write_json',
    'ensure_directory', 'file_exists', 'get_files_in_directory',
    'merge_markdown_documents', 'adjust_heading_levels',
    'inject_toc', 'replace_mermaid_diagrams'
]
