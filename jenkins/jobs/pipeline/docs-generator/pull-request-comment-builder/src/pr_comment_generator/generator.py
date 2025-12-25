"""PRコメント生成のオーケストレーションを担当するモジュール。"""
import concurrent.futures
import json
import logging
import os
import re
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple

from github_utils import GitHubClient

from .prompt_manager import PromptTemplateManager
from .models import PRInfo, FileChange
from .openai_client import OpenAIClient
from .chunk_analyzer import ChunkAnalyzer

class PRCommentGenerator:
    """改良版PRコメント生成を管理するクラス"""

    def __init__(self, log_level=logging.INFO):
        """OpenAIクライアントとGitHubクライアントを初期化"""
        # ロギングの設定
        self._setup_logging(log_level)
        
        # 現在のディレクトリから1つ上の階層のtemplatesディレクトリを指定
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(os.path.dirname(current_dir), 'templates')
        
        self.logger.info(f"Template directory path: {template_dir}")
        if not os.path.exists(template_dir):
            self.logger.warning(f"Warning: Template directory not found at {template_dir}")

        # カスタム再試行設定（環境変数から取得可能）
        retry_config = {
            'max_retries': int(os.getenv('OPENAI_MAX_RETRIES', '5')),
            'initial_backoff': float(os.getenv('OPENAI_INITIAL_BACKOFF', '1')),
            'max_backoff': float(os.getenv('OPENAI_MAX_BACKOFF', '60'))
        }

        # 初期化の順序を変更
        self.prompt_manager = PromptTemplateManager(template_dir)
        self.openai_client = OpenAIClient(self.prompt_manager, retry_config=retry_config)
        self.chunk_analyzer = ChunkAnalyzer(self.openai_client, log_level=log_level)
        self.github_client = GitHubClient(auth_method="app", app_id=os.getenv('GITHUB_APP_ID'), token=os.getenv('GITHUB_ACCESS_TOKEN'))
        
        # 大きなPR対応の設定
        self.max_files_to_process = int(os.getenv('MAX_FILES_TO_PROCESS', '50'))  # 最大処理ファイル数
        self.max_file_size = int(os.getenv('MAX_FILE_SIZE', '10000'))  # 最大ファイルサイズ（行数）
        self.parallel_processing = os.getenv('PARALLEL_PROCESSING', 'false').lower() == 'true'

    def _setup_logging(self, log_level):
        """ロギングの設定"""
        self.logger = logging.getLogger('pr_comment_generator')
        self.logger.setLevel(log_level)
        
        # ハンドラーがまだ設定されていない場合のみ追加
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def load_pr_data(self, pr_info_path: str, pr_diff_path: str) -> tuple[PRInfo, List[FileChange], List[str]]:
        """PR情報と差分情報を読み込み、必要なコンテキスト情報を追加（スキップファイル検出強化）"""
        try:
            # PR情報の読み込み
            with open(pr_info_path, 'r', encoding='utf-8') as f:
                pr_data = json.load(f)
                pr_info = PRInfo.from_json(pr_data)

            # 差分情報の読み込み
            with open(pr_diff_path, 'r', encoding='utf-8') as f:
                diff_data = json.load(f)
                self.logger.info(f"Loaded {len(diff_data)} file changes from diff")
                
                # 元のファイルリストを保存
                original_file_names = [file_data.get('filename') for file_data in diff_data]
                
                # ファイル数が多すぎる場合は制限
                if len(diff_data) > self.max_files_to_process:
                    self.logger.warning(
                        f"Too many files ({len(diff_data)}). Limiting to {self.max_files_to_process} files."
                    )
                    # 変更が大きいファイル順にソートして重要なものを処理
                    diff_data.sort(key=lambda x: x.get('changes', 0), reverse=True)
                    diff_data = diff_data[:self.max_files_to_process]
                
                changes = [FileChange.from_json(file_data) for file_data in diff_data]

            # 各ファイル名を追跡（スキップファイル検出用）
            processed_file_names = [change.filename for change in changes]
            
            # ファイルサイズが大きすぎないかチェック
            changes, skipped_from_size = self._filter_large_files(changes)
            
            # スキップされたファイル名を記録
            skipped_file_names = [f.filename for f in skipped_from_size]
            
            # 元のファイルリストとの差分からもスキップファイルを検出
            for original_file in original_file_names:
                if original_file not in processed_file_names and original_file not in skipped_file_names:
                    skipped_file_names.append(original_file)
                    self.logger.info(f"Detected skipped file: {original_file}")
            
            # 各ファイルの変更前後の内容を取得（並列処理オプション）
            if self.parallel_processing:
                changes = self._fetch_file_contents_parallel(pr_data, pr_info, changes)
            else:
                changes = self._fetch_file_contents_sequential(pr_data, pr_info, changes)

            return pr_info, changes, skipped_file_names
        except Exception as e:
            self.logger.error(f"Failed to load PR data: {str(e)}")
            traceback.print_exc()
            raise ValueError(f"Failed to load PR data: {str(e)}")

    def _filter_large_files(self, changes: List[FileChange]) -> Tuple[List[FileChange], List[FileChange]]:
        """大きすぎるファイルをフィルタリング（スキップされたファイルも返す）"""
        filtered_changes = []
        skipped_files = []
        
        for change in changes:
            # ファイルが大きすぎる場合はスキップ
            if change.changes > self.max_file_size:
                skipped_files.append(change)
                self.logger.warning(f"Skipping large file: {change.filename} ({change.changes} changes)")
                continue
                    
            # バイナリファイルなどもスキップ
            if self._is_binary_file(change.filename):
                skipped_files.append(change)
                self.logger.warning(f"Skipping binary file: {change.filename}")
                continue
                    
            filtered_changes.append(change)
        
        if skipped_files:
            self.logger.warning(f"Skipped {len(skipped_files)} large or binary files: {', '.join(f.filename for f in skipped_files[:5])}" + 
                            (f" and {len(skipped_files) - 5} more" if len(skipped_files) > 5 else ""))
        
        return filtered_changes, skipped_files
    
    def _is_binary_file(self, filename: str) -> bool:
        """ファイル名からバイナリファイルかどうかを判断"""
        binary_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.jar', '.class', '.exe', '.dll']
        for ext in binary_extensions:
            if filename.lower().endswith(ext):
                return True
        return False

    def _fetch_file_contents_sequential(self, pr_data: Dict, pr_info: PRInfo, changes: List[FileChange]) -> List[FileChange]:
        """ファイル内容を順次取得"""
        for i, change in enumerate(changes):
            self.logger.info(f"Fetching content for file {i+1}/{len(changes)}: {change.filename}")
            
            try:
                # ファイルの完全な内容を取得
                before_content, after_content = self.github_client.get_file_content(
                    owner=pr_data['base']['repo']['owner']['login'],
                    repo=pr_data['base']['repo']['name'],
                    path=change.filename,
                    base_sha=pr_info.base_sha,
                    head_sha=pr_info.head_sha
                )
                
                # 変更箇所の前後のコンテキストを取得（デフォルト: 前後10行）
                context_diff = self.github_client.get_change_context(
                    before_content, after_content, change.patch, context_lines=10
                )

                change.content_before = before_content
                change.content_after = after_content
                change.context_diff = context_diff
            except Exception as e:
                self.logger.error(f"Error fetching content for {change.filename}: {str(e)}")
                # エラーが発生しても完全に失敗させず、部分的な情報で続行
                change.content_before = None
                change.content_after = None
                change.context_diff = {"error": str(e)}
        
        return changes

    def _fetch_file_contents_parallel(self, pr_data: Dict, pr_info: PRInfo, changes: List[FileChange]) -> List[FileChange]:
        """ファイル内容を並列取得"""
        self.logger.info(f"Fetching content for {len(changes)} files in parallel")
        
        owner = pr_data['base']['repo']['owner']['login']
        repo = pr_data['base']['repo']['name']
        
        def fetch_single_file(change):
            try:
                # ファイルの完全な内容を取得
                before_content, after_content = self.github_client.get_file_content(
                    owner=owner,
                    repo=repo,
                    path=change.filename,
                    base_sha=pr_info.base_sha,
                    head_sha=pr_info.head_sha
                )
                
                # 変更箇所の前後のコンテキストを取得
                context_diff = self.github_client.get_change_context(
                    before_content, after_content, change.patch, context_lines=10
                )
                
                return (change, before_content, after_content, context_diff, None)
            except Exception as e:
                self.logger.error(f"Error fetching content for {change.filename}: {str(e)}")
                return (change, None, None, None, str(e))
        
        # ThreadPoolExecutorで並列処理
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(fetch_single_file, changes))
        
        # 結果を変更オブジェクトに反映
        for change, before_content, after_content, context_diff, error in results:
            if error:
                change.content_before = None
                change.content_after = None
                change.context_diff = {"error": error}
            else:
                change.content_before = before_content
                change.content_after = after_content
                change.context_diff = context_diff
        
        return changes

    def _normalize_file_paths(self, file_paths: List[str], base_paths: List[str] = None) -> List[str]:
        """
        ファイルパスを正規化して、重複を防止する
        
        Args:
            file_paths: 正規化するファイルパスのリスト
            base_paths: 参照用の完全なファイルパスのリスト（元のPR情報から取得）
            
        Returns:
            List[str]: 正規化されたファイルパスのリスト
        """
        normalized_paths = []
        
        # マッピング用の辞書
        file_name_to_full_path = {}
        
        # 完全なパスの辞書を作成（あれば）
        if base_paths:
            for path in base_paths:
                file_name = os.path.basename(path)
                file_name_to_full_path[file_name] = path
        
        # 各パスを正規化
        for path in file_paths:
            file_name = os.path.basename(path)
            
            # すでにフルパスがあれば、それを使用
            if path in file_name_to_full_path.values():
                normalized_paths.append(path)
            # ファイル名のみの場合で、マッピングがあれば完全なパスに変換
            elif file_name in file_name_to_full_path:
                normalized_paths.append(file_name_to_full_path[file_name])
            # どちらでもない場合は元のパスを使用
            else:
                normalized_paths.append(path)
        
        # 重複を削除
        return list(dict.fromkeys(normalized_paths))  # Python 3.7+ではdictは挿入順を保持する

    def _rebuild_file_section(self, comment: str, original_file_paths: List[str]) -> str:
        """
        「修正されたファイル」セクションを再構築して重複を排除する
        
        Args:
            comment: 元のコメント
            original_file_paths: オリジナルのファイルパスリスト
            
        Returns:
            str: 重複を排除した新しいコメント
        """
        self.logger.info("Rebuilding file section to remove duplicates")
        
        # ファイルセクションを抽出
        section_info = self._extract_file_section(comment)
        if not section_info:
            self.logger.warning("File section not found in summary, cannot fix duplicates")
            return comment
        
        file_section, section_start, section_end = section_info
        
        # ファイル情報を収集
        file_infos = self._collect_file_infos(file_section, original_file_paths)
        
        # 新しいセクションを構築
        new_file_section = self._build_new_file_section(file_infos)
        
        # コメントを再構築
        new_comment = comment[:section_start] + new_file_section + "\n" + comment[section_end:]
        
        return new_comment
    
    def _extract_file_section(self, comment: str) -> Optional[Tuple[str, int, int]]:
        """ファイルセクションを抽出する"""
        file_section_pattern = r"## 修正されたファイル\n(.*?)(?:\n##|\Z)"
        file_section_match = re.search(file_section_pattern, comment, re.DOTALL)
        
        if not file_section_match:
            return None
            
        return (
            file_section_match.group(1),
            file_section_match.start(),
            file_section_match.end()
        )
    
    def _collect_file_infos(self, file_section: str, original_file_paths: List[str]) -> Dict[str, str]:
        """ファイル情報を収集して正規化する"""
        file_infos = {}
        actual_file_paths = set(original_file_paths)
        
        for line in file_section.split('\n'):
            if not line.strip():
                continue
            
            file_info = self._parse_file_line(line, original_file_paths, actual_file_paths)
            if file_info:
                file_path, normalized_line = file_info
                if file_path not in file_infos:
                    file_infos[file_path] = normalized_line
        
        return file_infos
    
    def _parse_file_line(self, line: str, original_file_paths: List[str], 
                         actual_file_paths: set) -> Optional[Tuple[str, str]]:
        """ファイル行を解析して正規化する"""
        file_match = re.search(r'`([^`]+)`', line)
        if not file_match:
            return None
        
        file_path = file_match.group(1)
        
        # 実際のファイルパスかチェック
        normalized_path = self._normalize_single_file_path(file_path, original_file_paths, actual_file_paths)
        if not normalized_path:
            self.logger.info(f"Skipping non-file item: {file_path}")
            return None
        
        # 元のファイルパスを正規化されたパスに置き換え
        normalized_line = line.replace(f"`{file_path}`", f"`{normalized_path}`")
        return normalized_path, normalized_line
    
    def _normalize_single_file_path(self, file_path: str, original_file_paths: List[str], 
                                   actual_file_paths: set) -> Optional[str]:
        """単一のファイルパスを正規化する"""
        # 完全一致のチェック
        if file_path in actual_file_paths:
            return file_path
        
        # ファイル名だけの部分一致チェック
        base_name = os.path.basename(file_path)
        for orig_path in original_file_paths:
            if orig_path.endswith(base_name):
                return orig_path
        
        return None
    
    def _build_new_file_section(self, file_infos: Dict[str, str]) -> str:
        """新しいファイルセクションを構築する"""
        new_file_section = "## 修正されたファイル\n"
        
        # 既存のファイル情報を追加
        for file_path, info in file_infos.items():
            new_file_section += info + "\n"
        
        # スキップされたファイルを追加
        skipped_files = getattr(self, 'skipped_file_names', [])
        existing_paths = set(file_infos.keys())
        
        for skipped_file in skipped_files:
            if not any(skipped_file in path for path in existing_paths):
                new_file_section += f"- `{skipped_file}`: スキップされました（ファイルサイズが大きいか特殊形式のため）\n"
        
        return new_file_section



    def generate_comment(self, pr_info_path: str, pr_diff_path: str) -> Dict[str, Any]:
        """PRコメントを生成する（スキップファイルを確実に含める）
        
        Args:
            pr_info_path: PR情報のJSONファイルパス
            pr_diff_path: PR差分情報のJSONファイルパス
            
        Returns:
            Dict[str, Any]: 生成されたコメント、タイトル、使用統計などを含む辞書
        """
        start_time = time.time()
        all_files = []
        
        try:
            # データの読み込み（3つの戻り値を受け取る）
            self.logger.info(f"Loading PR data from {pr_info_path} and {pr_diff_path}")
            pr_info, changes, skipped_file_names = self.load_pr_data(pr_info_path, pr_diff_path)
            
            # クラス属性として保存（他のメソッドから参照できるように）
            self.pr_info = pr_info
            self.skipped_file_names = skipped_file_names
            
            # 読み込んだファイルの一覧を取得
            with open(pr_diff_path, 'r', encoding='utf-8') as f:
                original_files = json.load(f)
                all_files = [file_data.get('filename') for file_data in original_files]
            
            self.logger.info(f"Total files in PR: {len(all_files)}")
            self.logger.info(f"Processed files: {len(changes)}")
            self.logger.info(f"Skipped files: {len(skipped_file_names)}")
            if skipped_file_names:
                self.logger.info(f"Skipped file list: {', '.join(skipped_file_names)}")
            
            # ファイルが空の場合のハンドリング
            if not changes:
                self.logger.warning("No valid files to analyze")
                return {
                    'comment': "変更されたファイルがないか、すべてのファイルが大きすぎるためスキップされました。",
                    'suggested_title': "変更内容の分析",
                    'usage': self.openai_client.get_usage_stats(),
                    'pr_number': pr_info.number,
                    'file_count': len(all_files),
                    'processed_file_count': 0,
                    'skipped_file_count': len(skipped_file_names),
                    'skipped_files': skipped_file_names,
                    'error': "No valid files to analyze"
                }
            
            # openai_clientのgenerate_commentメソッドを直接呼び出すのではなく、分析と生成を分離
            # chunk分析はChunkAnalyzer経由で実行
            chunk_size = self.chunk_analyzer.calculate_optimal_chunk_size(changes)
            chunks = self.chunk_analyzer.split_into_chunks(changes, chunk_size)
            
            self.logger.info(f"Analyzing {len(chunks)} chunks with chunk size {chunk_size}")
            
            # チャンク分析を呼び出し
            chunk_analyses = []
            for i, chunk in enumerate(chunks, 1):
                self.logger.info(f"Analyzing chunk {i}/{len(chunks)} ({len(chunk)} files)...")
                try:
                    chunk_analysis = self.chunk_analyzer.analyze_single_chunk(pr_info, chunk, i)
                    chunk_analyses.append(chunk_analysis)
                except Exception as e:
                    self.logger.error(f"Error analyzing chunk {i}: {str(e)}")
                    # エラーが発生したチャンクをスキップして続行
                    chunk_analyses.append(f"[チャンク {i} の分析に失敗しました: {str(e)}]")
            
            # 最終サマリー生成
            self.logger.info("Generating final summary from chunk analyses")
            comment = self.openai_client._generate_final_summary(pr_info, chunk_analyses)
            
            # タイトル生成
            self.logger.info("Generating title from summary")
            generated_title = self.openai_client._generate_title_from_summary(comment)
            
            # ファイルリストの重複を修正
            self.logger.info("Fixing file path duplicates")
            original_paths = [change.filename for change in changes] + skipped_file_names
            comment = self._rebuild_file_section(comment, original_paths)
            
            # 実行時間の計算
            execution_time = time.time() - start_time
            
            # 結果の作成
            result = {
                'comment': comment,
                'suggested_title': generated_title,
                'usage': self.openai_client.get_usage_stats(),
                'pr_number': pr_info.number,
                'file_count': len(all_files),
                'processed_file_count': len(changes),
                'skipped_file_count': len(skipped_file_names),
                'skipped_files': skipped_file_names,
                'total_changes': sum(c.changes for c in changes),
                'execution_time_seconds': round(execution_time, 2)
            }
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error generating PR comment: {str(e)}")
            traceback.print_exc()
            
            # エラーが発生しても最低限の結果を返す
            return {
                'comment': f"PRの分析中にエラーが発生しました: {str(e)}",
                'suggested_title': "エラー: PRの分析に失敗",
                'usage': getattr(self, 'openai_client', {}).get_usage_stats() if hasattr(self, 'openai_client') else {},
                'pr_number': getattr(self.pr_info, 'number', 0) if hasattr(self, 'pr_info') else 0,
                'file_count': len(all_files) if 'all_files' in locals() else 0,
                'processed_file_count': len(changes) if 'changes' in locals() else 0,
                'skipped_file_count': len(skipped_file_names) if 'skipped_file_names' in locals() else 0,
                'skipped_files': skipped_file_names if 'skipped_file_names' in locals() else [],
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        
