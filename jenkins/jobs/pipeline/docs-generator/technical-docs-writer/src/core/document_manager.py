"""!
ドキュメント管理モジュール

ドキュメント生成プロセス全体を調整し、各コンポーネント間の連携を管理します。
"""

import os
import json
from typing import Dict, Any, List, Optional

from config import SectionType, SECTION_ORDER, DOCUMENT_GENERATION_ORDER, DEFAULT_CONFIG
from utils.logger import logger
from utils.file_utils import read_file, read_json, write_file, ensure_directory
from api.openai_client import OpenAIClient
from templates.template_manager import TemplateManager
from core.section_analyzer import SectionAnalyzer
from core.document_merger import DocumentMerger
from sections.base_section import BaseSection
from sections.overview import OverviewSection
from sections.directory_structure import DirectoryStructureSection
from sections.architecture import ArchitectureSection
from sections.dataflow import DataflowSection
from sections.glossary import GlossarySection
from sections.changelog import ChangelogSection


class DocumentManager:
    """!
    ドキュメント生成プロセスを管理するクラス
    
    PRの解析、セクションの処理、ドキュメントの結合など、全体のワークフローを調整します。
    """
    
    def __init__(self, openai_client: OpenAIClient, template_manager: TemplateManager, 
                use_reflection: bool = False, reflection_sections: Optional[List[str]] = None):
        self.openai_client = openai_client
        self.template_manager = template_manager
        self.use_reflection = use_reflection
        
        # 自己対話を適用するセクション
        self.reflection_sections = set()
        if reflection_sections:
            logger.info(f"Using command line reflection sections: {reflection_sections}")
            for section_name in reflection_sections:
                try:
                    section_type = SectionType.from_string(section_name)
                    self.reflection_sections.add(section_type)
                except ValueError as e:
                    logger.warning(f"Unknown section type for reflection: {section_name}, Error: {str(e)}")
        elif use_reflection:
            logger.info(f"Using DEFAULT_CONFIG reflection sections: {DEFAULT_CONFIG.get('reflection_sections', [])}")
            for section_name in DEFAULT_CONFIG.get("reflection_sections", []):
                try:
                    section_type = SectionType.from_string(section_name)
                    self.reflection_sections.add(section_type)
                except ValueError as e:
                    logger.warning(f"Unknown section type in config: {section_name}, Error: {str(e)}")

        # セクションアナライザとマージャ
        self.section_analyzer = SectionAnalyzer(openai_client, template_manager)
        self.document_merger = DocumentMerger(openai_client, template_manager)
        
        # セクションハンドラの初期化
        self.section_handlers: Dict[SectionType, BaseSection] = {
            SectionType.OVERVIEW: OverviewSection(openai_client, template_manager),
            SectionType.DIRECTORY_STRUCTURE: DirectoryStructureSection(openai_client, template_manager),
            SectionType.ARCHITECTURE: ArchitectureSection(openai_client, template_manager),
            SectionType.DATAFLOW: DataflowSection(openai_client, template_manager),
            SectionType.GLOSSARY: GlossarySection(openai_client, template_manager),
            SectionType.CHANGELOG: ChangelogSection(openai_client, template_manager)
        }
        
        logger.info("DocumentManager initialized")
        if self.use_reflection:
            logger.info(f"Reflection mode enabled for sections: {', '.join([s.value for s in self.reflection_sections])}")
    
    def process_pr(self, pr_metadata_file: str, pr_comment_file: str, sections_dir: str,
                   changed_files_file: Optional[str] = None, 
                   specified_sections: Optional[List[str]] = None) -> Dict[str, bool]:
        """!
        PRの内容を処理して関連するセクションを更新
        """
        logger.start_group("Processing PR for document sections")
        try:
            # PRメタデータとコメントを読み込み
            pr_metadata = self._load_pr_metadata(pr_metadata_file)
            pr_comment = self._load_pr_comment(pr_comment_file)
            
            if not pr_metadata or not pr_comment:
                logger.error("Failed to load PR information")
                return {}
            
            # 変更ファイル情報を読み込み（提供されている場合）
            changed_files = None
            if changed_files_file:
                changed_files = self._load_changed_files(changed_files_file)
            
            # 処理するセクション決定
            sections_to_process = self._determine_sections_to_process(pr_metadata, pr_comment, specified_sections)
            
            # 最初のPRかどうか判定し、必要なら全セクションを包含
            if pr_metadata.get("pr_index", 0) == 1 or pr_metadata.get("pr_number", 0) == 1:
                logger.info("Processing first PR - ensuring all basic sections are included")
                all_basic_sections = list(SectionType)
                # 既存セクションと基本セクションの和集合
                sections_to_process = list(set(sections_to_process + all_basic_sections))
            
            logger.info(f"Processing sections: {', '.join([s.value for s in sections_to_process])}")
            
            # 出力ディレクトリを確保
            ensure_directory(sections_dir)
            
            # 各セクションを処理
            results = self._process_sections(pr_metadata, pr_comment, sections_to_process, sections_dir, changed_files)
            success_count = sum(1 for v in results.values() if v)
            logger.info(f"Processed {success_count}/{len(sections_to_process)} sections successfully")
            
            return results
        except Exception as e:
            logger.error(f"Error processing PR: {str(e)}")
            return {}
        finally:
            logger.end_group()
    
    def merge_documents(self, sections_dir: str, output_file: str,
                        pr_metadata_file: Optional[str] = None,
                        optimize_structure: bool = False) -> bool:
        """!
        各セクションを結合して単一のドキュメントを生成
        
        Args:
            sections_dir: セクションファイルが格納されたディレクトリ
            output_file: 出力ファイルのパス
            pr_metadata_file: PRメタデータファイルのパス（オプション）
            optimize_structure: 構造最適化を実行するかどうか
        """
        logger.start_group("Merging sections into a single document")
        try:
            pr_metadata = None
            if pr_metadata_file:
                pr_metadata = self._load_pr_metadata(pr_metadata_file)
            
            result = self.document_merger.merge_sections(
                sections_dir, output_file, pr_metadata,
                optimize_structure=optimize_structure  # フラグを渡す
            )
            if result:
                logger.info(f"Successfully merged documents to: {output_file}")
            else:
                logger.error("Failed to merge document sections")
            return result
        except Exception as e:
            logger.error(f"Error merging documents: {str(e)}")
            return False
        finally:
            logger.end_group()
    
    def _process_sections(
        self,
        pr_metadata: Dict[str, Any],
        pr_comment: str,
        sections: List[SectionType],
        sections_dir: str,
        changed_files: Optional[List[Dict[str, Any]]]
    ) -> Dict[SectionType, bool]:
        """!
        各セクションを処理（固定順序で）
        """
        results = {}
        processed_sections = {}
        
        sections_set = set(sections)
        
        for section_type in DOCUMENT_GENERATION_ORDER:
            if section_type not in sections_set:
                continue
            
            logger.info(f"Processing section: {section_type.value}")
            handler = self.section_handlers.get(section_type)
            if not handler:
                logger.warning(f"No handler found for section type: {section_type.value}")
                results[section_type] = False
                continue
            
            # ファイルパス
            current_file = os.path.join(sections_dir, f"{section_type.value}.md")
            output_file = current_file
            is_new = not os.path.exists(current_file)
            
            # Reflection を使うかどうか
            use_reflection = (section_type in self.reflection_sections)
            
            # 実行
            try:
                if is_new:
                    logger.info(f"Creating new {section_type.value} section (reflection={use_reflection})")
                    result = handler.create_section(
                        pr_metadata, pr_comment, output_file,
                        changed_files, processed_sections,
                        use_reflection=use_reflection
                    )
                else:
                    logger.info(f"Updating existing {section_type.value} section (reflection={use_reflection})")
                    result = handler.update_section(
                        pr_metadata, pr_comment,
                        current_file, output_file,
                        changed_files, processed_sections,
                        use_reflection=use_reflection
                    )
                
                results[section_type] = result
                if result:
                    content_after = handler.get_current_content(output_file)
                    if content_after:
                        processed_sections[section_type] = content_after
                else:
                    logger.warning(f"Failed to process {section_type.value} section")
            except Exception as e:
                logger.error(f"Error processing {section_type.value} section: {str(e)}")
                results[section_type] = False
        
        return results
    
    def _determine_sections_to_process(
        self,
        pr_metadata: Dict[str, Any],
        pr_comment: str,
        specified_sections: Optional[List[str]] = None
    ) -> List[SectionType]:
        """処理対象セクションを決定（指定がなければ AI 分析）"""
        if specified_sections:
            sections = []
            for name in specified_sections:
                try:
                    s = SectionType.from_string(name)
                    sections.append(s)
                except ValueError:
                    logger.warning(f"Unknown section type: {name}")
            if sections:
                logger.info(f"Using explicitly specified sections: {', '.join([s.value for s in sections])}")
                return sections
            else:
                logger.warning("No valid specified sections, falling back to analysis")
        
        # セクション分析
        return self.section_analyzer.analyze_sections(pr_metadata, pr_comment)
    
    def _load_pr_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        data = read_json(file_path)
        return data
    
    def _load_pr_comment(self, file_path: str) -> Optional[str]:
        return read_file(file_path)
    
    def _load_changed_files(self, file_path: str) -> Optional[List[Dict[str, Any]]]:
        data = read_json(file_path)
        if not data or not isinstance(data, list):
            logger.warning("Invalid changed files data")
            return None
        return data
