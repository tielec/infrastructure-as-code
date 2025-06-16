# generator.py
"""
Rust固有のドキュメント生成処理

このモジュールは、Rustソースコードに対して適切なドキュメントコメントを生成し、
ソースファイルに挿入する機能を提供します。各コード要素（関数、構造体など）に対して
OpenAI APIを使用して適切なDoxygen形式のドキュメントを生成します。
"""
import os
import re
import json
import traceback
from typing import Dict, List, Optional, Union, Any, Set, Tuple, cast # Tuple を追加

# 必要なモジュールをインポート
try:
    from common.base_generator import BaseDocGenerator, BaseElement, InsertionPoint
except ImportError:
    print("Warning: common.base_generator not found. Using dummy base classes.")
    @dataclass
    class InsertionPoint:
        def_line: int = 0; body_start: int = 0; existing_doc_start: int = -1
        existing_doc_end: int = -1; base_indent: str = ""
    class BaseElement:
         def __init__(self, info): self.info = info
         def get_unique_id(self): return "dummy_id"
         def analyze_insertion_point(self, lines): return InsertionPoint()
    class BaseDocGenerator:
         def __init__(self): pass

try:
    from common.openai_client import OpenAIClient
except ImportError:
     raise ImportError("common.openai_client not found. Please ensure it exists and is importable.")

try:
    from common.file_utils import read_file, write_file
except ImportError:
    print("Warning: common.file_utils not found. Using basic file I/O.")
    def read_file(file_path: str) -> Tuple[str, List[str]]:
         try:
             with open(file_path, 'r', encoding='utf-8') as f:
                 content = f.read(); lines = content.splitlines(keepends=True); return content, lines
         except Exception: return "", []
    def write_file(file_path: str, lines: List[str]):
         try:
             with open(file_path, 'w', encoding='utf-8') as f: f.writelines(lines)
         except Exception as e: print(f"Error writing file {file_path}: {e}")


from languages.rust.elements import (
    FunctionElement, StructElement, EnumElement, TraitElement, ModuleElement,
    FunctionElementInfo, StructElementInfo, EnumElementInfo, TraitElementInfo,
    ModuleElementInfo, RustElement # RustElement をインポート
)
from languages.rust.parser import TreeSitterRustParser


class RustDocGenerator(BaseDocGenerator):
    """Rustコードのドキュメント生成を管理するクラス"""

    def __init__(self, openai_endpoint: str, openai_key: str, deployment_name: str):
        """RustDocGeneratorクラスの初期化関数
        
        OpenAI APIの接続情報を設定し、必要なコンポーネント（パーサーなど）を初期化します。
        
        Args:
            openai_endpoint: OpenAI APIのエンドポイントURL
            openai_key: OpenAI APIの認証キー
            deployment_name: 使用するモデルのデプロイメント名
        """
        super().__init__()
        self.openai_client = OpenAIClient(openai_endpoint, openai_key, deployment_name)
        self.parser = TreeSitterRustParser()
        self.system_prompt = (
            "You are an expert Rust documentation generator specializing in Doxygen format."
            "Analyze the provided Rust code snippet and generate a concise and informative Doxygen comment block (/** ... */)."
            "Focus on explaining the purpose, parameters, return values, and any important behaviors or side effects."
            "For functions/methods:"
            " - Start with a @brief tag summarizing the main purpose."
            " - Use @param[in|out|in,out] name Description for each parameter (guess direction if unsure, or omit)."
            " - Use @return Description for the return value."
            " - Add @details for more elaborate explanations if needed."
            " - Use @note, @warning, @sa (see also), @exception/@throws where appropriate."
            "For structs/enums/traits:"
            " - Start with a @brief tag."
            " - Use @var Type name Description for fields/variants."
            " - Use @details for overall purpose."
            "Formatting Rules:"
            " - Start the block with /** on its own line."
            " - End the block with */ on its own line."
            " - Prepend each line in between with ' * ' (space, star, space)."
            " - Ensure there's a @brief tag, preferably near the beginning."
            " - Do NOT include ```rust ... ``` code blocks in the final documentation output."
            " - Keep descriptions clear, concise, and accurate based *only* on the provided code and context comments."
        )
        self.processed_element_ids = set()
        self.debug = True
        self.current_context = {}

    def process_file(self, file_path: str, templates: Dict[str, str], overwrite_doc: bool = False) -> None:
        """Rustソースファイルを処理し、ドキュメントコメントを生成・挿入する
        
        指定されたRustソースファイルを解析し、コード要素（関数、構造体など）を抽出します。
        各要素に対してOpenAI APIを使用してドキュメントコメントを生成し、ファイルに挿入します。
        
        処理の流れ:
        1. ファイルを読み込む
        2. パーサーでコード要素を抽出する
        3. 要素ごとにドキュメントを生成して挿入情報を収集する
        4. 収集した情報を使ってファイルを更新する
        
        Args:
            file_path: 処理するRustソースファイルのパス
            templates: 要素タイプごとのドキュメントテンプレート
            overwrite_doc: True の場合、既存のドキュメントを上書きする
        """
        print(f"Processing file: {file_path}")
        self.processed_element_ids.clear()

        # 1. ファイルを最初に一度だけ読み込む
        try:
            source_code, initial_lines = read_file(file_path)
            if not initial_lines and source_code: initial_lines = source_code.splitlines(keepends=True)
            elif not initial_lines and not source_code: print(f"Warning: File {file_path} is empty."); initial_lines = []
        except Exception as read_err:
            print(f"Error reading file {file_path}: {read_err}. Aborting."); traceback.print_exc(); return

        # 2. パースして要素を取得
        try:
            elements: List[RustElement] = self.parser.parse_file(file_path)
        except Exception as e: print(f"Error parsing file {file_path}: {e}"); traceback.print_exc(); return

        # コンテキスト設定
        self.current_context = {'file_path': file_path, 'all_type_names': set(), 'all_methods': {}}
        valid_elements = []
        for element in elements:
            if element.info is None: continue
            valid_elements.append(element)
            if isinstance(element.info, (StructElementInfo, EnumElementInfo, TraitElementInfo)):
                 if element.info.name: self.current_context['all_type_names'].add(element.info.name)
            if isinstance(element.info, FunctionElementInfo) and element.info.is_impl_method:
                 m_name, p_type = element.info.name, element.info.parent_type
                 if m_name and p_type:
                    if m_name not in self.current_context['all_methods']: self.current_context['all_methods'][m_name] = []
                    parent_base = re.sub(r'<.*?>.*$', '', p_type).strip()
                    self.current_context['all_methods'][m_name].append({'parent_type': parent_base, 'element_id': element.get_unique_id()})
        elements = valid_elements
        print(f"Found {len(elements)} valid elements with info.")

        # 要素の処理順序をソート
        element_order = {ModuleElement: 0, StructElement: 1, EnumElement: 1, TraitElement: 1, FunctionElement: 2}
        elements.sort(key=lambda e: (
             0 if isinstance(e, ModuleElement) and e.info and not e.info.is_inline else 1,
             element_order.get(type(e), 99),
             e.info.start_line if e.info else 0))

        # 3. ドキュメント生成と挿入情報の収集
        insertions: List[Tuple[InsertionPoint, str, str]] = []
        last_exception = None
        processed_count = 0; skipped_existing = 0; skipped_template = 0
        skipped_generate = 0; skipped_analyze = 0
        processed_ids_in_loop = set()

        for element in elements:
            if not element.info: continue
            element_id = element.get_unique_id()
            display_name = self._get_display_name(element)
            if element_id in processed_ids_in_loop:
                if self.debug: print(f"Debug: Skipping duplicate ID in this run: {element_id} ({display_name})")
                continue
            processed_ids_in_loop.add(element_id)

            element_type = element.__class__.__name__.lower().replace('element', '')
            template_key = 'function' if isinstance(element, FunctionElement) else element_type
            template = templates.get(template_key)
            if not template:
                if self.debug: print(f"Skipping {display_name}: No template for '{template_key}'.")
                skipped_template += 1; continue

            try:
                # 挿入位置解析 (initial_lines を使用)
                try:
                    insertion_point: InsertionPoint = element.analyze_insertion_point(initial_lines)
                except ValueError as analyze_err:
                    print(f"Error analyzing insertion point for {display_name} (ID: {element_id}): {analyze_err}. Skipping.")
                    skipped_analyze += 1; continue
                except Exception as analyze_err:
                    print(f"Unexpected error analyzing point for {display_name} (ID: {element_id}): {analyze_err}. Skipping.")
                    skipped_analyze += 1; traceback.print_exc(); continue

                # 既存ドキュメントチェック
                has_existing = insertion_point.existing_doc_start >= 0 and insertion_point.existing_doc_end >= 0
                if has_existing and not overwrite_doc:
                    if self.debug: print(f"Skipping {display_name}: Existing doc found (L{insertion_point.existing_doc_start+1}-L{insertion_point.existing_doc_end+1}) and overwrite=False.")
                    skipped_existing += 1; continue

                print(f"Processing: {display_name} (ID: {element_id}) defined at L{insertion_point.def_line + 1}")

                # コンテキスト作成
                context_info = {}
                if isinstance(element, FunctionElement): context_info = self._create_function_context(element)
                # プロンプト準備
                code_prompt = self._prepare_code_with_context(element, context_info)
                # ドキュメント生成
                print(f"  Generating doc for: {display_name}...")
                docstring = self.openai_client.generate_doc(code_prompt, template, self.system_prompt)
                if not docstring or "Error generating" in docstring or "Failed to generate" in docstring:
                    print(f"  Failed to generate doc for {display_name}. Skipping."); skipped_generate += 1; continue
                # ドキュメント整形
                formatted_doc = self._format_doc(docstring)
                if not formatted_doc or not formatted_doc.strip() or len(formatted_doc.splitlines()) <= 2:
                    print(f"  Generated doc empty/minimal for {display_name}. Skipping."); skipped_generate += 1; continue
                if self.debug: print(f"\n  Generated Doc:\n{'-'*30}\n{formatted_doc}\n{'-'*30}")
                # 挿入情報をリストに追加
                insertions.append((insertion_point, formatted_doc, display_name))
                processed_count += 1
            except Exception as loop_err:
                print(f"Unexpected error processing {display_name} (ID: {element_id}): {loop_err}")
                last_exception = loop_err; traceback.print_exc()

        # 4. ドキュメント挿入 (逆順処理)
        file_modified = False
        if insertions:
            print("-" * 80); print(f"Collected {len(insertions)} doc blocks. Applying changes...")
            insertions.sort(key=lambda item: item[0].def_line, reverse=True)
            modified_lines = list(initial_lines); insert_errors = 0
            for insertion_point, doc_to_insert, element_name in insertions:
                try:
                    self._insert_doc(modified_lines, insertion_point, doc_to_insert)
                    if self.debug: print(f"  Applied insertion for '{element_name}' (orig L{insertion_point.def_line + 1})")
                except IndexError as idx_err:
                     print(f"  Error inserting doc for '{element_name}': Index issue (orig L{insertion_point.def_line + 1}). Err: {idx_err}. Skipping.")
                     last_exception = idx_err; insert_errors += 1
                except Exception as insert_err:
                    print(f"  Error inserting doc for '{element_name}' (orig L{insertion_point.def_line + 1}): {insert_err}. Skipping.")
                    last_exception = insert_err; insert_errors += 1
            # 5. ファイル書き込み
            if insert_errors == 0:
                 final_content = "".join(modified_lines); initial_content = "".join(initial_lines)
                 if final_content != initial_content:
                     print(f"Changes detected. Writing updated content to {file_path}...")
                     try: write_file(file_path, modified_lines); print(f"Successfully updated file."); file_modified = True
                     except Exception as write_err: print(f"Error writing file: {write_err}"); last_exception = write_err
                 else: print("No effective changes detected. File not modified.")
            else: print(f"Skipped writing file due to {insert_errors} insertion error(s).")
        else: print("No documentation blocks were generated or needed insertion.")

        # サマリー表示
        total_elements_considered = len(elements); total_skipped = skipped_existing + skipped_template + skipped_generate + skipped_analyze
        other_skips = total_elements_considered - processed_count - total_skipped
        print("-" * 80); print(f"Completed processing {file_path}.")
        print(f"  Total elements parsed: {total_elements_considered}")
        print(f"  Docs generated & prepared for insertion: {processed_count}")
        print(f"  Skipped (Existing Doc, Overwrite=False): {skipped_existing}")
        print(f"  Skipped (No Template Found): {skipped_template}")
        print(f"  Skipped (Doc Generation Failed/Empty): {skipped_generate}")
        print(f"  Skipped (Insertion Point Analysis Error): {skipped_analyze}")
        if other_skips > 0: print(f"  Skipped (Other reasons e.g., duplicate ID): {max(0, other_skips)}")
        print(f"File modified: {file_modified}")
        if last_exception: print(f"An error occurred: {last_exception}")
        print("-" * 80)

    # _process_element は空実装
    def _process_element(self, element: BaseElement, file_path: str, template: str, overwrite_doc: bool = False) -> None: pass

    def _format_doc(self, raw_doc: str) -> str:
        """OpenAI APIから生成された生のドキュメントをDoxygen形式に整形する
        
        生成されたドキュメントテキストを解析し、適切なDoxygen形式（/** ... */)に変換します。
        マークダウンのコードブロックを削除し、日本語の句読点を英語形式に変換するなどの
        整形処理も行います。
        
        処理内容:
        - マークダウンコードブロックの削除
        - 日本語の句読点を英語形式に変換
        - Doxygen形式の開始・終了記号の適用
        - 各行に適切なインデントと「* 」接頭辞の追加
        - @briefタグの追加（ない場合）
        
        Args:
            raw_doc: OpenAI APIから返された生のドキュメント文字列
            
        Returns:
            Doxygen形式に整形されたドキュメント文字列
        """
        content = re.sub(r'```.*?```', '', raw_doc, flags=re.DOTALL).replace('```', '').strip()
        replacements = {'、': ',', '。': '.', '：': ':', '（': '(', '）': ')', '　': ' '}
        for old, new in replacements.items(): content = content.replace(old, new)
        lines = content.splitlines(); formatted = []; has_brief = False
        is_already = lines and lines[0].strip().startswith('/**') and lines[-1].strip().endswith('*/')

        if is_already:
             formatted.append(lines[0].rstrip())
             for i in range(1, len(lines) - 1):
                 line = lines[i]; stripped_line = line.lstrip(); indent = line[:-len(stripped_line)] if stripped_line else line
                 content_part = stripped_line
                 if content_part.startswith('* '): content_part = content_part[2:]
                 elif content_part.startswith('*'): content_part = content_part[1:]
                 formatted.append(indent.rstrip() + ' * ' + content_part.rstrip())
                 if '@brief' in line: has_brief = True
             if len(lines) > 1: formatted.append(lines[-1].rstrip())
        else:
             formatted.append('/**'); first_content_line_added = False
             for i, line in enumerate(lines):
                 s_line = line.strip()
                 if not s_line:
                     if formatted and formatted[-1] != ' *': formatted.append(' *'); continue
                 if not has_brief and not s_line.startswith('@') and not first_content_line_added:
                     formatted.append(' * @brief ' + s_line); has_brief = True; first_content_line_added = True
                 else:
                     formatted.append(' * ' + s_line)
                     if s_line.startswith('@brief'): has_brief = True
                     if not s_line.startswith('@'): first_content_line_added = True
             if not has_brief and len(formatted) > 1: formatted.insert(1, ' * @brief Add brief description here.')
             while len(formatted) > 1 and formatted[-1] == ' *': formatted.pop()
             formatted.append(' */')
        return '\n'.join(formatted)


    def _insert_doc(self, lines: List[str], insertion: InsertionPoint, doc: str) -> None:
        """生成されたドキュメントをソースコードの適切な位置に挿入する
        
        指定された挿入位置情報に基づいて、ドキュメントコメントをソースコードに挿入します。
        既存のドキュメントがある場合は削除してから新しいドキュメントを挿入します。
        
        Args:
            lines: ソースコードの行リスト（挿入によって変更される）
            insertion: 挿入位置の情報（行番号、既存ドキュメントの範囲など）
            doc: 挿入するドキュメント文字列
        """
        actual_insertion_line = insertion.def_line
        has_existing = insertion.existing_doc_start >= 0 and insertion.existing_doc_end >= 0
        if has_existing:
            start, end = insertion.existing_doc_start, insertion.existing_doc_end
            if 0 <= start <= end < len(lines):
                 if self.debug: print(f"    Deleting existing doc: L{start + 1}-L{end + 1}")
                 del lines[start : end + 1]; actual_insertion_line = start
            else:
                 print(f"Warning: Invalid existing doc range ({start}-{end}) at L{insertion.def_line}. List len {len(lines)}.")
                 actual_insertion_line = max(0, min(insertion.def_line, len(lines)))
        actual_insertion_line = max(0, min(actual_insertion_line, len(lines)))
        doc_lines = [(insertion.base_indent + line).rstrip() + '\n' for line in doc.splitlines()]
        if not doc_lines: print("Warning: Skipping insertion of empty doc."); return
        lines[actual_insertion_line:actual_insertion_line] = doc_lines


    def _get_display_name(self, element: BaseElement) -> str:
        """要素の表示用の名前を生成する
        
        コード要素の種類と名前を組み合わせて、ログ表示などに適した文字列を生成します。
        要素の種類（関数、構造体など）によって異なる形式で名前を生成します。
        
        特殊なケース:
        - インプリメントメソッドの場合は「Type::method_name」形式
        - トレイト実装の場合は「Type (impl Trait)::method_name」形式
        - ファイルモジュールの場合はファイル名を使用
        
        Args:
            element: 名前を生成するコード要素
            
        Returns:
            表示用に整形された要素名
        """
        if element.info is None: return f"{element.__class__.__name__.replace('Element', '')} <Name Unknown>"
        e_type = element.__class__.__name__.replace('Element', ''); name = element.info.name or "<Anonymous>"
        if isinstance(element.info, FunctionElementInfo):
            info = cast(FunctionElementInfo, element.info)
            if info.is_impl_method and info.parent_type:
                 parent_base = re.sub(r'<.*?>.*$', '', info.parent_type).strip(); trait_str = ""
                 if info.metadata and info.metadata.get('trait_name'):
                      trait_maybe = info.metadata.get('trait_name')
                      if isinstance(trait_maybe, str): trait_base = re.sub(r'<.*?>.*$', '', trait_maybe).strip(); trait_str = f" (impl {trait_base})"
                 return f"{e_type} {parent_base}{trait_str}::{name}"
            else: return f"{e_type} {name}"
        elif isinstance(element.info, ModuleElementInfo):
            info = cast(ModuleElementInfo, element.info)
            if not info.is_inline: file_name = os.path.splitext(os.path.basename(info.file_path or ""))[0]; return f"File Module {file_name or name}"
            else: return f"Inline Module {name}"
        else: return f"{e_type} {name}"


    def _create_function_context(self, element: FunctionElement) -> Dict[str, Any]:
        """関数要素のコンテキスト情報を収集・分析する
        
        関数の特性を分析し、ドキュメント生成に役立つコンテキスト情報を収集します。
        関数名、パラメータ、戻り値の型などからパターンを認識し、その関数の意図や動作を
        推測するための情報を構造化します。
        
        分析する情報:
        - 関数名のパターン（new、get_、set_、is_など）から関数の役割を推測
        - パラメータの種類と名前から操作対象や操作内容を推測
        - 戻り値の型（Result、Option、Selfなど）から関数の動作特性を推測
        - 他の関数との関連性（同名メソッドの存在など）
        
        Args:
            element: 分析対象の関数要素
            
        Returns:
            関数のコンテキスト情報を含む辞書
        """
        if not isinstance(element.info, FunctionElementInfo): 
            return {}
        
        context: Dict[str, Any] = {}
        info = cast(FunctionElementInfo, element.info)
        
        # メソッド関連の情報を抽出
        if info.is_impl_method and info.parent_type:
            parent_base = re.sub(r'<.*?>.*$', '', info.parent_type).strip()
            context['parent_type'] = parent_base
            
            # メソッド名によるパターン認識（一般的なRustのメソッド命名規則を考慮）
            m_name = info.name if info.name else ""
            
            # 同名メソッドが複数の型に実装されているかの識別
            same_name_methods = self.current_context.get('all_methods', {}).get(m_name, [])
            if len(same_name_methods) > 1:
                other_parents = list(set(m['parent_type'] for m in same_name_methods 
                                    if m.get('parent_type') != parent_base))
                if other_parents: 
                    context['common_method_name_in_types'] = other_parents
                    context['is_common_method_name'] = True
            
            # メソッド名パターン認識（一般的な命名規則に基づく）
            # コンストラクタパターン
            if m_name == 'new' or m_name.startswith('new_') or m_name.endswith('_new'):
                context.update({
                    'is_constructor': True, 
                    'constructs_type': parent_base,
                    'constructor_variant': m_name[4:] if m_name.startswith('new_') else 
                                        m_name[:-4] if m_name.endswith('_new') else None
                })
            
            # ゲッターパターン（複数のバリエーションに対応）
            elif m_name.startswith('get_'):
                context.update({
                    'is_getter': True, 
                    'property_name': m_name[4:],
                    'access_pattern': 'read'
                })
            
            # セッターパターン
            elif m_name.startswith('set_'):
                context.update({
                    'is_setter': True, 
                    'property_name': m_name[4:], 
                    'mutates_state': True,
                    'access_pattern': 'write'
                })
            
            # 状態確認パターン（is_/has_メソッド）
            elif m_name.startswith(('is_', 'has_', 'can_', 'should_', 'will_', 'must_')):
                prefix = next(p for p in ('is_', 'has_', 'can_', 'should_', 'will_', 'must_') if m_name.startswith(p))
                context.update({
                    'is_boolean_getter': True, 
                    'property_name': m_name[len(prefix):],
                    'check_type': prefix[:-1]  # '_'を除去
                })
            
            # データ変換パターン
            elif m_name.startswith(('to_', 'into_', 'from_', 'as_')):
                if m_name.startswith('to_') or m_name.startswith('into_'):
                    prefix = 'to_' if m_name.startswith('to_') else 'into_'
                    target_type = m_name[len(prefix):]
                    context.update({
                        'is_conversion': True,
                        'conversion_type': 'to',
                        'target_type': target_type,
                        'consumes_self': m_name.startswith('into_')
                    })
                elif m_name.startswith('from_'):
                    source_type = m_name[5:]
                    context.update({
                        'is_conversion': True,
                        'conversion_type': 'from',
                        'source_type': source_type
                    })
                elif m_name.startswith('as_'):
                    view_type = m_name[3:]
                    context.update({
                        'is_conversion': True,
                        'conversion_type': 'view',
                        'view_type': view_type,
                        'consumes_self': False
                    })
            
            # 操作種別の識別（一般的な動詞パターン）
            elif any(m_name.startswith(verb) for verb in 
                    ['add_', 'remove_', 'delete_', 'update_', 'create_', 'destroy_', 
                    'load_', 'save_', 'read_', 'write_', 'push_', 'pop_', 'enqueue_', 
                    'dequeue_', 'insert_', 'append_', 'prepend_', 'clear_', 'reset_',
                    'initialize_', 'finalize_', 'start_', 'stop_', 'pause_', 'resume_']):
                
                # 動詞部分を抽出
                verb = next(v for v in 
                        ['add_', 'remove_', 'delete_', 'update_', 'create_', 'destroy_', 
                        'load_', 'save_', 'read_', 'write_', 'push_', 'pop_', 'enqueue_', 
                        'dequeue_', 'insert_', 'append_', 'prepend_', 'clear_', 'reset_',
                        'initialize_', 'finalize_', 'start_', 'stop_', 'pause_', 'resume_'] 
                        if m_name.startswith(v))
                
                operation_target = m_name[len(verb):]
                
                # 状態変更の可能性がある操作
                state_modifying_verbs = [
                    'add_', 'remove_', 'delete_', 'update_', 'create_', 'destroy_',
                    'save_', 'write_', 'push_', 'pop_', 'enqueue_', 'dequeue_', 
                    'insert_', 'append_', 'prepend_', 'clear_', 'reset_', 
                    'initialize_', 'finalize_', 'start_', 'stop_', 'pause_', 'resume_'
                ]
                
                # 入出力関連の操作
                io_verbs = ['load_', 'save_', 'read_', 'write_']
                
                context.update({
                    'operation_type': verb[:-1],  # '_'を除去
                    'operation_target': operation_target,
                    'mutates_state': verb in state_modifying_verbs,
                    'is_io_operation': verb in io_verbs
                })
                
                # ファイル操作として識別可能なパターン
                if operation_target in ['file', 'files', 'config', 'configuration', 
                                    'settings', 'data', 'json', 'xml', 'yaml', 
                                    'toml', 'csv', 'database', 'db']:
                    context.update({
                        'is_file_operation': True,
                        'file_type': operation_target
                    })
            
            # 表示・ログ関連のメソッド
            elif any(m_name.startswith(verb) for verb in 
                    ['print_', 'display_', 'show_', 'log_', 'trace_', 'debug_']):
                verb = next(v for v in ['print_', 'display_', 'show_', 'log_', 'trace_', 'debug_'] 
                        if m_name.startswith(v))
                display_target = m_name[len(verb):]
                context.update({
                    'is_display_operation': True,
                    'display_type': verb[:-1],  # '_'を除去
                    'displays': display_target
                })
            
            # セキュリティ関連のメソッド
            elif any(security_term in m_name for security_term in 
                    ['encrypt', 'decrypt', 'hash', 'sign', 'verify', 'auth', 'password', 
                    'credential', 'token', 'secret', 'secure', 'masked']):
                context.update({'is_security_related': True})
                
                if 'encrypt' in m_name:
                    context.update({'security_operation': 'encryption'})
                elif 'decrypt' in m_name:
                    context.update({'security_operation': 'decryption'})
                elif 'hash' in m_name:
                    context.update({'security_operation': 'hashing'})
                elif 'sign' in m_name:
                    context.update({'security_operation': 'signing'})
                elif 'verify' in m_name:
                    context.update({'security_operation': 'verification'})
                elif 'masked' in m_name or 'mask' in m_name:
                    context.update({'security_operation': 'masking'})
        
        # パラメータの分析
        if isinstance(info.parameters, list) and info.parameters:
            param_details = []
            
            # 特定のパラメータパターンの検出
            has_self = False
            pattern_params = {
                'key': False,
                'value': False,
                'path': False,
                'id': False,
                'name': False,
                'index': False,
                'data': False,
                'config': False,
                'options': False,
                'callback': False,
                'handler': False,
                'listener': False,
                'observer': False,
                'context': False,
                'state': False,
                'result': False,
                'error': False,
            }
            
            for p in info.parameters:
                if isinstance(p, dict):
                    p_name = p.get('name', '')
                    p_type = p.get('type', '')
                    param_details.append({'name': p_name, 'type': p_type})
                    
                    # self/&self/&mut selfパラメータの検出
                    if p_name in ('self', '&self', '&mut self'):
                        has_self = True
                        if p_name == '&mut self':
                            context['has_mutable_self'] = True
                        elif p_name == '&self':
                            context['has_immutable_self'] = True
                        else:
                            context['has_owned_self'] = True
                    
                    # 特定のパラメータ名パターンの検出
                    for param_name in pattern_params:
                        if p_name == param_name or p_name.endswith(f'_{param_name}'):
                            pattern_params[param_name] = True
                    
                    # 参照渡しまたは可変参照渡しパラメータの検出
                    if p_type.startswith('&mut '):
                        context['has_mutable_reference_param'] = True
                    elif p_type.startswith('&'):
                        context['has_immutable_reference_param'] = True
                    
                    # ジェネリックパラメータの検出
                    if 'T' in p_type or p_type.startswith(('Option<', 'Result<')):
                        context['has_generic_param'] = True
                    
                    # コールバックパラメータの検出
                    if 'Fn' in p_type or 'FnMut' in p_type or 'FnOnce' in p_type:
                        context['has_callback_param'] = True
                else:
                    param_details.append({'name': 'unknown', 'type': 'unknown'})
            
            context['parameters_list'] = param_details
            
            if has_self:
                context['has_self_parameter'] = True
            
            # 特定のパラメータパターンをコンテキストに追加
            for param_name, exists in pattern_params.items():
                if exists:
                    context[f'has_{param_name}_parameter'] = True
                    
                    # 特定パラメータによる追加のコンテキスト
                    if param_name == 'path':
                        context.update({'is_file_related': True})
                    elif param_name == 'callback' or param_name == 'handler' or param_name == 'listener' or param_name == 'observer':
                        context.update({'is_event_related': True})
        
        # 戻り値の分析
        if isinstance(info.return_type, str) and info.return_type:
            rt = info.return_type
            context['return_type_str'] = rt
            
            # 一般的な戻り値パターンの検出
            if rt.startswith(('Result<', 'std::result::Result<')):
                context['returns_result'] = True
                # Resultの内部型を取得
                match = re.search(r'Result<(.*?)(?:,\s*(.*?))?>', rt)
                if match:
                    context['result_ok_type'] = match.group(1).strip()
                    if match.group(2):
                        context['result_err_type'] = match.group(2).strip()
            
            elif rt.startswith(('Option<', 'std::option::Option<')):
                context['returns_option'] = True
                # Optionの内部型を取得
                match = re.search(r'Option<(.*)>', rt)
                if match:
                    context['option_some_type'] = match.group(1).strip()
            
            elif rt == 'Self' and 'parent_type' in context:
                context['returns_self_type'] = True
            
            elif rt == 'bool':
                context['returns_boolean'] = True
                
                # 真偽値を返す関数の追加コンテキスト
                if info.name and info.name.startswith(('is_', 'has_', 'can_', 'should_', 'will_', 'must_')):
                    context['is_predicate_function'] = True
            
            elif rt.startswith(('Vec<', 'std::vec::Vec<')):
                context['returns_collection'] = True
                context['collection_type'] = 'vector'
                # ベクタの要素型を取得
                match = re.search(r'Vec<(.*)>', rt)
                if match:
                    context['collection_element_type'] = match.group(1).strip()
            
            elif rt.startswith(('HashMap<', 'std::collections::HashMap<')):
                context['returns_collection'] = True
                context['collection_type'] = 'hash_map'
                # HashMapのキーと値の型を取得
                match = re.search(r'HashMap<(.*),\s*(.*)>', rt)
                if match:
                    context['map_key_type'] = match.group(1).strip()
                    context['map_value_type'] = match.group(2).strip()
            
            elif rt.startswith(('HashSet<', 'std::collections::HashSet<')):
                context['returns_collection'] = True
                context['collection_type'] = 'hash_set'
                # HashSetの要素型を取得
                match = re.search(r'HashSet<(.*)>', rt)
                if match:
                    context['collection_element_type'] = match.group(1).strip()
            
            elif rt.startswith(('BTreeMap<', 'std::collections::BTreeMap<')):
                context['returns_collection'] = True
                context['collection_type'] = 'btree_map'
                # BTreeMapのキーと値の型を取得
                match = re.search(r'BTreeMap<(.*),\s*(.*)>', rt)
                if match:
                    context['map_key_type'] = match.group(1).strip()
                    context['map_value_type'] = match.group(2).strip()
            
            elif rt.startswith(('BTreeSet<', 'std::collections::BTreeSet<')):
                context['returns_collection'] = True
                context['collection_type'] = 'btree_set'
                # BTreeSetの要素型を取得
                match = re.search(r'BTreeSet<(.*)>', rt)
                if match:
                    context['collection_element_type'] = match.group(1).strip()
            
            elif rt.startswith('Box<'):
                context['returns_boxed'] = True
                # Boxの内部型を取得
                match = re.search(r'Box<(.*)>', rt)
                if match:
                    context['boxed_type'] = match.group(1).strip()
            
            elif rt.startswith('Arc<'):
                context['returns_thread_safe'] = True
                context['returns_shared'] = True
                # Arcの内部型を取得
                match = re.search(r'Arc<(.*)>', rt)
                if match:
                    context['shared_type'] = match.group(1).strip()
            
            elif rt.startswith('Rc<'):
                context['returns_shared'] = True
                # Rcの内部型を取得
                match = re.search(r'Rc<(.*)>', rt)
                if match:
                    context['shared_type'] = match.group(1).strip()
            
            elif rt.startswith('Ref<') or rt.startswith('RefMut<'):
                context['returns_cell_ref'] = True
                context['returns_mutable'] = rt.startswith('RefMut<')
                # Ref/RefMutの内部型を取得
                match = re.search(r'Ref(?:Mut)?<(.*)>', rt)
                if match:
                    context['ref_type'] = match.group(1).strip()
            
            elif rt.startswith('String') or rt.startswith('&str'):
                context['returns_string'] = True
            
            elif rt.startswith(('u8', 'u16', 'u32', 'u64', 'u128', 'usize', 'i8', 'i16', 'i32', 'i64', 'i128', 'isize')):
                context['returns_integer'] = True
                context['integer_type'] = rt
            
            elif rt.startswith(('f32', 'f64')):
                context['returns_float'] = True
                context['float_type'] = rt
            
            elif rt == '()':
                context['returns_unit'] = True
            
            elif rt.startswith('impl '):
                context['returns_trait_object'] = True
                match = re.search(r'impl (.*)', rt)
                if match:
                    context['trait_type'] = match.group(1).strip()
            
            elif rt.startswith('dyn '):
                context['returns_dynamic_trait'] = True
                match = re.search(r'dyn (.*)', rt)
                if match:
                    context['dynamic_trait_type'] = match.group(1).strip()
            
            # その他の関連性の検出
            if rt.startswith(('Future<', 'Pin<Box<dyn Future<')) or 'async' in info.signature:
                context['is_async'] = True
            
            if 'stream' in rt.lower() or rt.startswith(('Stream<', 'impl Stream<')):
                context['returns_stream'] = True
            
            if 'error' in rt.lower() or 'exception' in rt.lower():
                context['is_error_related'] = True
        
        # その他の特徴の検出（シグネチャやソースコードのパターン）
        if info.signature:
            if 'pub ' in info.signature:
                context['is_public'] = True
            
            if ' unsafe ' in info.signature:
                context['is_unsafe'] = True
            
            if ' async ' in info.signature:
                context['is_async'] = True
                
            if ' const ' in info.signature:
                context['is_const'] = True
                
            if '#[derive(' in info.signature:
                context['has_derive_attribute'] = True
                
            if '#[test]' in info.signature:
                context['is_test_function'] = True
                
            if '#[cfg(' in info.signature:
                context['has_conditional_compilation'] = True
        
        return context

    def _prepare_code_with_context(self, element: BaseElement, context_info: Dict[str, Any]) -> str:
        """コード要素とコンテキスト情報からドキュメント生成用のプロンプトを構築する
        
        要素の基本情報（型、名前、定義位置など）とコンテキスト分析結果を組み合わせて、
        OpenAI APIに送信するためのプロンプトを生成します。このプロンプトにはコードと
        そのコンテキスト情報が含まれ、APIが適切なドキュメントを生成するための情報を提供します。
        
        生成する情報:
        - 要素の基本情報（型、名前、ID、ファイルパス、行番号）
        - 要素の詳細情報（シグネチャ、パラメータ、戻り値など）
        - 分析されたコンテキスト情報（関数の役割、パラメータの特性、戻り値の意味など）
        - 周辺の型や関数に関する情報
        - AIシステムへのヒントや生成指示
        
        Args:
            element: ドキュメントを生成する対象のコード要素
            context_info: 要素の分析結果を含むコンテキスト情報
            
        Returns:
            OpenAI APIに送信するためのプロンプト文字列
        """
        if element.info is None or not element.info.source_code:
            display_name = self._get_display_name(element)
            return f"// Error: Source code missing for {display_name}"
        
        # 基本情報
        code_for_prompt = element.info.source_code
        element_type = element.__class__.__name__
        display_name = self._get_display_name(element)
        element_id = element.get_unique_id()
        file_path = element.info.file_path or 'N/A'
        start_line = element.info.start_line
        
        # 基本コメントの構築
        comments = [
            f"// Element Type: {element_type}",
            f"// Element Name: {display_name}",
            f"// Element ID: {element_id}",
            f"// File Path: {file_path}",
            f"// Start Line: {start_line}",
        ]
        
        info = element.info
        
        # 要素タイプ別の詳細情報
        if isinstance(info, FunctionElementInfo):
            # 関数の詳細情報
            signature = info.signature or 'N/A'
            return_type = info.return_type or '()'
            
            # 標準的なコメント
            comments.extend([
                f"// Signature: {signature}",
                f"// Returns: {return_type}",
            ])
            
            # パラメータ情報の詳細化
            if info.parameters:
                # テーブル形式のパラメータ表示
                comments.append("// Parameters:")
                for i, param in enumerate(info.parameters):
                    if isinstance(param, dict):
                        param_name = param.get('name', '?')
                        param_type = param.get('type', '?')
                        is_mut = '&mut ' in param_type or 'mut ' in param_name
                        is_ref = param_type.startswith('&') or param_name.startswith('&')
                        comments.append(f"//   {i+1}. {param_name}: {param_type} "
                                    f"{' (mutable)' if is_mut else ''}"
                                    f"{' (reference)' if is_ref and not is_mut else ''}")
            
            # メソッド関連情報
            if info.is_impl_method:
                comments.append(f"// Parent Type: {info.parent_type or 'N/A'}")
                
                # トレイト実装メソッドの場合
                if info.is_trait_method and info.metadata and info.metadata.get('trait_name'):
                    comments.append(f"// Implemented Trait: {info.metadata.get('trait_name', 'N/A')}")
            
            # 関数の特性（signature属性がある場合のみ）
            if hasattr(info, 'signature') and info.signature:
                sig = info.signature
                if ' pub ' in sig or sig.startswith('pub '):
                    comments.append("// Visibility: Public")
                else:
                    comments.append("// Visibility: Private/Internal")
                    
                if ' unsafe ' in sig:
                    comments.append("// Safety: Unsafe function")
                    
                if ' async ' in sig:
                    comments.append("// Concurrency: Asynchronous function")
                    
                if ' const ' in sig:
                    comments.append("// Evaluation: Compile-time constant function")
        
        elif isinstance(info, StructElementInfo):
            # 構造体の詳細情報
            # signatureプロパティの存在をチェック
            visibility = ""
            if hasattr(info, 'signature') and info.signature:
                visibility = "pub " if "pub " in info.signature else ""
            
            comments.append(f"// Definition: {visibility}struct {info.name or 'Anonymous'}")
            
            # 型パラメータ
            if info.type_params:
                comments.append(f"// Type Parameters: <{', '.join(info.type_params)}>")
            
            # フィールド情報を表形式で
            if info.fields:
                comments.append("// Fields:")
                for i, field in enumerate(info.fields):
                    if isinstance(field, dict):
                        field_name = field.get('name', '?')
                        field_type = field.get('type', '?')
                        visibility = "pub " if field.get('is_pub') else ""
                        comments.append(f"//   {i+1}. {visibility}{field_name}: {field_type}")
            
            # 実装されているトレイト
            if hasattr(info, 'impl_traits') and info.impl_traits:
                comments.append(f"// Implements: {', '.join(info.impl_traits)}")
        
        elif isinstance(info, EnumElementInfo):
            # 列挙型の詳細情報
            # signatureプロパティの存在をチェック
            visibility = ""
            if hasattr(info, 'signature') and info.signature:
                visibility = "pub " if "pub " in info.signature else ""
            
            comments.append(f"// Definition: {visibility}enum {info.name or 'Anonymous'}")
            
            # 型パラメータ
            if info.type_params:
                comments.append(f"// Type Parameters: <{', '.join(info.type_params)}>")
            
            # バリアント情報を表形式で
            if info.variants:
                comments.append("// Variants:")
                for i, variant in enumerate(info.variants):
                    if isinstance(variant, dict):
                        variant_name = variant.get('name', '?')
                        variant_type = variant.get('type', '')
                        if variant_type:
                            comments.append(f"//   {i+1}. {variant_name}({variant_type})")
                        else:
                            comments.append(f"//   {i+1}. {variant_name}")
            
            # 実装されているトレイト
            if hasattr(info, 'impl_traits') and info.impl_traits:
                comments.append(f"// Implements: {', '.join(info.impl_traits)}")
        
        elif isinstance(info, TraitElementInfo):
            # トレイトの詳細情報
            # signatureプロパティの存在をチェック
            visibility = ""
            if hasattr(info, 'signature') and info.signature:
                visibility = "pub " if "pub " in info.signature else ""
            
            comments.append(f"// Definition: {visibility}trait {info.name or 'Anonymous'}")
            
            # 型パラメータ
            if info.type_params:
                comments.append(f"// Type Parameters: <{', '.join(info.type_params)}>")
            
            # スーパートレイト
            if info.super_traits:
                super_traits_str = ', '.join(info.super_traits)
                comments.append(f"// Super Traits: {super_traits_str}")
            
            # 関連型
            if info.associated_types:
                assoc_types_str = ', '.join(info.associated_types)
                comments.append(f"// Associated Types: {assoc_types_str}")
            
            # 要求されるメソッド
            if info.methods:
                comments.append("// Required Methods:")
                for i, method in enumerate(info.methods):
                    if isinstance(method, dict):
                        method_name = method.get('name', '?')
                        method_sig = method.get('signature', '?')
                        comments.append(f"//   {i+1}. {method_name}: {method_sig}")
        
        elif isinstance(info, ModuleElementInfo):
            # モジュールの詳細情報
            module_kind = 'Inline Module' if info.is_inline else 'File Module'
            
            # signatureプロパティの存在をチェック
            visibility = ""
            if hasattr(info, 'signature') and info.signature:
                visibility = "pub " if "pub " in info.signature else ""
            
            comments.append(f"// Definition: {visibility}mod {info.name or 'Anonymous'}")
            comments.append(f"// Module Type: {module_kind}")
            
            # ファイルモジュールの場合、ファイルパス情報
            if not info.is_inline and info.file_path:
                comments.append(f"// Module File: {os.path.basename(info.file_path)}")
        
        # コンテキスト情報の追加（より構造化された形式で）
        if context_info:
            comments.append("\n// Context Information:")
            
            # 関数関連のコンテキスト情報をグループ化
            function_context = {}
            param_context = {}
            return_context = {}
            type_context = {}
            behavior_context = {}
            misc_context = {}
            
            # コンテキスト情報を分類
            for k, v in context_info.items():
                # 関数の特性に関するコンテキスト
                if k in ['is_constructor', 'is_getter', 'is_setter', 'is_boolean_getter', 
                        'is_conversion', 'is_public', 'is_unsafe', 'is_async', 'is_const',
                        'is_display_operation', 'is_security_related', 'is_file_operation',
                        'is_file_related', 'is_event_related', 'is_io_operation', 
                        'is_predicate_function', 'constructor_variant', 'operation_type',
                        'operation_target', 'conversion_type', 'property_name']:
                    function_context[k] = v
                
                # パラメータに関するコンテキスト
                elif k.startswith('has_') and k.endswith('_parameter') or k in ['parameters_list',
                                                                            'has_mutable_reference_param',
                                                                            'has_immutable_reference_param',
                                                                            'has_generic_param',
                                                                            'has_callback_param']:
                    param_context[k] = v
                
                # 戻り値に関するコンテキスト
                elif k.startswith('returns_') or k in ['return_type_str', 'result_ok_type', 
                                                    'result_err_type', 'option_some_type',
                                                    'collection_type', 'collection_element_type',
                                                    'map_key_type', 'map_value_type', 
                                                    'boxed_type', 'shared_type', 'ref_type',
                                                    'integer_type', 'float_type', 'trait_type',
                                                    'dynamic_trait_type']:
                    return_context[k] = v
                
                # 型関連のコンテキスト
                elif k in ['parent_type', 'constructs_type', 'target_type', 'source_type', 
                        'view_type', 'common_method_name_in_types', 'is_common_method_name']:
                    type_context[k] = v
                
                # 動作に関するコンテキスト
                elif k in ['mutates_state', 'consumes_self', 'has_mutable_self', 
                        'has_immutable_self', 'has_owned_self', 'access_pattern',
                        'check_type', 'display_type', 'displays', 'security_operation',
                        'file_type']:
                    behavior_context[k] = v
                
                # その他のコンテキスト
                else:
                    misc_context[k] = v
            
            # 関数の特性
            if function_context:
                comments.append("// Function Characteristics:")
                for k, v in function_context.items():
                    if isinstance(v, bool) and v:
                        # 真偽値のコンテキストは、Trueの場合のみシンプルに表示
                        comments.append(f"//   - {k.replace('_', ' ').capitalize()}")
                    else:
                        try:
                            v_str = json.dumps(v, ensure_ascii=False, indent=None, separators=(',', ':'))
                        except TypeError:
                            v_str = str(v)
                        max_len = 100
                        display_v = f"{v_str[:max_len]}{'...' if len(v_str) > max_len else ''}"
                        # キーを読みやすく整形
                        display_k = k.replace('_', ' ').capitalize()
                        comments.append(f"//   - {display_k}: {display_v}")
            
            # パラメータの特性
            if param_context:
                comments.append("// Parameter Characteristics:")
                for k, v in param_context.items():
                    if k == 'parameters_list':
                        continue  # パラメータリストは別途処理済み
                    if isinstance(v, bool) and v:
                        # 'has_' プレフィックスと '_parameter' サフィックスを除去
                        cleaned_k = k.replace('has_', '').replace('_parameter', '')
                        comments.append(f"//   - Has {cleaned_k} parameter")
                    else:
                        try:
                            v_str = json.dumps(v, ensure_ascii=False, indent=None, separators=(',', ':'))
                        except TypeError:
                            v_str = str(v)
                        max_len = 100
                        display_v = f"{v_str[:max_len]}{'...' if len(v_str) > max_len else ''}"
                        # キーを読みやすく整形
                        display_k = k.replace('_', ' ').replace('has ', 'Has ').capitalize()
                        comments.append(f"//   - {display_k}: {display_v}")
            
            # 戻り値の特性
            if return_context:
                comments.append("// Return Value Characteristics:")
                for k, v in return_context.items():
                    if k == 'return_type_str':
                        continue  # 戻り値の型は別途処理済み
                    if isinstance(v, bool) and v:
                        # 'returns_' プレフィックスを除去
                        cleaned_k = k.replace('returns_', '')
                        comments.append(f"//   - Returns {cleaned_k}")
                    else:
                        try:
                            v_str = json.dumps(v, ensure_ascii=False, indent=None, separators=(',', ':'))
                        except TypeError:
                            v_str = str(v)
                        max_len = 100
                        display_v = f"{v_str[:max_len]}{'...' if len(v_str) > max_len else ''}"
                        # キーを読みやすく整形
                        display_k = k.replace('_', ' ').replace('returns ', 'Returns ').capitalize()
                        comments.append(f"//   - {display_k}: {display_v}")
            
            # 型関連の特性
            if type_context:
                comments.append("// Type Relationships:")
                for k, v in type_context.items():
                    if isinstance(v, bool) and v:
                        comments.append(f"//   - {k.replace('_', ' ').replace('is ', 'Is ').capitalize()}")
                    else:
                        try:
                            v_str = json.dumps(v, ensure_ascii=False, indent=None, separators=(',', ':'))
                        except TypeError:
                            v_str = str(v)
                        max_len = 100
                        display_v = f"{v_str[:max_len]}{'...' if len(v_str) > max_len else ''}"
                        # キーを読みやすく整形
                        display_k = k.replace('_', ' ').capitalize()
                        comments.append(f"//   - {display_k}: {display_v}")
            
            # 動作に関する特性
            if behavior_context:
                comments.append("// Behavioral Characteristics:")
                for k, v in behavior_context.items():
                    if isinstance(v, bool) and v:
                        comments.append(f"//   - {k.replace('_', ' ').capitalize()}")
                    else:
                        try:
                            v_str = json.dumps(v, ensure_ascii=False, indent=None, separators=(',', ':'))
                        except TypeError:
                            v_str = str(v)
                        max_len = 100
                        display_v = f"{v_str[:max_len]}{'...' if len(v_str) > max_len else ''}"
                        # キーを読みやすく整形
                        display_k = k.replace('_', ' ').capitalize()
                        comments.append(f"//   - {display_k}: {display_v}")
            
            # その他の特性
            if misc_context:
                comments.append("// Additional Context:")
                for k, v in misc_context.items():
                    if isinstance(v, bool) and v:
                        comments.append(f"//   - {k.replace('_', ' ').capitalize()}")
                    else:
                        try:
                            v_str = json.dumps(v, ensure_ascii=False, indent=None, separators=(',', ':'))
                        except TypeError:
                            v_str = str(v)
                        max_len = 100
                        display_v = f"{v_str[:max_len]}{'...' if len(v_str) > max_len else ''}"
                        # キーを読みやすく整形
                        display_k = k.replace('_', ' ').capitalize()
                        comments.append(f"//   - {display_k}: {display_v}")
        
        # 周辺コード文脈情報（プロジェクト特有の情報）の追加
        try:
            # ファイル内の全型名のコンテキスト
            if hasattr(self, 'current_context') and self.current_context.get('all_type_names'):
                type_names = list(self.current_context.get('all_type_names'))
                if len(type_names) > 0:
                    comments.append("\n// Project Context:")
                    comments.append(f"//   - Known Types in File: {', '.join(sorted(type_names)[:10])}"
                                f"{' (and more...)' if len(type_names) > 10 else ''}")
        except Exception:
            # 周辺コンテキスト抽出でエラーが発生しても続行
            pass
        
        # プロンプトの構築（コメント + コード）
        prompt = "\n".join(comments) + "\n\n```rust\n" + code_for_prompt + "\n```"
        
        # 必要に応じて、AIシステムへの追加指示
        hint_comments = []
        
        # 関数型の場合の追加ヒント
        if isinstance(info, FunctionElementInfo):
            # 戻り値がResultの場合
            if context_info.get('returns_result'):
                hint_comments.append("// Hint: This function returns a Result type. Consider documenting both success and error cases.")
            
            # 戻り値がOptionの場合
            elif context_info.get('returns_option'):
                hint_comments.append("// Hint: This function returns an Option type. Consider documenting both Some and None cases.")
            
            # 非同期関数の場合
            if context_info.get('is_async'):
                hint_comments.append("// Hint: This is an asynchronous function. Consider mentioning any potential await points or completion behavior.")
            
            # unsafe関数の場合
            if context_info.get('is_unsafe'):
                hint_comments.append("// Hint: This is an unsafe function. Document the safety requirements and invariants that callers must uphold.")
        
        # 構造体/列挙型の場合の追加ヒント
        elif isinstance(info, (StructElementInfo, EnumElementInfo)):
            # 多くのフィールド/バリアントがある場合
            fields_count = len(info.fields) if isinstance(info, StructElementInfo) and info.fields else 0
            variants_count = len(info.variants) if isinstance(info, EnumElementInfo) and info.variants else 0
            if fields_count > 5 or variants_count > 5:
                hint_comments.append(f"// Hint: This {element_type.lower()} has many fields/variants. "
                                    "Consider grouping them logically in the documentation.")
        
        # ヒントがあれば追加
        if hint_comments:
            prompt += "\n\n" + "\n".join(hint_comments)
        
        return prompt


    def get_usage_stats(self) -> Dict[str, int]:
        """OpenAI APIの使用統計を取得する
        
        APIクライアントから使用したトークン数などの統計情報を取得します。
        
        Returns:
            APIの使用統計情報（プロンプトトークン数、完了トークン数、合計トークン数）
        """
        if hasattr(self.openai_client, 'get_usage_stats') and callable(self.openai_client.get_usage_stats):
             return self.openai_client.get_usage_stats()
        else: return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
