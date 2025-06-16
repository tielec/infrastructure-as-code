"""!
用語集セクション処理モジュール

プロジェクト固有の専門用語と定義を集めた用語集セクションを生成・更新します。
"""

import re
from typing import Dict, Any, Optional, List, Tuple

from config import SectionType
from utils.logger import logger
from sections.base_section import BaseSection


class GlossarySection(BaseSection):
    """!
    用語集セクションを処理するクラス
    
    プロジェクト固有の専門用語と定義のリストを生成・更新します。
    """
    
    def __init__(self, openai_client, template_manager):
        super().__init__(SectionType.GLOSSARY, openai_client, template_manager)
    
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
            logger.error("Glossary content is too short or empty")
            return False
        
        # 用語定義らしき行があるか簡易チェック
        if '**:' not in content and '|' not in content:
            logger.warning("Glossary content may be missing term definitions or table")
        
        return True
