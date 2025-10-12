"""Logger - ログ処理の統一モジュール

このモジュールは、プロジェクト全体で統一されたログ処理を提供します。

機能:
    - ログレベル管理（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ログフォーマット統一
    - コンテキスト情報の自動付与
    - ファイル出力とコンソール出力の同時サポート

使用例:
    >>> logger = Logger.get_logger(__name__)
    >>> logger.info("処理を開始します")
    >>> logger.error("エラーが発生しました", exc_info=True)
"""

import logging
import sys
from pathlib import Path
from typing import Optional


class Logger:
    """ログ処理クラス

    プロジェクト全体で統一されたログ処理を提供します。
    """

    # ログフォーマット定義
    LOG_FORMAT = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

    # ログレベルマッピング
    LOG_LEVELS = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    _initialized = False

    @classmethod
    def initialize(cls, log_level: str = 'INFO', log_file: Optional[Path] = None):
        """ログシステムの初期化

        Args:
            log_level: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
            log_file: ログファイルパス（省略時はコンソール出力のみ）

        Note:
            この関数は最初に一度だけ呼び出す必要があります。
            複数回呼び出しても、初回のみ有効です。
        """
        if cls._initialized:
            return

        # ルートロガーの設定
        root_logger = logging.getLogger()
        root_logger.setLevel(cls.LOG_LEVELS.get(log_level, logging.INFO))

        # フォーマッター作成
        formatter = logging.Formatter(cls.LOG_FORMAT, datefmt=cls.DATE_FORMAT)

        # コンソールハンドラー追加
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # ファイルハンドラー追加（指定された場合）
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        cls._initialized = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """ロガーインスタンスを取得

        Args:
            name: ロガー名（通常は __name__ を使用）

        Returns:
            logging.Logger: ロガーインスタンス

        Example:
            >>> logger = Logger.get_logger(__name__)
            >>> logger.info("処理を開始します")
        """
        # 初期化されていない場合は自動初期化
        if not cls._initialized:
            cls.initialize()

        return logging.getLogger(name)

    @classmethod
    def set_level(cls, name: str, level: str):
        """特定のロガーのログレベルを変更

        Args:
            name: ロガー名
            level: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

        Example:
            >>> Logger.set_level('core.git_manager', 'DEBUG')
        """
        logger = logging.getLogger(name)
        logger.setLevel(cls.LOG_LEVELS.get(level, logging.INFO))
