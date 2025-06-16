"""!
変更履歴セクション処理モジュール

プロジェクトの変更履歴を記録するセクションを生成・更新します。
"""

import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from config import SectionType, DATE_FORMAT
from utils.logger import logger
from sections.base_section import BaseSection


class ChangelogSection(BaseSection):
    """!
    変更履歴セクションを処理するクラス
    
    PRごとの変更内容を時系列で記録する変更履歴を生成・更新します。
    """
    
    def __init__(self, openai_client, template_manager):
        super().__init__(SectionType.CHANGELOG, openai_client, template_manager)
    
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
            # 日付挿入など
            "current_date": datetime.now().strftime(DATE_FORMAT),
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
            logger.error("Changelog content is too short or empty")
            return False
        
        # 簡易的にテーブル存在チェック
        if '|' not in content:
            logger.warning("Changelog section may be missing table format")
        
        return True
