"""!
アーキテクチャ図セクション処理モジュール

システムのコンポーネント構成やアーキテクチャを表す図と説明を生成・更新します。
"""

import re
from typing import Dict, Any, Optional
from config import SectionType, TemplateNames
from utils.logger import logger
from sections.base_section import BaseSection


class ArchitectureSection(BaseSection):
    """!
    アーキテクチャ図セクションを処理するクラス
    
    システムのコンポーネント関係図や全体構造を表すダイアグラムと説明を生成・更新します。
    """
    
    def __init__(self, openai_client, template_manager):
        super().__init__(SectionType.ARCHITECTURE, openai_client, template_manager)
    
    def _get_new_template_variables(
        self,
        pr_metadata: Dict[str, Any],
        pr_comment: str,
        previous_sections: Optional[Dict[SectionType, str]] = None
    ) -> Dict[str, Any]:
        """新規アーキテクチャ図セクション用の変数を準備"""
        variables = {
            "pr_number": pr_metadata.get("pr_number", ""),
            "pr_title": pr_metadata.get("pr_title", ""),
            "pr_url": pr_metadata.get("pr_url", ""),
            "pr_author": pr_metadata.get("pr_author", ""),
            "merged_at": pr_metadata.get("merged_at", ""),
            "pr_comment": pr_comment,
            "repository": f"{pr_metadata.get('repo_owner', '')}/{pr_metadata.get('repo_name', '')}",
        }
        # 他のセクション情報が必要なら適宜追加
        if previous_sections:
            variables["overview_content"] = previous_sections.get(SectionType.OVERVIEW, "")
            variables["glossary_content"] = previous_sections.get(SectionType.GLOSSARY, "")
        return variables

    def _get_update_template_variables(
        self,
        pr_metadata: Dict[str, Any],
        pr_comment: str,
        current_content: str,
        previous_sections: Optional[Dict[SectionType, str]] = None
    ) -> Dict[str, Any]:
        """既存アーキテクチャ図セクション更新用の変数を準備"""
        variables = self._get_new_template_variables(pr_metadata, pr_comment, previous_sections)
        variables["current_content"] = current_content
        return variables
    
    def validate(self, content: str) -> bool:
        """アーキテクチャ図セクションの最低限のバリデーション"""
        if not content or len(content.strip()) < 10:
            logger.error("Architecture content is too short or empty")
            return False
        
        # 少なくとも1つの mermaid ダイアグラムが含まれているかを確認
        if "```mermaid" not in content:
            logger.warning("Architecture section may be missing mermaid diagrams")
        
        return True
    
    def _extract_structured_info(
        self,
        previous_sections: Dict[SectionType, str]
    ) -> str:
        """
        前のセクション内容を元に、アーキテクチャ関連の構造化情報をAIで抽出。
        """
        logger.step("Extracting structured information for architecture section")
        try:
            # 入力データを準備
            input_data = {
                "overview": previous_sections.get(SectionType.OVERVIEW, ""),
                "directory_structure": previous_sections.get(SectionType.DIRECTORY_STRUCTURE, ""),
                "glossary": previous_sections.get(SectionType.GLOSSARY, ""),
                "dataflow": previous_sections.get(SectionType.DATAFLOW, ""),
            }
            
            # テンプレートを取得
            template = self.template_manager.get_extract_structure_template(input_data, "architecture")
            if not template["system_prompt"] or not template["user_prompt"]:
                logger.warning("Failed to prepare templates for architecture structure extraction")
                return ""
            
            # OpenAI APIを使用して構造化情報を抽出
            structured_info = self.openai_client.generate_content(
                system_prompt=template["system_prompt"],
                user_prompt=template["user_prompt"],
                operation_type="extract_structure",
                section_type="architecture"
            )
            
            return structured_info or ""
        except Exception as e:
            logger.error(f"Error extracting architecture structured information: {str(e)}")
            return ""
