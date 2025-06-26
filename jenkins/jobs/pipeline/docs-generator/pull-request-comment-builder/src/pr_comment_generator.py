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
        model_name = os.getenv('OPENAI_MODEL_NAME', 'gpt-4.1')  # デフォルトモデル名

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
        prompt_content = self._prepare_prompt_content(messages)
        
        retries = 0
        backoff = self.retry_config['initial_backoff']
        
        while retries <= self.retry_config['max_retries']:
            try:
                response = self._make_api_request(messages, max_tokens)
                return self._process_successful_response(response, prompt_content)
                    
            except Exception as e:
                retries += 1
                self.usage_stats['retries'] += 1
                
                # 再試行戦略を決定
                should_retry, sleep_time = self._determine_retry_strategy(
                    e, retries, backoff
                )
                
                if not should_retry:
                    raise
                
                # 待機して再試行
                self._wait_before_retry(sleep_time)
                backoff = min(backoff * 2, self.retry_config['max_backoff'])
        
        # 最大再試行回数に達した
        self.logger.error("Maximum retries reached. Failed to get response from API.")
        raise RuntimeError("Maximum retries exceeded for API call")
    
    def _prepare_prompt_content(self, messages: List[Dict[str, str]]) -> str:
        """プロンプトコンテンツを準備する"""
        return "\n\n".join([
            f"[{msg['role']}]\n{msg['content']}" 
            for msg in messages
        ])
    
    def _make_api_request(self, messages: List[Dict[str, str]], max_tokens: int) -> Any:
        """OpenAI APIリクエストを実行する"""
        # リクエスト情報をログ出力
        self.logger.info(f"Making API request to model: {self.model}")
        self.logger.info(f"Request parameters:")
        self.logger.info(f"  - Max tokens: {max_tokens}")
        self.logger.info(f"  - Temperature: 0.0")
        self.logger.info(f"  - Top-p: 0.1")
        self.logger.info(f"  - Messages count: {len(messages)}")
        
        # メッセージの概要をログ出力（長すぎる場合は省略）
        for i, msg in enumerate(messages):
            role = msg['role']
            content_preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            self.logger.info(f"  - Message {i+1} [{role}]: {content_preview}")
        
        # API呼び出し
        self.logger.info("Sending request to OpenAI API...")
        
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.0,
            max_tokens=max_tokens,
            top_p=0.1,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            response_format={"type": "text"}
        )
    
    def _process_successful_response(self, response: Any, prompt_content: str) -> str:
        """成功したレスポンスを処理する"""
        # トークン使用量を記録
        self._record_token_usage(response.usage)
        
        # レスポンス内容を取得
        generated_content = response.choices[0].message.content.strip()
        
        # ログ出力
        self._log_response_info(response, generated_content)
        
        # プロンプトと結果を保存
        self._save_prompt_and_result_if_needed(prompt_content, generated_content)
        
        return generated_content
    
    def _record_token_usage(self, usage: Any) -> None:
        """トークン使用量を記録する"""
        self.usage_stats['prompt_tokens'] += usage.prompt_tokens
        self.usage_stats['completion_tokens'] += usage.completion_tokens
    
    def _log_response_info(self, response: Any, content: str) -> None:
        """レスポンス情報をログに記録する"""
        self.logger.info("\nReceived response from OpenAI API:")
        self.logger.info("=" * 80)
        
        # 長いコンテンツは省略
        display_content = content[:500] + ("..." if len(content) > 500 else "")
        self.logger.info(display_content)
        
        self.logger.info("=" * 80)
        
        usage = response.usage
        self.logger.info(
            f"Token usage - Prompt: {usage.prompt_tokens}, "
            f"Completion: {usage.completion_tokens}, "
            f"Total: {usage.total_tokens}"
        )
    
    def _save_prompt_and_result_if_needed(self, prompt_content: str, generated_content: str) -> None:
        """必要に応じてプロンプトと結果を保存する"""
        if hasattr(self, '_current_chunk_index') and hasattr(self, '_current_phase'):
            self._save_prompt_and_result(
                prompt_content, 
                generated_content, 
                getattr(self, '_current_chunk_index', 0),
                getattr(self, '_current_phase', 'unknown')
            )
    
    def _determine_retry_strategy(self, error: Exception, retries: int, 
                                backoff: float) -> Tuple[bool, float]:
        """
        エラーに基づいて再試行戦略を決定する
        
        Returns:
            Tuple[bool, float]: (再試行すべきか, 待機時間)
        """
        if retries >= self.retry_config['max_retries']:
            return False, 0
        
        # レート制限エラーの場合
        if self._is_rate_limit_error(error):
            wait_time = self._handle_rate_limit_error(error, backoff)
            if wait_time is None:
                return False, 0
            return True, wait_time
        
        # その他のエラー
        self.logger.error(
            f"API error: {str(error)}. Retrying in {backoff} seconds... "
            f"(Attempt {retries}/{self.retry_config['max_retries']})"
        )
        return True, backoff
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """レート制限エラーかどうかを判定する"""
        return hasattr(error, 'status_code') and error.status_code == 429
    
    def _handle_rate_limit_error(self, error: Exception, default_backoff: float) -> Optional[float]:
        """
        レート制限エラーを処理する
        
        Returns:
            Optional[float]: 待機時間（秒）。None の場合は再試行しない
        """
        wait_time = self._extract_wait_time_from_error(str(error))
        
        # 待機時間が長すぎる場合はスキップ
        if wait_time and wait_time > 600:  # 10分以上
            self.logger.error(
                f"Rate limit exceeded. API requires {wait_time} seconds wait. "
                f"Skipping this request."
            )
            raise ValueError(
                f"Rate limit exceeded. Required wait time too long: {wait_time} seconds"
            )
        
        # 待機時間が指定されていればそれを使用、なければデフォルトのバックオフ
        actual_wait_time = wait_time if wait_time else default_backoff
        
        self.logger.warning(
            f"Rate limit exceeded. Retrying in {actual_wait_time} seconds..."
        )
        
        return actual_wait_time
    
    def _wait_before_retry(self, sleep_time: float) -> None:
        """再試行前に待機する（ジッター付き）"""
        jitter = random.uniform(0, 1)
        time.sleep(sleep_time + jitter)

    def _extract_wait_time_from_error(self, error_message: str) -> Optional[int]:
        """エラーメッセージから待機時間を抽出"""
        
        # レート制限エラーメッセージから待機時間を抽出するパターン
        pattern = r"retry after (\d+) seconds"
        match = re.search(pattern, error_message.lower())
        
        if match:
            return int(match.group(1))
        return None

    def generate_comment(self, pr_info_path: str, pr_diff_path: str) -> Dict[str, Any]:
        """PRコメントを生成する（スキップファイルを確実に含める）
        
        Args:
            pr_info_path: PR情報のJSONファイルパス
            pr_diff_path: PR差分情報のJSONファイルパス
            
        Returns:
            Dict[str, Any]: 生成されたコメント、タイトル、使用統計などを含む辞書
        """
        start_time = time.time()
        
        try:
            # データの読み込みと検証
            load_result = self._load_and_validate_data(pr_info_path, pr_diff_path)
            if load_result.get('error'):
                return load_result
            
            pr_info = load_result['pr_info']
            changes = load_result['changes']
            all_files = load_result['all_files']
            skipped_file_names = load_result['skipped_file_names']
            
            # ファイルが空の場合の処理
            if not changes:
                return self._create_empty_files_result(pr_info, all_files, skipped_file_names)
            
            # チャンク分析の実行
            chunk_analyses = self._perform_chunk_analyses(pr_info, changes)
            
            # サマリーとタイトルの生成
            comment, generated_title = self._generate_summary_and_title(
                pr_info, chunk_analyses, changes, skipped_file_names
            )
            
            # 実行時間の計算
            execution_time = time.time() - start_time
            
            # 結果の作成
            return self._create_success_result(
                comment, generated_title, pr_info, changes, 
                all_files, skipped_file_names, execution_time
            )
        
        except Exception as e:
            return self._create_error_result(e, start_time)
    
    def _load_and_validate_data(self, pr_info_path: str, pr_diff_path: str) -> Dict[str, Any]:
        """データの読み込みと検証"""
        try:
            self.logger.info(f"Loading PR data from {pr_info_path} and {pr_diff_path}")
            
            # データの読み込み
            pr_info, changes, skipped_file_names = self.load_pr_data(pr_info_path, pr_diff_path)
            
            # クラス属性として保存
            self.pr_info = pr_info
            self.skipped_file_names = skipped_file_names
            
            # 全ファイルリストを取得
            all_files = self._get_all_files_from_diff(pr_diff_path)
            
            # ログ出力
            self._log_load_results(all_files, changes, skipped_file_names)
            
            return {
                'pr_info': pr_info,
                'changes': changes,
                'all_files': all_files,
                'skipped_file_names': skipped_file_names,
                'error': None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to load PR data: {str(e)}")
            return {'error': str(e)}
    
    def _get_all_files_from_diff(self, pr_diff_path: str) -> List[str]:
        """差分ファイルから全ファイルリストを取得"""
        with open(pr_diff_path, 'r', encoding='utf-8') as f:
            original_files = json.load(f)
            return [file_data.get('filename') for file_data in original_files]
    
    def _log_load_results(self, all_files: List[str], changes: List[FileChange], 
                         skipped_file_names: List[str]) -> None:
        """読み込み結果をログ出力"""
        self.logger.info(f"Total files in PR: {len(all_files)}")
        self.logger.info(f"Processed files: {len(changes)}")
        self.logger.info(f"Skipped files: {len(skipped_file_names)}")
        if skipped_file_names:
            self.logger.info(f"Skipped file list: {', '.join(skipped_file_names)}")
    
    def _create_empty_files_result(self, pr_info: PRInfo, all_files: List[str], 
                                  skipped_file_names: List[str]) -> Dict[str, Any]:
        """ファイルが空の場合の結果を作成"""
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
    
    def _perform_chunk_analyses(self, pr_info: PRInfo, changes: List[FileChange]) -> List[str]:
        """チャンク分析を実行"""
        # チャンクサイズの計算
        chunk_size = self.openai_client._calculate_optimal_chunk_size(changes)
        chunks = self.openai_client._split_changes_into_chunks(changes, chunk_size)
        
        self.logger.info(f"Analyzing {len(chunks)} chunks with chunk size {chunk_size}")
        
        # 各チャンクの分析
        chunk_analyses = []
        for i, chunk in enumerate(chunks, 1):
            analysis = self._analyze_single_chunk(pr_info, chunk, i, len(chunks))
            chunk_analyses.append(analysis)
        
        return chunk_analyses
    
    def _analyze_single_chunk(self, pr_info: PRInfo, chunk: List[FileChange], 
                            chunk_num: int, total_chunks: int) -> str:
        """単一チャンクを分析"""
        self.logger.info(f"Analyzing chunk {chunk_num}/{total_chunks} ({len(chunk)} files)...")
        
        try:
            return self.openai_client._analyze_chunk(pr_info, chunk, chunk_num)
        except Exception as e:
            self.logger.error(f"Error analyzing chunk {chunk_num}: {str(e)}")
            return f"[チャンク {chunk_num} の分析に失敗しました: {str(e)}]"
    
    def _generate_summary_and_title(self, pr_info: PRInfo, chunk_analyses: List[str],
                                   changes: List[FileChange], skipped_file_names: List[str]) -> Tuple[str, str]:
        """サマリーとタイトルを生成"""
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
        
        return comment, generated_title
    
    def _create_success_result(self, comment: str, generated_title: str, pr_info: PRInfo,
                             changes: List[FileChange], all_files: List[str],
                             skipped_file_names: List[str], execution_time: float) -> Dict[str, Any]:
        """成功時の結果を作成"""
        return {
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
    
    def _create_error_result(self, error: Exception, start_time: float) -> Dict[str, Any]:
        """エラー時の結果を作成"""
        self.logger.error(f"Error generating PR comment: {str(error)}")
        traceback.print_exc()
        
        # 利用可能な情報を収集
        pr_number = getattr(self.pr_info, 'number', 0) if hasattr(self, 'pr_info') else 0
        usage_stats = self.openai_client.get_usage_stats() if hasattr(self, 'openai_client') else {}
        
        # 部分的な結果を含める
        result = {
            'comment': f"PRの分析中にエラーが発生しました: {str(error)}",
            'suggested_title': "エラー: PRの分析に失敗",
            'usage': usage_stats,
            'pr_number': pr_number,
            'file_count': 0,
            'processed_file_count': 0,
            'skipped_file_count': 0,
            'skipped_files': [],
            'error': str(error),
            'traceback': traceback.format_exc()
        }
        
        # 利用可能な追加情報を含める
        if hasattr(self, 'skipped_file_names'):
            result['skipped_file_count'] = len(self.skipped_file_names)
            result['skipped_files'] = self.skipped_file_names
        
        return result

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
        チャンク単位での分析を実行
        
        Args:
            pr_info: PR情報
            changes: 分析対象のファイル変更リスト
            chunk_index: チャンク番号（デフォルト: 0）
            
        Returns:
            str: 生成された分析結果
        """
        # チャンク番号と処理フェーズを記録
        self._current_chunk_index = chunk_index
        self._current_phase = "chunk"
        
        # 単一ファイルの場合と複数ファイルの場合で戦略を変える
        is_single_file = len(changes) == 1
        
        # JSON入力データを準備
        input_json = self._prepare_input_json(pr_info, changes, is_single_file)
        
        # トークン数を管理しながら入力サイズを調整
        input_json = self._manage_input_size(input_json, is_single_file)
        
        # プロンプトを生成してAPI呼び出し
        return self._execute_chunk_analysis(pr_info, input_json)

    def _prepare_input_json(self, pr_info: PRInfo, changes: List[FileChange], is_single_file: bool) -> Dict[str, Any]:
        """チャンク分析用のJSON入力データを準備"""
        # PR情報のJSON形式
        pr_json = self._create_pr_json(pr_info)
        
        # 変更ファイル情報のJSON形式
        changes_json = []
        for change in changes:
            change_obj = self._create_change_json(change, is_single_file)
            changes_json.append(change_obj)
        
        return {
            "pr_info": pr_json,
            "changes": changes_json
        }

    def _create_pr_json(self, pr_info: PRInfo) -> Dict[str, Any]:
        """PR情報のJSONを作成"""
        return {
            'title': pr_info.title,
            'number': pr_info.number,
            'body': (pr_info.body or '')[:500] if pr_info.body else '',
            'author': pr_info.author,
            'base_branch': pr_info.base_branch,
            'head_branch': pr_info.head_branch
        }

    def _create_change_json(self, change: FileChange, is_single_file: bool) -> Dict[str, Any]:
        """変更ファイルのJSONを作成"""
        # パッチ情報の処理
        patch = self._process_patch(change, is_single_file)
        
        # コンテキスト情報の処理
        context = self._process_context(change, is_single_file)
        
        return {
            'filename': change.filename,
            'status': change.status,
            'additions': change.additions,
            'deletions': change.deletions,
            'changes': change.changes,
            'patch': patch,
            'context': context
        }

    def _process_patch(self, change: FileChange, is_single_file: bool) -> str:
        """パッチ情報を処理"""
        if not change.patch:
            return ''
        
        if is_single_file:
            # 単一ファイルの場合はより多くのパッチ情報を保持
            patch_limit = 8000 if change.changes > 400 else 5000
            return self._truncate_patch(change.patch, patch_limit)
        else:
            # 複数ファイルの場合は制限を厳しく
            max_patch_length = 3000
            return self._truncate_patch(change.patch, max_patch_length)

    def _truncate_patch(self, patch: str, limit: int) -> str:
        """パッチを指定された制限に切り詰める"""
        if len(patch) <= limit:
            return patch
        
        # 前半と後半から重要な部分を取得
        if limit > 3000:
            front_part = int(limit * 0.7)  # 前半70%
            back_part = limit - front_part  # 残り30%
        else:
            front_part = limit // 2
            back_part = limit // 2
        
        return patch[:front_part] + "\n...[中略]...\n" + patch[-back_part:]

    def _process_context(self, change: FileChange, is_single_file: bool) -> Dict[str, Any]:
        """コンテキスト情報を処理"""
        if is_single_file:
            # 単一大きなファイルの場合はコンテキストを最小限に
            return {
                'before': None,
                'after': None,
                'diff_context': self._limit_diff_context(change.context_diff)
            }
        else:
            # 複数ファイルの場合はコンテキスト情報も保持
            return {
                'before': self._truncate_content(change.content_before, 1000) if change.content_before else None,
                'after': self._truncate_content(change.content_after, 1000) if change.content_after else None,
                'diff_context': self._limit_diff_context(change.context_diff)
            }

    def _manage_input_size(self, input_json: Dict[str, Any], is_single_file: bool) -> Dict[str, Any]:
        """入力サイズをトークン制限内に調整"""
        # 初回のトークン数推定
        input_json_text = json.dumps(input_json, ensure_ascii=False, indent=2)
        estimated_tokens = TokenEstimator.estimate_tokens(input_json_text)
        
        # 80%のマージンを超えている場合は削減
        if estimated_tokens > self.MAX_TOKENS_PER_REQUEST * 0.8:
            self.logger.warning(f"Input size ({estimated_tokens} est. tokens) exceeds limit. Reducing context...")
            input_json = self._reduce_input_size_phase1(input_json, is_single_file)
            
            # 再度サイズを確認
            input_json_text = json.dumps(input_json, ensure_ascii=False, indent=2)
            new_estimated_tokens = TokenEstimator.estimate_tokens(input_json_text)
            self.logger.info(f"Reduced input size to {new_estimated_tokens} est. tokens")
            
            # それでも大きすぎる場合はさらに削減
            if new_estimated_tokens > self.MAX_TOKENS_PER_REQUEST * 0.9:
                self.logger.warning("Input still too large, further reducing patches...")
                input_json = self._reduce_input_size_phase2(input_json, is_single_file)
                
                # 最終チェック
                input_json_text = json.dumps(input_json, ensure_ascii=False, indent=2)
                final_tokens = TokenEstimator.estimate_tokens(input_json_text)
                
                if final_tokens > self.MAX_TOKENS_PER_REQUEST * 0.95:
                    input_json = self._reduce_input_size_final(input_json, is_single_file)
                    
                    # 最終的なトークン数確認
                    input_json_text = json.dumps(input_json, ensure_ascii=False, indent=2)
                    very_final_tokens = TokenEstimator.estimate_tokens(input_json_text)
                    
                    if very_final_tokens > self.MAX_TOKENS_PER_REQUEST * 0.98:
                        raise ValueError(f"Input still too large for API ({very_final_tokens} est. tokens) even after maximum reduction")
                    
                    self.logger.info(f"Final input size after maximum reduction: {final_tokens} est. tokens")
        
        return input_json

    def _reduce_input_size_phase1(self, input_json: Dict[str, Any], is_single_file: bool) -> Dict[str, Any]:
        """入力サイズ削減フェーズ1: 基本的な削減"""
        changes_json = input_json["changes"]
        
        if is_single_file:
            # 単一ファイル: パッチの重要部分を保持しながら削減
            for change_obj in changes_json:
                if len(change_obj['patch']) > 6000:
                    change_obj['patch'] = self._extract_important_patch_lines(change_obj['patch'])
                change_obj['context'] = {"note": "大きなファイルのためコンテキスト情報省略"}
        else:
            # 複数ファイル: コンテキストを削除してパッチを削減
            for change_obj in changes_json:
                change_obj['context']['before'] = None
                change_obj['context']['after'] = None
                if change_obj['patch'] and len(change_obj['patch']) > 1000:
                    change_obj['patch'] = self._truncate_patch(change_obj['patch'], 1000)
        
        return input_json

    def _extract_important_patch_lines(self, patch: str) -> str:
        """パッチから重要な行を抽出"""
        patch_lines = patch.split('\n')
        
        # 追加行（+で始まる）と削除行（-で始まる）を優先的に保持
        important_lines = []
        other_lines = []
        
        for line in patch_lines:
            if line.startswith('+') or line.startswith('-'):
                important_lines.append(line)
            else:
                other_lines.append(line)
        
        # 重要な行を優先的に保持
        preserved_important = important_lines[:3000]
        preserved_context = other_lines[:1000]
        
        return "\n".join(preserved_important + ["\n...[コンテキスト省略]...\n"] + preserved_context)

    def _reduce_input_size_phase2(self, input_json: Dict[str, Any], is_single_file: bool) -> Dict[str, Any]:
        """入力サイズ削減フェーズ2: より積極的な削減"""
        changes_json = input_json["changes"]
        
        if is_single_file:
            # 単一ファイル: パッチを1500行程度に削減
            for change_obj in changes_json:
                if len(change_obj['patch']) > 1500:
                    change_obj['patch'] = change_obj['patch'][:1000] + "\n...[大部分省略]...\n" + change_obj['patch'][-500:]
        else:
            # 複数ファイル: パッチ情報を完全に除去
            for change_obj in changes_json:
                change_obj['patch'] = f"[パッチ情報省略: {change_obj['additions']} 行追加, {change_obj['deletions']} 行削除]"
                change_obj['context'] = {"note": "コンテキスト情報省略"}
        
        return input_json

    def _reduce_input_size_final(self, input_json: Dict[str, Any], is_single_file: bool) -> Dict[str, Any]:
        """入力サイズ削減最終フェーズ: 最小限の情報のみ残す"""
        changes_json = input_json["changes"]
        
        for change_obj in changes_json:
            # 基本的な統計情報のみ残す
            base_info = f"[パッチ大部分省略: {change_obj['additions']} 行追加, {change_obj['deletions']} 行削除]\n"
            
            if is_single_file and 'patch' in change_obj:
                # 単一ファイルの場合は最小限のサンプルを残す
                sample_lines = self._extract_sample_lines(change_obj.get('patch', ''))
                if sample_lines:
                    change_obj['patch'] = base_info + "\nサンプル変更内容:\n" + "\n".join(sample_lines)
                else:
                    change_obj['patch'] = base_info
            else:
                change_obj['patch'] = base_info
            
            change_obj['context'] = {"note": "トークン制限のため省略"}
        
        return input_json

    def _extract_sample_lines(self, patch: str) -> List[str]:
        """パッチからサンプル行を抽出"""
        sample_lines = []
        lines = patch.split('\n')
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
        
        return sample_lines

    def _execute_chunk_analysis(self, pr_info: PRInfo, input_json: Dict[str, Any]) -> str:
        """チャンク分析を実行してAPIを呼び出す"""
        # 入力形式の作成
        pr_json = input_json["pr_info"]
        changes_json = input_json["changes"]
        
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
        # 単一チャンクの場合は早期リターン
        if self._is_single_chunk_without_skipped_files(chunk_analyses, skipped_files):
            return self._clean_markdown_format(chunk_analyses[0])

        # ログ出力
        self._log_summary_generation_info(chunk_analyses, skipped_files)
        
        # 全ファイル情報を収集
        all_files = self._collect_all_file_names(chunk_analyses, skipped_files)
        
        # チャンク分析を準備
        kept_analyses = self._prepare_chunk_analyses(chunk_analyses)
        
        # 分析テキストを構築
        analyses_text = self._build_analyses_text(kept_analyses, all_files, skipped_files)
        
        # トークン数を管理
        analyses_text = self._manage_analyses_token_size(analyses_text, kept_analyses, all_files, skipped_files)
        
        # 最終サマリーを生成
        return self._generate_summary_from_analyses(pr_info, analyses_text, all_files, skipped_files)
    
    def _is_single_chunk_without_skipped_files(self, chunk_analyses: List[str], skipped_files: List[FileChange]) -> bool:
        """単一チャンクでスキップファイルがない場合をチェック"""
        return len(chunk_analyses) == 1 and not skipped_files
    
    def _log_summary_generation_info(self, chunk_analyses: List[str], skipped_files: List[FileChange]) -> None:
        """サマリー生成の情報をログ出力"""
        self.logger.info("\nGenerating final summary")
        self.logger.info(f"Number of chunk analyses: {len(chunk_analyses)}")
        if skipped_files:
            self.logger.info(f"Number of skipped files: {len(skipped_files)}")
    
    def _collect_all_file_names(self, chunk_analyses: List[str], skipped_files: List[FileChange]) -> set:
        """全てのファイル名を収集する"""
        all_files = set()
        
        # 分析結果からファイル名を抽出
        for analysis in chunk_analyses:
            file_matches = re.findall(r'`([^`]+\.[^`]+)`', analysis)
            all_files.update(file_matches)
        
        # スキップされたファイル名も追加
        if skipped_files:
            skipped_file_names = {f.filename for f in skipped_files}
            all_files.update(skipped_file_names)
        
        self.logger.info(f"Total files mentioned in analyses: {len(all_files)}")
        return all_files
    
    def _prepare_chunk_analyses(self, chunk_analyses: List[str]) -> List[str]:
        """チャンク分析を準備（多すぎる場合は削減）"""
        if len(chunk_analyses) > 10:
            self.logger.warning(
                f"Too many chunk analyses ({len(chunk_analyses)}). "
                f"Keeping only the first 5 and last 5."
            )
            return chunk_analyses[:5] + ['...中略...'] + chunk_analyses[-5:]
        return chunk_analyses
    
    def _build_analyses_text(self, kept_analyses: List[str], all_files: set, 
                           skipped_files: List[FileChange]) -> str:
        """分析テキストを構築する"""
        # チャンク分析を結合
        analyses_text = self._format_chunk_analyses(kept_analyses)
        
        # ファイル一覧を追加
        analyses_text += self._format_file_list(all_files)
        
        # スキップファイル情報を追加
        if skipped_files:
            analyses_text += self._format_skipped_files_info(skipped_files)
        
        return analyses_text
    
    def _format_chunk_analyses(self, kept_analyses: List[str]) -> str:
        """チャンク分析をフォーマット"""
        return "\n\n".join([
            f"=== チャンク {i+1} ===\n{analysis}"
            for i, analysis in enumerate(kept_analyses)
        ])
    
    def _format_file_list(self, all_files: set) -> str:
        """ファイル一覧をフォーマット"""
        return f"\n\n## 全ファイル一覧\n{', '.join(sorted(all_files))}"
    
    def _format_skipped_files_info(self, skipped_files: List[FileChange]) -> str:
        """スキップファイル情報をフォーマット"""
        info = "\n\n## スキップされたファイル\n"
        info += "以下のファイルはサイズが大きすぎるため詳細分析からスキップされましたが、変更内容に含まれています：\n"
        
        for f in skipped_files:
            info += f"- `{f.filename}` ({f.additions} 行追加, {f.deletions} 行削除, 合計 {f.changes} 行変更)\n"
        
        return info
    
    def _manage_analyses_token_size(self, analyses_text: str, kept_analyses: List[str], 
                                  all_files: set, skipped_files: List[FileChange]) -> str:
        """分析テキストのトークンサイズを管理"""
        est_tokens = TokenEstimator.estimate_tokens(analyses_text)
        token_limit = self.MAX_TOKENS_PER_REQUEST * 0.7
        
        if est_tokens <= token_limit:
            return analyses_text
        
        self.logger.warning(f"Summary too large ({est_tokens} est. tokens). Truncating.")
        
        # 各チャンクを切り詰め
        truncated_analyses = self._truncate_chunk_analyses(kept_analyses)
        
        # 再構築
        return self._rebuild_truncated_analyses_text(truncated_analyses, all_files, skipped_files)
    
    def _truncate_chunk_analyses(self, kept_analyses: List[str]) -> List[str]:
        """チャンク分析を切り詰める"""
        if len(kept_analyses) <= 2:
            return kept_analyses
        
        max_tokens_per_chunk = (self.MAX_TOKENS_PER_REQUEST * 0.6) / len(kept_analyses)
        truncated_analyses = []
        
        for analysis in kept_analyses:
            truncated = TokenEstimator.truncate_to_token_limit(
                analysis, int(max_tokens_per_chunk)
            )
            truncated_analyses.append(truncated)
        
        return truncated_analyses
    
    def _rebuild_truncated_analyses_text(self, truncated_analyses: List[str], 
                                       all_files: set, skipped_files: List[FileChange]) -> str:
        """切り詰められた分析テキストを再構築"""
        analyses_text = self._format_chunk_analyses(truncated_analyses)
        analyses_text += self._format_file_list(all_files)
        
        if skipped_files:
            analyses_text += self._format_skipped_files_info(skipped_files)
        
        return analyses_text
    
    def _generate_summary_from_analyses(self, pr_info: PRInfo, analyses_text: str, 
                                      all_files: set, skipped_files: List[FileChange]) -> str:
        """分析結果から最終サマリーを生成"""
        # プロンプトを生成
        summary_prompt = self._prepare_summary_prompt(pr_info, analyses_text, all_files, skipped_files)
        
        # メッセージを構築
        messages = self._build_summary_messages(summary_prompt)
        
        # API呼び出し
        result = self._call_openai_api(messages)
        
        return self._clean_markdown_format(result)
    
    def _prepare_summary_prompt(self, pr_info: PRInfo, analyses_text: str, 
                              all_files: set, skipped_files: List[FileChange]) -> str:
        """サマリー生成用のプロンプトを準備"""
        # 基本プロンプトを生成
        summary_prompt = self.prompt_manager.get_summary_prompt(pr_info, analyses_text)
        
        # ファイル一覧の指示を追加
        file_list_prompt = self._build_file_list_instructions(all_files, skipped_files)
        
        return summary_prompt + file_list_prompt
    
    def _build_file_list_instructions(self, all_files: set, skipped_files: List[FileChange]) -> str:
        """ファイル一覧に関する指示を構築"""
        instructions = f"\n\n## 必ず含めるべきファイル一覧\n{', '.join(sorted(all_files))}\n\n"
        instructions += "最終サマリーには、上記のすべてのファイル（スキップされたファイルを含む）を「修正されたファイル」セクションに含めてください。"
        
        if skipped_files:
            instructions += "\n\nスキップされたファイルも必ず「修正されたファイル」セクションに含めてください。"
            instructions += "\n\nスキップされたファイル: " + ", ".join(f"`{f.filename}`" for f in skipped_files)
        
        return instructions
    
    def _build_summary_messages(self, summary_prompt: str) -> List[Dict[str, str]]:
        """サマリー生成用のメッセージを構築"""
        return [
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
