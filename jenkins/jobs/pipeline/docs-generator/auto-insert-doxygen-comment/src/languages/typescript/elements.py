"""
TypeScript固有のコード要素クラス
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any

from common.base_generator import BaseElement, BaseElementInfo, InsertionPoint

@dataclass
class TypeScriptElementInfo(BaseElementInfo):
    """TypeScriptコード要素の基本情報を保持するデータクラス"""
    pass

@dataclass
class FunctionElementInfo(TypeScriptElementInfo):
    """関数の情報を保持するデータクラス"""
    parameters: List[Dict[str, str]] = None  # パラメータ情報のリスト
    return_type: Optional[str] = None
    is_async: bool = False
    is_export: bool = False
    decorators: List[str] = None

@dataclass
class ClassElementInfo(TypeScriptElementInfo):
    """クラスの情報を保持するデータクラス"""
    methods: List[str] = None
    properties: List[Dict[str, Any]] = None
    decorators: List[str] = None
    extends: Optional[str] = None
    implements: List[str] = None
    is_export: bool = False

@dataclass
class InterfaceElementInfo(TypeScriptElementInfo):
    """インターフェースの情報を保持するデータクラス"""
    methods: List[Dict[str, Any]] = None
    properties: List[Dict[str, Any]] = None
    extends: List[str] = None
    is_export: bool = False

@dataclass
class TypeElementInfo(TypeScriptElementInfo):
    """型エイリアスの情報を保持するデータクラス"""
    type_definition: str = None
    is_export: bool = False

@dataclass
class EnumElementInfo(TypeScriptElementInfo):
    """列挙型の情報を保持するデータクラス"""
    members: List[Dict[str, Any]] = None
    is_export: bool = False
    is_const: bool = False

@dataclass
class ModuleElementInfo(TypeScriptElementInfo):
    """モジュール全体の情報を保持するデータクラス"""
    imports: List[str] = None
    exports: List[str] = None
    classes: List[str] = None
    interfaces: List[str] = None
    functions: List[str] = None

class TypeScriptElement(BaseElement[TypeScriptElementInfo]):
    """TypeScriptコード要素を表す基底クラス"""
    
    def find_existing_doc(self, lines: List[str], def_line: int) -> tuple[int, int]:
        """既存のドキュメントコメントの位置を探す"""
        # 実装はサブクラスに委譲する
        return -1, -1

class FunctionElement(TypeScriptElement):
    """TypeScript関数を表すクラス"""
    
    def __init__(self, info: FunctionElementInfo):
        super().__init__(info)
        self.info: FunctionElementInfo = info  # 型ヒントのため再定義
    
    def get_definition_pattern(self) -> str:
        prefix = r"(export\s+)?(async\s+)?(function\s+)?" if self.info.is_export or self.info.is_async else ""
        return f"{prefix}{self.info.name}\\s*\\("
    
    def get_doc_indent(self) -> str:
        return self.info.indent
    
    def find_body_start(self, lines: List[str], def_line: int) -> int:
        """関数本体の開始行を見つける"""
        body_start = def_line
        
        # 括弧の対応を確認
        paren_count = lines[def_line].count('(') - lines[def_line].count(')')
        while paren_count > 0 and body_start < len(lines) - 1:
            body_start += 1
            paren_count += lines[body_start].count('(') - lines[body_start].count(')')
        
        # 関数シグネチャの終わりと本体の開始を見つける
        while body_start < len(lines) and '{' not in lines[body_start]:
            body_start += 1
            
        # 本体の開始行の次の行へ
        return body_start + 1
    
    def find_existing_doc(self, lines: List[str], def_line: int) -> tuple[int, int]:
        """既存のドキュメントコメントの位置を探す"""
        for i in range(def_line - 1, -1, -1):
            if not lines[i].strip():
                continue
                
            line = lines[i].strip()
            
            # JSDoc形式のドキュメントコメント (/** ... */)
            if line.startswith('/**'):
                start_line = i
                end_line = i
                
                # 閉じる */ を探す
                while end_line < len(lines) and '*/' not in lines[end_line]:
                    end_line += 1
                    
                if end_line < len(lines):
                    # コメントと定義行の間に空行か装飾コメント以外の内容がないか確認
                    is_valid_doc = True
                    for j in range(end_line + 1, def_line):
                        if lines[j].strip() and not (
                            lines[j].strip().startswith('//') or 
                            lines[j].strip().startswith('/*')
                        ):
                            is_valid_doc = False
                            break
                    
                    if is_valid_doc:
                        return start_line, end_line
            
            # その他のコード行が見つかったら検索終了
            elif not line.startswith('//') and not line.startswith('/*'):
                break
                
        return -1, -1

class ClassElement(TypeScriptElement):
    """TypeScriptクラスを表すクラス"""
    
    def __init__(self, info: ClassElementInfo):
        super().__init__(info)
        self.info: ClassElementInfo = info  # 型ヒントのため再定義
    
    def get_definition_pattern(self) -> str:
        prefix = r"export\s+" if self.info.is_export else ""
        return f"{prefix}class\\s+{self.info.name}\\s*"
    
    def get_doc_indent(self) -> str:
        return self.info.indent
    
    def find_body_start(self, lines: List[str], def_line: int) -> int:
        """クラス本体の開始行を見つける"""
        body_start = def_line
        
        # クラス定義の続きを探す
        while body_start < len(lines) and '{' not in lines[body_start]:
            body_start += 1
        
        # 本体の開始行の次の行へ
        return body_start + 1
    
    def find_existing_doc(self, lines: List[str], def_line: int) -> tuple[int, int]:
        """既存のドキュメントコメントの位置を探す"""
        for i in range(def_line - 1, -1, -1):
            if not lines[i].strip():
                continue
                
            line = lines[i].strip()
            
            # JSDoc形式のドキュメントコメント (/** ... */)
            if line.startswith('/**'):
                start_line = i
                end_line = i
                
                # 閉じる */ を探す
                while end_line < len(lines) and '*/' not in lines[end_line]:
                    end_line += 1
                    
                if end_line < len(lines):
                    # コメントと定義行の間に空行か装飾コメント以外の内容がないか確認
                    is_valid_doc = True
                    for j in range(end_line + 1, def_line):
                        if lines[j].strip() and not (
                            lines[j].strip().startswith('//') or 
                            lines[j].strip().startswith('/*')
                        ):
                            is_valid_doc = False
                            break
                    
                    if is_valid_doc:
                        return start_line, end_line
            
            # その他のコード行が見つかったら検索終了
            elif not line.startswith('//') and not line.startswith('/*'):
                break
                
        return -1, -1

class InterfaceElement(TypeScriptElement):
    """TypeScriptインターフェースを表すクラス"""
    
    def __init__(self, info: InterfaceElementInfo):
        super().__init__(info)
        self.info: InterfaceElementInfo = info  # 型ヒントのため再定義
    
    def get_definition_pattern(self) -> str:
        prefix = r"export\s+" if self.info.is_export else ""
        return f"{prefix}interface\\s+{self.info.name}\\s*"
    
    def get_doc_indent(self) -> str:
        return self.info.indent
    
    def find_body_start(self, lines: List[str], def_line: int) -> int:
        """インターフェース本体の開始行を見つける"""
        body_start = def_line
        
        # インターフェース定義の続きを探す
        while body_start < len(lines) and '{' not in lines[body_start]:
            body_start += 1
        
        # 本体の開始行の次の行へ
        return body_start + 1
    
    def find_existing_doc(self, lines: List[str], def_line: int) -> tuple[int, int]:
        """既存のドキュメントコメントの位置を探す"""
        for i in range(def_line - 1, -1, -1):
            if not lines[i].strip():
                continue
                
            line = lines[i].strip()
            
            # JSDoc形式のドキュメントコメント (/** ... */)
            if line.startswith('/**'):
                start_line = i
                end_line = i
                
                # 閉じる */ を探す
                while end_line < len(lines) and '*/' not in lines[end_line]:
                    end_line += 1
                    
                if end_line < len(lines):
                    # コメントと定義行の間に空行か装飾コメント以外の内容がないか確認
                    is_valid_doc = True
                    for j in range(end_line + 1, def_line):
                        if lines[j].strip() and not (
                            lines[j].strip().startswith('//') or 
                            lines[j].strip().startswith('/*')
                        ):
                            is_valid_doc = False
                            break
                    
                    if is_valid_doc:
                        return start_line, end_line
            
            # その他のコード行が見つかったら検索終了
            elif not line.startswith('//') and not line.startswith('/*'):
                break
                
        return -1, -1

class TypeElement(TypeScriptElement):
    """TypeScript型エイリアスを表すクラス"""
    
    def __init__(self, info: TypeElementInfo):
        super().__init__(info)
        self.info: TypeElementInfo = info  # 型ヒントのため再定義
    
    def get_definition_pattern(self) -> str:
        prefix = r"export\s+" if self.info.is_export else ""
        return f"{prefix}type\\s+{self.info.name}\\s*="
    
    def get_doc_indent(self) -> str:
        return self.info.indent
    
    def find_body_start(self, lines: List[str], def_line: int) -> int:
        """型定義本体の開始行を見つける"""
        # 型定義は通常1行だが、複数行にまたがる場合もある
        body_start = def_line
        
        while body_start < len(lines) and ';' not in lines[body_start]:
            body_start += 1
            
        return body_start + 1
    
    def find_existing_doc(self, lines: List[str], def_line: int) -> tuple[int, int]:
        """既存のドキュメントコメントの位置を探す"""
        for i in range(def_line - 1, -1, -1):
            if not lines[i].strip():
                continue
                
            line = lines[i].strip()
            
            # JSDoc形式のドキュメントコメント (/** ... */)
            if line.startswith('/**'):
                start_line = i
                end_line = i
                
                # 閉じる */ を探す
                while end_line < len(lines) and '*/' not in lines[end_line]:
                    end_line += 1
                    
                if end_line < len(lines):
                    # コメントと定義行の間に空行か装飾コメント以外の内容がないか確認
                    is_valid_doc = True
                    for j in range(end_line + 1, def_line):
                        if lines[j].strip() and not (
                            lines[j].strip().startswith('//') or 
                            lines[j].strip().startswith('/*')
                        ):
                            is_valid_doc = False
                            break
                    
                    if is_valid_doc:
                        return start_line, end_line
            
            # その他のコード行が見つかったら検索終了
            elif not line.startswith('//') and not line.startswith('/*'):
                break
                
        return -1, -1

class EnumElement(TypeScriptElement):
    """TypeScript列挙型を表すクラス"""
    
    def __init__(self, info: EnumElementInfo):
        super().__init__(info)
        self.info: EnumElementInfo = info  # 型ヒントのため再定義
    
    def get_definition_pattern(self) -> str:
        prefix = r"export\s+" if self.info.is_export else ""
        const_prefix = r"const\s+" if self.info.is_const else ""
        return f"{prefix}{const_prefix}enum\\s+{self.info.name}\\s*"
    
    def get_doc_indent(self) -> str:
        return self.info.indent
    
    def find_body_start(self, lines: List[str], def_line: int) -> int:
        """列挙型本体の開始行を見つける"""
        body_start = def_line
        
        # 列挙型定義の続きを探す
        while body_start < len(lines) and '{' not in lines[body_start]:
            body_start += 1
        
        # 本体の開始行の次の行へ
        return body_start + 1
    
    def find_existing_doc(self, lines: List[str], def_line: int) -> tuple[int, int]:
        """既存のドキュメントコメントの位置を探す"""
        for i in range(def_line - 1, -1, -1):
            if not lines[i].strip():
                continue
                
            line = lines[i].strip()
            
            # JSDoc形式のドキュメントコメント (/** ... */)
            if line.startswith('/**'):
                start_line = i
                end_line = i
                
                # 閉じる */ を探す
                while end_line < len(lines) and '*/' not in lines[end_line]:
                    end_line += 1
                    
                if end_line < len(lines):
                    # コメントと定義行の間に空行か装飾コメント以外の内容がないか確認
                    is_valid_doc = True
                    for j in range(end_line + 1, def_line):
                        if lines[j].strip() and not (
                            lines[j].strip().startswith('//') or 
                            lines[j].strip().startswith('/*')
                        ):
                            is_valid_doc = False
                            break
                    
                    if is_valid_doc:
                        return start_line, end_line
            
            # その他のコード行が見つかったら検索終了
            elif not line.startswith('//') and not line.startswith('/*'):
                break
                
        return -1, -1

class ModuleElement(TypeScriptElement):
    """TypeScriptモジュール全体を表すクラス"""
    
    def __init__(self, info: ModuleElementInfo):
        super().__init__(info)
        self.info: ModuleElementInfo = info  # 型ヒントのため再定義
    
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
        """既存のドキュメントコメントの位置を探す"""
        for i in range(len(lines)):
            line = lines[i].strip()
            
            # ファイル先頭のJSDocコメントを探す
            if line.startswith('/**'):
                start_line = i
                end_line = i
                
                # 閉じる */ を探す
                while end_line < len(lines) and '*/' not in lines[end_line]:
                    end_line += 1
                    
                if end_line < len(lines):
                    # 後続のコードが通常のコード行かどうか確認
                    next_code_line = end_line + 1
                    while next_code_line < len(lines) and not lines[next_code_line].strip():
                        next_code_line += 1
                    
                    if next_code_line < len(lines):
                        next_line = lines[next_code_line].strip()
                        # importやexport文の前のコメントならモジュールドキュメント
                        if (next_line.startswith('import ') or 
                            next_line.startswith('export ') or
                            next_line.startswith('/**')):
                            return start_line, end_line
            
            # 実質的なコード行が見つかったら検索終了
            elif line and not line.startswith('//') and not line.startswith('/*'):
                break
                
        return -1, -1
