"""!
ディレクトリ構造セクション処理モジュール

プロジェクトのフォルダ構成とファイル説明に関するセクションを生成・更新します。
"""

import re
from typing import Dict, Any, Optional, List

from config import SectionType
from utils.logger import logger
from sections.base_section import BaseSection


class DirectoryStructureSection(BaseSection):
    """!
    ディレクトリ構造セクションを処理するクラス
    
    プロジェクトのフォルダ構成、ファイル階層、各コンポーネントの役割説明を生成・更新します。
    """
    
    def __init__(self, openai_client, template_manager):
        super().__init__(SectionType.DIRECTORY_STRUCTURE, openai_client, template_manager)
    
    def _get_new_template_variables(
        self,
        pr_metadata: Dict[str, Any],
        pr_comment: str,
        previous_sections: Optional[Dict[SectionType, str]] = None
    ) -> Dict[str, Any]:
        variables = {
            "pr_number": pr_metadata.get("pr_number", ""),
            "pr_title": pr_metadata.get("pr_title", ""),
            "pr_url": pr_metadata.get("pr_url", ""),
            "pr_author": pr_metadata.get("pr_author", ""),
            "merged_at": pr_metadata.get("merged_at", ""),
            "pr_comment": pr_comment,
            "repository": f"{pr_metadata.get('repo_owner', '')}/{pr_metadata.get('repo_name', '')}",
        }
        return variables

    def _get_update_template_variables(
        self,
        pr_metadata: Dict[str, Any],
        pr_comment: str,
        current_content: str,
        previous_sections: Optional[Dict[SectionType, str]] = None
    ) -> Dict[str, Any]:
        variables = self._get_new_template_variables(pr_metadata, pr_comment, previous_sections)
        variables["current_content"] = current_content
        return variables
    
    def validate(self, content: str) -> bool:
        if not content or len(content.strip()) < 10:
            logger.error("Directory structure content is too short or empty")
            return False
        
        # ディレクトリ構造の可視化(ツリーなど)が含まれるか簡易チェック
        if not re.search(r'[│├└]', content) and '```' not in content:
            logger.warning("Directory structure may be missing tree or code blocks")
        
        return True
