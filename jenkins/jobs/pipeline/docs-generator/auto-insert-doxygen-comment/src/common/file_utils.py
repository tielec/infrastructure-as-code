"""
ファイル操作に関するユーティリティ関数
"""
import os
from typing import List, Dict, Optional, Any, TextIO

def read_file(file_path: str) -> tuple[str, List[str]]:
    """ファイルを読み込み、内容と行のリストを返す
    
    Args:
        file_path (str): 読み込むファイルのパス
        
    Returns:
        tuple[str, List[str]]: ファイルの内容と行のリスト
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    if os.path.getsize(file_path) == 0:
        return "", []
        
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()
        source_lines = source.splitlines(True)  # 改行文字を保持
        
    return source, source_lines

def write_file(file_path: str, lines: List[str]) -> None:
    """行のリストをファイルに書き込む
    
    Args:
        file_path (str): 書き込むファイルのパス
        lines (List[str]): 書き込む行のリスト
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def is_empty_or_comment_only(source: str) -> bool:
    """ソースが空または単なるコメントのみかをチェック
    
    Args:
        source (str): チェックするソースコード
        
    Returns:
        bool: 空またはコメントのみの場合はTrue
    """
    # 一般的なコメント開始文字
    comment_markers = ['#', '//', '/*', '<!--', '"""', "'''"]
    
    # 空白行または各行がコメントで始まるかをチェック
    lines = source.splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped and not any(stripped.startswith(marker) for marker in comment_markers):
            return False
    
    return True

def read_template(template_path: str) -> str:
    """テンプレートファイルを読み込む
    
    Args:
        template_path (str): テンプレートファイルのパス
        
    Returns:
        str: テンプレートの内容
    """
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()

def normalize_text(text: str, replacements: Dict[str, str] = None) -> str:
    """テキストを正規化する（句読点などを置換）
    
    Args:
        text (str): 正規化する元のテキスト
        replacements (Dict[str, str], optional): 置換辞書
        
    Returns:
        str: 正規化されたテキスト
    """
    if replacements is None:
        # デフォルトの置換辞書（日本語の句読点を英語の句読点に変換）
        replacements = {
            '、': ',',
            '。': '.',
            '：': ':',
            '（': '(',
            '）': ')'
        }
    
    result = text
    for old, new in replacements.items():
        result = result.replace(old, new)
        
    return result
