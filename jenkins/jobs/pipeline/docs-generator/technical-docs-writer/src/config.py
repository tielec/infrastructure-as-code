"""!
設定と定数の管理モジュール

システム全体で使用される設定値、定数、列挙型を定義します。
"""

import os
import enum
from typing import Dict, List, Set, Optional


class SectionType(enum.Enum):
    """ドキュメントセクションの種類を定義する列挙型"""
    OVERVIEW = "overview"
    DIRECTORY_STRUCTURE = "directory_structure"
    ARCHITECTURE = "architecture"
    DATAFLOW = "dataflow"
    GLOSSARY = "glossary"
    CHANGELOG = "changelog"
    
    @classmethod
    def from_string(cls, section_name: str) -> 'SectionType':
        """文字列からセクションタイプを取得"""
        try:
            # 大文字小文字を区別せず処理するために小文字に変換
            section_name = section_name.lower()
            return cls(section_name)
        except ValueError:
            raise ValueError(f"Unknown section type: {section_name}")
        
    @classmethod
    def all_names(cls) -> List[str]:
        """全セクション名のリストを取得"""
        return [section.value for section in cls]
    
    @classmethod
    def all_types(cls) -> List['SectionType']:
        """全セクションタイプのリストを取得"""
        return [section for section in cls]

# テンプレートファイル名の定義
class TemplateNames:
    """テンプレートファイル名の定数"""
    NEW = "new.txt"
    UPDATE = "update.txt"
    SECTION_ANALYSIS = "section_analysis.txt"
    MERGE_TEMPLATE = "merge_template.txt"
    SYSTEM_PROMPT = "system_prompt.txt"
    EXTRACT_ARCHITECTURE = "extract_architecture_structure.txt"
    EXTRACT_DATAFLOW = "extract_dataflow_structure.txt"
    REFLECTION_SYSTEM_PROMPT = "reflection_system_prompt.txt"  # 従来の自己対話システムプロンプト
    
    # 自己対話プロセス用の共通ガイドライン
    REFLECTION_COMMON = "reflection_common_guidelines.txt"
    
    # 段階別プロンプト - 共通
    REFLECTION_PLANNING = "reflection_planning_prompt.txt"
    REFLECTION_DIALOG = "reflection_dialog_prompt.txt"
    REFLECTION_FINAL = "reflection_final_prompt.txt"
    
    # 段階別プロンプト - セクション別（新規作成）
    NEW_PLANNING = "new_planning.txt" 
    NEW_DIALOG = "new_dialog.txt"
    NEW_FINAL = "new_final.txt"
    
    # 段階別プロンプト - セクション別（更新）
    UPDATE_PLANNING = "update_planning.txt"
    UPDATE_DIALOG = "update_dialog.txt"
    UPDATE_FINAL = "update_final.txt"

# ドキュメント生成順序（依存関係を考慮した順序）
DOCUMENT_GENERATION_ORDER = [
    SectionType.OVERVIEW,
    SectionType.DIRECTORY_STRUCTURE,
    SectionType.GLOSSARY,
    SectionType.DATAFLOW,
    SectionType.ARCHITECTURE,
    SectionType.CHANGELOG
]

# セクション処理の順序
SECTION_ORDER: List[SectionType] = [
    SectionType.OVERVIEW,
    SectionType.DIRECTORY_STRUCTURE,
    SectionType.ARCHITECTURE,
    SectionType.DATAFLOW, 
    SectionType.GLOSSARY,
    SectionType.CHANGELOG
]


# セクション見出しの定義
SECTION_HEADINGS: Dict[SectionType, str] = {
    SectionType.OVERVIEW: "概要",
    SectionType.DIRECTORY_STRUCTURE: "ディレクトリ構造",
    SectionType.ARCHITECTURE: "システムアーキテクチャ図",
    SectionType.DATAFLOW: "データフロー図",
    SectionType.GLOSSARY: "用語集",
    SectionType.CHANGELOG: "変更履歴"
}


# ファイル名の接尾辞
class FileExtensions:
    """ファイル拡張子の定数"""
    MARKDOWN = ".md"
    TEXT = ".txt"
    JSON = ".json"


# デフォルト設定値
DEFAULT_CONFIG = {
    "openai_model": "gpt-4o-mini",
    "api_version": "2024-02-15-preview",
    "temperature": 0.1,
    "max_tokens": 10000,
    "log_level": "INFO",
    
    # 自己対話機能の設定
    "use_reflection": True,                            # 自己対話機能を有効化するかどうか
    "reflection_sections": ["dataflow", "architecture"], # 自己対話を適用するセクション（デフォルトではデータフローとアーキテクチャ）
    "save_reflection_process": False,                  # 自己対話プロセスの詳細を保存するかどうか
    "reflection_temperature": 0.2,                     # 自己対話用の温度設定（通常よりやや高め）
    "reflection_log_level": "INFO"                     # 自己対話ログのレベル設定
}


# 日付フォーマット
DATE_FORMAT = "%Y/%m/%d"
DATETIME_FORMAT = "%Y/%m/%d %H:%M:%S"


# ログ設定
LOG_FORMAT = "%(asctime)s - [%(levelname)s] - %(message)s"


def get_template_path(section: SectionType, template_name: str, base_dir: str) -> str:
    """
    セクションとテンプレート名からテンプレートファイルのパスを取得
    
    Args:
        section: セクションタイプ
        template_name: テンプレートファイル名
        base_dir: テンプレートベースディレクトリ
        
    Returns:
        テンプレートファイルの絶対パス
    """
    if section:
        return os.path.join(base_dir, section.value, template_name)
    return os.path.join(base_dir, "common", template_name)


def get_common_template_path(template_name: str, base_dir: str) -> str:
    """
    共通テンプレートファイルのパスを取得
    
    Args:
        template_name: テンプレートファイル名
        base_dir: テンプレートベースディレクトリ
        
    Returns:
        テンプレートファイルの絶対パス
    """
    return os.path.join(base_dir, "common", template_name)
