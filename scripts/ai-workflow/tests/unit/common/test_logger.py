"""
Unit tests for common/logger.py

Test Scenarios:
- UT-LOG-001: Logger.get_logger() - 正常系
- UT-LOG-002: Logger.info() - ログ出力
- UT-LOG-003: Logger.error() - ログ出力
"""
import pytest
import logging
from pathlib import Path
from common.logger import Logger


class TestLogger:
    """Logger クラスのユニットテスト"""

    def test_get_logger_returns_logger_instance(self):
        """UT-LOG-001: get_logger() がロガーインスタンスを返すことを確認"""
        # Given: モジュール名
        module_name = "test_module"

        # When: get_logger()を呼び出す
        logger = Logger.get_logger(module_name)

        # Then: logging.Loggerインスタンスが返される
        assert isinstance(logger, logging.Logger)
        assert logger.name == module_name

    def test_get_logger_returns_same_instance(self):
        """get_logger() が同じ名前で呼ばれた場合、同じインスタンスを返すことを確認"""
        # Given: 同じモジュール名
        module_name = "test_module"

        # When: 2回get_logger()を呼び出す
        logger1 = Logger.get_logger(module_name)
        logger2 = Logger.get_logger(module_name)

        # Then: 同じインスタンスが返される
        assert logger1 is logger2

    def test_logger_info_logs_message(self, caplog):
        """UT-LOG-002: info()でログが出力されることを確認"""
        # Given: ロガーインスタンス
        logger = Logger.get_logger("test_info")

        # When: infoログを出力
        with caplog.at_level(logging.INFO):
            logger.info("Test info message")

        # Then: ログメッセージが出力される
        assert "Test info message" in caplog.text

    def test_logger_error_logs_message(self, caplog):
        """UT-LOG-003: error()でエラーログが出力されることを確認"""
        # Given: ロガーインスタンス
        logger = Logger.get_logger("test_error")

        # When: errorログを出力
        with caplog.at_level(logging.ERROR):
            logger.error("Test error message")

        # Then: エラーメッセージが出力される
        assert "Test error message" in caplog.text

    def test_logger_set_level(self, caplog):
        """set_level()でログレベルが変更されることを確認"""
        # Given: ロガーインスタンス
        logger = Logger.get_logger("test_level")

        # When: ログレベルをERRORに設定
        Logger.set_level(logging.ERROR)

        # Then: INFOログは出力されない
        with caplog.at_level(logging.INFO):
            logger.info("This should not appear")
            assert "This should not appear" not in caplog.text

        # Then: ERRORログは出力される
        with caplog.at_level(logging.ERROR):
            logger.error("This should appear")
            assert "This should appear" in caplog.text
