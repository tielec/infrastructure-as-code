"""!
セクション基底クラスモジュール

ドキュメントの各セクションを扱うための抽象基底クラスを提供します。
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from config import SectionType
from utils.logger import logger
from utils.file_utils import read_file, write_file, file_exists
from utils.markdown_utils import replace_mermaid_diagrams
from utils.mermaid_helper import MermaidHelper
from api.openai_client import OpenAIClient
from templates.template_manager import TemplateManager


class BaseSection(ABC):
    """!
    ドキュメントセクションの抽象基底クラス
    
    すべてのセクションタイプのクラスはこのクラスを継承します。
    セクションの生成、更新、検証の共通インターフェースを定義します。
    """
    
    def __init__(self, section_type: SectionType, openai_client: OpenAIClient, 
                template_manager: TemplateManager):
        """!
        BaseSection初期化
        
        Args:
            section_type: セクションタイプ
            openai_client: OpenAI APIクライアント
            template_manager: テンプレート管理クラス
        """
        self.section_type = section_type
        self.openai_client = openai_client
        self.template_manager = template_manager
        
        logger.debug(f"Initialized {self.section_type.value} section handler")
    
    @abstractmethod
    def _get_new_template_variables(
        self,
        pr_metadata: Dict[str, Any],
        pr_comment: str,
        previous_sections: Optional[Dict[SectionType, str]] = None
    ) -> Dict[str, Any]:
        """
        新規セクション生成時に必要なテンプレート用変数を準備する。
        セクション固有のロジックを各サブクラスで実装。
        """
        pass
    
    @abstractmethod
    def _get_update_template_variables(
        self,
        pr_metadata: Dict[str, Any],
        pr_comment: str,
        current_content: str,
        previous_sections: Optional[Dict[SectionType, str]] = None
    ) -> Dict[str, Any]:
        """
        既存セクション更新時に必要なテンプレート用変数を準備する。
        セクション固有のロジックを各サブクラスで実装。
        """
        pass
    
    @abstractmethod
    def validate(self, content: str) -> bool:
        """!
        セクション内容を検証する。
        セクションごとに必須要件が異なるため、各サブクラスで実装。
        """
        pass

    def create_section(
        self,
        pr_metadata: Dict[str, Any],
        pr_comment: str,
        output_file: str,
        changed_files: Optional[List[Dict[str, Any]]] = None,
        previous_sections: Optional[Dict[SectionType, str]] = None,
        use_reflection: bool = False
    ) -> bool:
        """!
        新規セクションを作成する（Reflection利用の有無はフラグで分岐）
        """
        logger.start_group(f"Creating new {self.section_type.value} section (reflection={use_reflection})")
        try:
            # テンプレート変数の作成（セクション固有）
            variables = self._get_new_template_variables(pr_metadata, pr_comment, previous_sections)
            
            # 例：構造化情報抽出が必要な場合、サブクラス側で _extract_structured_info を実装している
            structured_info = self._extract_structured_info(previous_sections) if previous_sections else ""
            if structured_info:
                variables["structured_info"] = structured_info
            
            # 変更ファイル情報があれば共通で分析
            if changed_files:
                variables["changed_files"] = self._analyze_changed_files(changed_files)
            else:
                variables["changed_files"] = "変更ファイル情報は提供されていません。"
            
            # コンテンツ生成
            content = (
                self._generate_content_with_reflection(variables, operation_type="new")
                if use_reflection else
                self._generate_content(variables, operation_type="new")
            )
            
            # mermaid ダイアグラムの置換など共通後処理
            content = replace_mermaid_diagrams(content)
            
            # 保存
            return self.save_content(content, output_file)
        except Exception as e:
            logger.error(f"Error creating {self.section_type.value} section: {str(e)}")
            return False
        finally:
            logger.end_group()
    
    def update_section(
        self,
        pr_metadata: Dict[str, Any],
        pr_comment: str,
        current_file: str,
        output_file: str,
        changed_files: Optional[List[Dict[str, Any]]] = None,
        previous_sections: Optional[Dict[SectionType, str]] = None,
        use_reflection: bool = False
    ) -> bool:
        """!
        既存セクションを更新する（Reflection利用の有無はフラグで分岐）
        """
        logger.start_group(f"Updating {self.section_type.value} section (reflection={use_reflection})")
        try:
            current_content = self.get_current_content(current_file)
            if current_content is None:
                # ファイルが存在しない場合は新規作成扱い
                logger.warning("Current content not found. Switching to create_section.")
                return self.create_section(
                    pr_metadata, pr_comment, output_file,
                    changed_files, previous_sections,
                    use_reflection
                )
            
            # テンプレート変数の作成（セクション固有）
            variables = self._get_update_template_variables(pr_metadata, pr_comment, current_content, previous_sections)
            
            # 構造化情報抽出（必要なら）
            structured_info = self._extract_structured_info(previous_sections) if previous_sections else ""
            if structured_info:
                variables["structured_info"] = structured_info
            
            # 変更ファイル情報があれば共通で分析
            if changed_files:
                variables["changed_files"] = self._analyze_changed_files(changed_files)
            else:
                variables["changed_files"] = "変更ファイル情報は提供されていません。"
            
            # コンテンツ生成
            content = (
                self._generate_content_with_reflection(variables, operation_type="update")
                if use_reflection else
                self._generate_content(variables, operation_type="update")
            )
            
            # mermaid ダイアグラムの置換など共通後処理
            content = replace_mermaid_diagrams(content)
            
            # 保存
            return self.save_content(content, output_file)
        except Exception as e:
            logger.error(f"Error updating {self.section_type.value} section: {str(e)}")
            return False
        finally:
            logger.end_group()
    
    def get_current_content(self, file_path: str) -> Optional[str]:
        """
        現在のセクション内容を取得。
        ファイルがなければ None を返す。
        """
        if not file_exists(file_path):
            logger.info(f"Current {self.section_type.value} section file does not exist: {file_path}")
            return None
        
        content = read_file(file_path)
        if content is None:
            logger.error(f"Failed to read {self.section_type.value} section file: {file_path}")
            return None
        return content
    
    def save_content(self, content: str, output_file: str) -> bool:
        """
        セクション内容をファイルに保存する前に validate を実行。
        Mermaidダイアグラムを含むセクションの場合は検証・修正も行います。
        """
        # バリデーション
        if not self.validate(content):
            logger.error(f"Invalid {self.section_type.value} section content. Output not saved.")
            return False
        
        # ファイル出力
        if not write_file(output_file, content):
            logger.error(f"Failed to write {self.section_type.value} section to: {output_file}")
            return False
        
        logger.info(f"Successfully saved {self.section_type.value} section to: {output_file}")
        
        # Mermaidダイアグラムを検証・修正（アーキテクチャやデータフローセクションのみ）
        if self.section_type in [SectionType.ARCHITECTURE, SectionType.DATAFLOW]:
            try:
                mermaid_helper = MermaidHelper(self.openai_client)
                result = mermaid_helper.process_section_file(output_file)
                if result:
                    logger.info(f"Mermaid diagrams validated and fixed in {self.section_type.value} section")
                else:
                    logger.warning(f"Some Mermaid diagrams could not be validated in {self.section_type.value} section")
            except Exception as e:
                logger.warning(f"Failed to validate Mermaid diagrams in {self.section_type.value} section: {str(e)}")
        
        return True
    
    def _generate_content(self, variables: Dict[str, Any], operation_type: str) -> str:
        """
        Reflection を使わずにコンテンツ生成する共通メソッド。
        """
        # operation_type が "new" か "update" かでテンプレートを切り替え
        if operation_type == "new":
            template = self.template_manager.get_new_section_template(self.section_type, variables)
        else:
            template = self.template_manager.get_update_section_template(self.section_type, variables)
        
        if not template["system_prompt"] or not template["user_prompt"]:
            logger.error(f"Failed to prepare templates for {operation_type} {self.section_type.value} section")
            return ""
        
        # OpenAI API呼び出し
        content = self.openai_client.generate_content(
            system_prompt=template["system_prompt"],
            user_prompt=template["user_prompt"],
            operation_type=operation_type,
            section_type=self.section_type.value
        )
        return content or ""
    
    def _generate_content_with_reflection(self, variables: Dict[str, Any], operation_type: str) -> str:
        """
        Reflection（自己対話）を使ってコンテンツ生成する共通メソッド。
        """
        if operation_type == "new":
            template = self.template_manager.get_new_section_template(self.section_type, variables)
        else:
            template = self.template_manager.get_update_section_template(self.section_type, variables)
        
        if not template["system_prompt"] or not template["user_prompt"]:
            logger.error(f"Failed to prepare reflection templates for {operation_type} {self.section_type.value} section")
            return ""
        
        content = self.openai_client.generate_content_with_reflection(
            system_prompt=template["system_prompt"],
            user_prompt=template["user_prompt"],
            operation_type=operation_type,
            section_type=self.section_type.value,
            variables=variables
        )
        return content or ""
    
    def _extract_structured_info(
        self,
        previous_sections: Dict[SectionType, str]
    ) -> str:
        """
        前のセクション内容を元に構造化情報を抽出するメソッド。
        
        デフォルト実装は空文字を返すだけ。
        必要なセクション（Architecture, Dataflow 等）でオーバーライドして、
        AIテンプレートを呼び出す処理を実装してください。
        """
        return ""
    
    def _analyze_changed_files(self, changed_files: List[Dict[str, Any]]) -> str:
        """
        変更ファイル情報を整形する共通メソッド。
        """
        if not changed_files:
            return "変更ファイル情報が提供されていません。"
        
        result = []
        for file in changed_files:
            filename = file.get("filename", "")
            status = file.get("status", "")
            if filename:
                result.append(f"- {filename} ({status})")
        
        return "\n".join(result)
