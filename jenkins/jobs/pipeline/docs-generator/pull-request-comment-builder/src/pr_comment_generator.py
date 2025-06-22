# 標準ライブラリ
import argparse
import concurrent.futures
import datetime
import json
import logging
import os
import random
import re
import time
import traceback
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

# サードパーティライブラリ
from openai import OpenAI  

# ローカルモジュール
from github_utils import GitHubClient


@dataclass
class PRInfo:
    """PRの基本情報を保持するデータクラス"""
    title: str
    number: int
    body: Optional[str]
    author: str
    base_branch: str
    head_branch: str
    base_sha: str
    head_sha: str
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'PRInfo':
        """JSONデータからPRInfoを作成する"""
        return cls(
            title=data.get('title', ''),
            number=data.get('number', 0),
            body=data.get('body') or '',
            author=data.get('user', {}).get('login', ''),
            base_branch=data.get('base', {}).get('ref', ''),
            head_branch=data.get('head', {}).get('ref', ''),
            base_sha=data.get('base', {}).get('sha', ''),
            head_sha=data.get('head', {}).get('sha', '')
        )

@dataclass
class FileChange:
    """ファイルの変更内容を保持するデータクラス"""
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: Optional[str] = None
    content_before: Optional[str] = None  # 変更前のファイル内容
    content_after: Optional[str] = None   # 変更後のファイル内容
    context_diff: Optional[Dict[str, Any]] = field(default_factory=dict)  # 変更箇所の前後のコンテキスト

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'FileChange':
        """JSONデータからFileChangeを作成する"""
        return cls(
            filename=data.get('filename', ''),
            status=data.get('status', ''),
            additions=data.get('additions', 0),
            deletions=data.get('deletions', 0),
            changes=data.get('changes', 0),
            patch=data.get('patch')
        )

class PromptTemplateManager:
    """プロンプトテンプレートを管理するクラス"""
    
    def __init__(self, template_dir: str = "templates"):
        """
        初期化
        Args:
            template_dir: テンプレートファイルのディレクトリパス
        """
        self.template_dir = template_dir
        self._load_templates()
    
    def _load_templates(self):
        """テンプレートファイルを読み込む"""
        template_files = {
            'base': 'base_template.md',
            'chunk': 'chunk_analysis_extension.md',
            'summary': 'summary_extension.md'
        }
        
        self.templates = {}
        for key, filename in template_files.items():
            path = os.path.join(self.template_dir, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.templates[key] = f.read().strip()
            except FileNotFoundError:
                print(f"Warning: Template file {filename} not found")
                self.templates[key] = ""
    
    def get_chunk_analysis_prompt(self, pr_info_format: str) -> str:
        # テンプレートの内容を確認
        if not self.templates['base'] or not self.templates['chunk']:
            print("Warning: Template content is empty!")
        
        formatted_prompt = self.templates['base'].format(
            input_format=pr_info_format,
            additional_instructions=self.templates['chunk']
        )
        
        return formatted_prompt
    
    def get_summary_prompt(self, pr_info: PRInfo, analyses_text: str) -> str:
        """サマリー生成用のプロンプトを生成"""
        pr_info_format = (
            "### PR情報\n"
            f"- PR番号: {pr_info.number}\n"
            f"- タイトル: {pr_info.title}\n"
            f"- 作成者: {pr_info.author}\n"
            f"- ブランチ: {pr_info.base_branch} → {pr_info.head_branch}\n\n"
            "### 分析結果\n"
            f"{analyses_text}"
        )
        
        return self.templates['base'].format(
            input_format=pr_info_format,
            additional_instructions=self.templates['summary']
        )

class TokenEstimator:
    """トークン数を推定するためのユーティリティクラス"""
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """テキストのトークン数を大まかに推定する
        
        英語の場合、平均的に4文字で1トークン程度になる
        日本語の場合、大体1文字で1.5トークン程度と言われる
        ここでは安全側に見積もって、より大きい方を使用
        """
        # 日本語と英語の混在を考慮して保守的に見積もる
        japanese_chars = sum(1 for c in text if ord(c) > 0x3000)
        total_chars = len(text)
        
        # 日本語文字が50%以上ならより高いレートを適用
        if japanese_chars / total_chars > 0.5:
            return int(total_chars * 1.5)  # 日本語主体
        else:
            return int(total_chars / 4)    # 英語主体
    
    @staticmethod
    def truncate_to_token_limit(text: str, max_tokens: int) -> str:
        """最大トークン数に収まるようにテキストを切り詰める"""
        if TokenEstimator.estimate_tokens(text) <= max_tokens:
            return text
        
        # 大まかに文字数換算してカット
        chars_per_token = 4  # 英語中心の場合の概算
        max_chars = max_tokens * chars_per_token
        
        if len(text) <= max_chars:
            return text
            
        # 前半と後半から重要な部分を取得
        half_chars = max_chars // 2
        first_part = text[:half_chars]
        last_part = text[-half_chars:]
        
        return first_part + "\n...[中略]...\n" + last_part


class OpenAIClient:
    """OpenAI APIとのインタラクションを管理するクラス"""
    
    # APIレート制限のデフォルト設定
    DEFAULT_MAX_RETRIES = 5
    DEFAULT_INITIAL_BACKOFF = 1  # 秒
    DEFAULT_MAX_BACKOFF = 60  # 秒
    
    # トークン制限の管理
    MAX_TOKENS_PER_REQUEST = 16000  # GPT-4の一般的な入力制限の安全側
    MAX_PATCH_TOKENS = 2000  # パッチに割り当てる最大トークン
    MAX_CONTENT_TOKENS = 3000  # ファイル内容に割り当てる最大トークン
    
    def __init__(self, prompt_manager, retry_config=None, log_level=logging.INFO):
        """
        環境変数から認証情報を取得してクライアントを初期化
        
        Args:
            prompt_manager: プロンプトテンプレート管理クラスのインスタンス
            retry_config: 再試行設定
            log_level: ロギングレベル
        """
        # ロガーの設定
        self._setup_logging(log_level)
        
        # 環境変数から認証情報を取得
        api_key = os.getenv('OPENAI_API_KEY')
        model_name = os.getenv('OPENAI_MODEL_NAME', 'gpt-4o')  # デフォルトモデル名

        if not api_key:
            raise ValueError("Missing required environment variable: OPENAI_API_KEY")

        print(f"Debug: Using OpenAI model {model_name}")

        self.model = model_name
        self.prompt_manager = prompt_manager
        
        # 再試行設定
        self.retry_config = retry_config or {
            'max_retries': self.DEFAULT_MAX_RETRIES,
            'initial_backoff': self.DEFAULT_INITIAL_BACKOFF,
            'max_backoff': self.DEFAULT_MAX_BACKOFF
        }
        
        # OpenAI用のクライアント初期化
        try:
            self.client = OpenAI(
                api_key=api_key,
            )
            self.usage_stats = {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'retries': 0,
                'skipped_files': 0
            }
            
            print(f"Debug: OpenAI client initialized successfully")
            
        except Exception as e:
            raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")

    def _setup_logging(self, log_level):
        """ロギングの設定"""
        self.logger = logging.getLogger('openai_client')
        self.logger.setLevel(log_level)
        
        # ハンドラーがまだ設定されていない場合のみ追加
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _save_prompt_and_result(self, prompt: str, result: str, chunk_index: int = 0, phase: str = "chunk") -> None:
        """
        プロンプトとその実行結果を個別のファイルに保存する
        
        Args:
            prompt: OpenAIに送信したプロンプト
            result: OpenAIからの応答結果
            chunk_index: チャンク番号（0の場合は最終サマリーなど）
            phase: 処理フェーズ（chunk, summary, title など）
        """
        try:
            # 環境変数で設定を取得（デフォルトをtrueに変更）
            save_prompts = os.getenv('SAVE_PROMPTS', 'true').lower() == 'true'
            if not save_prompts:
                self.logger.info("Prompt saving is disabled. Set SAVE_PROMPTS=true to enable.")
                return
                
            # 出力ディレクトリの作成
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            pr_number = getattr(self.pr_info, 'number', 'unknown') if hasattr(self, 'pr_info') else 'unknown'
            
            output_dir = os.getenv('PROMPT_OUTPUT_DIR', '/prompts')
            pr_output_dir = os.path.join(output_dir, f"pr_{pr_number}_{timestamp}")
            
            # 出力ディレクトリのチェックと作成
            if not os.path.exists(pr_output_dir):
                os.makedirs(pr_output_dir, exist_ok=True)
                self.logger.info(f"Created prompt output directory: {pr_output_dir}")
            
            # ファイル名の作成
            if chunk_index > 0:
                prompt_filename = f"{phase}_chunk{chunk_index}_prompt.txt"
                result_filename = f"{phase}_chunk{chunk_index}_result.txt"
            else:
                prompt_filename = f"{phase}_prompt.txt"
                result_filename = f"{phase}_result.txt"
            
            # プロンプトの保存
            prompt_path = os.path.join(pr_output_dir, prompt_filename)
            with open(prompt_path, 'w', encoding='utf-8') as f:
                f.write(prompt)
            
            # 結果の保存
            result_path = os.path.join(pr_output_dir, result_filename)
            with open(result_path, 'w', encoding='utf-8') as f:
                f.write(result)
            
            # 使用統計情報の保存（JSONファイル）
            meta_info = {
                "timestamp": timestamp,
                "pr_number": pr_number,
                "phase": phase,
                "chunk_index": chunk_index,
                "prompt_length": len(prompt),
                "result_length": len(result),
                "usage_stats": self.get_usage_stats() if hasattr(self, 'get_usage_stats') else {}
            }
            
            meta_path = os.path.join(pr_output_dir, f"{phase}_chunk{chunk_index}_meta.json" if chunk_index > 0 else f"{phase}_meta.json")
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta_info, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved prompt and result for {phase} {'chunk ' + str(chunk_index) if chunk_index > 0 else ''}")
            self.logger.info(f"  Prompt saved to: {prompt_path}")
            self.logger.info(f"  Result saved to: {result_path}")
            self.logger.info(f"  Metadata saved to: {meta_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving prompt and result: {str(e)}")
            traceback.print_exc()
            # ログには残すが、メイン処理は継続するため例外は再発生させない

    def _call_openai_api(self, messages: List[Dict[str, str]], max_tokens: int = 2000) -> str:
        """
        OpenAI APIを呼び出し、レート制限に対応した再試行ロジックを実装
        
        Args:
            messages: 送信するメッセージリスト
            max_tokens: 生成する最大トークン数
            
        Returns:
            str: 生成されたテキスト
        """
        retries = 0
        backoff = self.retry_config['initial_backoff']
        
        # 送信するプロンプトの内容（システムメッセージとユーザーメッセージの結合）
        prompt_content = "\n\n".join([f"[{msg['role']}]\n{msg['content']}" for msg in messages])
        
        while retries <= self.retry_config['max_retries']:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=max_tokens,
                    top_p=0.1,
                    frequency_penalty=0.0,
                    presence_penalty=0.0
                    # response_format={"type": "text"} を削除（OpenAI APIでは不要）
                )

                # トークン使用量の記録
                usage = response.usage
                self.usage_stats['prompt_tokens'] += usage.prompt_tokens
                self.usage_stats['completion_tokens'] += usage.completion_tokens

                generated_content = response.choices[0].message.content.strip()
                
                # ログ出力（一部省略）
                self.logger.info("\nReceived response from OpenAI API:")
                self.logger.info("=" * 80)
                self.logger.info(generated_content[:500] + ("..." if len(generated_content) > 500 else ""))
                self.logger.info("=" * 80)
                self.logger.info(f"Token usage - Prompt: {usage.prompt_tokens}, Completion: {usage.completion_tokens}, Total: {usage.total_tokens}")

                # プロンプトと結果を保存
                # チャンク番号などのコンテキスト情報は呼び出し側から提供される必要がある
                if hasattr(self, '_current_chunk_index') and hasattr(self, '_current_phase'):
                    self._save_prompt_and_result(
                        prompt_content, 
                        generated_content, 
                        getattr(self, '_current_chunk_index', 0),
                        getattr(self, '_current_phase', 'unknown')
                    )

                return generated_content
                    
            except Exception as e:
                retries += 1
                self.usage_stats['retries'] += 1
                
                # レート制限エラーの場合の特別処理
                if hasattr(e, 'status_code') and e.status_code == 429:
                    # エラーメッセージから待機時間を抽出
                    wait_time = self._extract_wait_time_from_error(str(e))
                    if wait_time and wait_time > 600:  # 10分以上の待機が必要な場合
                        self.logger.error(f"Rate limit exceeded. API requires {wait_time} seconds wait. Skipping this request.")
                        raise ValueError(f"Rate limit exceeded. Required wait time too long: {wait_time} seconds")
                    
                    # 待機時間が指定されていればそれを使用、なければバックオフを計算
                    sleep_time = wait_time if wait_time else backoff
                    self.logger.warning(f"Rate limit exceeded. Retrying in {sleep_time} seconds... (Attempt {retries}/{self.retry_config['max_retries']})")
                else:
                    self.logger.error(f"API error: {str(e)}. Retrying in {backoff} seconds... (Attempt {retries}/{self.retry_config['max_retries']})")
                    sleep_time = backoff
                
                # 指数バックオフ + ジッター
                if retries < self.retry_config['max_retries']:
                    time.sleep(sleep_time + random.uniform(0, 1))
                    backoff = min(backoff * 2, self.retry_config['max_backoff'])
                else:
                    self.logger.error(f"Maximum retries reached. Failed to get response from API.")
                    raise
    
    def _extract_wait_time_from_error(self, error_message: str) -> Optional[int]:
        """エラーメッセージから待機時間を抽出"""
        
        # レート制限エラーメッセージから待機時間を抽出するパターン
        pattern = r"retry after (\d+) seconds"
        match = re.search(pattern, error_message.lower())
        
        if match:
            return int(match.group(1))
        return None

    def generate_comment(self, pr_info: PRInfo, changes: List[FileChange]) -> tuple[str, str, List[FileChange]]:
        """
        PRの内容を分析してコメントを生成（チャンク分割と最大サイズ制限）
        
        Args:
            pr_info: PR情報
            changes: ファイル変更リスト
            
        Returns:
            tuple[str, str, List[FileChange]]: (生成されたサマリー, 生成されたタイトル, スキップされたファイルリスト)
        """
        # 大きなファイルのフィルタリングと前処理
        filtered_changes, skipped_files = self._preprocess_file_changes(changes)
        
        if skipped_files:
            self.logger.info(f"Skipped {len(skipped_files)} large files: {', '.join(f.filename for f in skipped_files)}")
            self.usage_stats['skipped_files'] += len(skipped_files)
        
        if not filtered_changes:
            return "No files to analyze or all files were skipped due to size limitations.", "PRの分析結果", skipped_files
        
        # 動的なチャンクサイズ計算
        chunk_size = self._calculate_optimal_chunk_size(filtered_changes)
        print(f"Using dynamic chunk size: {chunk_size} files per chunk")
        
        # チャンクに分割
        chunks = self._split_changes_into_chunks(filtered_changes, chunk_size=chunk_size)
        
        # 各チャンクの分析結果を保存
        chunk_analyses = []
        
        for i, chunk in enumerate(chunks, 1):
            print(f"\nAnalyzing chunk {i}/{len(chunks)} ({len(chunk)} files)...")
            try:
                chunk_analysis = self._analyze_chunk(pr_info, chunk)
                chunk_analyses.append(chunk_analysis)
            except ValueError as e:
                self.logger.error(f"Error analyzing chunk {i}: {str(e)}")
                # エラーが発生したチャンクをスキップして続行
                chunk_analyses.append(f"[チャンク {i} の分析に失敗しました: {str(e)}]")
        
        # 最終的なサマリーを生成
        final_summary = self._generate_final_summary(pr_info, chunk_analyses, skipped_files)
        
        # サマリーを基にタイトルを生成
        generated_title = self._generate_title_from_summary(final_summary)
        self.logger.info(f"\nGenerated Title: {generated_title}")

        return final_summary, generated_title, skipped_files

    def _preprocess_file_changes(self, changes: List[FileChange]) -> Tuple[List[FileChange], List[FileChange]]:
        """ファイル変更リストを前処理し、大きすぎるファイルをフィルタリング"""
        filtered_changes = []
        skipped_files = []
        
        for change in changes:
            # バイナリファイルやサイズが巨大なファイルをスキップ
            if self._should_skip_file(change):
                skipped_files.append(change)
                continue
                
            # 大きなファイルの内容を切り詰め
            self._truncate_large_file_content(change)
            filtered_changes.append(change)
        
        return filtered_changes, skipped_files
    
    def _should_skip_file(self, change: FileChange) -> bool:
        """このファイルをスキップすべきかどうかを判断"""
        # バイナリファイルや画像、ビルドファイルなどをスキップ
        binary_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.jar', '.class', '.min.js']
        for ext in binary_extensions:
            if change.filename.endswith(ext):
                return True
        
        # JSONファイルが一定サイズを超える場合はスキップ
        if change.filename.endswith('.json') and (change.additions + change.deletions > 10000):
            return True
            
        # 大規模なデータファイルをスキップ
        data_extensions = ['.csv', '.tsv', '.xlsx', '.parquet']
        for ext in data_extensions:
            if change.filename.endswith(ext):
                return True
        
        # 変更内容が非常に大きい場合はスキップ
        if change.changes > 20000:  # 2万行以上の変更
            return True
            
        return False
    
    def _truncate_large_file_content(self, change: FileChange) -> None:
        """大きなファイルの内容を切り詰める"""
        # パッチの切り詰め
        if change.patch:
            change.patch = TokenEstimator.truncate_to_token_limit(
                change.patch, self.MAX_PATCH_TOKENS
            )
        
        # ファイル内容の切り詰め
        if change.content_before:
            change.content_before = TokenEstimator.truncate_to_token_limit(
                change.content_before, self.MAX_CONTENT_TOKENS
            )
            
        if change.content_after:
            change.content_after = TokenEstimator.truncate_to_token_limit(
                change.content_after, self.MAX_CONTENT_TOKENS
            )

    def _calculate_optimal_chunk_size(self, changes: List[FileChange]) -> int:
        """変更リストに基づいて最適なチャンクサイズを計算"""
        # ファイル数とサイズから最適なチャンクサイズを判断
        total_files = len(changes)
        
        if total_files <= 2:
            return total_files  # ファイル数が少ない場合は全て1チャンクに
        
        # 各ファイルの変更行数とファイルサイズを確認
        for change in changes:
            # 個別のファイルが非常に大きい場合は1ファイル1チャンクにする
            if change.changes > 300 or (change.content_before and len(change.content_before) > 10000) or (change.content_after and len(change.content_after) > 10000):
                self.logger.info(f"Large file detected: {change.filename} with {change.changes} changes. Using 1 file per chunk.")
                return 1
        
        # ファイルの平均サイズを見積もる
        avg_file_size = sum(c.changes for c in changes) / total_files
        
        if avg_file_size > 200:
            self.logger.info(f"Average file size is large: {avg_file_size:.1f} changes. Using 1 file per chunk.")
            return 1  # ファイルが大きい場合は1ファイルずつ処理
        elif avg_file_size > 100:
            self.logger.info(f"Average file size is medium: {avg_file_size:.1f} changes. Using 2 files per chunk.")
            return 2  # 中程度のサイズなら2ファイルずつ
        else:
            self.logger.info(f"Average file size is small: {avg_file_size:.1f} changes. Using 3 files per chunk.")
            return 3  # 小さいファイルなら3ファイルずつ（デフォルト）

    def _split_changes_into_chunks(self, changes: List[FileChange], chunk_size: int = 3) -> List[List[FileChange]]:
        """変更リストを小さなチャンクに分割（重要なファイル優先）"""
        if chunk_size <= 0:
            chunk_size = 1
        
        # 変更量に基づいてファイルを並べ替え（大きな変更が先）
        sorted_changes = sorted(changes, key=lambda c: c.changes, reverse=True)
        
        # 大規模な変更（main.pyなど）を個別のチャンクに
        large_files = []
        normal_files = []
        
        for change in sorted_changes:
            # 変更行数が多いファイルは個別チャンクに
            if change.changes > 300:
                large_files.append([change])
            # ソースコードファイルが大きい場合も個別チャンクに
            elif (change.filename.endswith('.py') or change.filename.endswith('.js') or change.filename.endswith('.java') or change.filename.endswith('.ts')) and change.changes > 100:
                large_files.append([change])
            else:
                normal_files.append(change)
        
        # 残りのファイルを指定サイズのチャンクに分割
        normal_chunks = [normal_files[i:i + chunk_size] for i in range(0, len(normal_files), chunk_size)]
        
        # 大きなファイルのチャンクと通常チャンクを結合
        all_chunks = large_files + normal_chunks
        
        self.logger.info(f"Split {len(changes)} files into {len(all_chunks)} chunks " +
                    f"({len(large_files)} individual large files, {len(normal_chunks)} normal chunks)")
        
        return all_chunks

    def _analyze_chunk(self, pr_info: PRInfo, changes: List[FileChange], chunk_index: int = 0) -> str:
        """
        チャンク単位での分析を実行（チャンク番号を追加。デフォルト値を設定）
        
        Args:
            pr_info: PR情報
            changes: 分析対象のファイル変更リスト
            chunk_index: チャンク番号（デフォルト: 0）
            
        Returns:
            str: 生成された分析結果
        """
        # チャンク番号と処理フェーズを記録（_call_openai_apiで使用）
        self._current_chunk_index = chunk_index
        self._current_phase = "chunk"
        # 単一ファイルの場合と複数ファイルの場合で戦略を変える
        is_single_file = len(changes) == 1
        
        # PR情報のJSON形式
        pr_json = {
            'title': pr_info.title,
            'number': pr_info.number,
            'body': (pr_info.body or '')[:500] if pr_info.body else '',
            'author': pr_info.author,
            'base_branch': pr_info.base_branch,
            'head_branch': pr_info.head_branch
        }

        # 変更ファイル情報のJSON形式
        changes_json = []
        for change in changes:
            # 単一ファイルの場合はパッチ情報をできるだけ保持する
            if is_single_file:
                # パッチ情報の処理（最大サイズを緩和）
                if change.patch:
                    # 単一ファイルの場合は、より多くのパッチ情報を保持
                    patch_limit = 8000 if change.changes > 400 else 5000
                    if len(change.patch) > patch_limit:
                        # 重要な部分を保持するため、前半をより多く取得
                        front_part = int(patch_limit * 0.7)  # 前半70%
                        back_part = patch_limit - front_part  # 残り30%
                        patch = change.patch[:front_part] + "\n...[中略]...\n" + change.patch[-back_part:]
                    else:
                        patch = change.patch
                else:
                    patch = ''
                    
                # コンテキスト情報は単一ファイルの場合は減らす
                context = {
                    'before': None,  # 単一大きなファイルの場合はbeforeは除外
                    'after': None,   # 単一大きなファイルの場合はafterは除外
                    'diff_context': self._limit_diff_context(change.context_diff)
                }
            else:
                # 複数ファイルの場合は従来通りパッチ情報を調整
                if change.patch:
                    if len(change.patch) > 3000:
                        patch = change.patch[:1500] + "\n...[中略]...\n" + change.patch[-1500:]
                    else:
                        patch = change.patch
                else:
                    patch = ''
                    
                # 複数ファイルの場合はコンテキスト情報も保持
                context = {
                    'before': self._truncate_content(change.content_before, 1000) if change.content_before else None,
                    'after': self._truncate_content(change.content_after, 1000) if change.content_after else None,
                    'diff_context': self._limit_diff_context(change.context_diff)
                }

            # 変更ファイルのJSONデータ作成
            change_obj = {
                'filename': change.filename,
                'status': change.status,
                'additions': change.additions,
                'deletions': change.deletions,
                'changes': change.changes,
                'patch': patch,
                'context': context
            }
            changes_json.append(change_obj)

        # チャンク全体を含むJSONの作成
        input_json = {
            "pr_info": pr_json,
            "changes": changes_json
        }
        
        # JSONをテキストに変換してトークン数を推定
        input_json_text = json.dumps(input_json, ensure_ascii=False, indent=2)
        estimated_tokens = TokenEstimator.estimate_tokens(input_json_text)
        
        # トークン数が多すぎる場合は徐々に削減
        if estimated_tokens > self.MAX_TOKENS_PER_REQUEST * 0.8:  # 80%のマージンを取る
            self.logger.warning(f"Input size ({estimated_tokens} est. tokens) exceeds limit. Reducing context...")
            
            # 単一ファイルの場合のトークン削減戦略
            if is_single_file:
                # まずパッチ情報を調整（大幅に削減せず重要部分を残す）
                for change_obj in changes_json:
                    # パッチ情報の調整（まだ大きいが、完全には削除しない）
                    patch_size = len(change_obj['patch'])
                    if patch_size > 6000:
                        # 追加/削除行数の情報を元にパッチの重要部分を特定
                        patch_lines = change_obj['patch'].split('\n')
                        
                        # 追加行（+で始まる）と削除行（-で始まる）を優先的に保持
                        important_lines = []
                        other_lines = []
                        
                        for line in patch_lines:
                            if line.startswith('+') or line.startswith('-'):
                                important_lines.append(line)
                            else:
                                other_lines.append(line)
                        
                        # 重要な行を優先的に保持（最大3000行）
                        preserved_important = important_lines[:3000]
                        
                        # コンテキスト行も少し保持（最大1000行）
                        preserved_context = other_lines[:1000]
                        
                        # 結合して新しいパッチを作成
                        new_patch = "\n".join(preserved_important + ["\n...[コンテキスト省略]...\n"] + preserved_context)
                        change_obj['patch'] = new_patch
                    
                    # コンテキスト情報は完全に削除
                    change_obj['context'] = {"note": "大きなファイルのためコンテキスト情報省略"}
            else:
                # 複数ファイルの場合は通常の削減戦略
                for change_obj in changes_json:
                    change_obj['context']['before'] = None
                    change_obj['context']['after'] = None
                    # パッチの削減
                    if change_obj['patch'] and len(change_obj['patch']) > 1000:
                        change_obj['patch'] = change_obj['patch'][:500] + "\n...[中略]...\n" + change_obj['patch'][-500:]
            
            # 再度サイズを確認
            input_json = {"pr_info": pr_json, "changes": changes_json}
            input_json_text = json.dumps(input_json, ensure_ascii=False, indent=2)
            new_estimated_tokens = TokenEstimator.estimate_tokens(input_json_text)
            self.logger.info(f"Reduced input size to {new_estimated_tokens} est. tokens")
            
            # それでも大きすぎる場合はさらに削減
            if new_estimated_tokens > self.MAX_TOKENS_PER_REQUEST * 0.9:
                self.logger.warning("Input still too large, further reducing patches...")
                
                if is_single_file:
                    # 単一ファイルの場合は、パッチを部分的に保持
                    for change_obj in changes_json:
                        # パッチを1500行程度に削減
                        if len(change_obj['patch']) > 1500:
                            # 最初と最後の部分を保持
                            change_obj['patch'] = change_obj['patch'][:1000] + "\n...[大部分省略]...\n" + change_obj['patch'][-500:]
                else:
                    # 複数ファイルの場合はパッチ情報を完全に除去
                    for change_obj in changes_json:
                        change_obj['patch'] = f"[パッチ情報省略: {change_obj['additions']} 行追加, {change_obj['deletions']} 行削除]"
                        change_obj['context'] = {"note": "コンテキスト情報省略"}
                
                input_json = {"pr_info": pr_json, "changes": changes_json}
                input_json_text = json.dumps(input_json, ensure_ascii=False, indent=2)
                final_tokens = TokenEstimator.estimate_tokens(input_json_text)
                
                # 最終チェック
                if final_tokens > self.MAX_TOKENS_PER_REQUEST * 0.95:
                    if is_single_file:
                        # 単一ファイルの場合でも最終手段としてパッチを大幅削減
                        for change_obj in changes_json:
                            # ファイル名と変更統計情報のみ残し、最小限のパッチを表示
                            change_obj['patch'] = f"[パッチ大部分省略: {change_obj['additions']} 行追加, {change_obj['deletions']} 行削除]\n"
                            # 追加/削除行のサンプルを少し残す（各50行程度）
                            if change.patch:
                                sample_lines = []
                                lines = change.patch.split('\n')
                                add_count = del_count = 0
                                for line in lines:
                                    if line.startswith('+') and add_count < 50:
                                        sample_lines.append(line)
                                        add_count += 1
                                    elif line.startswith('-') and del_count < 50:
                                        sample_lines.append(line)
                                        del_count += 1
                                    if add_count >= 50 and del_count >= 50:
                                        break
                                if sample_lines:
                                    change_obj['patch'] += "\nサンプル変更内容:\n" + "\n".join(sample_lines)
                    else:
                        # 複数ファイルの場合は完全に情報を削減
                        for change_obj in changes_json:
                            change_obj['patch'] = f"[パッチ情報省略: {change_obj['additions']} 行追加, {change_obj['deletions']} 行削除]"
                            change_obj['context'] = {"note": "トークン制限のため省略"}
                    
                    input_json = {"pr_info": pr_json, "changes": changes_json}
                    input_json_text = json.dumps(input_json, ensure_ascii=False, indent=2)
                    very_final_tokens = TokenEstimator.estimate_tokens(input_json_text)
                    
                    if very_final_tokens > self.MAX_TOKENS_PER_REQUEST * 0.98:
                        raise ValueError(f"Input still too large for API ({very_final_tokens} est. tokens) even after maximum reduction")
                
                self.logger.info(f"Final input size after maximum reduction: {final_tokens} est. tokens")

        # 入力形式の作成
        input_format = (
            "### pr_info.json\n"
            f"{json.dumps(pr_json, indent=2)}\n\n"
            "### pr_diff.json\n"
            f"{json.dumps(changes_json, indent=2)}"
        )
        
        # プロンプトの取得
        chunk_prompt = self.prompt_manager.get_chunk_analysis_prompt(input_format)

        # APIリクエスト用のメッセージ作成
        messages = [
            {
                "role": "system",
                "content": "あなたは変更内容を分かりやすく説明する技術ライターです。"
            },
            {
                "role": "user",
                "content": chunk_prompt
            }
        ]

        # API呼び出し
        return self._call_openai_api(messages)

    def _truncate_content(self, content: Optional[str], max_length: int) -> Optional[str]:
        """ファイル内容を指定された長さに切り詰める"""
        if not content:
            return None
        if len(content) <= max_length:
            return content
        
        # 半分ずつ前後から取る
        half_length = max_length // 2
        return content[:half_length] + "\n...[中略]...\n" + content[-half_length:]

    def _limit_diff_context(self, context_diff: Dict[str, Any]) -> Dict[str, Any]:
        """差分コンテキストをトークン制限に合わせて制限する"""
        if not context_diff:
            return {}
            
        result = {}
        for k, v in context_diff.items():
            if isinstance(v, str) and len(v) > 1000:
                result[k] = v[:500] + "\n...[中略]...\n" + v[-500:]
            else:
                result[k] = v
        return result

    def _estimate_chunk_tokens(self, pr_info: PRInfo, changes: List[FileChange]) -> int:
        """チャンク全体のトークン数を概算する"""
        # PR情報の概算トークン数
        pr_info_str = f"{pr_info.title} {pr_info.number} {pr_info.author} {pr_info.base_branch} {pr_info.head_branch}"
        if pr_info.body:
            pr_info_str += pr_info.body[:500]
        
        pr_tokens = TokenEstimator.estimate_tokens(pr_info_str)
        
        # ファイル変更の概算トークン数
        changes_tokens = 0
        for change in changes:
            file_str = f"{change.filename} {change.status} {change.additions} {change.deletions} {change.changes}"
            
            if change.patch:
                file_str += change.patch[:1000] if len(change.patch) > 1000 else change.patch
            
            if change.content_before:
                content_sample = change.content_before[:500] if len(change.content_before) > 500 else change.content_before
                file_str += content_sample
            
            if change.content_after:
                content_sample = change.content_after[:500] if len(change.content_after) > 500 else change.content_after
                file_str += content_sample
            
            changes_tokens += TokenEstimator.estimate_tokens(file_str)
        
        # 固定オーバーヘッドの追加（JSONフォーマット、プロンプトなど）
        overhead_tokens = 1000
        
        total_tokens = pr_tokens + changes_tokens + overhead_tokens
        return total_tokens

    def _clean_markdown_format(self, text: str) -> str:
        """マークダウンのフォーマットをクリーンアップ"""
        # コードブロックマーカーの削除
        text = re.sub(r'^```markdown\s*\n', '', text)  # 先頭の```markdownを削除
        text = re.sub(r'\n```\s*$', '', text)          # 末尾の```を削除
        return text.strip()                             # 余分な空白を削除

    def _generate_final_summary(self, pr_info: PRInfo, chunk_analyses: List[str], skipped_files: List[FileChange] = None) -> str:
        """各チャンクの分析結果を統合して最終的なサマリーを生成"""
        # チャンクが1つしかない場合は、そのまま使用
        if len(chunk_analyses) == 1 and not skipped_files:
            return self._clean_markdown_format(chunk_analyses[0])

        self.logger.info("\nGenerating final summary")
        self.logger.info(f"Number of chunk analyses: {len(chunk_analyses)}")
        if skipped_files:
            self.logger.info(f"Number of skipped files: {len(skipped_files)}")
        
        # 分析結果からファイル名を抽出
        all_files = set()
        for analysis in chunk_analyses:
            # 正規表現でファイル名を抽出（`のついたファイルパスを探す）
            file_matches = re.findall(r'`([^`]+\.[^`]+)`', analysis)
            all_files.update(file_matches)
        
        # スキップされたファイル名も追加
        if skipped_files:
            skipped_file_names = {f.filename for f in skipped_files}
            all_files.update(skipped_file_names)
        
        self.logger.info(f"Total files mentioned in analyses: {len(all_files)}")
        
        # チャンク分析が多すぎる場合は削減
        if len(chunk_analyses) > 10:
            self.logger.warning(f"Too many chunk analyses ({len(chunk_analyses)}). Keeping only the first 5 and last 5.")
            kept_analyses = chunk_analyses[:5] + ['...中略...'] + chunk_analyses[-5:]
        else:
            kept_analyses = chunk_analyses
        
        # 分析結果を結合
        analyses_text = "\n\n".join([
            f"=== チャンク {i+1} ===\n{analysis}"
            for i, analysis in enumerate(kept_analyses)
        ])
        
        # ファイル一覧を追加
        analyses_text += f"\n\n## 全ファイル一覧\n{', '.join(sorted(all_files))}"
        
        # スキップされたファイルがあれば情報を追加
        if skipped_files:
            skipped_info = "\n\n## スキップされたファイル\n"
            skipped_info += "以下のファイルはサイズが大きすぎるため詳細分析からスキップされましたが、変更内容に含まれています：\n"
            for f in skipped_files:
                skipped_info += f"- `{f.filename}` ({f.additions} 行追加, {f.deletions} 行削除, 合計 {f.changes} 行変更)\n"
            analyses_text += skipped_info
        
        # 総トークン数を見積もる
        est_tokens = TokenEstimator.estimate_tokens(analyses_text)
        if est_tokens > self.MAX_TOKENS_PER_REQUEST * 0.7:  # 70%制限で安全マージン
            self.logger.warning(f"Summary too large ({est_tokens} est. tokens). Truncating.")
            # チャンク数に応じて各チャンクの内容を削減
            if len(kept_analyses) > 2:
                max_tokens_per_chunk = (self.MAX_TOKENS_PER_REQUEST * 0.6) / len(kept_analyses)
                truncated_analyses = []
                for i, analysis in enumerate(kept_analyses):
                    truncated = TokenEstimator.truncate_to_token_limit(analysis, int(max_tokens_per_chunk))
                    truncated_analyses.append(truncated)
                
                analyses_text = "\n\n".join([
                    f"=== チャンク {i+1} ===\n{analysis}"
                    for i, analysis in enumerate(truncated_analyses)
                ])
                
                # ファイル一覧とスキップファイル情報を再度追加（これは保持する）
                analyses_text += f"\n\n## 全ファイル一覧\n{', '.join(sorted(all_files))}"
                
                if skipped_files:
                    skipped_info = "\n\n## スキップされたファイル\n"
                    skipped_info += "以下のファイルはサイズが大きすぎるため詳細分析からスキップされましたが、変更内容に含まれています：\n"
                    for f in skipped_files:
                        skipped_info += f"- `{f.filename}` ({f.additions} 行追加, {f.deletions} 行削除, 合計 {f.changes} 行変更)\n"
                    analyses_text += skipped_info

        # プロンプトを生成
        summary_prompt = self.prompt_manager.get_summary_prompt(pr_info, analyses_text)
        
        # ファイル一覧を明示的にプロンプトに追加
        file_list_prompt = f"\n\n## 必ず含めるべきファイル一覧\n{', '.join(sorted(all_files))}\n\n"
        file_list_prompt += "最終サマリーには、上記のすべてのファイル（スキップされたファイルを含む）を「修正されたファイル」セクションに含めてください。"
        
        if skipped_files:
            file_list_prompt += "\n\nスキップされたファイルも必ず「修正されたファイル」セクションに含めてください。"
            file_list_prompt += "\n\nスキップされたファイル: " + ", ".join(f"`{f.filename}`" for f in skipped_files)
        
        summary_prompt += file_list_prompt

        messages = [
            {
                "role": "system",
                "content": "あなたは変更内容を分かりやすく説明する技術ライターです。"
                "与えられたフォーマットに厳密に従ってドキュメントを作成してください。"
            },
            {
                "role": "user",
                "content": summary_prompt
            }
        ]

        result = self._call_openai_api(messages)
        return self._clean_markdown_format(result)

    def _generate_title_from_summary(self, summary: str) -> str:
        """サマリーからPRのタイトルを生成"""
        # サマリーが大きすぎる場合は先頭部分のみ使用
        if len(summary) > 2000:
            truncated_summary = summary[:2000] + "..."
        else:
            truncated_summary = summary

        title_prompt = (
            "以下の変更内容サマリーを基に、PRのタイトルを生成してください。\n\n"
            "## 要件\n"
            "- 50文字以内で簡潔に\n"
            "- 変更の主要な目的を表現\n"
            "- 技術的な変更の場合は具体的な技術用語を含める\n"
            "- 日本語で記述\n\n"
            "## 入力サマリー\n"
            f"{truncated_summary}\n\n"
            "## 出力形式\n"
            "タイトルのみを出力してください（説明や補足は不要）"
        )

        messages = [
            {
                "role": "system",
                "content": "あなたは技術文書のタイトルを生成する専門家です。"
            },
            {
                "role": "user",
                "content": title_prompt
            }
        ]

        return self._call_openai_api(messages, max_tokens=100)

    def get_usage_stats(self) -> Dict[str, int]:
        """APIの使用統計を取得"""
        return {
            'prompt_tokens': self.usage_stats['prompt_tokens'],
            'completion_tokens': self.usage_stats['completion_tokens'],
            'total_tokens': self.usage_stats['prompt_tokens'] + self.usage_stats['completion_tokens'],
            'retries': self.usage_stats['retries'],
            'skipped_files': self.usage_stats['skipped_files']
        }

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
        
        # マークダウンのファイルリストセクションを探す
        file_section_pattern = r"## 修正されたファイル\n(.*?)(?:\n##|\Z)"
        file_section_match = re.search(file_section_pattern, comment, re.DOTALL)
        
        if not file_section_match:
            self.logger.warning("File section not found in summary, cannot fix duplicates")
            return comment
            
        # 現在のファイルセクションとその位置を取得
        file_section = file_section_match.group(1)
        section_start = file_section_match.start()
        section_end = file_section_match.end()
        
        # ファイルパスと説明文のマップを作成
        file_infos = {}
        
        # 行ごとに処理
        for line in file_section.split('\n'):
            if not line.strip():
                continue
                
            # 正規表現でファイルパスを抽出（`のついたファイルパス）
            file_match = re.search(r'`([^`]+)`', line)
            if file_match:
                file_path = file_match.group(1)
                
                # ファイルのベース名（拡張子付き）を取得
                base_name = os.path.basename(file_path)
                
                # オリジナルのパスで完全なパスを見つける
                full_path = None
                for orig_path in original_file_paths:
                    if orig_path.endswith(base_name):
                        full_path = orig_path
                        break
                
                # 完全なパスが見つかった場合は置き換え、見つからなければそのまま使用
                normalized_path = full_path if full_path else file_path
                
                # すでに同じパスの情報があるか確認
                if normalized_path not in file_infos:
                    file_infos[normalized_path] = line.replace(f"`{file_path}`", f"`{normalized_path}`")
        
        # 新しいファイルセクションを構築
        new_file_section = "## 修正されたファイル\n"
        for file_path, info in file_infos.items():
            new_file_section += info + "\n"
        
        # スキップされたファイルを確認して追加
        skipped_files = getattr(self, 'skipped_file_names', [])
        for skipped_file in skipped_files:
            if not any(skipped_file in path for path in file_infos.keys()):
                new_file_section += f"- `{skipped_file}`: スキップされました（ファイルサイズが大きいか特殊形式のため）\n"
        
        # コメント内のファイルリストセクションを置換
        new_comment = comment[:section_start] + new_file_section + "\n" + comment[section_end:]
        
        return new_comment

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
        
        # マークダウンのファイルリストセクションを探す
        file_section_pattern = r"## 修正されたファイル\n(.*?)(?:\n##|\Z)"
        file_section_match = re.search(file_section_pattern, comment, re.DOTALL)
        
        if not file_section_match:
            self.logger.warning("File section not found in summary, cannot fix duplicates")
            return comment
            
        # 現在のファイルセクションとその位置を取得
        file_section = file_section_match.group(1)
        section_start = file_section_match.start()
        section_end = file_section_match.end()
        
        # ファイルパスと説明文のマップを作成
        file_infos = {}
        
        # 実際のファイルパスのリスト
        actual_file_paths = set(original_file_paths)
        
        # 行ごとに処理
        for line in file_section.split('\n'):
            if not line.strip():
                continue
                
            # 正規表現でファイルパスを抽出（`のついたファイルパス）
            file_match = re.search(r'`([^`]+)`', line)
            if file_match:
                file_path = file_match.group(1)
                
                # ライブラリ名など、実際には存在しないファイルパスをスキップ
                # 実際のファイルパスかどうかをチェック
                is_real_file = False
                
                # 完全一致のチェック
                if file_path in actual_file_paths:
                    is_real_file = True
                else:
                    # ファイル名だけの部分一致チェック
                    base_name = os.path.basename(file_path)
                    for orig_path in original_file_paths:
                        if orig_path.endswith(base_name):
                            file_path = orig_path  # 完全なパスに置き換え
                            is_real_file = True
                            break
                
                # 実際のファイルでない場合はスキップ
                if not is_real_file:
                    self.logger.info(f"Skipping non-file item: {file_path}")
                    continue
                
                # すでに同じパスの情報があるか確認
                if file_path not in file_infos:
                    # 元のファイルパスを正規化されたパスに置き換え
                    file_infos[file_path] = line.replace(f"`{file_match.group(1)}`", f"`{file_path}`")
        
        # 新しいファイルセクションを構築
        new_file_section = "## 修正されたファイル\n"
        for file_path, info in file_infos.items():
            new_file_section += info + "\n"
        
        # スキップされたファイルを確認して追加
        skipped_files = getattr(self, 'skipped_file_names', [])
        for skipped_file in skipped_files:
            if not any(skipped_file in path for path in file_infos.keys()):
                new_file_section += f"- `{skipped_file}`: スキップされました（ファイルサイズが大きいか特殊形式のため）\n"
        
        # コメント内のファイルリストセクションを置換
        new_comment = comment[:section_start] + new_file_section + "\n" + comment[section_end:]
        
        return new_comment


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
            # chunk分析はopenai_clientの内部メソッドを呼び出す形に修正
            chunk_size = self.openai_client._calculate_optimal_chunk_size(changes)
            chunks = self.openai_client._split_changes_into_chunks(changes, chunk_size)
            
            self.logger.info(f"Analyzing {len(chunks)} chunks with chunk size {chunk_size}")
            
            # チャンク分析を呼び出し
            chunk_analyses = []
            for i, chunk in enumerate(chunks, 1):
                self.logger.info(f"Analyzing chunk {i}/{len(chunks)} ({len(chunk)} files)...")
                try:
                    chunk_analysis = self.openai_client._analyze_chunk(pr_info, chunk, i)
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
        
def main():
    """メイン処理（プロンプト保存オプションを追加）"""
    parser = argparse.ArgumentParser(description='Generate PR comments using OpenAI API')
    parser.add_argument('--pr-diff', required=True, help='PR diff JSON file path')
    parser.add_argument('--pr-info', required=True, help='PR info JSON file path')
    parser.add_argument('--output', required=True, help='Output JSON file path')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--parallel', action='store_true', help='Use parallel processing for file fetching')
    parser.add_argument('--save-prompts', action='store_true', help='Save prompts and results to files')
    parser.add_argument('--prompt-output-dir', default='/prompts', help='Directory to save prompts and results')
    args = parser.parse_args()

    # 環境変数から設定を上書き（CIパイプラインでの制御を容易に）
    if args.parallel:
        os.environ['PARALLEL_PROCESSING'] = 'true'
    
    # save-prompts フラグを環境変数に反映
    if args.save_prompts:
        os.environ['SAVE_PROMPTS'] = 'true'
        os.environ['PROMPT_OUTPUT_DIR'] = args.prompt_output_dir
        
        # 出力ディレクトリが存在しない場合は作成
        if not os.path.exists(args.prompt_output_dir):
            os.makedirs(args.prompt_output_dir, exist_ok=True)
            print(f"Created prompt output directory: {args.prompt_output_dir}")
    
    # ログレベルの設定
    log_level = getattr(logging, args.log_level)
    
    try:
        # ジェネレーターの初期化とコメント生成
        generator = PRCommentGenerator(log_level=log_level)
        result = generator.generate_comment(args.pr_info, args.pr_diff)
        
        # 結果をJSONファイルに保存
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # エラーがあった場合でも基本情報は出力（完全な失敗を防ぐ）
        if 'error' in result:
            print(f"\nWarning: Comment generation completed with errors: {result['error']}")
            if 'usage' in result and result['usage']:
                print(f"Partial tokens used: {result['usage'].get('total_tokens', 0)}")
            exit(1)  # エラーコードで終了
        else:
            print("\nComment generation completed successfully!")
            print(f"Total tokens used: {result['usage']['total_tokens']}")
            print(f"Files analyzed: {result['file_count']}")
            print(f"Total changes: {result['total_changes']}")
            print(f"Execution time: {result.get('execution_time_seconds', 0)} seconds")
            
            # プロンプト保存状況を出力
            if args.save_prompts:
                print(f"Prompts and results saved to: {args.prompt_output_dir}")

    except Exception as e:
        print(f"Critical error: {str(e)}")
        traceback.print_exc()
        
        # 最低限の失敗情報をJSONに出力
        try:
            error_result = {
                'error': str(e),
                'traceback': traceback.format_exc(),
                'comment': f"Critical error occurred: {str(e)}",
                'suggested_title': "Error: PR Analysis Failed"
            }
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(error_result, f, indent=2, ensure_ascii=False)
        except:
            print("Failed to write error information to output file")
            
        exit(1)  # エラーコードで終了

if __name__ == "__main__":
    main()