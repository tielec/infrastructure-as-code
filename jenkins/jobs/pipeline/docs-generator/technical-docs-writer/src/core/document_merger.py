"""!
ドキュメント結合モジュール

複数のセクションドキュメントを結合し、一貫性のある完全なドキュメントを生成します。
"""

import os
import re
from typing import Dict, Any, List, Optional

from config import SectionType, SECTION_ORDER, SECTION_HEADINGS, TemplateNames, DOCUMENT_GENERATION_ORDER
from utils.logger import logger
from utils.file_utils import read_file, write_file, ensure_directory
from utils.markdown_utils import (
    merge_markdown_documents,
    adjust_heading_levels,
    inject_toc,
    replace_mermaid_diagrams
)
from api.openai_client import OpenAIClient
from templates.template_manager import TemplateManager


class DocumentMerger:
    """!
    複数のセクションドキュメントを結合するクラス
    
    独立して生成された各セクションを結合し、調整して最終的なドキュメントを作成します。
    """
    
    def __init__(self, openai_client: OpenAIClient, template_manager: TemplateManager):
        """!
        DocumentMerger初期化
        
        Args:
            openai_client: OpenAI APIクライアント
            template_manager: テンプレート管理クラス
        """
        self.openai_client = openai_client
        self.template_manager = template_manager
        # 出力順序の整合性チェック
        self._validate_section_orders()
    
    def _validate_section_orders(self) -> None:
        """
        出力順序と生成順序の整合性を確認します
        """
        # 両方の順序に同じセクションが含まれているか確認
        generation_set = set(DOCUMENT_GENERATION_ORDER)
        output_set = set(SECTION_ORDER)
        
        if generation_set != output_set:
            missing_in_generation = output_set - generation_set
            missing_in_output = generation_set - output_set
            
            if missing_in_generation:
                logger.warning(f"Sections in SECTION_ORDER but not in DOCUMENT_GENERATION_ORDER: {', '.join([s.value for s in missing_in_generation])}")
            
            if missing_in_output:
                logger.warning(f"Sections in DOCUMENT_GENERATION_ORDER but not in SECTION_ORDER: {', '.join([s.value for s in missing_in_output])}")
        
        # 特定の依存関係が出力順序でも維持されているか確認
        output_indices = {section: i for i, section in enumerate(SECTION_ORDER)}
        
        # 重要な依存関係のチェック
        key_dependencies = [
            (SectionType.OVERVIEW, SectionType.DIRECTORY_STRUCTURE),  # 概要→ディレクトリ構造
            (SectionType.DIRECTORY_STRUCTURE, SectionType.ARCHITECTURE)  # ディレクトリ構造→アーキテクチャ図
        ]
        
        for prerequisite, dependent in key_dependencies:
            if prerequisite in output_indices and dependent in output_indices:
                if output_indices[prerequisite] > output_indices[dependent]:
                    logger.warning(f"Dependency ordering issue in output order: {prerequisite.value} should come before {dependent.value}")
    
    def merge_sections(self, sections_dir: str, output_file: str, 
                       pr_metadata: Optional[Dict[str, Any]] = None,
                       optimize_structure: bool = False) -> bool:
        """!
        各セクションファイルを結合して単一のドキュメントを生成
        
        Args:
            sections_dir: セクションファイルが格納されているディレクトリ
            output_file: 出力ファイルパス
            pr_metadata: PRメタデータ辞書（オプション）
            optimize_structure: 構造最適化を実行するかどうか
            
        Returns:
            bool: 成功した場合はTrue
        """
        logger.start_group("Merging section documents")
        
        try:
            # 各セクションの内容を読み込み
            section_contents = {}
            missing_sections = []
            
            # SECTION_ORDERに従ってセクションを読み込み
            # これは最終的な出力ドキュメントの順序を決定します
            for section_type in SECTION_ORDER:
                file_path = os.path.join(sections_dir, f"{section_type.value}.md")
                content = read_file(file_path)
                
                if content:
                    # 見出しレベルを調整（最初の見出しをレベル2に）
                    adjusted_content = adjust_heading_levels(content, base_level=1)
                    section_contents[section_type] = adjusted_content
                else:
                    missing_sections.append(section_type.value)
            
            if missing_sections:
                logger.warning(f"Missing sections: {', '.join(missing_sections)}")
            
            if not section_contents:
                logger.error("No section content available for merging")
                return False
            
            # 各セクションに固有の見出しを追加
            for section_type, content in section_contents.items():
                heading = SECTION_HEADINGS.get(section_type, section_type.value.replace('_', ' ').title())
                section_contents[section_type] = f"## {heading}\n\n{content}"
            
            # SECTION_ORDERに従って順序付け（出力順序）
            ordered_sections = []
            for section_type in SECTION_ORDER:
                if section_type in section_contents:
                    ordered_sections.append(section_contents[section_type])
            
            # セクションを結合
            merged_content = merge_markdown_documents(ordered_sections, add_separator=False)
            
            # メインドキュメントのタイトルを追加
            title = "技術ドキュメント"
            if pr_metadata and pr_metadata.get("repo_name"):
                repo_name = pr_metadata.get("repo_name", "")
                title = f"{repo_name} 技術ドキュメント"
            
            merged_content = f"# {title}\n\n{merged_content}"
            
            # 目次を生成して挿入
            merged_content = inject_toc(merged_content)
            
            # Mermaidダイアグラムのフォーマットを修正
            merged_content = replace_mermaid_diagrams(merged_content)
            
            # 構造最適化の条件分岐
            if optimize_structure:
                logger.step("Applying full structure optimization")
                # AIによる完全な構造最適化を適用
                merged_content = self._apply_ai_refinement(merged_content, pr_metadata)
            else:
                logger.step("Applying minimal formatting adjustments")
                # 最小限のフォーマット調整のみ
                merged_content = self._apply_minimal_formatting(merged_content)

            # 結果を保存
            logger.step("Saving merged document")
            if not write_file(output_file, merged_content):
                logger.error(f"Failed to write merged document to: {output_file}")
                return False
            
            logger.info(f"Successfully merged documents to: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error merging documents: {str(e)}")
            return False
        finally:
            logger.end_group()
    
    def _apply_minimal_formatting(self, content: str) -> str:
        """
        最小限のフォーマット調整を行う（軽量処理）
        
        Args:
            content: マージされたドキュメント内容
            
        Returns:
            str: 調整されたドキュメント内容
        """
        logger.step("Applying minimal formatting adjustments")
        
        # 基本的なフォーマット修正のみ
        # - 空行の正規化
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # - マークダウンの構文エラー修正
        content = self._fix_markdown_syntax(content)
        
        # - 明らかな重複見出しの除去（目次の重複など）
        content = self._remove_obvious_duplicates(content)
        
        return content

    def _fix_markdown_syntax(self, content: str) -> str:
        """マークダウンの基本的な構文エラーを修正"""
        # コードブロックの開始と終了の整合性チェック
        lines = content.split('\n')
        in_code_block = False
        fixed_lines = []
        
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
            fixed_lines.append(line)
        
        # コードブロックが閉じられていない場合
        if in_code_block:
            fixed_lines.append('```')
        
        return '\n'.join(fixed_lines)
    
    def _remove_obvious_duplicates(self, content: str) -> str:
        """明らかな重複（目次の重複など）を除去"""
        lines = content.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 目次の重複をチェック
            if line.strip() == "## 目次" and i < len(lines) - 1:
                # 次の同じ見出しを探す
                next_toc_index = -1
                for j in range(i + 1, min(i + 50, len(lines))):  # 50行以内で探す
                    if lines[j].strip() == "## 目次":
                        next_toc_index = j
                        break
                
                # 重複する目次が見つかった場合、最初の目次を削除
                if next_toc_index != -1:
                    # 最初の目次のセクション全体をスキップ
                    logger.debug(f"Removing duplicate table of contents at line {i}")
                    while i < len(lines) and not (lines[i].startswith('##') and i > 0):
                        i += 1
                    continue
            
            result_lines.append(line)
            i += 1
        
        return '\n'.join(result_lines)
    
    def _apply_ai_refinement(self, content: str, 
                            pr_metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        AIを使用してドキュメントの最終調整を行う（構造最適化）
        
        Args:
            content: マージされたドキュメント内容
            pr_metadata: PRメタデータ辞書（オプション）
            
        Returns:
            str: 調整されたドキュメント内容
        """
        logger.step("Applying AI refinements to merged document")
        
        # 短いドキュメントの場合は調整を行わない
        if len(content) < 500:
            logger.info("Document too short for AI refinement, skipping")
            return content
        
        try:
            # テンプレート変数を準備
            variables = {
                "merged_content": content,
                "repo_name": pr_metadata.get("repo_name", "") if pr_metadata else ""
            }
            
            # テンプレートを取得（デフォルトのmerge_template.txtを使用）
            template = self.template_manager.get_merge_template(variables)
            
            if not template["system_prompt"] or not template["user_prompt"]:
                logger.warning("Failed to prepare templates for document refinement")
                return content
            
            # OpenAI APIを使用して最終調整
            refined_content = self.openai_client.generate_content(
                template["system_prompt"],
                template["user_prompt"],
                operation_type="merge"
            )
            
            if not refined_content:
                logger.warning("Failed to get AI refinement, using original merged content")
                return content
            
            return refined_content
            
        except Exception as e:
            logger.warning(f"Error applying AI refinement: {str(e)}")
            return content  # エラー時は元の内容を返す
    
    def ensure_section_files(self, sections_dir: str, sections: List[SectionType]) -> None:
        """
        必要なセクションファイルが存在することを確認
        
        Args:
            sections_dir: セクションファイルが格納されているディレクトリ
            sections: 確認するセクションタイプのリスト
        """
        # ディレクトリが存在することを確認
        ensure_directory(sections_dir)
        
        # 各セクションファイルをチェック
        for section_type in sections:
            file_path = os.path.join(sections_dir, f"{section_type.value}.md")
            
            if not os.path.exists(file_path):
                # 空のファイルを作成（後で処理される）
                with open(file_path, 'w', encoding='utf-8') as f:
                    heading = SECTION_HEADINGS.get(section_type, section_type.value.replace('_', ' ').title())
                    f.write(f"# {heading}\n\n")
                
                logger.debug(f"Created empty section file: {file_path}")
