#!/usr/bin/env python
"""!
技術ドキュメント自動生成・更新スクリプト

GitHubのPRコメントを基に技術的な文書を自動生成または更新します。
Azure OpenAI APIを使用して、PRの内容を解析し、構造化された技術ドキュメントを作成します。
"""

import argparse
import os
import sys
import logging
import traceback
from typing import List, Optional, Dict, Any

# 内部モジュールのインポート
from utils.logger import logger, setup_logging
from api.openai_client import OpenAIClient
from templates.template_manager import TemplateManager
from core.document_manager import DocumentManager
from config import SectionType, DEFAULT_CONFIG, SECTION_HEADINGS
from utils.file_utils import read_file, write_file, ensure_directory
from utils.markdown_utils import split_markdown_into_sections


def main():
    """!
    メイン関数

    コマンドライン引数を解析し、ドキュメント生成処理を実行します。
    """
    # 開始ロゴの表示
    print("\n" + "=" * 80)
    print(" " * 20 + "TECHNICAL DOCUMENT GENERATOR")
    print(" " * 10 + "Based on PR Comments and Multiple Section Documents")
    print("=" * 80 + "\n")
    
    # コマンドライン引数の解析
    args = parse_arguments()
    
    # 詳細ログが要求された場合はDEBUGレベルに設定
    if args.verbose:
        logger.set_level(logging.DEBUG)
    
    logger.start_group("INITIALIZATION")
    
    # API認証情報の取得（コマンドライン引数 > 環境変数）
    logger.step("Setting up OpenAI API credentials")
    api_key = args.api_key or os.environ.get('OPENAI_API_KEY')
    api_endpoint = args.api_endpoint or os.environ.get('OPENAI_API_ENDPOINT')
    
    if not api_key or not api_endpoint:
        logger.error("Azure OpenAI API Key and Endpoint must be provided via arguments or environment variables")
        sys.exit(1)
    
    # テンプレートディレクトリの検証
    logger.step("Validating templates directory")
    if not os.path.isdir(args.templates_dir):
        logger.error(f"Templates directory not found: {args.templates_dir}")
        sys.exit(1)
    
    # 出力ディレクトリの確保
    logger.step("Setting up output directories")
    sections_dir = args.sections_dir
    os.makedirs(sections_dir, exist_ok=True)
    
    # 出力ファイル用のディレクトリを確保
    output_dir = os.path.dirname(args.output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # 更新モードの場合、既存の結合済みドキュメントをセクションごとに分割
    if args.update_mode and os.path.exists(args.output_file):
        logger.step("Update mode: Splitting existing document into sections")
        try:
            existing_content = read_file(args.output_file)
            if existing_content:
                # ドキュメントをセクションごとに分割
                sections = split_markdown_into_sections(existing_content, SECTION_HEADINGS)
                
                # 分割されたセクションをファイルに書き出し
                for section_type, section_content in sections.items():
                    section_file = os.path.join(sections_dir, f"{section_type.value}.md")
                    write_file(section_file, section_content)
                    logger.info(f"Created section file: {section_file}")
                
                logger.info(f"Successfully split existing document into {len(sections)} sections")
            else:
                logger.warning("Existing document is empty, proceeding without splitting")
        except Exception as e:
            logger.error(f"Error splitting existing document: {str(e)}")
            logger.error("Proceeding without pre-existing sections")
    
    logger.end_group()
    
    try:
        # コンポーネントの初期化
        logger.start_group("COMPONENT INITIALIZATION")
        
        # テンプレートマネージャーの初期化
        logger.step("Initializing template manager")
        template_manager = TemplateManager(args.templates_dir)
        
        # OpenAI クライアントの初期化
        logger.step("Initializing OpenAI client")
        openai_client = OpenAIClient(
            endpoint=api_endpoint,
            api_key=api_key,
            deployment_name=args.openai_model,
            save_reflection=args.save_reflection,
            template_manager=template_manager  # template_manager を渡す
        )
        
        # ドキュメントマネージャーの初期化
        logger.step("Initializing document manager")
        document_manager = DocumentManager(
            openai_client, 
            template_manager,
            use_reflection=args.use_reflection,
            reflection_sections=args.reflection_sections
        )
        
        logger.end_group()
        
        # 処理モードに応じた実行
        logger.start_group("EXECUTION")
        
        if args.section_mode == 'merge':
            # マージのみのモード
            logger.step("Executing merge-only mode")
            process_merge_only(document_manager, args)
        else:
            # セクション処理モード
            logger.step(f"Executing section processing mode: {args.section_mode}")
            process_sections(document_manager, args)
        
        logger.end_group()
        
        # 使用統計を出力
        usage = openai_client.get_usage_stats()
        logger.token_usage(
            usage['prompt_tokens'],
            usage['completion_tokens'],
            usage['total_tokens']
        )
        
        # プロンプト履歴を保存
        if args.save_prompts:
            prompts_file = os.path.join(os.path.dirname(args.output_file), "generate_doc_prompts.md")
            openai_client.save_prompt_history(prompts_file)
            logger.info(f"Saved prompt history to: {prompts_file}")
        
        # 完了メッセージ
        print("\n" + "=" * 80)
        print(" " * 25 + "PROCESS COMPLETED")
        print("=" * 80 + "\n")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)


def parse_arguments():
    """
    コマンドライン引数をパースする
    
    Returns:
        argparse.Namespace: パースされた引数
    """
    parser = argparse.ArgumentParser(
        description='Generate and update technical documentation based on PR comments'
    )
    
    # 必須の引数
    parser.add_argument('--pr-metadata', required=True,
                       help='Path to the PR metadata JSON file')
    parser.add_argument('--pr-comment', required=True,
                       help='Path to the PR comment Markdown file')
    parser.add_argument('--output-file', required=True,
                       help='Path to the output document file')
    
    # オプションの引数
    parser.add_argument('--sections-dir', default='sections',
                       help='Directory to store individual section files')
    parser.add_argument('--templates-dir', default='templates',
                       help='Directory containing prompt template files')
    parser.add_argument('--changed-files',
                       help='Path to the changed files JSON file (optional)')
    
    # セクション処理モード
    parser.add_argument('--section-mode', choices=['all', 'merge', 'analyze'] + SectionType.all_names(),
                    default='all',
                    help='Process specific section or all sections (analyze: use PR analysis result)')
    
    # 更新モードフラグを追加
    parser.add_argument('--update-mode', action='store_true',
                       help='Enable update mode (split existing document into sections)')
    
    # 構造最適化フラグを追加
    parser.add_argument('--optimize-structure', action='store_true',
                       help='Enable document structure optimization (heavy processing)')
    parser.add_argument('--no-optimize-structure', action='store_true',
                       help='Disable document structure optimization (default)')
    
    # API設定
    parser.add_argument('--openai-model', default=DEFAULT_CONFIG['openai_model'],
                       help='OpenAI model deployment name')
    parser.add_argument('--api-key',
                       help='Azure OpenAI API Key (or use env var OPENAI_API_KEY)')
    parser.add_argument('--api-endpoint',
                       help='Azure OpenAI Endpoint (or use env var OPENAI_API_ENDPOINT)')
    
    # 自己対話関連の引数を追加
    parser.add_argument('--use-reflection', action='store_true',
                       help='Enable reflection-based document generation')
    parser.add_argument('--reflection-sections', nargs='+',
                    choices=['all'] + SectionType.all_names(),
                    default=DEFAULT_CONFIG.get('reflection_sections', ['dataflow']),
                    help='Sections to use reflection for')
    parser.add_argument('--save-reflection', action='store_true',
                       help='Save reflection process details')
    
    # オプションの動作設定
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--save-prompts', action='store_true',
                       help='Save the prompts used for document generation')
    
    return parser.parse_args()


def process_merge_only(document_manager: DocumentManager, args):
    """
    マージのみのモードを処理
    
    Args:
        document_manager: ドキュメントマネージャーインスタンス
        args: コマンドライン引数
    """
    logger.info("Processing merge-only mode")
    
    # セクションの存在を確認
    sections_exist = any([
        os.path.exists(os.path.join(args.sections_dir, f"{section.value}.md"))
        for section in SectionType
    ])
    
    if not sections_exist:
        logger.error("No section files found for merging")
        sys.exit(1)
    
    # セクションをマージして出力
    result = document_manager.merge_documents(
        args.sections_dir,
        args.output_file,
        args.pr_metadata,
        optimize_structure=args.optimize_structure  # フラグを渡す
    )
    
    if not result:
        logger.error("Failed to merge documents")
        sys.exit(1)
    
    logger.info(f"Successfully merged documents to: {args.output_file}")


def process_sections(document_manager: DocumentManager, args):
    """
    セクション処理モードを実行
    
    Args:
        document_manager: ドキュメントマネージャーインスタンス
        args: コマンドライン引数
    """
    # 処理するセクションを決定
    specified_sections = None
    if args.section_mode != 'all' and args.section_mode != 'analyze':
        # 特定のセクションが指定されている場合
        specified_sections = [args.section_mode]
    elif args.section_mode == 'analyze':
        # 分析モードの場合は、specified_sectionsをNoneのままにして
        # document_manager.process_pr内でセクション分析を実行させる
        specified_sections = None
        logger.info("Using PR analysis to determine relevant sections")
    else:
        # 'all'の場合は全セクションを処理
        specified_sections = []
        logger.info("Processing all sections")
    
    # PRを処理してセクションを更新
    results = document_manager.process_pr(
        args.pr_metadata,
        args.pr_comment,
        args.sections_dir,
        args.changed_files,
        specified_sections
    )
    
    if not results:
        logger.error("Failed to process any sections")
        sys.exit(1)
    
    # 成功したセクション数をカウント
    success_count = sum(1 for result in results.values() if result)
    total_count = len(results)
    
    logger.info(f"Successfully processed {success_count}/{total_count} sections")
    
    # セクションをマージして出力
    if success_count > 0:
        merge_result = document_manager.merge_documents(
            args.sections_dir,
            args.output_file,
            args.pr_metadata,
            optimize_structure=args.optimize_structure  # フラグを渡す
        )
        
        if not merge_result:
            logger.error("Failed to merge documents")
            sys.exit(1)
        
        logger.info(f"Successfully merged documents to: {args.output_file}")


if __name__ == "__main__":
    main()
