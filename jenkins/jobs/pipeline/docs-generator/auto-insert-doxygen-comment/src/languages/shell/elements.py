"""
Shell固有のコード要素クラス
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any

from common.base_generator import BaseElement, BaseElementInfo, InsertionPoint

@dataclass
class ShellElementInfo(BaseElementInfo):
    """シェルスクリプト要素の基本情報を保持するデータクラス"""
    pass

@dataclass
class FunctionElementInfo(ShellElementInfo):
    """シェル関数の情報を保持するデータクラス"""
    parameters: List[str] = None  # 関数のパラメータリスト

@dataclass
class ScriptElementInfo(ShellElementInfo):
    """スクリプト全体の情報を保持するデータクラス"""
    functions: List[str] = None
    dependencies: List[str] = None

class ShellElement(BaseElement[ShellElementInfo]):
    """シェルスクリプトの要素（関数やスクリプト全体）を表す基底クラス"""
    
    def find_existing_doc(self, lines: List[str], def_line: int) -> tuple[int, int]:
        """既存のDoxygenコメントの位置を探す"""
        for i in range(def_line - 1, -1, -1):
            if not lines[i].strip():
                continue
            line = lines[i].strip()
            if line.startswith('##'):
                start_line = i
                while i >= 0 and (lines[i].strip().startswith('#') or not lines[i].strip()):
                    i -= 1
                return i + 1, start_line
            elif not line.startswith('#'):
                break
        return -1, -1

class FunctionElement(ShellElement):
    """シェル関数を表すクラス"""
    
    def __init__(self, info: FunctionElementInfo):
        super().__init__(info)
        self.info: FunctionElementInfo = info  # 型ヒントのため再定義
    
    def get_definition_pattern(self) -> str:
        return f"^{self.info.indent}(function\\s+)?{self.info.name}\\s*\\(\\)"
    
    def get_doc_indent(self) -> str:
        return self.info.indent
    
    def find_body_start(self, lines: List[str], def_line: int) -> int:
        """関数本体の開始行を見つける"""
        i = def_line
        while i < len(lines) and '{' not in lines[i]:
            i += 1
        return i + 1

class ScriptElement(ShellElement):
    """スクリプト全体を表すクラス"""
    
    def __init__(self, info: ScriptElementInfo):
        super().__init__(info)
        self.info: ScriptElementInfo = info  # 型ヒントのため再定義
    
    def get_definition_pattern(self) -> str:
        # スクリプト全体なのでパターンは不要
        return ""
    
    def get_doc_indent(self) -> str:
        # スクリプトレベルのコメントはインデントなし
        return ""
    
    def find_body_start(self, lines: List[str], def_line: int) -> int:
        """スクリプト本体の開始行を見つける"""
        # シバン行をチェック
        for i, line in enumerate(lines):
            if line.strip():
                if line.startswith('#!'):
                    return i + 1
                return i
        return 0
    
    def _find_definition_line(self, lines: List[str]) -> Optional[int]:
        """スクリプトの開始行を探す（シバン行）"""
        for i, line in enumerate(lines):
            if line.strip():
                if line.startswith('#!'):
                    return i + 1
                return i
        return 0
