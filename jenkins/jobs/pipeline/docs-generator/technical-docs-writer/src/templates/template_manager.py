"""!
テンプレート管理モジュール

各種セクション用のプロンプトテンプレートの読み込み、変数置換、選択を行います。
"""

import os
import re
from typing import Dict, Any, Optional, List

from config import SectionType, TemplateNames, get_template_path, get_common_template_path
from utils.logger import logger
from utils.file_utils import read_file


class TemplateManager:
    """!
    プロンプトテンプレートを管理するクラス
    
    セクションタイプごとの適切なテンプレートを読み込み、変数を置換します。
    """
    
    def __init__(self, templates_dir: str):
        """!
        TemplateManagerを初期化します
        
        Args:
            templates_dir: テンプレートファイルが格納されたディレクトリのパス
        """
        self.templates_dir = templates_dir
        self.templates_cache: Dict[str, str] = {}  # テンプレートキャッシュ
        
        logger.info(f"Template manager initialized with directory: {templates_dir}")
        self._validate_templates()
    
    def _validate_templates(self) -> None:
        """
        各セクションに必要なテンプレートファイルが存在するか検証します
        """
        logger.start_group("Validating template files")
        
        # 共通テンプレートの確認
        common_templates = [
            TemplateNames.SECTION_ANALYSIS,
            TemplateNames.MERGE_TEMPLATE,
            TemplateNames.SYSTEM_PROMPT,
            TemplateNames.EXTRACT_ARCHITECTURE,  # 新しく追加された構造抽出テンプレート
            TemplateNames.EXTRACT_DATAFLOW       # 新しく追加された構造抽出テンプレート
        ]
        
        for template_name in common_templates:
            template_path = get_common_template_path(template_name, self.templates_dir)
            if not os.path.exists(template_path):
                logger.warning(f"Common template not found: {template_path}")
            else:
                logger.debug(f"✓ Found common template: {template_name}")
        
        # 各セクション用テンプレートの確認
        required_templates = [
            TemplateNames.NEW,
            TemplateNames.UPDATE
        ]
        
        for section in SectionType:
            logger.debug(f"Checking templates for section: {section.value}")
            section_dir = os.path.join(self.templates_dir, section.value)
            
            if not os.path.exists(section_dir):
                logger.warning(f"Section template directory not found: {section_dir}")
                continue
                
            for template_name in required_templates:
                template_path = get_template_path(section, template_name, self.templates_dir)
                if not os.path.exists(template_path):
                    logger.warning(f"Template not found for {section.value}: {template_name}")
                else:
                    logger.debug(f"✓ Found {section.value} template: {template_name}")
        
        logger.end_group()
    
    def get_template(self, section: SectionType, template_name: str) -> Optional[str]:
        """
        指定されたセクションとテンプレート名に対応するテンプレートを取得します
        
        Args:
            section: セクションタイプ
            template_name: テンプレート名
            
        Returns:
            str: テンプレート内容、または取得できない場合はNone
        """
        template_path = get_template_path(section, template_name, self.templates_dir)
        cache_key = f"{section.value}:{template_name}" if section else f"common:{template_name}"
        
        # キャッシュから取得
        if cache_key in self.templates_cache:
            return self.templates_cache[cache_key]
        
        # ファイルから読み込み
        template_content = read_file(template_path)
        if template_content is None:
            logger.error(f"Failed to load template: {template_path}")
            return None
            
        # キャッシュに保存
        self.templates_cache[cache_key] = template_content
        return template_content
    
    def get_common_template(self, template_name: str) -> Optional[str]:
        """
        共通テンプレートを取得します
        
        Args:
            template_name: テンプレート名
            
        Returns:
            str: テンプレート内容、または取得できない場合はNone
        """
        template_path = get_common_template_path(template_name, self.templates_dir)
        cache_key = f"common:{template_name}"
        
        # キャッシュから取得
        if cache_key in self.templates_cache:
            return self.templates_cache[cache_key]
        
        # ファイルから読み込み
        template_content = read_file(template_path)
        if template_content is None:
            logger.error(f"Failed to load common template: {template_path}")
            return None
            
        # キャッシュに保存
        self.templates_cache[cache_key] = template_content
        return template_content
    
    def render_template(self, template_content: str, variables: Dict[str, Any]) -> str:
        """
        テンプレート内の変数を置換します
        
        Args:
            template_content: テンプレート内容
            variables: 置換する変数の辞書
            
        Returns:
            str: 変数が置換されたテンプレート
        """
        if not template_content:
            return ""
                
        result = template_content
        
        # デバッグ情報として、受け取った変数の一覧をログに残す
        logger.debug(f"Template variables: {', '.join(variables.keys())}")
        
        # 変数を置換
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            
            # 値がNoneの場合は空文字列に
            str_value = str(value) if value is not None else ""
            
            # 置換前後の状態をチェックしてログに記録（デバッグ用）
            if placeholder in result:
                if not str_value:
                    logger.warning(f"Empty value for placeholder {placeholder}")
                logger.debug(f"Replacing placeholder {placeholder} with {len(str_value)} chars")
            
            # 実際の置換を実行
            result = result.replace(placeholder, str_value)
        
        # 未置換のプレースホルダーを検出してログに記録
        unresolved = re.findall(r'{[a-zA-Z_]+}', result)
        if unresolved:
            logger.warning(f"Unresolved placeholders: {', '.join(unresolved)}")
        
        return result
    
    def get_extract_structure_template(self, input_data: Dict[str, str], 
                                    structure_type: str) -> Dict[str, str]:
        """
        構造化情報抽出用のテンプレートを取得し、変数を置換します
        
        Args:
            input_data: セクションデータの辞書
            structure_type: 構造化タイプ ("architecture" または "dataflow")
            
        Returns:
            Dict[str, str]: システムプロンプトとユーザープロンプトを含む辞書
        """
        # システムプロンプト
        system_prompt = "あなたはシステム構造を分析し、構造化された情報を抽出する専門家です。"
        
        # 情報抽出テンプレートファイル名
        if structure_type == "architecture":
            template_name = TemplateNames.EXTRACT_ARCHITECTURE
        elif structure_type == "dataflow":
            template_name = TemplateNames.EXTRACT_DATAFLOW
        else:
            logger.error(f"Unknown structure type: {structure_type}")
            return {"system_prompt": system_prompt, "user_prompt": ""}
        
        # テンプレートを取得
        template_content = self.get_common_template(template_name)
        if not template_content:
            logger.error(f"Failed to load structure extraction template: {template_name}")
            return {"system_prompt": system_prompt, "user_prompt": ""}
        
        # テンプレートを変数で置換
        rendered_template = self.render_template(template_content, input_data)
        
        logger.debug(f"Rendered structure extraction template for {structure_type}")
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": rendered_template
        }
    
    def get_new_section_template(self, section: SectionType, variables: Dict[str, Any]) -> Dict[str, str]:
        """
        新規セクション作成用のテンプレートを取得し、変数を置換します
        
        Args:
            section: セクションタイプ
            variables: 置換する変数の辞書
            
        Returns:
            Dict[str, str]: システムプロンプトとユーザープロンプトを含む辞書
        """
        # システムプロンプト
        system_prompt = self.get_common_template(TemplateNames.SYSTEM_PROMPT) or ""
        
        # セクション用の新規テンプレート
        template = self.get_template(section, TemplateNames.NEW) or ""
        
        if not system_prompt or not template:
            logger.error(f"Failed to load templates for new {section.value} section")
            return {"system_prompt": "", "user_prompt": ""}
        
        # システムプロンプトをセクション固有の情報で拡張
        system_prompt_variables = {
            "SECTION_TYPE": section.value,
            "SECTION_NAME": section.value.replace("_", " ").title()
        }
        rendered_system_prompt = self.render_template(system_prompt, system_prompt_variables)
        
        # セクションテンプレートを変数で置換
        rendered_template = self.render_template(template, variables)
        
        # デバッグ情報
        logger.debug(f"Rendered new section template for {section.value}")
        
        return {
            "system_prompt": rendered_system_prompt,
            "user_prompt": rendered_template
        }
    
    def get_update_section_template(self, section: SectionType, variables: Dict[str, Any]) -> Dict[str, str]:
        """
        セクション更新用のテンプレートを取得し、変数を置換します
        
        Args:
            section: セクションタイプ
            variables: 置換する変数の辞書
            
        Returns:
            Dict[str, str]: システムプロンプトとユーザープロンプトを含む辞書
        """
        # システムプロンプト
        system_prompt = self.get_common_template(TemplateNames.SYSTEM_PROMPT) or ""
        
        # セクション用の更新テンプレート
        template = self.get_template(section, TemplateNames.UPDATE) or ""
        
        if not system_prompt or not template:
            logger.error(f"Failed to load templates for updating {section.value} section")
            return {"system_prompt": "", "user_prompt": ""}
        
        # システムプロンプトをセクション固有の情報で拡張
        system_prompt_variables = {
            "SECTION_TYPE": section.value,
            "SECTION_NAME": section.value.replace("_", " ").title()
        }
        rendered_system_prompt = self.render_template(system_prompt, system_prompt_variables)
        
        # セクションテンプレートを変数で置換
        rendered_template = self.render_template(template, variables)
        
        # デバッグ情報
        logger.debug(f"Rendered update section template for {section.value}")
        
        return {
            "system_prompt": rendered_system_prompt,
            "user_prompt": rendered_template
        }
    
    def get_section_analysis_template(self, variables: Dict[str, Any]) -> Dict[str, str]:
        """
        セクション分析用のテンプレートを取得し、変数を置換します
        
        Args:
            variables: 置換する変数の辞書
            
        Returns:
            Dict[str, str]: システムプロンプトとユーザープロンプトを含む辞書
        """
        # システムプロンプト
        system_prompt = "あなたはPRコメントを分析し、関連するドキュメントセクションを特定する専門家です。"
        
        # 分析テンプレート
        template = self.get_common_template(TemplateNames.SECTION_ANALYSIS) or ""
        
        if not template:
            logger.error("Failed to load section analysis template")
            return {"system_prompt": system_prompt, "user_prompt": ""}
        
        # テンプレートを変数で置換
        rendered_template = self.render_template(template, variables)
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": rendered_template
        }
    
    def get_merge_template(self, variables: Dict[str, Any]) -> Dict[str, str]:
        """
        ドキュメント統合用のテンプレートを取得し、変数を置換します
        
        Args:
            variables: 置換する変数の辞書
            
        Returns:
            Dict[str, str]: システムプロンプトとユーザープロンプトを含む辞書
        """
        # システムプロンプト
        system_prompt = "あなたは複数のドキュメントセクションを統合して一貫性のある完全なドキュメントを作成する専門家です。"
        
        # 統合テンプレート
        template = self.get_common_template(TemplateNames.MERGE_TEMPLATE) or ""
        
        if not template:
            logger.error("Failed to load merge template")
            return {"system_prompt": system_prompt, "user_prompt": ""}
        
        # テンプレートを変数で置換
        rendered_template = self.render_template(template, variables)
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": rendered_template
        }

    def get_reflection_template(self, stage: str, section_type: SectionType, variables: Dict[str, Any]) -> Dict[str, str]:
        """
        省察プロセスの特定段階用のテンプレートを取得し、変数を置換します。
        
        Args:
            stage: 省察の段階 ("planning", "dialog", "final")
            section_type: セクションタイプ
            variables: 置換する変数の辞書
            
        Returns:
            Dict[str, str]: システムプロンプトとユーザープロンプトを含む辞書
        """
        # セクション名を取得
        section_name = section_type.value.replace('_', ' ').title()
        
        # ステージに応じたプロンプトファイル名
        prompt_files = {
            "planning": TemplateNames.REFLECTION_PLANNING,
            "dialog": TemplateNames.REFLECTION_DIALOG,
            "final": TemplateNames.REFLECTION_FINAL
        }
        
        # 共通ガイドラインを取得
        common_guidelines = self.get_common_template(TemplateNames.REFLECTION_COMMON) or ""
        
        # 段階別プロンプトを取得
        stage_prompt_file = prompt_files.get(stage, TemplateNames.REFLECTION_SYSTEM_PROMPT)
        stage_prompt = self.get_common_template(stage_prompt_file) or ""
        
        if not stage_prompt:
            logger.error(f"Failed to load reflection template for stage {stage}")
            return {"system_prompt": "", "user_prompt": ""}
        
        # セクション固有の情報で拡張
        system_prompt_variables = {
            "SECTION_TYPE": section_type.value,
            "SECTION_NAME": section_name
        }
        
        # 組み合わせたプロンプトを変数で置換
        combined_prompt = f"{stage_prompt}\n\n{common_guidelines}"
        rendered_system_prompt = self.render_template(combined_prompt, system_prompt_variables)
        
        # セクションテンプレートを変数で置換
        if stage == "planning":
            template = self.get_template(section_type, TemplateNames.NEW) or ""
        else:
            # 他のステージ用にはユーザープロンプトを使用
            template = ""
        
        rendered_template = self.render_template(template, variables) if template else ""
        
        return {
            "system_prompt": rendered_system_prompt,
            "user_prompt": rendered_template
        }

    def get_reflection_stage_template(self, section: SectionType, stage: str, 
                                    operation_type: str, variables: Dict[str, Any]) -> Dict[str, str]:
        """
        自己対話プロセスの特定段階用のテンプレートを取得し、変数を置換します。
        
        Args:
            section: セクションタイプ
            stage: 省察の段階 ("planning", "dialog", "final")
            operation_type: 操作タイプ ("new" または "update")
            variables: 置換する変数の辞書
            
        Returns:
            Dict[str, str]: システムプロンプトとユーザープロンプトを含む辞書
        """
        # セクション名を取得
        section_name = section.value.replace('_', ' ').title()
        
        # ステージに応じた共通プロンプトファイル名
        common_prompt_files = {
            "planning": TemplateNames.REFLECTION_PLANNING,
            "dialog": TemplateNames.REFLECTION_DIALOG,
            "final": TemplateNames.REFLECTION_FINAL
        }
        
        # 操作とステージに応じたセクション別プロンプトファイル名の決定
        section_prompt_file = None
        
        if operation_type == "new":
            if stage == "planning":
                section_prompt_file = "new_planning.txt"
            elif stage == "dialog":
                section_prompt_file = "new_dialog.txt"
            elif stage == "final":
                section_prompt_file = "new_final.txt"
        else:  # update
            if stage == "planning":
                section_prompt_file = "update_planning.txt"
            elif stage == "dialog":
                section_prompt_file = "update_dialog.txt"
            elif stage == "final":
                section_prompt_file = "update_final.txt"
        
        # 共通ガイドラインを取得
        common_guidelines = self.get_common_template(TemplateNames.REFLECTION_COMMON) or ""
        
        # 段階別の共通プロンプトを取得
        stage_common_file = common_prompt_files.get(stage, TemplateNames.REFLECTION_SYSTEM_PROMPT)
        stage_common_prompt = self.get_common_template(stage_common_file) or ""
        
        # セクション・段階・操作に特化したプロンプトを取得
        section_specific_prompt = None
        
        if section_prompt_file:
            # セクション固有のプロンプトファイルのフルパスを構築
            section_dir = os.path.join(self.templates_dir, section.value)
            section_prompt_path = os.path.join(section_dir, section_prompt_file)
            
            # ファイルが存在するか確認
            if os.path.exists(section_prompt_path):
                try:
                    with open(section_prompt_path, 'r', encoding='utf-8') as f:
                        section_specific_prompt = f.read()
                    logger.debug(f"Loaded specific {stage} prompt for {section.value} from {section_prompt_path}")
                except Exception as e:
                    logger.warning(f"Error reading {section_prompt_path}: {str(e)}")
        
        # セクション固有のプロンプトが見つからない場合は通常のプロンプトを使用
        if not section_specific_prompt:
            if operation_type == "new":
                section_specific_prompt = self.get_template(section, TemplateNames.NEW) or ""
                logger.debug(f"Using standard NEW template for {section.value} {stage} phase")
            else:  # update
                section_specific_prompt = self.get_template(section, TemplateNames.UPDATE) or ""
                logger.debug(f"Using standard UPDATE template for {section.value} {stage} phase")
        
        # セクション固有の情報で拡張
        system_prompt_variables = {
            "SECTION_TYPE": section.value,
            "SECTION_NAME": section_name
        }
        
        # 組み合わせたシステムプロンプトを変数で置換
        combined_system_prompt = f"{stage_common_prompt}\n\n{common_guidelines}"
        rendered_system_prompt = self.render_template(combined_system_prompt, system_prompt_variables)
        
        # セクション固有のユーザープロンプトを変数で置換
        rendered_user_prompt = ""
        if section_specific_prompt:
            # 変数辞書に基本的なセクション情報を追加
            complete_variables = variables.copy()
            complete_variables.update(system_prompt_variables)
            
            rendered_user_prompt = self.render_template(section_specific_prompt, complete_variables)
        
        return {
            "system_prompt": rendered_system_prompt,
            "user_prompt": rendered_user_prompt
        }