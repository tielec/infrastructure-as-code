"""
Python固有のコード要素クラス
"""
from dataclasses import dataclass
import re
from typing import Dict, List, Optional, Union, Any

from common.base_generator import BaseElement, BaseElementInfo, InsertionPoint

@dataclass
class PythonElementInfo(BaseElementInfo):
    """Pythonコード要素の基本情報を保持するデータクラス"""
    pass

@dataclass
class FunctionElementInfo(PythonElementInfo):
    """関数の情報を保持するデータクラス"""
    is_async: bool = False
    decorators: List[str] = None

@dataclass
class ClassElementInfo(PythonElementInfo):
    """クラスの情報を保持するデータクラス"""
    methods: List[str] = None
    decorators: List[str] = None

@dataclass
class ModuleElementInfo(PythonElementInfo):
    """モジュールの情報を保持するデータクラス"""
    imports: List[str] = None
    classes: List[str] = None
    functions: List[str] = None

class PythonElement(BaseElement[PythonElementInfo]):
    """Pythonコード要素を表す基底クラス"""
    
    def find_existing_doc(self, lines: List[str], def_line: int) -> tuple[int, int]:
        """既存のdocstringの位置を探す"""
        # 実装はサブクラスに委譲する
        return -1, -1

class FunctionElement(PythonElement):
    """Python関数を表すクラス"""
    
    def __init__(self, info: FunctionElementInfo):
        super().__init__(info)
        self.info: FunctionElementInfo = info  # 型ヒントのため再定義
    
    def get_definition_pattern(self) -> str:
        prefix = r"(async\s+)?def" if self.info.is_async else "def"
        return f"{prefix}\\s+{self.info.name}\\s*\\("
    
    def get_doc_indent(self) -> str:
        return self.info.indent + '    '  # 標準の4スペースインデント
    
    def find_body_start(self, lines: List[str], def_line: int) -> int:
        """関数本体の開始行を見つける"""
        body_start = def_line
        
        # 括弧の対応を確認
        paren_count = lines[def_line].count('(') - lines[def_line].count(')')
        while paren_count > 0 and body_start < len(lines) - 1:
            body_start += 1
            paren_count += lines[body_start].count('(') - lines[body_start].count(')')
        
        # コロンを探す
        while body_start < len(lines) and ':' not in lines[body_start]:
            body_start += 1
        
        if body_start >= len(lines):
            raise ValueError(f"Could not find function body start for {self.info.name}")
        
        # コロンの次の行へ
        body_start += 1
        
        # 空行をスキップ
        while body_start < len(lines) and not lines[body_start].strip():
            body_start += 1
            
        return body_start
    
    def find_existing_doc(self, lines: List[str], def_line: int) -> tuple[int, int]:
        """既存のdocstringの位置を探す"""
        body_start = self.find_body_start(lines, def_line)
        if body_start >= len(lines):
            return -1, -1
            
        stripped_line = lines[body_start].strip()
        if not (stripped_line.startswith('"""') or stripped_line.startswith("'''")):
            return -1, -1
            
        quote_char = stripped_line[0] * 3
        
        # 単一行のdocstring
        if stripped_line.count(quote_char) == 2:
            return body_start, body_start
            
        # 複数行のdocstring
        doc_end = body_start + 1
        while doc_end < len(lines) and quote_char not in lines[doc_end]:
            doc_end += 1
            
        if doc_end < len(lines):
            return body_start, doc_end
            
        return -1, -1

class ClassElement(PythonElement):
    """Pythonクラスを表すクラス"""
    
    def __init__(self, info: ClassElementInfo):
        super().__init__(info)
        self.info: ClassElementInfo = info  # 型ヒントのため再定義
    
    def get_definition_pattern(self) -> str:
        return f"class\\s+{self.info.name}\\s*[:\\(]"
    
    def get_doc_indent(self) -> str:
        return self.info.indent + '    '  # 標準の4スペースインデント
    
    def find_body_start(self, lines: List[str], def_line: int) -> int:
        """クラス本体の開始行を見つける"""
        body_start = def_line
        
        # 継承がある場合は括弧の対応を確認
        if '(' in lines[def_line]:
            paren_count = lines[def_line].count('(') - lines[def_line].count(')')
            while paren_count > 0 and body_start < len(lines) - 1:
                body_start += 1
                paren_count += lines[body_start].count('(') - lines[body_start].count(')')
        
        # コロンを探す
        while body_start < len(lines) and ':' not in lines[body_start]:
            body_start += 1
        
        if body_start >= len(lines):
            raise ValueError(f"Could not find class body start for {self.info.name}")
        
        # コロンの次の行へ
        body_start += 1
        
        # 空行をスキップ
        while body_start < len(lines) and not lines[body_start].strip():
            body_start += 1
            
        return body_start
    
    def find_existing_doc(self, lines: List[str], def_line: int) -> tuple[int, int]:
        """既存のdocstringの位置を探す"""
        body_start = self.find_body_start(lines, def_line)
        if body_start >= len(lines):
            return -1, -1
            
        stripped_line = lines[body_start].strip()
        if not (stripped_line.startswith('"""') or stripped_line.startswith("'''")):
            return -1, -1
            
        quote_char = stripped_line[0] * 3
        
        # 単一行のdocstring
        if stripped_line.count(quote_char) == 2:
            return body_start, body_start
            
        # 複数行のdocstring
        doc_end = body_start + 1
        while doc_end < len(lines) and quote_char not in lines[doc_end]:
            doc_end += 1
            
        if doc_end < len(lines):
            return body_start, doc_end
            
        return -1, -1

class ModuleElement(PythonElement):
    """Pythonモジュール全体を表すクラス"""
    
    def __init__(self, info: ModuleElementInfo):
        super().__init__(info)
        self.info: ModuleElementInfo = info
    
    def get_definition_pattern(self) -> str:
        # モジュールは特定のパターンを持たないため、空文字を返す
        return ""
    
    def get_doc_indent(self) -> str:
        # モジュールレベルのdocstringはインデントなし
        return ""
    
    def find_body_start(self, lines: List[str], def_line: int) -> int:
        """モジュール本体の開始行を見つける"""
        body_start = 0
        while body_start < len(lines) and not lines[body_start].strip():
            body_start += 1
        return body_start
    
    def _find_definition_line(self, lines: List[str]) -> Optional[int]:
        """モジュールの開始行を探す（常に0を返す）"""
        return 0
    
    def find_existing_doc(self, lines: List[str], def_line: int) -> tuple[int, int]:
        """既存のdocstringの位置を探す"""
        body_start = self.find_body_start(lines, def_line)
        if body_start >= len(lines):
            return -1, -1
            
        stripped_line = lines[body_start].strip()
        if not (stripped_line.startswith('"""') or stripped_line.startswith("'''")):
            return -1, -1
            
        quote_char = stripped_line[0] * 3
        
        # 単一行のdocstring
        if stripped_line.count(quote_char) == 2:
            return body_start, body_start
            
        # 複数行のdocstring
        doc_end = body_start + 1
        while doc_end < len(lines) and quote_char not in lines[doc_end]:
            doc_end += 1
            
        if doc_end < len(lines):
            return body_start, doc_end
            
        return -1, -1
