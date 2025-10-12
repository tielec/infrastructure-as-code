"""File Handler - ファイル操作の抽象化モジュール

このモジュールは、プロジェクト全体で統一されたファイル操作を提供します。

機能:
    - ファイル読み書き処理の統一
    - パス操作の統一
    - エラーハンドリングの統一
    - エンコーディングの自動処理

使用例:
    >>> from common.file_handler import FileHandler
    >>> content = FileHandler.read_file(Path('README.md'))
    >>> FileHandler.write_file(Path('output.txt'), 'Hello World')
"""

from pathlib import Path
from typing import Optional, List
from common.logger import Logger
from common.error_handler import WorkflowError


class FileHandler:
    """ファイル操作ユーティリティクラス

    ファイルの読み書き、ディレクトリ操作等の共通処理を提供します。
    """

    logger = Logger.get_logger(__name__)

    @classmethod
    def read_file(
        cls,
        file_path: Path,
        encoding: str = 'utf-8',
        raise_on_error: bool = True
    ) -> Optional[str]:
        """ファイルを読み込み

        Args:
            file_path: ファイルパス
            encoding: エンコーディング（デフォルト: utf-8）
            raise_on_error: エラー時に例外を発生させるか

        Returns:
            Optional[str]: ファイル内容（エラー時はNone）

        Raises:
            WorkflowError: ファイル読み込みに失敗した場合（raise_on_error=True）

        Example:
            >>> content = FileHandler.read_file(Path('README.md'))
        """
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            cls.logger.debug(f"File read successfully: {file_path}")
            return content

        except FileNotFoundError as e:
            cls.logger.error(f"File not found: {file_path}")
            if raise_on_error:
                raise WorkflowError(
                    f"File not found: {file_path}",
                    details={'path': str(file_path)},
                    original_exception=e
                )
            return None

        except PermissionError as e:
            cls.logger.error(f"Permission denied: {file_path}")
            if raise_on_error:
                raise WorkflowError(
                    f"Permission denied: {file_path}",
                    details={'path': str(file_path)},
                    original_exception=e
                )
            return None

        except Exception as e:
            cls.logger.error(f"Failed to read file: {file_path} ({e})")
            if raise_on_error:
                raise WorkflowError(
                    f"Failed to read file: {file_path}",
                    details={'path': str(file_path)},
                    original_exception=e
                )
            return None

    @classmethod
    def write_file(
        cls,
        file_path: Path,
        content: str,
        encoding: str = 'utf-8',
        create_parents: bool = True,
        raise_on_error: bool = True
    ) -> bool:
        """ファイルを書き込み

        Args:
            file_path: ファイルパス
            content: 書き込む内容
            encoding: エンコーディング（デフォルト: utf-8）
            create_parents: 親ディレクトリを自動作成するか
            raise_on_error: エラー時に例外を発生させるか

        Returns:
            bool: 成功した場合True

        Raises:
            WorkflowError: ファイル書き込みに失敗した場合（raise_on_error=True）

        Example:
            >>> FileHandler.write_file(Path('output.txt'), 'Hello World')
        """
        try:
            # 親ディレクトリ作成
            if create_parents:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            # ファイル書き込み
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)

            cls.logger.debug(f"File written successfully: {file_path}")
            return True

        except PermissionError as e:
            cls.logger.error(f"Permission denied: {file_path}")
            if raise_on_error:
                raise WorkflowError(
                    f"Permission denied: {file_path}",
                    details={'path': str(file_path)},
                    original_exception=e
                )
            return False

        except Exception as e:
            cls.logger.error(f"Failed to write file: {file_path} ({e})")
            if raise_on_error:
                raise WorkflowError(
                    f"Failed to write file: {file_path}",
                    details={'path': str(file_path)},
                    original_exception=e
                )
            return False

    @classmethod
    def ensure_directory(cls, dir_path: Path, raise_on_error: bool = True) -> bool:
        """ディレクトリの存在を確認し、存在しない場合は作成

        Args:
            dir_path: ディレクトリパス
            raise_on_error: エラー時に例外を発生させるか

        Returns:
            bool: 成功した場合True

        Raises:
            WorkflowError: ディレクトリ作成に失敗した場合（raise_on_error=True）

        Example:
            >>> FileHandler.ensure_directory(Path('output'))
        """
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            cls.logger.debug(f"Directory ensured: {dir_path}")
            return True

        except PermissionError as e:
            cls.logger.error(f"Permission denied: {dir_path}")
            if raise_on_error:
                raise WorkflowError(
                    f"Permission denied: {dir_path}",
                    details={'path': str(dir_path)},
                    original_exception=e
                )
            return False

        except Exception as e:
            cls.logger.error(f"Failed to create directory: {dir_path} ({e})")
            if raise_on_error:
                raise WorkflowError(
                    f"Failed to create directory: {dir_path}",
                    details={'path': str(dir_path)},
                    original_exception=e
                )
            return False

    @classmethod
    def file_exists(cls, file_path: Path) -> bool:
        """ファイルの存在確認

        Args:
            file_path: ファイルパス

        Returns:
            bool: 存在する場合True

        Example:
            >>> if FileHandler.file_exists(Path('README.md')):
            ...     print("File exists")
        """
        return file_path.exists() and file_path.is_file()

    @classmethod
    def directory_exists(cls, dir_path: Path) -> bool:
        """ディレクトリの存在確認

        Args:
            dir_path: ディレクトリパス

        Returns:
            bool: 存在する場合True

        Example:
            >>> if FileHandler.directory_exists(Path('output')):
            ...     print("Directory exists")
        """
        return dir_path.exists() and dir_path.is_dir()

    @classmethod
    def list_files(
        cls,
        dir_path: Path,
        pattern: str = '*',
        recursive: bool = False
    ) -> List[Path]:
        """ディレクトリ内のファイル一覧を取得

        Args:
            dir_path: ディレクトリパス
            pattern: ファイル名パターン（デフォルト: *）
            recursive: 再帰的に検索するか

        Returns:
            List[Path]: ファイルパスのリスト

        Example:
            >>> files = FileHandler.list_files(Path('output'), '*.md')
        """
        if not cls.directory_exists(dir_path):
            cls.logger.warning(f"Directory not found: {dir_path}")
            return []

        if recursive:
            return [p for p in dir_path.rglob(pattern) if p.is_file()]
        else:
            return [p for p in dir_path.glob(pattern) if p.is_file()]
