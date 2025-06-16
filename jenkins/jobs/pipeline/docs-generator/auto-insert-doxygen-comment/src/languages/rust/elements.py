# elements.py
"""
Rust固有のコード要素クラス

このモジュールは、Rustコードの構造要素（関数、構造体、列挙型など）を表現するデータモデルを定義します。
各クラスは、コード要素の情報とドキュメント管理に必要な機能を提供します。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any, Set
import hashlib
import re
import os
import json # For context serialization in prepare_code_with_context

# 共通基底クラス (common ディレクトリにある想定)
# BaseElement, BaseElementInfo, InsertionPoint をインポート
try:
    from common.base_generator import BaseElement as BaseElementFromCommon, BaseElementInfo as BaseInfoFromCommon, InsertionPoint as InsertionPointFromCommon
except ImportError:
    # common.base_generator が存在しない場合のフォールバック (ダミー定義)
    print("Warning: common.base_generator not found. Using dummy base classes.")
    @dataclass
    class BaseInfoFromCommon:
        name: str = ""
    @dataclass
    class InsertionPointFromCommon:
        def_line: int = 0; body_start: int = 0; existing_doc_start: int = -1
        existing_doc_end: int = -1; base_indent: str = ""
    class BaseElementFromCommon:
        def __init__(self, info: BaseInfoFromCommon): self.info = info
        def get_unique_id(self) -> str: return f"base:{self.info.name or 'unknown'}"
        def analyze_insertion_point(self, lines: List[str]) -> 'InsertionPointFromCommon': raise NotImplementedError

BaseElement = BaseElementFromCommon
BaseInfo = BaseInfoFromCommon
InsertionPoint = InsertionPointFromCommon


@dataclass
class RustElementInfo(BaseInfo):
    """Rustコード要素の基本情報を保持するデータクラス"""
    name: str = ""
    code: str = ""
    start_line: int = 0
    end_line: int = 0
    start_col: int = 0
    end_col: int = 0
    indent: str = ""
    source_code: str = ""
    source_lines: List[str] = field(default_factory=list)
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FunctionElementInfo(RustElementInfo):
    """関数の情報を保持するデータクラス"""
    parameters: List[Dict[str, str]] = field(default_factory=list)
    return_type: Optional[str] = None
    is_pub: bool = False
    is_async: bool = False
    is_const: bool = False
    is_unsafe: bool = False
    parent_type: Optional[str] = None
    parent_path: Optional[str] = None
    is_impl_method: bool = False
    is_trait_method: bool = False
    args_str: str = ""
    signature: str = ""
    fully_qualified_name: str = ""


@dataclass
class StructElementInfo(RustElementInfo):
    """構造体の情報を保持するデータクラス"""
    fields: List[Dict[str, Any]] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    is_pub: bool = False
    type_params: List[str] = field(default_factory=list)
    implemented_traits: List[str] = field(default_factory=list)


@dataclass
class EnumElementInfo(RustElementInfo):
    """列挙型の情報を保持するデータクラス"""
    variants: List[Dict[str, Any]] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    is_pub: bool = False
    type_params: List[str] = field(default_factory=list)
    implemented_traits: List[str] = field(default_factory=list)


@dataclass
class TraitElementInfo(RustElementInfo):
    """トレイトの情報を保持するデータクラス"""
    methods: List[Dict[str, Any]] = field(default_factory=list)
    associated_types: List[str] = field(default_factory=list)
    is_pub: bool = False
    super_traits: List[str] = field(default_factory=list)


@dataclass
class ModuleElementInfo(RustElementInfo):
    """モジュールの情報を保持するデータクラス"""
    imports: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    structs: List[str] = field(default_factory=list)
    enums: List[str] = field(default_factory=list)
    traits: List[str] = field(default_factory=list)
    is_inline: bool = False


@dataclass
class ImplBlockInfo:
    """implブロックの情報を保持するデータクラス (パーサー内部で使用)"""
    target_type: str
    trait_name: Optional[str] = None
    start_line: int = 1
    end_line: int = 1
    start_col: int = 0
    end_col: int = 0
    methods: List[Dict[str, Any]] = field(default_factory=list)
    type_params: List[str] = field(default_factory=list)
    where_clauses: List[str] = field(default_factory=list)
    source_code: str = ""


class RustElement(BaseElement[RustElementInfo]):
    """Rustコード要素を表す基底クラス"""

    def __init__(self, info: RustElementInfo):
        if info is None:
            raise ValueError("Cannot initialize RustElement with None info")
        super().__init__(info)
        self.info: RustElementInfo = info

    def get_definition_pattern(self) -> str:
        """要素定義行を特定するための正規表現パターン文字列を返す"""
        if not self.info or not self.info.name:
            return r"$.^"
        escaped_name = re.escape(self.info.name)
        element_type = self.__class__.__name__.replace('Element', '').lower()
        # Provide specific patterns for known types
        if element_type == 'function':
            vis = r"(?:pub(?:\([^)]+\))?\s+)?"
            prefix = r"^\s*" + vis + r"(?:async\s+)?(?:const\s+)?(?:unsafe\s+)?"
            suffix = r"fn\s+" + escaped_name + r"(?:<.*?>)?\s*\("
            return prefix + suffix
        elif element_type == 'struct':
            vis = r"(?:pub(?:\([^)]+\))?\s+)?"
            prefix = r"^\s*" + vis
            suffix = r"struct\s+" + escaped_name + r"(?:<.*?>)?\s*(?:\{|;|\()"
            return prefix + suffix
        elif element_type == 'enum':
             vis = r"(?:pub(?:\([^)]+\))?\s+)?"
             prefix = r"^\s*" + vis
             suffix = r"enum\s+" + escaped_name + r"(?:<.*?>)?\s*\{"
             return prefix + suffix
        elif element_type == 'trait':
             vis = r"(?:pub(?:\([^)]+\))?\s+)?"
             prefix = r"^\s*" + vis + r"(?:unsafe\s+)?"
             suffix = r"trait\s+" + escaped_name + r"(?:<.*?>)?\s*(?::|\{)"
             return prefix + suffix
        elif element_type == 'module' and isinstance(self.info, ModuleElementInfo) and self.info.is_inline:
             vis = r"(?:pub(?:\([^)]+\))?\s+)?"
             prefix = r"^\s*" + vis
             suffix = r"mod\s+" + escaped_name + r"\s*(?:\{|;)"
             return prefix + suffix
        else: # Fallback
            return r"\b" + escaped_name + r"\b"

    def get_doc_indent(self) -> str:
        """ドキュメントのインデントレベルを返す"""
        return self.info.indent if self.info and self.info.indent is not None else ""

    def find_body_start(self, lines: List[str], def_line: int) -> int:
        """コード本体の開始行を見つける (0-based)"""
        if self.info is None: return def_line + 1
        search_end_line_idx = len(lines) - 1
        if self.info.end_line > 0:
             search_end_line_idx = min(self.info.end_line - 1, len(lines) - 1)
        for i in range(def_line, search_end_line_idx + 1):
            if '{' in lines[i]: return i + 1
        for i in range(def_line, search_end_line_idx + 1):
            if lines[i].rstrip().endswith(';'): return i + 1
        return def_line + 1

    def find_existing_doc(self, lines: List[str], def_line: int) -> tuple[int, int]:
        """指定行(def_line, 0-based)の直前にあるDoxygenブロックコメントを探す"""
        doc_start = -1; doc_end = -1; in_doc_block = False
        search_limit = 20; start_search_line = max(0, def_line - search_limit)
        for i in range(def_line - 1, start_search_line - 1, -1):
            if i < 0: break
            line_stripped = lines[i].strip()
            if not line_stripped: continue
            if line_stripped.endswith('*/'):
                if not in_doc_block: doc_end = i; in_doc_block = True
                continue
            if line_stripped.startswith('/**'):
                if in_doc_block:
                    doc_start = i; is_valid = True
                    for j in range(doc_end + 1, def_line):
                        if j >= len(lines): break
                        line_j_stripped = lines[j].strip()
                        if line_j_stripped and not line_j_stripped.startswith(('#[', '//', '/*')):
                             is_valid = False; break
                    if is_valid: return doc_start, doc_end
                    else: break
                else: break
            if in_doc_block: continue
            if line_stripped.startswith('#['): continue
            if line_stripped.startswith('//') or (line_stripped.startswith('/*') and not line_stripped.startswith('/**')): continue
            break
        return -1, -1 # Return default if not found or invalid

    # --- analyze_insertion_point (修正済み) ---
    def analyze_insertion_point(self, lines: List[str]) -> InsertionPoint:
        """
        要素のドキュメント挿入位置を解析する。
        Tree-sitter から得られた開始行 (`self.info.start_line`) を使用する。
        """
        if self.info is None or self.info.start_line <= 0:
            display_name = self.info.name if self.info else "<Unknown>"
            raise ValueError(f"Cannot analyze insertion point for '{display_name}': Element info or start_line is missing or invalid ({self.info})")

        def_line_0based = self.info.start_line - 1

        if not (0 <= def_line_0based < len(lines)):
             display_name = self.info.name if self.info else "<Unknown>"
             raise ValueError(f"Definition line ({def_line_0based + 1}) for '{display_name}' is out of range for file with {len(lines)} lines.")

        base_indent = self.get_doc_indent()

        # --- 3. 既存ドキュメントの検索 (修正箇所) ---
        # find_existing_doc の結果を一時変数に格納
        existing_doc_info = self.find_existing_doc(lines, def_line_0based)

        # find_existing_doc が期待通りタプルを返したか確認
        if isinstance(existing_doc_info, tuple) and len(existing_doc_info) == 2:
            _existing_doc_start = existing_doc_info[0]
            _existing_doc_end = existing_doc_info[1] # NameError回避のためアンダースコア付き変数名に変更
        else:
            # 期待通りでない場合は警告を出し、デフォルト値(-1)を設定
            print(f"Warning: find_existing_doc for '{self.info.name}' returned unexpected value: {existing_doc_info}. Assuming no existing doc.")
            _existing_doc_start = -1
            _existing_doc_end = -1

        # --- 4. 本体開始行の検索 ---
        body_start = self.find_body_start(lines, def_line_0based)

        # --- 5. InsertionPoint オブジェクトの作成 (修正箇所) ---
        try:
            insertion_point_obj = InsertionPoint(
                def_line=def_line_0based,
                body_start=body_start,
                existing_doc_start=_existing_doc_start, # アンダースコア付き変数を使用
                existing_doc_end=_existing_doc_end,     # アンダースコア付き変数を使用
                base_indent=base_indent
            )
            return insertion_point_obj
        except Exception as e:
             print(f"Error creating InsertionPoint for '{self.info.name}': {e}")
             print(f"  Values: def_line={def_line_0based}, body_start={body_start}, existing_start={_existing_doc_start}, existing_end={_existing_doc_end}, indent='{base_indent}'")
             raise

    def get_unique_id(self) -> str:
        """要素の一意なIDを生成する (シグネチャベース、改善版)"""
        if self.info is None: return "unknown:unknown:0"
        element_type_prefix = self.__class__.__name__.replace('Element', '').lower()
        name_part = self.info.name or "anonymous"
        base_id = f"{element_type_prefix}:{name_part}"
        signature_hash = ""
        if isinstance(self.info, FunctionElementInfo):
            param_types = [p.get('type', '?') for p in self.info.parameters] if self.info.parameters else []
            signature_str = f"({','.join(param_types)})->({self.info.return_type or '()'})"
            signature_hash = hashlib.md5(signature_str.encode()).hexdigest()[:12]
            if self.info.is_impl_method and self.info.parent_type:
                parent_base = re.sub(r'<.*?>.*$', '', self.info.parent_type).strip()
                trait_base = ""
                if self.info.metadata and self.info.metadata.get('trait_name'):
                     trait_maybe = self.info.metadata.get('trait_name')
                     if isinstance(trait_maybe, str):
                         trait_base = re.sub(r'<.*?>.*$', '', trait_maybe).strip()
                prefix = f"impl_trait_method:{parent_base}_for_{trait_base}" if trait_base else f"impl_method:{parent_base}"
                base_id = f"{prefix}::{name_part}"
        elif isinstance(self.info, ModuleElementInfo):
            prefix = "file_module" if not self.info.is_inline else "inline_module"
            if not self.info.is_inline and self.info.file_path:
                file_id = os.path.splitext(os.path.basename(self.info.file_path))[0]
                name_part = file_id
            base_id = f"{prefix}:{name_part}"
        final_id = f"{base_id.rstrip(':')}:{signature_hash}" if signature_hash else base_id.rstrip(':')
        return final_id

# --- 要素サブクラス ---
class FunctionElement(RustElement):
    def __init__(self, info: FunctionElementInfo):
        if not isinstance(info, FunctionElementInfo): raise TypeError("FunctionElement requires FunctionElementInfo")
        super().__init__(info); self.info: FunctionElementInfo = info

class StructElement(RustElement):
    def __init__(self, info: StructElementInfo):
        if not isinstance(info, StructElementInfo): raise TypeError("StructElement requires StructElementInfo")
        super().__init__(info); self.info: StructElementInfo = info

class EnumElement(RustElement):
    def __init__(self, info: EnumElementInfo):
        if not isinstance(info, EnumElementInfo): raise TypeError("EnumElement requires EnumElementInfo")
        super().__init__(info); self.info: EnumElementInfo = info

class TraitElement(RustElement):
    def __init__(self, info: TraitElementInfo):
        if not isinstance(info, TraitElementInfo): raise TypeError("TraitElement requires TraitElementInfo")
        super().__init__(info); self.info: TraitElementInfo = info

# ModuleElement は analyze_insertion_point をオーバーライド
class ModuleElement(RustElement):
    def __init__(self, info: ModuleElementInfo):
        if not isinstance(info, ModuleElementInfo): raise TypeError("ModuleElement requires ModuleElementInfo")
        super().__init__(info); self.info: ModuleElementInfo = info

    def get_definition_pattern(self) -> str:
        if not self.info or not self.info.is_inline or not self.info.name : return r"$.^"
        name = re.escape(self.info.name)
        vis = r"(?:pub(?:\([^)]+\))?\s+)?"
        prefix = r"^\s*" + vis
        suffix = r"mod\s+" + name + r"\s*(?:\{|;)"
        return prefix + suffix

    def find_body_start(self, lines: List[str], def_line: int) -> int:
        if not self.info.is_inline: return 0
        else: return super().find_body_start(lines, def_line)

    def find_existing_doc(self, lines: List[str], def_line: int) -> tuple[int, int]:
         if not self.info.is_inline:
             if not lines: return -1, -1
             first_code_line_idx = 0
             while first_code_line_idx < len(lines):
                 line_stripped = lines[first_code_line_idx].strip()
                 if line_stripped and not line_stripped.startswith('#!') and not line_stripped.startswith('//') and not line_stripped.startswith('/*'):
                     break
                 first_code_line_idx += 1
             # Search *before* the first code line
             return super().find_existing_doc(lines, first_code_line_idx)
         else:
             return super().find_existing_doc(lines, def_line)

    # analyze_insertion_point (ModuleElementのオーバーライド) - 修正済み analyze_insertion_point に合わせる
    def analyze_insertion_point(self, lines: List[str]) -> InsertionPoint:
         if not self.info.is_inline:
             # File-level module
             def_line_0based = 0
             # Use the corrected find_existing_doc for file level
             existing_doc_info = self.find_existing_doc(lines, def_line_0based)
             if isinstance(existing_doc_info, tuple) and len(existing_doc_info) == 2:
                  _existing_doc_start, _existing_doc_end = existing_doc_info
             else:
                  print(f"Warning: find_existing_doc for file module '{self.info.name}' returned unexpected value: {existing_doc_info}.")
                  _existing_doc_start, _existing_doc_end = -1, -1

             body_start = self.find_body_start(lines, def_line_0based) # Always 0
             base_indent = "" # No indent

             return InsertionPoint(
                 def_line=def_line_0based,
                 body_start=body_start,
                 existing_doc_start=_existing_doc_start,
                 existing_doc_end=_existing_doc_end,
                 base_indent=base_indent
             )
         else:
             # Inline module: use the base class's corrected analyze_insertion_point
             return super().analyze_insertion_point(lines)
