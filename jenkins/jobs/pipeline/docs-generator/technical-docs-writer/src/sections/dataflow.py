"""!
データフロー図セクション処理モジュール

システム内のデータの流れや処理フローを図と説明で生成・更新します。
"""

import re
from typing import Dict, Any, Optional
from config import SectionType
from utils.logger import logger
from sections.base_section import BaseSection


class DataflowSection(BaseSection):
    """!
    データフロー図セクションを処理するクラス
    
    システム内のデータの流れやプロセスフローを表すダイアグラムと説明を生成・更新します。
    """
    
    def __init__(self, openai_client, template_manager):
        super().__init__(SectionType.DATAFLOW, openai_client, template_manager)
    
    def _get_new_template_variables(
        self,
        pr_metadata: Dict[str, Any],
        pr_comment: str,
        previous_sections: Optional[Dict[SectionType, str]] = None
    ) -> Dict[str, Any]:
        """新規データフロー図セクション用の変数を準備"""
        variables = {
            "pr_number": pr_metadata.get("pr_number", ""),
            "pr_title": pr_metadata.get("pr_title", ""),
            "pr_url": pr_metadata.get("pr_url", ""),
            "pr_author": pr_metadata.get("pr_author", ""),
            "merged_at": pr_metadata.get("merged_at", ""),
            "pr_comment": pr_comment,
            "repository": f"{pr_metadata.get('repo_owner', '')}/{pr_metadata.get('repo_name', '')}",
        }
        # 前のセクション情報
        if previous_sections:
            variables["overview_content"] = previous_sections.get(SectionType.OVERVIEW, "")
            variables["architecture_content"] = previous_sections.get(SectionType.ARCHITECTURE, "")
        return variables

    def _get_update_template_variables(
        self,
        pr_metadata: Dict[str, Any],
        pr_comment: str,
        current_content: str,
        previous_sections: Optional[Dict[SectionType, str]] = None
    ) -> Dict[str, Any]:
        """既存データフロー図セクション更新用の変数を準備"""
        variables = self._get_new_template_variables(pr_metadata, pr_comment, previous_sections)
        variables["current_content"] = current_content
        return variables
    
    def validate(self, content: str) -> bool:
        """データフロー図セクションの最低限のバリデーション"""
        if not content or len(content.strip()) < 10:
            logger.error("Dataflow content is too short or empty")
            return False
        
        # データフローには mermaid や sequenceDiagram, flowchart などが含まれるかチェック
        if "```mermaid" not in content:
            logger.warning("Dataflow section may be missing diagrams")
        
        return True
    
    def _extract_structured_info(
        self,
        previous_sections: Dict[SectionType, str]
    ) -> str:
        """
        前のセクション内容からデータフローに必要な構造化情報を抽出。
        """
        logger.step("Extracting structured information for dataflow section")
        try:
            # 入力データを準備
            input_data = {
                "overview": previous_sections.get(SectionType.OVERVIEW, ""),
                "directory_structure": previous_sections.get(SectionType.DIRECTORY_STRUCTURE, ""),
                "glossary": previous_sections.get(SectionType.GLOSSARY, ""),
                "architecture": previous_sections.get(SectionType.ARCHITECTURE, "")
            }
            
            # テンプレートを取得
            template = self.template_manager.get_extract_structure_template(input_data, "dataflow")
            if not template["system_prompt"] or not template["user_prompt"]:
                logger.warning("Failed to prepare templates for dataflow structure extraction")
                return ""
            
            # OpenAI APIを使用して構造化情報を抽出
            structured_info = self.openai_client.generate_content(
                template["system_prompt"],
                template["user_prompt"],
                operation_type="extract_structure",
                section_type="dataflow"
            )
            
            return structured_info or ""
        except Exception as e:
            logger.error(f"Error extracting dataflow structured information: {str(e)}")
            return ""
