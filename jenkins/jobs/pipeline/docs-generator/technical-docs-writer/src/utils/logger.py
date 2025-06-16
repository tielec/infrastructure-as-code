"""!
ログ機能モジュール

プロセスの区切りを明確にし、可読性の高いログ出力を提供します。
"""

import logging
import sys
import os
from typing import Optional


class CustomFormatter(logging.Formatter):
    """!
    カスタムログフォーマッター
    
    プロセスの区切りを明確にし、ログの可読性を向上させます。
    """
    # 色の定義
    COLORS = {
        'INFO': '\033[94m',    # 青
        'DEBUG': '\033[92m',   # 緑
        'WARNING': '\033[93m', # 黄
        'ERROR': '\033[91m',   # 赤
        'CRITICAL': '\033[91m\033[1m', # 太字赤
        'REFLECTION': '\033[95m',      # 紫 (自己対話用)
        'RESET': '\033[0m'     # リセット
    }
    
    def __init__(self, use_colors=True):
        super().__init__()
        self.use_colors = use_colors and sys.stdout.isatty()
        
    def format(self, record):
        # ログレベルに応じたフォーマット文字列を作成
        level_name = record.levelname
        
        if self.use_colors and level_name in self.COLORS:
            prefix = f"{self.COLORS[level_name]}[{level_name}]{self.COLORS['RESET']} "
        else:
            prefix = f"[{level_name}] "
            
        formatter = logging.Formatter(f"%(asctime)s - {prefix}%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


class CustomLogger:
    """!
    カスタムロガークラス
    
    プロセスの区切りやグループ化を明確にし、ログの可読性を向上させます。
    """
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.step_count = 0
        self.reflection_phase_count = 0
        self.current_group = None
        self.group_stack = []  # ネストされたグループを管理するためのスタック
    
    def set_level(self, level: int) -> None:
        """ログレベルを設定"""
        self.logger.setLevel(level)
    
    def start_group(self, group_name: str) -> None:
        """ログのグループを開始"""
        if self.current_group:
            # 現在のグループをスタックに保存（ネストされたグループの場合）
            self.group_stack.append(self.current_group)
            
        self.current_group = group_name
        self._print_separator("=", f" STARTING: {group_name} ")
        self.step_count = 0
    
    def end_group(self) -> None:
        """ログのグループを終了"""
        if self.current_group:
            self._print_separator("-", f" COMPLETED: {self.current_group} ")
            
            # スタックから前のグループを復元（ネストされたグループの場合）
            if self.group_stack:
                self.current_group = self.group_stack.pop()
            else:
                self.current_group = None
    
    def step(self, message: str) -> None:
        """処理ステップをログ出力"""
        self.step_count += 1
        self.logger.info(f"STEP {self.step_count}: {message}")
    
    def reflection_phase(self, phase_name: str) -> None:
        """自己対話プロセスのフェーズをログ出力"""
        self.reflection_phase_count += 1
        # REFLECTIONは標準のログレベルではないが、INFOレベルでフォーマットを工夫して出力
        self.logger.info(f"REFLECTION PHASE {self.reflection_phase_count}: {phase_name}")
    
    def reflection_insight(self, insight: str) -> None:
        """自己対話プロセスでの考察をログ出力"""
        # インデントを付けて見やすく
        for line in insight.split('\n'):
            self.logger.info(f"  INSIGHT: {line}")
    
    def reflection_process(self, process_type: str, message: str) -> None:
        """自己対話プロセスの全般的な情報をログ出力"""
        self.logger.info(f"REFLECTION {process_type}: {message}")
    
    # 標準ログメソッドの実装
    def debug(self, message: str) -> None: 
        """デバッグレベルのログを出力"""
        self.logger.debug(message)
    
    def info(self, message: str) -> None: 
        """情報レベルのログを出力"""
        self.logger.info(message)
    
    def warning(self, message: str) -> None: 
        """警告レベルのログを出力"""
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """エラーログを出力"""
        self._print_separator("!", f" ERROR: {message} ")
    
    def critical(self, message: str) -> None:
        """致命的エラーログを出力"""
        self._print_separator("#", f" CRITICAL ERROR: {message} ")
    
    def api_call(self, model: str, status: str) -> None:
        """API呼び出しのログ"""
        self.logger.info(f"API Call: Using model {model} -> {status}")
    
    def token_usage(self, prompt: int, completion: int, total: int) -> None:
        """トークン使用量のログ"""
        self._print_separator("-", header_only=True)
        self.logger.info("TOKEN USAGE:")
        self.logger.info(f"  Prompt:     {prompt:,}")
        self.logger.info(f"  Completion: {completion:,}")
        self.logger.info(f"  Total:      {total:,}")
        self._print_separator("-", header_only=True)
    
    def section_processing(self, section: str, status: str) -> None:
        """セクション処理状態のログ"""
        self.logger.info(f"Section '{section}': {status}")
    
    def _print_separator(self, char: str, message: Optional[str] = None, header_only: bool = False) -> None:
        """区切り線と任意のメッセージを出力"""
        width = 80
        
        if message:
            message_len = len(message)
            padding = (width - message_len) // 2
            separator = char * padding + message + char * (width - padding - message_len)
        else:
            separator = char * width
            
        self.logger.info(separator)
        if message and not header_only:
            self.logger.info(separator)


def setup_logging(name: str = __name__, level: int = logging.INFO) -> CustomLogger:
    """!
    ロギングを設定します
    
    @param name ロガー名
    @param level ログレベル
    @return カスタムロガーインスタンス
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 既存のハンドラをクリア
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 標準出力へのハンドラを追加
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CustomFormatter())
    root_logger.addHandler(console_handler)
    
    # ログディレクトリが指定されている場合はファイルへのハンドラも追加
    log_dir = os.environ.get('LOG_DIR')
    if log_dir and os.path.isdir(log_dir):
        log_file = os.path.join(log_dir, 'document_generator.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - [%(levelname)s] - %(message)s',
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        root_logger.addHandler(file_handler)
    
    # カスタムロガーを返す
    return CustomLogger(name)


# モジュールレベルのロガーインスタンスを作成
logger = setup_logging()
