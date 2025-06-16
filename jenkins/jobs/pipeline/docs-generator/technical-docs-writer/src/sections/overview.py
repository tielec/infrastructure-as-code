"""!
概要セクション処理モジュール

システムの目的や主要機能に関する概要セクションを生成・更新します。
"""

from typing import Dict, Any, Optional, List

from config import SectionType
from utils.logger import logger
from sections.base_section import BaseSection


class OverviewSection(BaseSection):
    """!
    システム概要セクションを処理するクラス
    
    システムの目的、主要機能、背景などを含む概要セクションを生成・更新します。
    """
    
    def __init__(self, openai_client, template_manager):
        super().__init__(SectionType.OVERVIEW, openai_client, template_manager)
    
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
        # 必要に応じて previous_sections から情報を取得
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
            logger.error("Overview content is too short or empty")
            return False
        
        # 見出しとパラグラフがあるか簡易チェック
        if "#" not in content:
            logger.warning("Overview content may be missing headings")
        
        return True
