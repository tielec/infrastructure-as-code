"""!
ファイル操作ユーティリティモジュール

ファイルの読み書き、存在確認、ディレクトリ作成などの共通機能を提供します。
"""

import os
import json
import shutil
from typing import Dict, List, Any, Optional, Union, BinaryIO, TextIO
import json

from .logger import logger


def ensure_directory(directory: str) -> bool:
    """
    ディレクトリが存在することを確認し、存在しない場合は作成します。
    
    Args:
        directory: 確認/作成するディレクトリパス
        
    Returns:
        bool: 成功した場合はTrue、失敗した場合はFalse
    """
    try:
        if not os.path.exists(directory):
            logger.debug(f"Creating directory: {directory}")
            os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {str(e)}")
        return False


def read_file(file_path: str, encoding: str = 'utf-8') -> Optional[str]:
    """
    ファイルを読み込み、内容を文字列で返します。
    
    Args:
        file_path: 読み込むファイルのパス
        encoding: ファイルのエンコーディング（デフォルトはUTF-8）
        
    Returns:
        ファイルの内容、またはエラー時はNone
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File does not exist: {file_path}")
            return None
            
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        return content
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {str(e)}")
        return None


def write_file(file_path: str, content: str, encoding: str = 'utf-8') -> bool:
    """
    文字列の内容をファイルに書き込みます。
    
    Args:
        file_path: 書き込み先のファイルパス
        content: 書き込む内容
        encoding: ファイルのエンコーディング（デフォルトはUTF-8）
        
    Returns:
        bool: 成功した場合はTrue、失敗した場合はFalse
    """
    try:
        # 親ディレクトリが存在することを確認
        parent_dir = os.path.dirname(file_path)
        if parent_dir:
            ensure_directory(parent_dir)
            
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        logger.debug(f"File written: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {str(e)}")
        return False


def read_json(file_path: str, encoding: str = 'utf-8') -> Optional[Dict[str, Any]]:
    """
    JSONファイルを読み込んで辞書として返します。
    
    Args:
        file_path: 読み込むJSONファイルのパス
        encoding: ファイルのエンコーディング（デフォルトはUTF-8）
        
    Returns:
        辞書、またはエラー時はNone
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"JSON file does not exist: {file_path}")
            return None
            
        with open(file_path, 'r', encoding=encoding) as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in file: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Failed to read JSON file {file_path}: {str(e)}")
        return None


def write_json(file_path: str, data: Dict[str, Any], encoding: str = 'utf-8', pretty: bool = True) -> bool:
    """
    辞書をJSONファイルとして書き込みます。
    
    Args:
        file_path: 書き込み先のJSONファイルパス
        data: 書き込む辞書データ
        encoding: ファイルのエンコーディング（デフォルトはUTF-8）
        pretty: 整形して出力するかどうか（デフォルトは整形あり）
        
    Returns:
        bool: 成功した場合はTrue、失敗した場合はFalse
    """
    try:
        # 親ディレクトリが存在することを確認
        parent_dir = os.path.dirname(file_path)
        if parent_dir:
            ensure_directory(parent_dir)
            
        with open(file_path, 'w', encoding=encoding) as f:
            if pretty:
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                json.dump(data, f, ensure_ascii=False)
        logger.debug(f"JSON file written: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to write JSON file {file_path}: {str(e)}")
        return False


def copy_file(src_path: str, dst_path: str) -> bool:
    """
    ファイルをコピーします。
    
    Args:
        src_path: コピー元のファイルパス
        dst_path: コピー先のファイルパス
        
    Returns:
        bool: 成功した場合はTrue、失敗した場合はFalse
    """
    try:
        if not os.path.exists(src_path):
            logger.warning(f"Source file does not exist: {src_path}")
            return False
            
        # 親ディレクトリが存在することを確認
        parent_dir = os.path.dirname(dst_path)
        if parent_dir:
            ensure_directory(parent_dir)
            
        shutil.copyfile(src_path, dst_path)
        logger.debug(f"File copied from {src_path} to {dst_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to copy file from {src_path} to {dst_path}: {str(e)}")
        return False


def file_exists(file_path: str) -> bool:
    """
    ファイルが存在するかどうかを確認します。
    
    Args:
        file_path: 確認するファイルパス
        
    Returns:
        bool: ファイルが存在する場合はTrue、存在しない場合はFalse
    """
    return os.path.isfile(file_path)


def get_files_in_directory(directory: str, extension: Optional[str] = None) -> List[str]:
    """
    ディレクトリ内のファイル一覧を取得します。
    
    Args:
        directory: 検索するディレクトリパス
        extension: フィルタリングする拡張子（例: ".md"、デフォルトはすべてのファイル）
        
    Returns:
        List[str]: ファイルパスのリスト
    """
    try:
        if not os.path.exists(directory):
            logger.warning(f"Directory does not exist: {directory}")
            return []
            
        file_list = []
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                if extension is None or file.endswith(extension):
                    file_list.append(file_path)
        return file_list
    except Exception as e:
        logger.error(f"Failed to get files from directory {directory}: {str(e)}")
        return []


def delete_file(file_path: str) -> bool:
    """
    ファイルを削除します。
    
    Args:
        file_path: 削除するファイルパス
        
    Returns:
        bool: 成功した場合はTrue、失敗した場合はFalse
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File does not exist: {file_path}")
            return False
            
        os.remove(file_path)
        logger.debug(f"File deleted: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete file {file_path}: {str(e)}")
        return False


def get_filename(file_path: str) -> str:
    """
    パスからファイル名（拡張子付き）を取得します。
    
    Args:
        file_path: ファイルパス
        
    Returns:
        str: ファイル名
    """
    return os.path.basename(file_path)


def get_filename_without_extension(file_path: str) -> str:
    """
    パスからファイル名（拡張子なし）を取得します。
    
    Args:
        file_path: ファイルパス
        
    Returns:
        str: 拡張子なしのファイル名
    """
    basename = os.path.basename(file_path)
    return os.path.splitext(basename)[0]


def get_file_extension(file_path: str) -> str:
    """
    ファイルの拡張子を取得します。
    
    Args:
        file_path: ファイルパス
        
    Returns:
        str: 拡張子（ドット付き）
    """
    return os.path.splitext(file_path)[1]
