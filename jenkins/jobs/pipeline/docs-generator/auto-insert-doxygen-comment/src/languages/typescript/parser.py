"""
TypeScriptコードを解析するためのパーサークラス
"""
import re
from typing import Dict, List, Optional, Union, Any, Set

from common.base_generator import ElementParser
from languages.typescript.elements import (
    TypeScriptElementInfo, FunctionElementInfo, ClassElementInfo,
    InterfaceElementInfo, TypeElementInfo, EnumElementInfo, ModuleElementInfo,
    FunctionElement, ClassElement, InterfaceElement, TypeElement, EnumElement, ModuleElement
)

class TypeScriptParser(ElementParser):
    """TypeScriptコードを解析するパーサークラス"""
    
    def __init__(self):
        """パーサーを初期化"""
        # デバッグモード（詳細なログ出力用）
        self.debug = False
        # プロセス中の情報を保持するための辞書
        self.context = {}
    
    def parse_file(self, file_path: str) -> List[Union[FunctionElement, ClassElement, InterfaceElement, TypeElement, EnumElement]]:
        """TypeScriptファイルを解析し、コード要素を抽出する
        
        Args:
            file_path (str): 解析対象のTypeScriptファイルパス
            
        Returns:
            List[Union[...]]: 抽出されたコード要素のリスト
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
            source_lines = source.splitlines(True)  # 改行文字を保持
        
        # パース結果を保存するリスト
        elements = []
        
        # クラスを抽出
        classes = self._extract_classes(source_lines)
        elements.extend(classes)
        
        # インターフェースを抽出
        interfaces = self._extract_interfaces(source_lines)
        elements.extend(interfaces)
        
        # 関数を抽出
        functions = self._extract_functions(source_lines)
        elements.extend(functions)
        
        # 型エイリアスを抽出
        types = self._extract_types(source_lines)
        elements.extend(types)
        
        # 列挙型を抽出
        enums = self._extract_enums(source_lines)
        elements.extend(enums)
        
        return elements
    
    def extract_module_info(self, source: str, source_lines: List[str]) -> ModuleElement:
        """モジュール情報を抽出する
        
        Args:
            source (str): ソースコード全体
            source_lines (List[str]): ソースコードの行のリスト
            
        Returns:
            ModuleElement: モジュール情報を含むModuleElement
        """
        # importを抽出
        imports = []
        import_pattern = r'import\s+.*?from\s+[\'"].*?[\'"];'
        for match in re.finditer(import_pattern, source):
            imports.append(match.group())
        
        # exportを抽出
        exports = []
        export_pattern = r'export\s+(?:default\s+)?(?:class|interface|function|const|let|var|type|enum)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        for match in re.finditer(export_pattern, source):
            exports.append(match.group(1))
        
        info = ModuleElementInfo(
            name="module",  # モジュール名はファイル名から取得することも可能
            code=source,
            start_line=0,
            source_lines=source_lines,
            indent="",
            imports=imports,
            exports=exports,
            classes=[],
            interfaces=[],
            functions=[]
        )
        
        return ModuleElement(info)
    
    def _extract_classes(self, source_lines: List[str]) -> List[ClassElement]:
        """クラスを抽出する
        
        Args:
            source_lines (List[str]): ソースコードの行のリスト
            
        Returns:
            List[ClassElement]: 抽出されたクラス要素のリスト
        """
        classes = []
        class_pattern = r'^(\s*)(export\s+)?(abstract\s+)?class\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        
        i = 0
        while i < len(source_lines):
            line = source_lines[i]
            match = re.search(class_pattern, line)
            
            if match:
                indent, export, abstract, name = match.groups()
                indent = indent or ""
                is_export = export is not None
                start_line = i
                
                # クラス定義の行を解析してextendsとimplements情報を抽出
                extends = None
                implements = []
                
                # extends部分を抽出
                extends_match = re.search(r'extends\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
                if extends_match:
                    extends = extends_match.group(1)
                
                # implements部分を抽出
                implements_match = re.search(r'implements\s+(.*?)(?:\{|$)', line)
                if implements_match:
                    implements_str = implements_match.group(1).strip()
                    implements = [s.strip() for s in implements_str.split(',')]
                
                # クラス本体の終了位置を見つける
                end_line = self._find_balanced_block(source_lines, i)
                
                # クラスのコードを取得
                code_lines = source_lines[start_line:end_line + 1]
                code = ''.join(code_lines)
                
                # メソッドとプロパティを抽出する処理（簡略化）
                methods = []
                properties = []
                
                # クラス情報を作成
                info = ClassElementInfo(
                    name=name,
                    code=code,
                    start_line=start_line,
                    source_lines=code_lines,
                    indent=indent,
                    methods=methods,
                    properties=properties,
                    decorators=[],
                    extends=extends,
                    implements=implements,
                    is_export=is_export
                )
                
                classes.append(ClassElement(info))
                
                # 次の検索位置を更新
                i = end_line + 1
                continue
            
            i += 1
        
        return classes
    
    def _extract_interfaces(self, source_lines: List[str]) -> List[InterfaceElement]:
        """インターフェースを抽出する
        
        Args:
            source_lines (List[str]): ソースコードの行のリスト
            
        Returns:
            List[InterfaceElement]: 抽出されたインターフェース要素のリスト
        """
        interfaces = []
        # より柔軟なパターンマッチングのための正規表現（ジェネリック型もサポート）
        interface_pattern = r'^(\s*)(export\s+)?interface\s+([a-zA-Z_][a-zA-Z0-9_]*(?:<[^{>]*>)?)'
        
        i = 0
        while i < len(source_lines):
            line = source_lines[i]
            match = re.search(interface_pattern, line)
            
            if match:
                indent, export, name = match.groups()
                
                # ジェネリック型パラメータが含まれている場合、基本名を抽出
                base_name = name.split('<')[0] if '<' in name else name
                
                indent = indent or ""
                is_export = export is not None
                start_line = i
                
                # extends情報を抽出（複数の継承をサポート）
                extends = []
                # クラス定義行だけでなく、次の行も含めて調査
                extends_line = line
                j = i
                while j < len(source_lines) and '{' not in extends_line:
                    j += 1
                    if j < len(source_lines):
                        extends_line += source_lines[j]
                
                extends_match = re.search(r'extends\s+(.*?)(?:\{|$)', extends_line)
                if extends_match:
                    # 継承対象をカンマで分割し、それぞれをトリミング
                    extends_str = extends_match.group(1).strip()
                    # ジェネリック型を含む継承も適切に処理
                    extends = []
                    curr_extend = ""
                    angle_brackets = 0
                    
                    for char in extends_str:
                        if char == '<':
                            angle_brackets += 1
                            curr_extend += char
                        elif char == '>':
                            angle_brackets -= 1
                            curr_extend += char
                        elif char == ',' and angle_brackets == 0:
                            extends.append(curr_extend.strip())
                            curr_extend = ""
                        else:
                            curr_extend += char
                    
                    if curr_extend:
                        extends.append(curr_extend.strip())
                
                # インターフェース本体の終了位置を見つける
                end_line = self._find_balanced_block(source_lines, i)
                
                # インターフェースのコードを取得
                code_lines = source_lines[start_line:end_line + 1]
                code = ''.join(code_lines)
                
                # メソッドとプロパティを抽出（より詳細な抽出）
                methods = []
                properties = []
                
                # インターフェース本体を解析（中括弧内を探索）
                in_body = False
                for body_line_idx in range(len(code_lines)):
                    body_line = code_lines[body_line_idx]
                    
                    if '{' in body_line and not in_body:
                        in_body = True
                        continue
                    
                    if in_body and '}' in body_line and body_line.strip() == '}':
                        break
                    
                    if in_body:
                        line_content = body_line.strip()
                        if not line_content or line_content.startswith('//') or line_content.startswith('/*'):
                            continue
                        
                        # メソッド（括弧を含む）とプロパティ（型定義のみ）を区別
                        if '(' in line_content:
                            method_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\(|\?:)', line_content)
                            if method_match:
                                method_name = method_match.group(1)
                                # params, return_typeなどの情報を抽出
                                methods.append({
                                    'name': method_name,
                                    'signature': line_content.rstrip(';')
                                })
                        else:
                            property_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)(?:\?)?:\s*(.*)', line_content)
                            if property_match:
                                prop_name, prop_type = property_match.groups()
                                prop_type = prop_type.rstrip(';')
                                properties.append({
                                    'name': prop_name,
                                    'type': prop_type,
                                    'optional': '?' in line_content and line_content.index('?') < line_content.index(':')
                                })
                
                # インターフェース情報を作成
                info = InterfaceElementInfo(
                    name=base_name,  # ジェネリックを除いた基本名を使用
                    code=code,
                    start_line=start_line,
                    source_lines=code_lines,
                    indent=indent,
                    methods=methods,
                    properties=properties,
                    extends=extends,
                    is_export=is_export
                )
                
                interfaces.append(InterfaceElement(info))
                
                # 次の検索位置を更新
                i = end_line + 1
                continue
            
            i += 1
        
        return interfaces
    
    def _extract_functions(self, source_lines: List[str]) -> List[FunctionElement]:
        """関数を抽出する
        
        Args:
            source_lines (List[str]): ソースコードの行のリスト
            
        Returns:
            List[FunctionElement]: 抽出された関数要素のリスト
        """
        functions = []
        # 通常の関数定義とアロー関数の両方をサポート
        function_pattern = r'^(\s*)(export\s+)?(async\s+)?(?:function\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        
        i = 0
        while i < len(source_lines):
            line = source_lines[i]
            match = re.search(function_pattern, line)
            
            if match:
                indent, export, async_kw, name = match.groups()
                indent = indent or ""
                is_export = export is not None
                is_async = async_kw is not None
                start_line = i
                
                # 関数の括弧の対応を確認して終了位置を特定
                paren_count = line.count('(') - line.count(')')
                current_line = i
                while paren_count > 0 and current_line < len(source_lines) - 1:
                    current_line += 1
                    paren_count += source_lines[current_line].count('(') - source_lines[current_line].count(')')
                
                # 戻り値の型情報を抽出
                return_type = None
                signature_end = current_line
                while signature_end < len(source_lines) and '{' not in source_lines[signature_end]:
                    signature_line = source_lines[signature_end]
                    if ':' in signature_line and '=>' not in signature_line:
                        type_match = re.search(r':\s*(.*?)(?:\{|=>|$)', signature_line)
                        if type_match:
                            return_type = type_match.group(1).strip()
                    signature_end += 1
                
                # 関数本体の終了位置を見つける
                end_line = self._find_balanced_block(source_lines, signature_end)
                
                # 関数のコードを取得
                code_lines = source_lines[start_line:end_line + 1]
                code = ''.join(code_lines)
                
                # パラメータを抽出する処理（簡略化）
                parameters = []
                
                # 関数情報を作成
                info = FunctionElementInfo(
                    name=name,
                    code=code,
                    start_line=start_line,
                    source_lines=code_lines,
                    indent=indent,
                    parameters=parameters,
                    return_type=return_type,
                    is_async=is_async,
                    is_export=is_export,
                    decorators=[]
                )
                
                functions.append(FunctionElement(info))
                
                # 次の検索位置を更新
                i = end_line + 1
                continue
            
            i += 1
        
        return functions
    
    def _extract_types(self, source_lines: List[str]) -> List[TypeElement]:
        """型エイリアスを抽出する
        
        Args:
            source_lines (List[str]): ソースコードの行のリスト
            
        Returns:
            List[TypeElement]: 抽出された型エイリアス要素のリスト
        """
        types = []
        # ジェネリック型パラメータをサポートするパターン
        type_pattern = r'^(\s*)(export\s+)?type\s+([a-zA-Z_][a-zA-Z0-9_]*(?:<[^=]*>)?)\s*='
        
        i = 0
        while i < len(source_lines):
            line = source_lines[i]
            match = re.search(type_pattern, line)
            
            if match:
                indent, export, name = match.groups()
                
                # ジェネリック型パラメータが含まれている場合、基本名を抽出
                base_name = name.split('<')[0] if '<' in name else name
                
                indent = indent or ""
                is_export = export is not None
                start_line = i
                
                # 型定義の終了位置を見つける（セミコロンもしくは次の型定義まで）
                # 複数行にまたがる可能性を考慮
                end_line = start_line
                semicolon_found = False
                bracket_balance = 0
                
                while end_line < len(source_lines):
                    current_line = source_lines[end_line]
                    
                    # 括弧のバランスを追跡
                    bracket_balance += current_line.count('{') - current_line.count('}')
                    bracket_balance += current_line.count('(') - current_line.count(')')
                    bracket_balance += current_line.count('<') - current_line.count('>')
                    bracket_balance += current_line.count('[') - current_line.count(']')
                    
                    # セミコロンを検出（括弧内でないとき）
                    if ';' in current_line and bracket_balance <= 0:
                        semicolon_found = True
                        break
                    
                    # 次の型定義か別の要素の開始を検出
                    if end_line > start_line and bracket_balance <= 0:
                        next_line = current_line.strip()
                        if (next_line.startswith('type ') or 
                            next_line.startswith('interface ') or 
                            next_line.startswith('class ') or 
                            next_line.startswith('function ')):
                            end_line -= 1  # 現在の行は含めない
                            break
                    
                    end_line += 1
                    
                    # ファイルの終端に達した場合
                    if end_line >= len(source_lines):
                        end_line = len(source_lines) - 1
                        break
                
                # 型定義のコードを取得
                code_lines = source_lines[start_line:end_line + 1]
                code = ''.join(code_lines)
                
                # 型定義の内容を抽出（複数行にまたがる可能性を考慮）
                type_def = ""
                if '=' in code:
                    type_def = code.split('=', 1)[1].strip()
                    if semicolon_found and type_def.endswith(';'):
                        type_def = type_def[:-1].strip()
                
                # 型情報を作成
                info = TypeElementInfo(
                    name=base_name,  # ジェネリックを除いた基本名を使用
                    code=code,
                    start_line=start_line,
                    source_lines=code_lines,
                    indent=indent,
                    type_definition=type_def,
                    is_export=is_export
                )
                
                types.append(TypeElement(info))
                
                # 次の検索位置を更新
                i = end_line + 1
                continue
            
            i += 1
        
        return types
    
    def _extract_enums(self, source_lines: List[str]) -> List[EnumElement]:
        """列挙型を抽出する
        
        Args:
            source_lines (List[str]): ソースコードの行のリスト
            
        Returns:
            List[EnumElement]: 抽出された列挙型要素のリスト
        """
        enums = []
        enum_pattern = r'^(\s*)(export\s+)?(const\s+)?enum\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        
        i = 0
        while i < len(source_lines):
            line = source_lines[i]
            match = re.search(enum_pattern, line)
            
            if match:
                indent, export, const, name = match.groups()
                indent = indent or ""
                is_export = export is not None
                is_const = const is not None
                start_line = i
                
                # 列挙型本体の終了位置を見つける
                end_line = self._find_balanced_block(source_lines, i)
                
                # 列挙型のコードを取得
                code_lines = source_lines[start_line:end_line + 1]
                code = ''.join(code_lines)
                
                # メンバーを抽出する処理（簡略化）
                members = []
                
                # 列挙型情報を作成
                info = EnumElementInfo(
                    name=name,
                    code=code,
                    start_line=start_line,
                    source_lines=code_lines,
                    indent=indent,
                    members=members,
                    is_export=is_export,
                    is_const=is_const
                )
                
                enums.append(EnumElement(info))
                
                # 次の検索位置を更新
                i = end_line + 1
                continue
            
            i += 1
        
        return enums
    
    def _find_balanced_block(self, source_lines: List[str], start_line: int, open_char='{', close_char='}') -> int:
        """括弧で囲まれたブロックの終了行を見つける
        
        Args:
            source_lines (List[str]): ソースコードの行のリスト
            start_line (int): 開始行インデックス
            open_char (str): 開始括弧文字
            close_char (str): 終了括弧文字
            
        Returns:
            int: ブロックの終了行インデックス
        """
        i = start_line
        balance = 0
        open_found = False
        
        # 最初の開き括弧を見つける
        while i < len(source_lines) and not open_found:
            if open_char in source_lines[i]:
                open_found = True
                balance = source_lines[i].count(open_char) - source_lines[i].count(close_char)
            i += 1
        
        if not open_found:
            return start_line
        
        # バランスが取れるまで探索
        while i < len(source_lines) and balance > 0:
            line = source_lines[i]
            balance += line.count(open_char) - line.count(close_char)
            
            if balance == 0:
                return i
            
            i += 1
        
        # バランスが取れなかった場合は開始行を返す
        return start_line
