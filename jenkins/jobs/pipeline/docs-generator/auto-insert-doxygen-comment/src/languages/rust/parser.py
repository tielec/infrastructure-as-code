# parser.py
"""
Rustコードを解析するためのパーサークラス
このモジュールは、Rustソースコードからコード要素を抽出するためのパーサーを提供します。
tree-sitterライブラリを使用して、Rustコードの正確な構文解析を行います。
"""
import os
import re
import traceback
from typing import Dict, List, Optional, Union, Any, Tuple, Set, cast
import tree_sitter
from tree_sitter import Language, Parser, Node
try:
    import tree_sitter_rust
except ImportError:
    raise ImportError("tree-sitter-rust not found. Please install it: pip install tree-sitter-rust")

from languages.rust.elements import (
    RustElementInfo, FunctionElementInfo, StructElementInfo, EnumElementInfo,
    TraitElementInfo, ModuleElementInfo, ImplBlockInfo,
    FunctionElement, StructElement, EnumElement, TraitElement, ModuleElement, RustElement
)
try:
    from common.base_generator import ElementParser
except ImportError:
    print("Warning: common.base_generator.ElementParser not found. Using basic class structure.")
    class ElementParser:
         def parse_file(self, file_path: str) -> List[Any]: raise NotImplementedError
try:
    from common.file_utils import read_file
except ImportError:
    print("Warning: common.file_utils not found. Using basic file reading.")
    def read_file(file_path: str) -> Tuple[str, List[str]]:
         try:
             with open(file_path, 'r', encoding='utf-8') as f:
                 content = f.read(); lines = content.splitlines(keepends=True); return content, lines
         except Exception as e: print(f"Error reading file {file_path}: {e}"); return "", []


class TreeSitterRustParser(ElementParser):
    """Tree-sitterを使用してRustコードを解析するパーサークラス"""

    def __init__(self):
        """パーサーを初期化"""
        try:
            RUST_LANGUAGE = Language(tree_sitter_rust.language())
            self.parser = Parser(RUST_LANGUAGE)
            print("Tree-sitter Rust パーサーが正常に初期化されました")
        except Exception as e:
            raise RuntimeError(f"tree-sitter Rust パーサーの初期化に失敗: {e}. tree-sitter と tree-sitter-rust のインストールを確認してください。")
        self.debug = True
        self.context = {}

    def _find_all_nodes(self, node: Node, node_type: Union[str, List[str]]) -> List[Node]:
        """指定されたタイプ(単一orリスト)のノードを再帰的にすべて見つける"""
        nodes = []
        types_to_find = [node_type] if isinstance(node_type, str) else node_type
        queue = [node]
        while queue:
            current_node = queue.pop(0)
            if current_node.type in types_to_find:
                nodes.append(current_node)
            queue.extend(current_node.children)
        return nodes

    def _get_node_text(self, node: Optional[Node], source_code: str) -> str:
        """ノードのテキストを取得"""
        if not node: return ""
        source_bytes = source_code.encode('utf-8')
        try:
            return source_bytes[node.start_byte:node.end_byte].decode('utf-8', errors='replace')
        except IndexError:
             # Tree-sitter can sometimes report invalid byte ranges, especially with errors
             # print(f"Warning: IndexError getting text for node {node.type} ({node.start_byte}-{node.end_byte})")
             return "" # Return empty string on error
        except Exception as e:
             print(f"Warning: Error getting text for node {node.type}: {e}")
             return ""

    def _get_node_name(self, node: Node, source_code: str) -> Optional[str]:
        """ノードの名前を取得 (主要な要素タイプに対応)"""
        name_node = node.child_by_field_name('name')
        if name_node:
            name = self._get_node_text(name_node, source_code).strip()
            if self._is_valid_identifier(name): return name

        type_node = node.child_by_field_name('type')
        if type_node and node.type in ('struct_item', 'enum_item', 'trait_item', 'impl_item'):
             type_text = self._get_node_text(type_node, source_code)
             name_match = re.match(r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)', type_text)
             if name_match:
                 name = name_match.group(1)
                 if self._is_valid_identifier(name): return name

        if node.type == 'mod_item':
             name_node = node.child_by_field_name('name')
             if name_node:
                  name = self._get_node_text(name_node, source_code).strip()
                  if self._is_valid_identifier(name): return name
             mod_text = self._get_node_text(node, source_code)
             match = re.search(r'mod\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:;|{)', mod_text)
             if match:
                  name = match.group(1)
                  if self._is_valid_identifier(name): return name

        if node.type in ('function_item', 'function_signature_item'):
             name_node = node.child_by_field_name('name')
             if name_node:
                  name = self._get_node_text(name_node, source_code).strip()
                  if self._is_valid_identifier(name): return name

        return None

    def _is_valid_identifier(self, name: Optional[str]) -> bool:
        """有効なRust識別子かチェック"""
        if not name or not isinstance(name, str): return False
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name): return False
        reserved = {'as','break','const','continue','crate','else','enum','extern','false','fn','for','if','impl','in','let','loop','match','mod','move','mut','pub','ref','return','self','static','struct','super','trait','true','type','unsafe','use','where','while','async','await','dyn', 'abstract', 'become', 'box', 'do', 'final', 'macro', 'override', 'priv', 'typeof', 'unsized', 'virtual', 'yield'}
        return name not in reserved and name != 'Self'

    def _extract_visibility(self, node: Node, source_code: str) -> bool:
        """可視性(pub)を取得"""
        vis_mod = next((child for child in node.children if child.type == 'visibility_modifier'), None)
        return vis_mod is not None

    def _extract_type_params(self, node: Node, source_code: str) -> List[str]:
        """型パラメータ(<T: Trait, U>)を抽出"""
        params_node = node.child_by_field_name('type_parameters')
        if params_node:
            params_text = self._get_node_text(params_node, source_code)
            match = re.search(r'<\s*(.*?)\s*>', params_text, re.DOTALL)
            if match:
                content = match.group(1)
                params = []; balance = 0; current_param = ""
                for char in content:
                    if char == '<': balance += 1
                    elif char == '>': balance -= 1
                    elif char == ',' and balance == 0:
                        params.append(current_param.strip()); current_param = ""
                        continue
                    current_param += char
                if current_param.strip(): params.append(current_param.strip())
                return params
        return []

    def _extract_function_parameters(self, node: Node, source_code: str) -> Tuple[List[Dict[str, str]], str]:
        """関数パラメータを抽出"""
        params = []; args_text = ""
        params_node = node.child_by_field_name('parameters')
        if params_node:
            args_text = self._get_node_text(params_node, source_code)
            for child in params_node.named_children:
                name, type_ = "?", "?"
                if child.type == 'parameter':
                    pattern_node = child.child_by_field_name('pattern')
                    type_node = child.child_by_field_name('type')
                    if pattern_node: name = self._get_node_text(pattern_node, source_code)
                    if type_node: type_ = self._get_node_text(type_node, source_code)
                    # Clean up common patterns like 'mut name'
                    name_clean = re.sub(r'^\s*(?:mut\s+|&\s*|\s*)+', '', name).split(':')[0].strip()
                    params.append({'name': name_clean, 'type': type_.strip()})
                elif child.type == 'self_parameter':
                    name = self._get_node_text(child, source_code)
                    params.append({'name': name.strip(), 'type': 'Self'})
                elif child.type == 'variadic_parameter':
                    params.append({'name': '...', 'type': 'variadic'})
        cleaned_args_text = args_text.strip().lstrip('(').rstrip(')')
        return params, cleaned_args_text

    def _extract_return_type(self, node: Node, source_code: str) -> Optional[str]:
        """返り値の型を抽出"""
        ret_node = node.child_by_field_name('return_type')
        return self._get_node_text(ret_node, source_code).strip() if ret_node else None

    def _extract_indent(self, line_0_based: int, source_lines: List[str]) -> str:
        """指定行(0-based)のインデント"""
        if 0 <= line_0_based < len(source_lines):
            line = source_lines[line_0_based]
            match = re.match(r"^(\s*)", line)
            if match: return match.group(1)
        return ""

    def _populate_base_info(self, info: RustElementInfo, node: Node, source_code: str, source_lines: List[str]):
        """RustElementInfo の共通フィールド設定"""
        info.code = self._get_node_text(node, source_code)
        info.start_line = node.start_point[0] + 1
        info.end_line = node.end_point[0] + 1
        info.start_col = node.start_point[1]
        info.end_col = node.end_point[1]
        info.source_code = info.code
        info.source_lines = source_lines # Assign the full list of lines
        info.indent = self._extract_indent(node.start_point[0], source_lines)
        info.file_path = self.context.get('file_path')


    def parse_file(self, file_path: str) -> List[RustElement]:
        """Rustファイルを解析し、コード要素を抽出"""
        try:
            source_code, source_lines = read_file(file_path)
            if not source_lines and source_code: source_lines = source_code.splitlines(keepends=True)
            elif not source_lines and not source_code: print(f"Warning: File {file_path} is empty."); source_lines = []
        except Exception as e: print(f"Error reading file {file_path}: {e}"); traceback.print_exc(); return []

        self.context = {
            'file_path': file_path, 'source_code': source_code, 'source_lines': source_lines,
            'file_name': os.path.basename(file_path), 'impl_blocks': [], 'type_names': set(), 'method_names': {}
        }

        try:
            tree = self.parser.parse(bytes(source_code, 'utf8')); root_node = tree.root_node
        except Exception as e: print(f"Error parsing {file_path}: {e}"); traceback.print_exc(); return []
        if root_node.has_error: print(f"Warning: Syntax errors found in {file_path}.")

        elements: List[RustElement] = []
        # Pass source_lines consistently
        module_element = self._create_module_element(root_node, source_code, source_lines)
        if module_element: elements.append(module_element)
        self.context['impl_blocks'] = self._extract_impl_blocks(root_node, source_code, source_lines)
        elements.extend(self._extract_structs(root_node, source_code, source_lines))
        elements.extend(self._extract_enums(root_node, source_code, source_lines))
        elements.extend(self._extract_traits(root_node, source_code, source_lines))
        elements.extend(self._extract_inline_modules(root_node, source_code, source_lines))
        elements.extend(self._extract_functions(root_node, source_code, source_lines))
        for block in self.context['impl_blocks']:
            elements.extend(self._extract_impl_methods(block, source_code, source_lines))

        # Deduplication
        unique_elements_map: Dict[str, RustElement] = {}
        for el in elements:
            if el and el.info:
                el_id = el.get_unique_id()
                if el_id not in unique_elements_map: unique_elements_map[el_id] = el
                else:
                     if self.debug:
                         existing_el = unique_elements_map[el_id]
                         print(f"Debug: Duplicate element ID detected: {el_id}\n"
                               f"  Existing: {existing_el.__class__.__name__} '{existing_el.info.name}' L{existing_el.info.start_line}\n"
                               f"  New:      {el.__class__.__name__} '{el.info.name}' L{el.info.start_line}")
        unique_elements_list = list(unique_elements_map.values())
        if self.debug: print(f"Finished parsing {file_path}. Found {len(unique_elements_list)} unique elements.")
        return unique_elements_list

    # --- Extraction Helper Methods ---
    def _create_module_element(self, root_node: Node, source_code: str, source_lines: List[str]) -> Optional[ModuleElement]:
        f_path = self.context.get('file_path', '')
        name = os.path.splitext(os.path.basename(f_path))[0] if f_path else "unknown_module"
        info = ModuleElementInfo(name=name)
        info.code = source_code; info.start_line = 1; info.end_line = len(source_lines) if source_lines else 1
        info.start_col = 0; info.end_col = 0; info.source_code = source_code; info.source_lines = source_lines
        info.indent = ""; info.file_path = f_path; info.is_inline = False
        info.imports = [self._get_node_text(n, source_code) for n in root_node.children if n.type == 'use_declaration']
        return ModuleElement(info)

    def _extract_struct_fields(self, node: Node, source_code: str) -> List[Dict[str, Any]]:
        fields = []; body = node.child_by_field_name('body')
        if body and body.type == 'field_declaration_list':
            for field_node in body.named_children:
                if field_node.type == 'field_declaration':
                    f_name_node = field_node.child_by_field_name('name')
                    f_type_node = field_node.child_by_field_name('type')
                    if f_name_node and f_type_node:
                         fields.append({'name': self._get_node_text(f_name_node, source_code).strip(),
                                        'type': self._get_node_text(f_type_node, source_code).strip(),
                                        'is_pub': self._extract_visibility(field_node, source_code)})
        elif body and body.type == 'ordered_field_declaration_list':
             valid_types = ('type_identifier', 'generic_type', 'reference_type', 'pointer_type', 'tuple_type', 'array_type', 'never_type', 'abstract_type', 'primitive_type', 'scoped_type_identifier', 'function_type')
             for i, field_type_node in enumerate(body.named_children):
                 if field_type_node.type in valid_types:
                     fields.append({'name': str(i), 'type': self._get_node_text(field_type_node, source_code).strip(), 'is_pub': self._extract_visibility(field_type_node, source_code)})
        return fields

    def _extract_structs(self, root_node: Node, source_code: str, source_lines: List[str]) -> List[StructElement]:
        structs = []; nodes = self._find_all_nodes(root_node, 'struct_item')
        for node in nodes:
            name = self._get_node_name(node, source_code)
            if not name: continue
            info = StructElementInfo(name=name)
            self._populate_base_info(info, node, source_code, source_lines)
            info.is_pub = self._extract_visibility(node, source_code)
            info.type_params = self._extract_type_params(node, source_code)
            info.fields = self._extract_struct_fields(node, source_code)
            structs.append(StructElement(info))
        return structs

    def _extract_enum_variants(self, node: Node, source_code: str) -> List[Dict[str, Any]]:
        variants = []; body = node.child_by_field_name('body')
        if body and body.type == 'enum_variant_list':
            for variant_node in body.named_children:
                 if variant_node.type == 'enum_variant':
                      v_name_node = variant_node.child_by_field_name('name')
                      if v_name_node:
                           v_name = self._get_node_text(v_name_node, source_code).strip()
                           v_data_node = next((child for child in variant_node.children if child.type in ('ordered_field_declaration_list', 'field_declaration_list')), None)
                           v_type = self._get_node_text(v_data_node, source_code).strip() if v_data_node else None
                           variants.append({'name': v_name, 'type': v_type})
        return variants

    def _extract_enums(self, root_node: Node, source_code: str, source_lines: List[str]) -> List[EnumElement]:
        enums = []; nodes = self._find_all_nodes(root_node, 'enum_item')
        for node in nodes:
            name = self._get_node_name(node, source_code)
            if not name: continue
            info = EnumElementInfo(name=name)
            self._populate_base_info(info, node, source_code, source_lines)
            info.is_pub = self._extract_visibility(node, source_code)
            info.type_params = self._extract_type_params(node, source_code)
            info.variants = self._extract_enum_variants(node, source_code)
            enums.append(EnumElement(info))
        return enums

    def _extract_trait_items(self, node: Node, source_code: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        methods = []; associated_types = []; body = node.child_by_field_name('body')
        if body and body.type == 'declaration_list':
            for item_node in body.named_children:
                if item_node.type == 'function_signature_item':
                     method_name = self._get_node_name(item_node, source_code)
                     if method_name:
                          info_temp = FunctionElementInfo(name=method_name)
                          self._extract_function_details(info_temp, item_node, source_code)
                          signature = self._build_signature(info_temp)
                          methods.append({'name': method_name, 'parameters': info_temp.parameters, 'return_type': info_temp.return_type, 'signature': signature})
                elif item_node.type == 'associated_type':
                     type_name_node = item_node.child_by_field_name('name')
                     if type_name_node: associated_types.append(self._get_node_text(type_name_node, source_code).strip())
        return methods, associated_types

    def _extract_trait_bounds(self, node: Node, source_code: str) -> List[str]:
         bounds = []; super_traits_node = node.child_by_field_name('super_traits')
         if super_traits_node and super_traits_node.type == 'trait_bounds':
              for bound_node in super_traits_node.named_children:
                   if bound_node.type in ('type_identifier', 'generic_type', 'scoped_type_identifier'):
                        bounds.append(self._get_node_text(bound_node, source_code).strip())
         return bounds

    def _extract_traits(self, root_node: Node, source_code: str, source_lines: List[str]) -> List[TraitElement]:
        traits = []; nodes = self._find_all_nodes(root_node, 'trait_item')
        for node in nodes:
            name = self._get_node_name(node, source_code)
            if not name: continue
            info = TraitElementInfo(name=name)
            self._populate_base_info(info, node, source_code, source_lines)
            info.is_pub = self._extract_visibility(node, source_code)
            info.super_traits = self._extract_trait_bounds(node, source_code)
            info.methods, info.associated_types = self._extract_trait_items(node, source_code)
            traits.append(TraitElement(info))
        return traits

    def _extract_inline_modules(self, root_node: Node, source_code: str, source_lines: List[str]) -> List[ModuleElement]:
        modules = []; nodes = self._find_all_nodes(root_node, 'mod_item')
        for node in nodes:
            body = node.child_by_field_name('body')
            if body:
                name = self._get_node_name(node, source_code)
                if not name: continue
                info = ModuleElementInfo(name=name)
                self._populate_base_info(info, node, source_code, source_lines)
                info.is_inline = True
                modules.append(ModuleElement(info))
        return modules

    def _extract_impl_blocks(self, root_node: Node, source_code: str, source_lines: List[str]) -> List[ImplBlockInfo]:
        infos = []; nodes = self._find_all_nodes(root_node, 'impl_item')
        for node in nodes:
             target_node = node.child_by_field_name('type'); trait_node = node.child_by_field_name('trait')
             if not target_node: continue
             methods = []; body = node.child_by_field_name('body')
             if body and body.type == 'declaration_list':
                 methods = [{'name': name, 'node': item}
                              for item in body.named_children
                              if item.type == 'function_item' and (name := self._get_node_name(item, source_code)) and self._is_valid_identifier(name)]
             infos.append(ImplBlockInfo(
                 target_type=self._get_node_text(target_node, source_code).strip(),
                 trait_name=self._get_node_text(trait_node, source_code).strip() if trait_node else None,
                 start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                 start_col=node.start_point[1], end_col=node.end_point[1], methods=methods,
                 type_params=self._extract_type_params(node, source_code),
                 source_code=self._get_node_text(node, source_code)))
        return infos

    def _extract_function_details(self, info: FunctionElementInfo, node: Node, source_code: str):
         params_node = node.child_by_field_name('parameters')
         if params_node is None: info.parameters = []; info.args_str = ""
         else:
             try: before_params_bytes = source_code.encode('utf-8')[node.start_byte:params_node.start_byte]; before_params = before_params_bytes.decode('utf-8', errors='ignore')
             except IndexError: before_params = ""
             info.is_pub = self._extract_visibility(node, source_code)
             info.is_async = 'async ' in before_params; info.is_const = 'const ' in before_params; info.is_unsafe = 'unsafe ' in before_params
             info.parameters, args_paren_cleaned = self._extract_function_parameters(node, source_code)
             info.args_str = args_paren_cleaned
             info.return_type = self._extract_return_type(node, source_code)

    def _build_signature(self, info: FunctionElementInfo) -> str:
        sig_parts = []
        if info.is_pub: sig_parts.append("pub")
        if info.is_async: sig_parts.append("async")
        if info.is_const: sig_parts.append("const")
        if info.is_unsafe: sig_parts.append("unsafe")
        sig_parts.append(f"fn {info.name}")
        # TODO: Add generic params extraction and inclusion if needed
        sig_parts.append(f"({info.args_str})")
        if info.return_type: sig_parts.append(f"-> {info.return_type}")
        # TODO: Add where clause extraction and inclusion if needed
        return " ".join(sig_parts)

    def _extract_impl_methods(self, impl_block: ImplBlockInfo, source_code: str, source_lines: List[str]) -> List[FunctionElement]:
        elements = []; parent_display_name = re.sub(r'<.*?>.*$', '', impl_block.target_type).strip()
        for m_detail in impl_block.methods:
            node, name = m_detail['node'], m_detail['name']
            info = FunctionElementInfo(name=name)
            self._populate_base_info(info, node, source_code, source_lines)
            self._extract_function_details(info, node, source_code)
            info.parent_type = impl_block.target_type
            info.is_impl_method = True
            info.is_trait_method = impl_block.trait_name is not None
            if info.is_trait_method: info.metadata['trait_name'] = impl_block.trait_name
            info.signature = self._build_signature(info)
            info.fully_qualified_name = f"{parent_display_name}::{name}"
            elements.append(FunctionElement(info))
        return elements

    def _extract_functions(self, root_node: Node, source_code: str, source_lines: List[str]) -> List[FunctionElement]:
        funcs = []; top_level_func_nodes = [child for child in root_node.children if child.type == 'function_item']
        for node in top_level_func_nodes:
            name = self._get_node_name(node, source_code)
            if not name: continue
            info = FunctionElementInfo(name=name)
            self._populate_base_info(info, node, source_code, source_lines)
            self._extract_function_details(info, node, source_code)
            info.parent_type = None; info.is_impl_method = False; info.is_trait_method = False
            info.signature = self._build_signature(info)
            info.fully_qualified_name = name
            funcs.append(FunctionElement(info))
        return funcs
