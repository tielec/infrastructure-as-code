"""!
セクション分析モジュール

PRコメントを解析し、どのセクションタイプが関連するかを判断します。
"""

import re
import json
from typing import Dict, Any, List, Set

from config import SectionType
from utils.logger import logger
from api.openai_client import OpenAIClient
from templates.template_manager import TemplateManager


class SectionAnalyzer:
    """!
    PRコメントの分析を担当するクラス
    
    PRコメントを分析し、関連するセクションタイプを特定します。
    """
    
    def __init__(self, openai_client: OpenAIClient, template_manager: TemplateManager):
        """!
        SectionAnalyzer初期化
        
        Args:
            openai_client: OpenAI APIクライアント
            template_manager: テンプレート管理クラス
        """
        self.openai_client = openai_client
        self.template_manager = template_manager
    
    def analyze_sections(self, pr_metadata: Dict[str, Any], pr_comment: str) -> List[SectionType]:
        """!
        PRコメントを分析して関連するセクションを特定
        
        Args:
            pr_metadata: PRメタデータ辞書
            pr_comment: PRコメント文字列
            
        Returns:
            List[SectionType]: 関連するセクションタイプのリスト
        """
        logger.start_group("Analyzing PR comment to identify relevant sections")
        
        try:
            # ルールベースの分析を実行
            rule_based_sections = self._rule_based_analysis(pr_comment)
            logger.info(f"Rule-based analysis identified sections: {', '.join([s.value for s in rule_based_sections])}")
            
            # AIベースの分析を実行
            ai_based_sections = self._ai_based_analysis(pr_metadata, pr_comment)
            logger.info(f"AI-based analysis identified sections: {', '.join([s.value for s in ai_based_sections])}")
            
            # 両方の結果を統合
            combined_sections = list(set(rule_based_sections + ai_based_sections))

            # 必須セクションの確認 - 概要セクションは常に含める
            if SectionType.OVERVIEW not in combined_sections:
                combined_sections.append(SectionType.OVERVIEW)
                logger.info("Adding OVERVIEW section as it's essential for documentation")

            # セクションが特定されない場合は全セクションを対象とする
            if not combined_sections:
                logger.info("No specific sections identified, targeting all sections")
                combined_sections = list(SectionType)
            
            # デバッグ情報
            logger.info(f"Final relevant sections: {', '.join([s.value for s in combined_sections])}")
            
            return combined_sections
            
        except Exception as e:
            logger.error(f"Error analyzing PR comment for sections: {str(e)}")
            # エラー時は全セクションを対象とする
            return list(SectionType)
        finally:
            logger.end_group()
    
    def _rule_based_analysis(self, pr_comment: str) -> List[SectionType]:
        """
        ルールベースのキーワード分析によってセクションを特定
        
        Args:
            pr_comment: PRコメント文字列
            
        Returns:
            List[SectionType]: 関連するセクションタイプのリスト
        """
        # セクションごとの関連キーワード
        section_keywords = {
            SectionType.OVERVIEW: [
                "概要", "overview", "概略", "サマリー", "summary", "紹介", "introduction",
                "背景", "background", "目的", "purpose", "機能", "feature"
            ],
            SectionType.DIRECTORY_STRUCTURE: [
                "ディレクトリ", "directory", "フォルダ", "folder", "構造", "structure",
                "ファイル構成", "file structure", "プロジェクト構成", "project structure",
                "ファイル一覧", "file list", "tree", "ツリー"
            ],
            SectionType.ARCHITECTURE: [
                "アーキテクチャ", "architecture", "構成", "composition", "設計", "design",
                "コンポーネント", "component", "モジュール", "module", "クラス図", "class diagram",
                "システム構成", "system architecture", "依存関係", "dependency"
            ],
            SectionType.DATAFLOW: [
                "データフロー", "data flow", "フロー", "flow", "シーケンス", "sequence",
                "プロセス", "process", "処理フロー", "processing flow", "ロジック", "logic",
                "パイプライン", "pipeline", "データ処理", "data processing",
                "入力", "input", "出力", "output", "API", "エンドポイント", "endpoint"
            ],
            SectionType.GLOSSARY: [
                "用語", "glossary", "用語集", "terminology", "定義", "definition",
                "専門用語", "technical term", "略語", "abbreviation", "専門語", "jargon",
                "解説", "explanation", "辞書", "dictionary", "語彙", "vocabulary"
            ],
            SectionType.CHANGELOG: [
                "変更履歴", "changelog", "履歴", "history", "変更点", "changes",
                "アップデート", "update", "リリースノート", "release note", "バージョン", "version",
                "修正", "fix", "改善", "improvement", "追加", "addition"
            ]
        }
        
        related_sections = set()
        
        # 各セクションのキーワードを検索
        for section, keywords in section_keywords.items():
            for keyword in keywords:
                if keyword.lower() in pr_comment.lower():
                    related_sections.add(section)
                    break
        
        # mermaidダイアグラムの存在を確認（アーキテクチャまたはデータフロー）
        if "```mermaid" in pr_comment:
            if "sequenceDiagram" in pr_comment:
                related_sections.add(SectionType.DATAFLOW)
            if any(x in pr_comment for x in ["graph", "flowchart"]):
                related_sections.add(SectionType.ARCHITECTURE)
        
        # ディレクトリ構造らしき行を検出
        directory_pattern = r'(?:│|├|└|─|tree|ls -l)'
        if re.search(directory_pattern, pr_comment):
            related_sections.add(SectionType.DIRECTORY_STRUCTURE)
        
        # 用語定義らしき行を検出
        glossary_pattern = r'^\s*[\*\-]\s+\*\*([^*]+)\*\*\s*[:：]\s*(.+)$'
        if re.search(glossary_pattern, pr_comment, re.MULTILINE):
            related_sections.add(SectionType.GLOSSARY)
        
        return list(related_sections)
    
    def _ai_based_analysis(self, pr_metadata: Dict[str, Any], pr_comment: str) -> List[SectionType]:
        """
        AIによる分析でセクションを特定
        
        Args:
            pr_metadata: PRメタデータ辞書
            pr_comment: PRコメント文字列
            
        Returns:
            List[SectionType]: 関連するセクションタイプのリスト
        """
        try:
            # テンプレート変数を準備
            variables = {
                "pr_number": pr_metadata.get("pr_number", ""),
                "pr_title": pr_metadata.get("pr_title", ""),
                "pr_comment": pr_comment,
                "section_types": ", ".join([s.value for s in SectionType])
            }
            
            # 分析用テンプレートを取得
            template = self.template_manager.get_section_analysis_template(variables)
            
            if not template["system_prompt"] or not template["user_prompt"]:
                logger.error("Failed to prepare templates for section analysis")
                return []
            
            # OpenAI APIを使用して分析
            logger.step("Analyzing PR comment with OpenAI API")
            analysis_result = self.openai_client.generate_content(
                template["system_prompt"],
                template["user_prompt"],
                operation_type="analysis"
            )
            
            if not analysis_result:
                logger.error("Failed to get section analysis result")
                return []
            
            # 結果をパース
            return self._parse_analysis_result(analysis_result)
            
        except Exception as e:
            logger.error(f"Error in AI-based section analysis: {str(e)}")
            return []
    
    def _parse_analysis_result(self, analysis_result: str) -> List[SectionType]:
        """
        分析結果をパースしてセクションタイプのリストを取得
        
        Args:
            analysis_result: 分析結果のJSON文字列
            
        Returns:
            List[SectionType]: 関連するセクションタイプのリスト
        """
        # JSON部分を抽出
        json_pattern = r'```json\s*([\s\S]*?)\s*```|(\{[\s\S]*\})'
        json_matches = re.search(json_pattern, analysis_result)
        
        if not json_matches:
            logger.warning("Failed to extract JSON from analysis result")
            return []
        
        json_str = json_matches.group(1) if json_matches.group(1) else json_matches.group(2)
        
        try:
            data = json.loads(json_str)
            related_sections_str = data.get("related_sections", [])
            
            # 文字列からSectionTypeに変換
            sections = []
            for section_str in related_sections_str:
                try:
                    section = SectionType.from_string(section_str)
                    sections.append(section)
                except ValueError:
                    logger.warning(f"Unknown section type: {section_str}")
            
            return sections
            
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON in analysis result")
            return []
        except Exception as e:
            logger.error(f"Error parsing analysis result: {str(e)}")
            return []
