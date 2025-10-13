"""ConfigManager - 設定管理クラス

このモジュールは、config.yamlと環境変数からの設定読み込みを統一的に管理します。

機能:
    - config.yamlの読み込み
    - 環境変数の読み込み（最優先）
    - 設定のバリデーション
    - デフォルト値の管理

優先順位:
    1. 環境変数（最優先）
    2. config.yaml
    3. デフォルト値

使用例:
    >>> from core.config_manager import ConfigManager
    >>> config_manager = ConfigManager()
    >>> config = config_manager.load_config()
    >>> github_token = config_manager.get('github_token')
"""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml
import os
from common.error_handler import ConfigValidationError
from common.logger import Logger


class ConfigManager:
    """設定管理クラス

    責務:
        - config.yamlの読み込み
        - 環境変数の読み込み
        - 設定のバリデーション
        - デフォルト値の管理

    優先順位:
        1. 環境変数（最優先）
        2. config.yaml
        3. デフォルト値
    """

    # デフォルト値定義
    DEFAULT_CONFIG = {
        'working_dir': '.',
        'log_level': 'INFO',
        'max_turns': 30,
        'timeout': 300,
    }

    # 必須項目定義（環境変数から取得する想定）
    REQUIRED_ENV_KEYS = [
        'CLAUDE_CODE_OAUTH_TOKEN',
        'OPENAI_API_KEY',
        'GITHUB_TOKEN',
        'GITHUB_REPOSITORY'
    ]

    # 有効なLOG_LEVEL
    VALID_LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

    def __init__(self, config_path: Optional[Path] = None):
        """初期化

        Args:
            config_path: config.yamlのパス（デフォルト: カレントディレクトリ）
        """
        self.config_path = config_path or Path('config.yaml')
        self.logger = Logger(__name__)
        self._config: Dict[str, Any] = {}

    def load_config(self) -> Dict[str, Any]:
        """設定を読み込み

        処理順序:
            1. デフォルト値を設定
            2. config.yamlを読み込み（存在する場合）
            3. 環境変数で上書き
            4. バリデーション

        Returns:
            Dict[str, Any]: 読み込まれた設定

        Raises:
            ConfigValidationError: バリデーションエラー
        """
        # 1. デフォルト値を設定
        self._config = self.DEFAULT_CONFIG.copy()

        # 2. config.yamlを読み込み
        if self.config_path.exists():
            self._load_from_yaml()
        else:
            self.logger.warning(f'Config file not found: {self.config_path}. Using default values and environment variables.')

        # 3. 環境変数で上書き
        self._load_from_environment()

        # 4. バリデーション
        self._validate_config()

        return self._config

    def _load_from_yaml(self) -> None:
        """config.yamlから設定を読み込み"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f)

            if yaml_config:
                self._config.update(yaml_config)
                self.logger.info(f'Config loaded from: {self.config_path}')
        except Exception as e:
            raise ConfigValidationError(
                f'Failed to load config.yaml: {e}',
                details={'config_path': str(self.config_path)},
                original_exception=e
            )

    def _load_from_environment(self) -> None:
        """環境変数から設定を読み込み（環境変数が最優先）"""
        # API認証情報（環境変数のみ）
        env_mappings = {
            'CLAUDE_CODE_OAUTH_TOKEN': 'claude_code_oauth_token',
            'OPENAI_API_KEY': 'openai_api_key',
            'GITHUB_TOKEN': 'github_token',
            'GITHUB_REPOSITORY': 'github_repository',
            'WORKING_DIR': 'working_dir',
            'LOG_LEVEL': 'log_level',
        }

        for env_var, config_key in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                self._config[config_key] = value
                # 機密情報はログに出力しない
                if env_var in ['CLAUDE_CODE_OAUTH_TOKEN', 'OPENAI_API_KEY', 'GITHUB_TOKEN']:
                    self.logger.debug(f'Config loaded from environment variable: {env_var}')
                else:
                    self.logger.debug(f'Config overridden by environment variable: {env_var}={value}')

    def _validate_config(self) -> None:
        """設定のバリデーション"""
        # 必須環境変数チェック
        missing_keys = []
        for env_key in self.REQUIRED_ENV_KEYS:
            config_key = env_key.lower()
            if config_key not in self._config or not self._config[config_key]:
                missing_keys.append(env_key)

        if missing_keys:
            raise ConfigValidationError(
                f"Required environment variables are missing: {', '.join(missing_keys)}\n"
                f"Please set them as environment variables."
            )

        # LOG_LEVELのバリデーション
        log_level = self._config.get('log_level', 'INFO')
        if log_level not in self.VALID_LOG_LEVELS:
            raise ConfigValidationError(
                f"Invalid log_level: {log_level}. "
                f"Must be one of {', '.join(self.VALID_LOG_LEVELS)}"
            )

        self.logger.info('Config validation passed')

    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得

        Args:
            key: 設定キー
            default: デフォルト値

        Returns:
            Any: 設定値
        """
        return self._config.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        """すべての設定値を取得

        Returns:
            Dict[str, Any]: すべての設定
        """
        return self._config.copy()
