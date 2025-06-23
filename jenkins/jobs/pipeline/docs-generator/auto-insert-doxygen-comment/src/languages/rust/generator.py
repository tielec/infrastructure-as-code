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
        
        Args:
            file_path: 処理するRustソースファイルのパス
            templates: 要素タイプごとのドキュメントテンプレート
            overwrite_doc: True の場合、既存のドキュメントを上書きする
        """
        print(f"Processing file: {file_path}")
        self.processed_element_ids.clear()
        
        # 1. ファイルを読み込む
        initial_lines = self._read_file_safely(file_path)
        if initial_lines is None:
            return
        
        # 2. パースして要素を取得
        elements = self._parse_file_safely(file_path)
        if not elements:
            return
        
        # 3. コンテキストを設定し、要素を準備
        valid_elements = self._prepare_elements_and_context(elements, file_path)
        if not valid_elements:
            print("No valid elements with info found.")
            return
        
        # 4. ドキュメント生成と挿入情報の収集
        insertions, stats = self._generate_documentation(valid_elements, templates, initial_lines, overwrite_doc)
        
        # 5. ドキュメント挿入とファイル更新
        file_modified = self._apply_insertions_and_save(insertions, initial_lines, file_path)
        
        # 6. サマリー表示
        self._print_summary(file_path, len(valid_elements), stats, file_modified)

    def _read_file_safely(self, file_path: str) -> Optional[List[str]]:
        """ファイルを安全に読み込む"""
        try:
            source_code, initial_lines = read_file(file_path)
            if not initial_lines and source_code:
                initial_lines = source_code.splitlines(keepends=True)
            elif not initial_lines and not source_code:
                print(f"Warning: File {file_path} is empty.")
                initial_lines = []
            return initial_lines
        except Exception as read_err:
            print(f"Error reading file {file_path}: {read_err}. Aborting.")
            traceback.print_exc()
            return None

    def _parse_file_safely(self, file_path: str) -> List[RustElement]:
        """ファイルを安全にパースする"""
        try:
            return self.parser.parse_file(file_path)
        except Exception as e:
            print(f"Error parsing file {file_path}: {e}")
            traceback.print_exc()
            return []

    def _prepare_elements_and_context(self, elements: List[RustElement], file_path: str) -> List[RustElement]:
        """要素を準備し、コンテキストを設定する"""
        # コンテキストの初期化
        self.current_context = {
            'file_path': file_path,
            'all_type_names': set(),
            'all_methods': {}
        }
        
        # 有効な要素のフィルタリングとコンテキスト収集
        valid_elements = []
        for element in elements:
            if element.info is None:
                continue
            
            valid_elements.append(element)
            self._collect_element_context(element)
        
        # 要素を処理順序でソート
        return self._sort_elements_by_priority(valid_elements)

    def _collect_element_context(self, element: RustElement) -> None:
        """要素からコンテキスト情報を収集"""
        info = element.info
        
        # 型名の収集
        if isinstance(info, (StructElementInfo, EnumElementInfo, TraitElementInfo)):
            if info.name:
                self.current_context['all_type_names'].add(info.name)
        
        # メソッド情報の収集
        if isinstance(info, FunctionElementInfo) and info.is_impl_method:
            self._collect_method_context(info, element)

    def _collect_method_context(self, info: FunctionElementInfo, element: RustElement) -> None:
        """メソッドのコンテキスト情報を収集"""
        method_name = info.name
        parent_type = info.parent_type
        
        if method_name and parent_type:
            if method_name not in self.current_context['all_methods']:
                self.current_context['all_methods'][method_name] = []
            
            parent_base = re.sub(r'<.*?>.*$', '', parent_type).strip()
            self.current_context['all_methods'][method_name].append({
                'parent_type': parent_base,
                'element_id': element.get_unique_id()
            })

    def _sort_elements_by_priority(self, elements: List[RustElement]) -> List[RustElement]:
        """要素を処理優先度でソート"""
        element_order = {
            ModuleElement: 0,
            StructElement: 1,
            EnumElement: 1,
            TraitElement: 1,
            FunctionElement: 2
        }
        
        def sort_key(e):
            # ファイルモジュールを最優先
            if isinstance(e, ModuleElement) and e.info and not e.info.is_inline:
                return (0, 0, e.info.start_line if e.info else 0)
            # その他の要素
            priority = element_order.get(type(e), 99)
            start_line = e.info.start_line if e.info else 0
            return (1, priority, start_line)
        
        return sorted(elements, key=sort_key)

    def _generate_documentation(self, elements: List[RustElement], templates: Dict[str, str], 
                            initial_lines: List[str], overwrite_doc: bool) -> Tuple[List[Tuple[InsertionPoint, str, str]], Dict[str, int]]:
        """ドキュメントを生成し、挿入情報を収集する"""
        insertions = []
        stats = {
            'processed': 0,
            'skipped_existing': 0,
            'skipped_template': 0,
            'skipped_generate': 0,
            'skipped_analyze': 0,
            'last_exception': None
        }
        
        processed_ids = set()
        
        for element in elements:
            if not element.info:
                continue
            
            # 重複チェック
            element_id = element.get_unique_id()
            if element_id in processed_ids:
                if self.debug:
                    print(f"Debug: Skipping duplicate ID: {element_id}")
                continue
            processed_ids.add(element_id)
            
            # 要素を処理
            result = self._process_single_element(
                element, templates, initial_lines, overwrite_doc
            )
            
            if result:
                insertions.append(result)
                stats['processed'] += 1
            else:
                # 統計情報の更新は_process_single_element内で行う
                pass
        
        return insertions, stats

    def _process_single_element(self, element: RustElement, templates: Dict[str, str], 
                            initial_lines: List[str], overwrite_doc: bool) -> Optional[Tuple[InsertionPoint, str, str]]:
        """単一の要素を処理"""
        display_name = self._get_display_name(element)
        
        # テンプレートの取得
        template = self._get_template_for_element(element, templates)
        if not template:
            if self.debug:
                print(f"Skipping {display_name}: No template found.")
            return None
        
        # 挿入位置の解析
        insertion_point = self._analyze_insertion_safely(element, initial_lines, display_name)
        if not insertion_point:
            return None
        
        # 既存ドキュメントのチェック
        if self._should_skip_existing_doc(insertion_point, overwrite_doc, display_name):
            return None
        
        print(f"Processing: {display_name} (ID: {element.get_unique_id()}) at L{insertion_point.def_line + 1}")
        
        # ドキュメント生成
        formatted_doc = self._generate_and_format_doc(element, template, display_name)
        if not formatted_doc:
            return None
        
        return (insertion_point, formatted_doc, display_name)

    def _get_template_for_element(self, element: RustElement, templates: Dict[str, str]) -> Optional[str]:
        """要素に対応するテンプレートを取得"""
        element_type = element.__class__.__name__.lower().replace('element', '')
        template_key = 'function' if isinstance(element, FunctionElement) else element_type
        return templates.get(template_key)

    def _analyze_insertion_safely(self, element: RustElement, initial_lines: List[str], 
                                display_name: str) -> Optional[InsertionPoint]:
        """挿入位置を安全に解析"""
        try:
            return element.analyze_insertion_point(initial_lines)
        except ValueError as e:
            print(f"Error analyzing insertion point for {display_name}: {e}. Skipping.")
            return None
        except Exception as e:
            print(f"Unexpected error analyzing {display_name}: {e}. Skipping.")
            traceback.print_exc()
            return None

    def _should_skip_existing_doc(self, insertion_point: InsertionPoint, 
                                overwrite_doc: bool, display_name: str) -> bool:
        """既存ドキュメントのためスキップすべきか判定"""
        has_existing = (insertion_point.existing_doc_start >= 0 and 
                    insertion_point.existing_doc_end >= 0)
        
        if has_existing and not overwrite_doc:
            if self.debug:
                print(f"Skipping {display_name}: Existing doc found "
                    f"(L{insertion_point.existing_doc_start+1}-L{insertion_point.existing_doc_end+1})")
            return True
        
        return False

    def _generate_and_format_doc(self, element: RustElement, template: str, 
                                display_name: str) -> Optional[str]:
        """ドキュメントを生成し整形する"""
        # コンテキスト作成
        context_info = self._create_element_context(element)
        
        # プロンプト準備
        code_prompt = self._prepare_code_with_context(element, context_info)
        
        # ドキュメント生成
        print(f"  Generating doc for: {display_name}...")
        docstring = self.openai_client.generate_doc(code_prompt, template, self.system_prompt)
        
        if not self._is_valid_docstring(docstring):
            print(f"  Failed to generate valid doc for {display_name}. Skipping.")
            return None
        
        # ドキュメント整形
        formatted_doc = self._format_doc(docstring)
        if not self._is_valid_formatted_doc(formatted_doc):
            print(f"  Generated doc empty/minimal for {display_name}. Skipping.")
            return None
        
        if self.debug:
            self._print_generated_doc(formatted_doc)
        
        return formatted_doc

    def _create_element_context(self, element: RustElement) -> Dict[str, Any]:
        """要素のコンテキスト情報を作成"""
        if isinstance(element, FunctionElement):
            return self._create_function_context(element)
        return {}

    def _is_valid_docstring(self, docstring: str) -> bool:
        """生成されたdocstringが有効か判定"""
        return (docstring and 
                "Error generating" not in docstring and 
                "Failed to generate" not in docstring)

    def _is_valid_formatted_doc(self, formatted_doc: str) -> bool:
        """整形されたドキュメントが有効か判定"""
        return (formatted_doc and 
                formatted_doc.strip() and 
                len(formatted_doc.splitlines()) > 2)

    def _print_generated_doc(self, formatted_doc: str) -> None:
        """生成されたドキュメントを表示"""
        print(f"\n  Generated Doc:\n{'-'*30}\n{formatted_doc}\n{'-'*30}")

    def _apply_insertions_and_save(self, insertions: List[Tuple[InsertionPoint, str, str]], 
                                initial_lines: List[str], file_path: str) -> bool:
        """挿入を適用してファイルを保存"""
        if not insertions:
            print("No documentation blocks were generated or needed insertion.")
            return False
        
        print("-" * 80)
        print(f"Collected {len(insertions)} doc blocks. Applying changes...")
        
        # 挿入を適用
        modified_lines = self._apply_insertions(insertions, initial_lines)
        if modified_lines is None:
            return False
        
        # ファイルを保存
        return self._save_file_if_changed(modified_lines, initial_lines, file_path)

    def _apply_insertions(self, insertions: List[Tuple[InsertionPoint, str, str]], 
                        initial_lines: List[str]) -> Optional[List[str]]:
        """挿入を適用"""
        # 逆順でソート（後ろから挿入）
        insertions.sort(key=lambda item: item[0].def_line, reverse=True)
        
        modified_lines = list(initial_lines)
        insert_errors = 0
        
        for insertion_point, doc_to_insert, element_name in insertions:
            try:
                self._insert_doc(modified_lines, insertion_point, doc_to_insert)
                if self.debug:
                    print(f"  Applied insertion for '{element_name}' (orig L{insertion_point.def_line + 1})")
            except Exception as e:
                print(f"  Error inserting doc for '{element_name}': {e}. Skipping.")
                insert_errors += 1
                if isinstance(e, IndexError):
                    traceback.print_exc()
        
        if insert_errors > 0:
            print(f"Skipped writing due to {insert_errors} insertion error(s).")
            return None
        
        return modified_lines

    def _save_file_if_changed(self, modified_lines: List[str], initial_lines: List[str], 
                            file_path: str) -> bool:
        """変更があればファイルを保存"""
        final_content = "".join(modified_lines)
        initial_content = "".join(initial_lines)
        
        if final_content != initial_content:
            print(f"Changes detected. Writing updated content to {file_path}...")
            try:
                write_file(file_path, modified_lines)
                print(f"Successfully updated file.")
                return True
            except Exception as e:
                print(f"Error writing file: {e}")
                return False
        else:
            print("No effective changes detected. File not modified.")
            return False

    def _print_summary(self, file_path: str, total_elements: int, 
                    stats: Dict[str, int], file_modified: bool) -> None:
        """処理結果のサマリーを表示"""
        print("-" * 80)
        print(f"Completed processing {file_path}.")
        print(f"  Total elements parsed: {total_elements}")
        print(f"  Docs generated & prepared for insertion: {stats['processed']}")
        
        # スキップ理由の表示
        if stats['skipped_existing'] > 0:
            print(f"  Skipped (Existing Doc, Overwrite=False): {stats['skipped_existing']}")
        if stats['skipped_template'] > 0:
            print(f"  Skipped (No Template Found): {stats['skipped_template']}")
        if stats['skipped_generate'] > 0:
            print(f"  Skipped (Doc Generation Failed/Empty): {stats['skipped_generate']}")
        if stats['skipped_analyze'] > 0:
            print(f"  Skipped (Insertion Point Analysis Error): {stats['skipped_analyze']}")
        
        # その他のスキップ
        total_skipped = (stats['skipped_existing'] + stats['skipped_template'] + 
                        stats['skipped_generate'] + stats['skipped_analyze'])
        other_skips = total_elements - stats['processed'] - total_skipped
        if other_skips > 0:
            print(f"  Skipped (Other reasons e.g., duplicate ID): {max(0, other_skips)}")
        
        print(f"File modified: {file_modified}")
        
        if stats.get('last_exception'):
            print(f"An error occurred: {stats['last_exception']}")
        
        print("-" * 80)

    # _process_element は空実装
    def _process_element(self, element: BaseElement, file_path: str, template: str, overwrite_doc: bool = False) -> None: pass

    def _format_doc(self, raw_doc: str) -> str:
        """OpenAI APIから生成された生のドキュメントをDoxygen形式に整形する
        
        生成されたドキュメントテキストを解析し、適切なDoxygen形式（/** ... */)に変換します。
        マークダウンのコードブロックを削除し、日本語の句読点を英語形式に変換するなどの
        整形処理も行います。
        
        Args:
            raw_doc: OpenAI APIから返された生のドキュメント文字列
            
        Returns:
            Doxygen形式に整形されたドキュメント文字列
        """
        # コンテンツのクリーンアップ
        content = self._clean_content(raw_doc)
        
        # 行に分割
        lines = content.splitlines()
        
        # すでにDoxygen形式かチェック
        if self._is_already_doxygen_format(lines):
            return self._format_existing_doxygen(lines)
        else:
            return self._format_new_doxygen(lines)

    def _clean_content(self, raw_doc: str) -> str:
        """生のドキュメントコンテンツをクリーンアップ"""
        # コードブロックの削除
        content = self._remove_code_blocks(raw_doc)
        
        # 日本語句読点の変換
        content = self._normalize_punctuation(content)
        
        return content.strip()

    def _remove_code_blocks(self, content: str) -> str:
        """マークダウンのコードブロックを削除"""
        # ```で囲まれたコードブロックを削除
        content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
        # 残った```を削除
        content = content.replace('```', '')
        return content

    def _normalize_punctuation(self, content: str) -> str:
        """日本語の句読点を英語形式に正規化"""
        replacements = {
            '、': ',',
            '。': '.',
            '：': ':',
            '（': '(',
            '）': ')',
            '　': ' '  # 全角スペースを半角に
        }
        
        for jp_char, en_char in replacements.items():
            content = content.replace(jp_char, en_char)
        
        return content

    def _is_already_doxygen_format(self, lines: List[str]) -> bool:
        """すでにDoxygen形式かどうかをチェック"""
        if not lines:
            return False
        
        first_line = lines[0].strip()
        last_line = lines[-1].strip() if len(lines) > 1 else ""
        
        return (first_line.startswith('/**') and 
                last_line.endswith('*/'))

    def _format_existing_doxygen(self, lines: List[str]) -> List[str]:
        """既存のDoxygen形式を整形"""
        formatted = []
        has_brief = False
        
        # 最初の行（/**）
        formatted.append(lines[0].rstrip())
        
        # 中間の行を処理
        for i in range(1, len(lines) - 1):
            formatted_line = self._format_doxygen_line(lines[i])
            formatted.append(formatted_line)
            
            if '@brief' in lines[i]:
                has_brief = True
        
        # 最後の行（*/）
        if len(lines) > 1:
            formatted.append(lines[-1].rstrip())
        
        return '\n'.join(formatted)

    def _format_doxygen_line(self, line: str) -> str:
        """Doxygenの1行を整形"""
        stripped_line = line.lstrip()
        indent = line[:-len(stripped_line)] if stripped_line else line
        
        # コンテンツ部分を抽出
        content_part = self._extract_content_part(stripped_line)
        
        # インデントと '* ' プレフィックスを追加
        return indent.rstrip() + ' * ' + content_part.rstrip()

    def _extract_content_part(self, stripped_line: str) -> str:
        """行からコンテンツ部分を抽出"""
        if stripped_line.startswith('* '):
            return stripped_line[2:]
        elif stripped_line.startswith('*'):
            return stripped_line[1:]
        else:
            return stripped_line

    def _format_new_doxygen(self, lines: List[str]) -> str:
        """新しいDoxygen形式のドキュメントを作成"""
        formatted = ['/**']
        has_brief = False
        first_content_line_added = False
        
        for line in lines:
            formatted_lines = self._process_doc_line(
                line, has_brief, first_content_line_added
            )
            
            for formatted_line, is_brief, is_content in formatted_lines:
                formatted.append(formatted_line)
                if is_brief:
                    has_brief = True
                if is_content:
                    first_content_line_added = True
        
        # @briefタグがない場合は追加
        if not has_brief and len(formatted) > 1:
            formatted.insert(1, ' * @brief Add brief description here.')
        
        # 末尾の空行を削除
        formatted = self._remove_trailing_empty_lines(formatted)
        
        # 終了タグを追加
        formatted.append(' */')
        
        return '\n'.join(formatted)

    def _process_doc_line(self, line: str, has_brief: bool, 
                        first_content_line_added: bool) -> List[Tuple[str, bool, bool]]:
        """ドキュメントの1行を処理
        
        Returns:
            List of tuples: (formatted_line, is_brief_line, is_content_line)
        """
        stripped_line = line.strip()
        
        # 空行の処理
        if not stripped_line:
            return [(' *', False, False)]
        
        # @briefタグがない最初のコンテンツ行
        if not has_brief and not stripped_line.startswith('@') and not first_content_line_added:
            return [(' * @brief ' + stripped_line, True, True)]
        
        # 通常の行
        is_brief = stripped_line.startswith('@brief')
        is_content = not stripped_line.startswith('@')
        
        return [(' * ' + stripped_line, is_brief, is_content)]

    def _remove_trailing_empty_lines(self, formatted: List[str]) -> List[str]:
        """末尾の空の ' * ' 行を削除"""
        while len(formatted) > 1 and formatted[-1] == ' *':
            formatted.pop()
        
        return formatted


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
            self._analyze_method_context(info, context)
        
        # パラメータの分析
        if isinstance(info.parameters, list) and info.parameters:
            self._analyze_parameters(info.parameters, context)
        
        # 戻り値の分析
        if isinstance(info.return_type, str) and info.return_type:
            self._analyze_return_type(info.return_type, info, context)
        
        # その他の特徴の検出
        if info.signature:
            self._analyze_signature_features(info.signature, context)
        
        return context

    def _analyze_method_context(self, info: FunctionElementInfo, context: Dict[str, Any]) -> None:
        """メソッドのコンテキスト情報を分析する"""
        parent_base = re.sub(r'<.*?>.*$', '', info.parent_type).strip()
        context['parent_type'] = parent_base
        
        m_name = info.name if info.name else ""
        
        # 同名メソッドが複数の型に実装されているかの識別
        self._check_common_method_names(m_name, parent_base, context)
        
        # メソッド名パターン認識
        self._analyze_method_name_pattern(m_name, parent_base, context)

    def _check_common_method_names(self, method_name: str, parent_type: str, context: Dict[str, Any]) -> None:
        """同名メソッドの存在をチェック"""
        same_name_methods = self.current_context.get('all_methods', {}).get(method_name, [])
        if len(same_name_methods) > 1:
            other_parents = list(set(m['parent_type'] for m in same_name_methods 
                                if m.get('parent_type') != parent_type))
            if other_parents: 
                context['common_method_name_in_types'] = other_parents
                context['is_common_method_name'] = True

    def _analyze_method_name_pattern(self, method_name: str, parent_type: str, context: Dict[str, Any]) -> None:
        """メソッド名のパターンを分析する"""
        # コンストラクタパターン
        if self._is_constructor_pattern(method_name):
            self._set_constructor_context(method_name, parent_type, context)
        # ゲッター/セッターパターン
        elif method_name.startswith('get_'):
            self._set_getter_context(method_name, context)
        elif method_name.startswith('set_'):
            self._set_setter_context(method_name, context)
        # 状態確認パターン
        elif self._is_boolean_getter_pattern(method_name):
            self._set_boolean_getter_context(method_name, context)
        # データ変換パターン
        elif self._is_conversion_pattern(method_name):
            self._set_conversion_context(method_name, context)
        # 操作種別パターン
        elif self._is_operation_pattern(method_name):
            self._set_operation_context(method_name, context)
        # 表示・ログ関連パターン
        elif self._is_display_pattern(method_name):
            self._set_display_context(method_name, context)
        # セキュリティ関連パターン
        elif self._is_security_pattern(method_name):
            self._set_security_context(method_name, context)

    def _is_constructor_pattern(self, method_name: str) -> bool:
        """コンストラクタパターンかどうかを判定"""
        return method_name == 'new' or method_name.startswith('new_') or method_name.endswith('_new')

    def _set_constructor_context(self, method_name: str, parent_type: str, context: Dict[str, Any]) -> None:
        """コンストラクタのコンテキストを設定"""
        context.update({
            'is_constructor': True, 
            'constructs_type': parent_type,
            'constructor_variant': method_name[4:] if method_name.startswith('new_') else 
                                method_name[:-4] if method_name.endswith('_new') else None
        })

    def _set_getter_context(self, method_name: str, context: Dict[str, Any]) -> None:
        """ゲッターのコンテキストを設定"""
        context.update({
            'is_getter': True, 
            'property_name': method_name[4:],
            'access_pattern': 'read'
        })

    def _set_setter_context(self, method_name: str, context: Dict[str, Any]) -> None:
        """セッターのコンテキストを設定"""
        context.update({
            'is_setter': True, 
            'property_name': method_name[4:], 
            'mutates_state': True,
            'access_pattern': 'write'
        })

    def _is_boolean_getter_pattern(self, method_name: str) -> bool:
        """真偽値ゲッターパターンかどうかを判定"""
        return any(method_name.startswith(prefix) for prefix in 
                ('is_', 'has_', 'can_', 'should_', 'will_', 'must_'))

    def _set_boolean_getter_context(self, method_name: str, context: Dict[str, Any]) -> None:
        """真偽値ゲッターのコンテキストを設定"""
        prefixes = ('is_', 'has_', 'can_', 'should_', 'will_', 'must_')
        prefix = next(p for p in prefixes if method_name.startswith(p))
        context.update({
            'is_boolean_getter': True, 
            'property_name': method_name[len(prefix):],
            'check_type': prefix[:-1]  # '_'を除去
        })

    def _is_conversion_pattern(self, method_name: str) -> bool:
        """変換パターンかどうかを判定"""
        return any(method_name.startswith(prefix) for prefix in ('to_', 'into_', 'from_', 'as_'))

    def _set_conversion_context(self, method_name: str, context: Dict[str, Any]) -> None:
        """変換メソッドのコンテキストを設定"""
        if method_name.startswith('to_') or method_name.startswith('into_'):
            prefix = 'to_' if method_name.startswith('to_') else 'into_'
            target_type = method_name[len(prefix):]
            context.update({
                'is_conversion': True,
                'conversion_type': 'to',
                'target_type': target_type,
                'consumes_self': method_name.startswith('into_')
            })
        elif method_name.startswith('from_'):
            source_type = method_name[5:]
            context.update({
                'is_conversion': True,
                'conversion_type': 'from',
                'source_type': source_type
            })
        elif method_name.startswith('as_'):
            view_type = method_name[3:]
            context.update({
                'is_conversion': True,
                'conversion_type': 'view',
                'view_type': view_type,
                'consumes_self': False
            })

    def _is_operation_pattern(self, method_name: str) -> bool:
        """操作パターンかどうかを判定"""
        operation_verbs = [
            'add_', 'remove_', 'delete_', 'update_', 'create_', 'destroy_', 
            'load_', 'save_', 'read_', 'write_', 'push_', 'pop_', 'enqueue_', 
            'dequeue_', 'insert_', 'append_', 'prepend_', 'clear_', 'reset_',
            'initialize_', 'finalize_', 'start_', 'stop_', 'pause_', 'resume_'
        ]
        return any(method_name.startswith(verb) for verb in operation_verbs)

    def _set_operation_context(self, method_name: str, context: Dict[str, Any]) -> None:
        """操作メソッドのコンテキストを設定"""
        operation_verbs = [
            'add_', 'remove_', 'delete_', 'update_', 'create_', 'destroy_', 
            'load_', 'save_', 'read_', 'write_', 'push_', 'pop_', 'enqueue_', 
            'dequeue_', 'insert_', 'append_', 'prepend_', 'clear_', 'reset_',
            'initialize_', 'finalize_', 'start_', 'stop_', 'pause_', 'resume_'
        ]
        
        verb = next(v for v in operation_verbs if method_name.startswith(v))
        operation_target = method_name[len(verb):]
        
        state_modifying_verbs = [
            'add_', 'remove_', 'delete_', 'update_', 'create_', 'destroy_',
            'save_', 'write_', 'push_', 'pop_', 'enqueue_', 'dequeue_', 
            'insert_', 'append_', 'prepend_', 'clear_', 'reset_', 
            'initialize_', 'finalize_', 'start_', 'stop_', 'pause_', 'resume_'
        ]
        
        io_verbs = ['load_', 'save_', 'read_', 'write_']
        
        context.update({
            'operation_type': verb[:-1],  # '_'を除去
            'operation_target': operation_target,
            'mutates_state': verb in state_modifying_verbs,
            'is_io_operation': verb in io_verbs
        })
        
        # ファイル操作として識別可能なパターン
        file_related_targets = [
            'file', 'files', 'config', 'configuration', 
            'settings', 'data', 'json', 'xml', 'yaml', 
            'toml', 'csv', 'database', 'db'
        ]
        if operation_target in file_related_targets:
            context.update({
                'is_file_operation': True,
                'file_type': operation_target
            })

    def _is_display_pattern(self, method_name: str) -> bool:
        """表示パターンかどうかを判定"""
        return any(method_name.startswith(verb) for verb in 
                ['print_', 'display_', 'show_', 'log_', 'trace_', 'debug_'])

    def _set_display_context(self, method_name: str, context: Dict[str, Any]) -> None:
        """表示メソッドのコンテキストを設定"""
        display_verbs = ['print_', 'display_', 'show_', 'log_', 'trace_', 'debug_']
        verb = next(v for v in display_verbs if method_name.startswith(v))
        display_target = method_name[len(verb):]
        context.update({
            'is_display_operation': True,
            'display_type': verb[:-1],  # '_'を除去
            'displays': display_target
        })

    def _is_security_pattern(self, method_name: str) -> bool:
        """セキュリティパターンかどうかを判定"""
        security_terms = [
            'encrypt', 'decrypt', 'hash', 'sign', 'verify', 'auth', 'password', 
            'credential', 'token', 'secret', 'secure', 'masked'
        ]
        return any(term in method_name for term in security_terms)

    def _set_security_context(self, method_name: str, context: Dict[str, Any]) -> None:
        """セキュリティメソッドのコンテキストを設定"""
        context.update({'is_security_related': True})
        
        security_operations = {
            'encrypt': 'encryption',
            'decrypt': 'decryption',
            'hash': 'hashing',
            'sign': 'signing',
            'verify': 'verification',
            'masked': 'masking',
            'mask': 'masking'
        }
        
        for term, operation in security_operations.items():
            if term in method_name:
                context.update({'security_operation': operation})
                break

    def _analyze_parameters(self, parameters: List[Dict[str, Any]], context: Dict[str, Any]) -> None:
        """パラメータを分析する"""
        param_details = []
        has_self = False
        pattern_params = self._initialize_pattern_params()
        
        for p in parameters:
            if isinstance(p, dict):
                p_name = p.get('name', '')
                p_type = p.get('type', '')
                param_details.append({'name': p_name, 'type': p_type})
                
                # self/&self/&mut selfパラメータの検出
                if p_name in ('self', '&self', '&mut self'):
                    has_self = True
                    self._analyze_self_parameter(p_name, context)
                
                # 特定のパラメータ名パターンの検出
                self._check_parameter_patterns(p_name, pattern_params)
                
                # 参照渡しパラメータの検出
                self._analyze_reference_parameters(p_type, context)
                
                # その他のパラメータ特性
                self._analyze_parameter_types(p_type, context)
            else:
                param_details.append({'name': 'unknown', 'type': 'unknown'})
        
        context['parameters_list'] = param_details
        
        if has_self:
            context['has_self_parameter'] = True
        
        # パラメータパターンの結果を反映
        self._apply_parameter_patterns(pattern_params, context)

    def _initialize_pattern_params(self) -> Dict[str, bool]:
        """パラメータパターンの初期化"""
        return {
            'key': False, 'value': False, 'path': False, 'id': False,
            'name': False, 'index': False, 'data': False, 'config': False,
            'options': False, 'callback': False, 'handler': False,
            'listener': False, 'observer': False, 'context': False,
            'state': False, 'result': False, 'error': False,
        }

    def _analyze_self_parameter(self, param_name: str, context: Dict[str, Any]) -> None:
        """selfパラメータの分析"""
        if param_name == '&mut self':
            context['has_mutable_self'] = True
        elif param_name == '&self':
            context['has_immutable_self'] = True
        else:
            context['has_owned_self'] = True

    def _check_parameter_patterns(self, param_name: str, pattern_params: Dict[str, bool]) -> None:
        """パラメータ名のパターンをチェック"""
        for param_pattern in pattern_params:
            if param_name == param_pattern or param_name.endswith(f'_{param_pattern}'):
                pattern_params[param_pattern] = True

    def _analyze_reference_parameters(self, param_type: str, context: Dict[str, Any]) -> None:
        """参照パラメータの分析"""
        if param_type.startswith('&mut '):
            context['has_mutable_reference_param'] = True
        elif param_type.startswith('&'):
            context['has_immutable_reference_param'] = True

    def _analyze_parameter_types(self, param_type: str, context: Dict[str, Any]) -> None:
        """パラメータの型を分析"""
        # ジェネリックパラメータの検出
        if 'T' in param_type or param_type.startswith(('Option<', 'Result<')):
            context['has_generic_param'] = True
        
        # コールバックパラメータの検出
        if 'Fn' in param_type or 'FnMut' in param_type or 'FnOnce' in param_type:
            context['has_callback_param'] = True

    def _apply_parameter_patterns(self, pattern_params: Dict[str, bool], context: Dict[str, Any]) -> None:
        """パラメータパターンの結果を適用"""
        for param_name, exists in pattern_params.items():
            if exists:
                context[f'has_{param_name}_parameter'] = True
                
                # 特定パラメータによる追加のコンテキスト
                if param_name == 'path':
                    context.update({'is_file_related': True})
                elif param_name in ('callback', 'handler', 'listener', 'observer'):
                    context.update({'is_event_related': True})

    def _analyze_return_type(self, return_type: str, info: FunctionElementInfo, context: Dict[str, Any]) -> None:
        """戻り値の型を分析する"""
        context['return_type_str'] = return_type
        
        # Result型の分析
        if return_type.startswith(('Result<', 'std::result::Result<')):
            self._analyze_result_type(return_type, context)
        # Option型の分析
        elif return_type.startswith(('Option<', 'std::option::Option<')):
            self._analyze_option_type(return_type, context)
        # Self型
        elif return_type == 'Self' and 'parent_type' in context:
            context['returns_self_type'] = True
        # bool型
        elif return_type == 'bool':
            self._analyze_bool_return(info, context)
        # コレクション型
        elif self._is_collection_type(return_type):
            self._analyze_collection_type(return_type, context)
        # スマートポインタ型
        elif self._is_smart_pointer_type(return_type):
            self._analyze_smart_pointer_type(return_type, context)
        # 文字列型
        elif return_type.startswith('String') or return_type.startswith('&str'):
            context['returns_string'] = True
        # 数値型
        elif self._is_numeric_type(return_type):
            self._analyze_numeric_type(return_type, context)
        # Unit型
        elif return_type == '()':
            context['returns_unit'] = True
        # トレイトオブジェクト
        elif return_type.startswith('impl '):
            self._analyze_impl_trait(return_type, context)
        elif return_type.startswith('dyn '):
            self._analyze_dyn_trait(return_type, context)
        
        # 非同期・ストリーム関連
        self._check_async_stream_types(return_type, info, context)
        
        # エラー関連
        if 'error' in return_type.lower() or 'exception' in return_type.lower():
            context['is_error_related'] = True

    def _analyze_result_type(self, return_type: str, context: Dict[str, Any]) -> None:
        """Result型を分析"""
        context['returns_result'] = True
        match = re.search(r'Result<(.*?)(?:,\s*(.*?))?>', return_type)
        if match:
            context['result_ok_type'] = match.group(1).strip()
            if match.group(2):
                context['result_err_type'] = match.group(2).strip()

    def _analyze_option_type(self, return_type: str, context: Dict[str, Any]) -> None:
        """Option型を分析"""
        context['returns_option'] = True
        match = re.search(r'Option<(.*)>', return_type)
        if match:
            context['option_some_type'] = match.group(1).strip()

    def _analyze_bool_return(self, info: FunctionElementInfo, context: Dict[str, Any]) -> None:
        """bool戻り値を分析"""
        context['returns_boolean'] = True
        if info.name and info.name.startswith(('is_', 'has_', 'can_', 'should_', 'will_', 'must_')):
            context['is_predicate_function'] = True

    def _is_collection_type(self, return_type: str) -> bool:
        """コレクション型かどうかを判定"""
        collection_prefixes = [
            'Vec<', 'std::vec::Vec<',
            'HashMap<', 'std::collections::HashMap<',
            'HashSet<', 'std::collections::HashSet<',
            'BTreeMap<', 'std::collections::BTreeMap<',
            'BTreeSet<', 'std::collections::BTreeSet<'
        ]
        return any(return_type.startswith(prefix) for prefix in collection_prefixes)

    def _analyze_collection_type(self, return_type: str, context: Dict[str, Any]) -> None:
        """コレクション型を分析"""
        context['returns_collection'] = True
        
        collection_mappings = {
            'Vec<': ('vector', r'Vec<(.*)>'),
            'std::vec::Vec<': ('vector', r'Vec<(.*)>'),
            'HashMap<': ('hash_map', r'HashMap<(.*),\s*(.*)>'),
            'std::collections::HashMap<': ('hash_map', r'HashMap<(.*),\s*(.*)>'),
            'HashSet<': ('hash_set', r'HashSet<(.*)>'),
            'std::collections::HashSet<': ('hash_set', r'HashSet<(.*)>'),
            'BTreeMap<': ('btree_map', r'BTreeMap<(.*),\s*(.*)>'),
            'std::collections::BTreeMap<': ('btree_map', r'BTreeMap<(.*),\s*(.*)>'),
            'BTreeSet<': ('btree_set', r'BTreeSet<(.*)>'),
            'std::collections::BTreeSet<': ('btree_set', r'BTreeSet<(.*)>')
        }
        
        for prefix, (collection_type, pattern) in collection_mappings.items():
            if return_type.startswith(prefix):
                context['collection_type'] = collection_type
                match = re.search(pattern, return_type)
                if match:
                    if collection_type in ('hash_map', 'btree_map'):
                        context['map_key_type'] = match.group(1).strip()
                        context['map_value_type'] = match.group(2).strip()
                    else:
                        context['collection_element_type'] = match.group(1).strip()
                break

    def _is_smart_pointer_type(self, return_type: str) -> bool:
        """スマートポインタ型かどうかを判定"""
        return any(return_type.startswith(prefix) for prefix in 
                ['Box<', 'Arc<', 'Rc<', 'Ref<', 'RefMut<'])

    def _analyze_smart_pointer_type(self, return_type: str, context: Dict[str, Any]) -> None:
        """スマートポインタ型を分析"""
        if return_type.startswith('Box<'):
            context['returns_boxed'] = True
            match = re.search(r'Box<(.*)>', return_type)
            if match:
                context['boxed_type'] = match.group(1).strip()
        
        elif return_type.startswith('Arc<'):
            context['returns_thread_safe'] = True
            context['returns_shared'] = True
            match = re.search(r'Arc<(.*)>', return_type)
            if match:
                context['shared_type'] = match.group(1).strip()
        
        elif return_type.startswith('Rc<'):
            context['returns_shared'] = True
            match = re.search(r'Rc<(.*)>', return_type)
            if match:
                context['shared_type'] = match.group(1).strip()
        
        elif return_type.startswith(('Ref<', 'RefMut<')):
            context['returns_cell_ref'] = True
            context['returns_mutable'] = return_type.startswith('RefMut<')
            match = re.search(r'Ref(?:Mut)?<(.*)>', return_type)
            if match:
                context['ref_type'] = match.group(1).strip()

    def _is_numeric_type(self, return_type: str) -> bool:
        """数値型かどうかを判定"""
        integer_types = ['u8', 'u16', 'u32', 'u64', 'u128', 'usize', 
                        'i8', 'i16', 'i32', 'i64', 'i128', 'isize']
        float_types = ['f32', 'f64']
        return return_type in integer_types or return_type in float_types

    def _analyze_numeric_type(self, return_type: str, context: Dict[str, Any]) -> None:
        """数値型を分析"""
        integer_types = ['u8', 'u16', 'u32', 'u64', 'u128', 'usize', 
                        'i8', 'i16', 'i32', 'i64', 'i128', 'isize']
        float_types = ['f32', 'f64']
        
        if return_type in integer_types:
            context['returns_integer'] = True
            context['integer_type'] = return_type
        elif return_type in float_types:
            context['returns_float'] = True
            context['float_type'] = return_type

    def _analyze_impl_trait(self, return_type: str, context: Dict[str, Any]) -> None:
        """impl Trait型を分析"""
        context['returns_trait_object'] = True
        match = re.search(r'impl (.*)', return_type)
        if match:
            context['trait_type'] = match.group(1).strip()

    def _analyze_dyn_trait(self, return_type: str, context: Dict[str, Any]) -> None:
        """dyn Trait型を分析"""
        context['returns_dynamic_trait'] = True
        match = re.search(r'dyn (.*)', return_type)
        if match:
            context['dynamic_trait_type'] = match.group(1).strip()

    def _check_async_stream_types(self, return_type: str, info: FunctionElementInfo, context: Dict[str, Any]) -> None:
        """非同期・ストリーム関連の型をチェック"""
        if return_type.startswith(('Future<', 'Pin<Box<dyn Future<')) or 'async' in info.signature:
            context['is_async'] = True
        
        if 'stream' in return_type.lower() or return_type.startswith(('Stream<', 'impl Stream<')):
            context['returns_stream'] = True

    def _analyze_signature_features(self, signature: str, context: Dict[str, Any]) -> None:
        """シグネチャの特徴を分析"""
        feature_mappings = {
            'pub ': 'is_public',
            ' unsafe ': 'is_unsafe',
            ' async ': 'is_async',
            ' const ': 'is_const',
            '#[derive(': 'has_derive_attribute',
            '#[test]': 'is_test_function',
            '#[cfg(': 'has_conditional_compilation'
        }
        
        for pattern, context_key in feature_mappings.items():
            if pattern in signature:
                context[context_key] = True

    def _prepare_code_with_context(self, element: BaseElement, context_info: Dict[str, Any]) -> str:
        """コード要素とコンテキスト情報からドキュメント生成用のプロンプトを構築する
        
        要素の基本情報（型、名前、定義位置など）とコンテキスト分析結果を組み合わせて、
        OpenAI APIに送信するためのプロンプトを生成します。
        
        Args:
            element: ドキュメントを生成する対象のコード要素
            context_info: 要素の分析結果を含むコンテキスト情報
            
        Returns:
            OpenAI APIに送信するためのプロンプト文字列
        """
        if element.info is None or not element.info.source_code:
            display_name = self._get_display_name(element)
            return f"// Error: Source code missing for {display_name}"
        
        # 基本コメントの構築
        comments = self._build_basic_comments(element)
        
        # 要素タイプ別の詳細情報を追加
        self._add_element_specific_comments(element, comments)
        
        # コンテキスト情報の追加
        if context_info:
            self._add_context_comments(context_info, comments)
        
        # 周辺コード文脈情報の追加
        self._add_project_context_comments(comments)
        
        # プロンプトの構築
        prompt = self._build_prompt(comments, element.info.source_code)
        
        # AIシステムへの追加ヒントを追加
        prompt = self._add_ai_hints(element, context_info, prompt)
        
        return prompt

    def _build_basic_comments(self, element: BaseElement) -> List[str]:
        """基本的なコメント情報を構築"""
        element_type = element.__class__.__name__
        display_name = self._get_display_name(element)
        element_id = element.get_unique_id()
        file_path = element.info.file_path or 'N/A'
        start_line = element.info.start_line
        
        return [
            f"// Element Type: {element_type}",
            f"// Element Name: {display_name}",
            f"// Element ID: {element_id}",
            f"// File Path: {file_path}",
            f"// Start Line: {start_line}",
        ]

    def _add_element_specific_comments(self, element: BaseElement, comments: List[str]) -> None:
        """要素タイプに応じた詳細コメントを追加"""
        info = element.info
        
        if isinstance(info, FunctionElementInfo):
            self._add_function_comments(info, comments)
        elif isinstance(info, StructElementInfo):
            self._add_struct_comments(info, comments)
        elif isinstance(info, EnumElementInfo):
            self._add_enum_comments(info, comments)
        elif isinstance(info, TraitElementInfo):
            self._add_trait_comments(info, comments)
        elif isinstance(info, ModuleElementInfo):
            self._add_module_comments(info, comments)

    def _add_function_comments(self, info: FunctionElementInfo, comments: List[str]) -> None:
        """関数の詳細コメントを追加"""
        signature = info.signature or 'N/A'
        return_type = info.return_type or '()'
        
        comments.extend([
            f"// Signature: {signature}",
            f"// Returns: {return_type}",
        ])
        
        # パラメータ情報
        if info.parameters:
            self._add_parameter_comments(info.parameters, comments)
        
        # メソッド関連情報
        if info.is_impl_method:
            self._add_method_comments(info, comments)
        
        # 関数の特性
        if hasattr(info, 'signature') and info.signature:
            self._add_function_characteristics(info.signature, comments)

    def _add_parameter_comments(self, parameters: List[Dict[str, Any]], comments: List[str]) -> None:
        """パラメータのコメントを追加"""
        comments.append("// Parameters:")
        for i, param in enumerate(parameters):
            if isinstance(param, dict):
                param_name = param.get('name', '?')
                param_type = param.get('type', '?')
                is_mut = '&mut ' in param_type or 'mut ' in param_name
                is_ref = param_type.startswith('&') or param_name.startswith('&')
                
                param_desc = f"//   {i+1}. {param_name}: {param_type}"
                if is_mut:
                    param_desc += " (mutable)"
                elif is_ref:
                    param_desc += " (reference)"
                comments.append(param_desc)

    def _add_method_comments(self, info: FunctionElementInfo, comments: List[str]) -> None:
        """メソッド関連のコメントを追加"""
        comments.append(f"// Parent Type: {info.parent_type or 'N/A'}")
        
        if info.is_trait_method and info.metadata and info.metadata.get('trait_name'):
            comments.append(f"// Implemented Trait: {info.metadata.get('trait_name', 'N/A')}")

    def _add_function_characteristics(self, signature: str, comments: List[str]) -> None:
        """関数の特性コメントを追加"""
        if ' pub ' in signature or signature.startswith('pub '):
            comments.append("// Visibility: Public")
        else:
            comments.append("// Visibility: Private/Internal")
        
        characteristics = [
            (' unsafe ', "// Safety: Unsafe function"),
            (' async ', "// Concurrency: Asynchronous function"),
            (' const ', "// Evaluation: Compile-time constant function")
        ]
        
        for pattern, comment in characteristics:
            if pattern in signature:
                comments.append(comment)

    def _add_struct_comments(self, info: StructElementInfo, comments: List[str]) -> None:
        """構造体の詳細コメントを追加"""
        visibility = self._get_visibility(info)
        comments.append(f"// Definition: {visibility}struct {info.name or 'Anonymous'}")
        
        if info.type_params:
            comments.append(f"// Type Parameters: <{', '.join(info.type_params)}>")
        
        if info.fields:
            self._add_field_comments(info.fields, comments)
        
        if hasattr(info, 'impl_traits') and info.impl_traits:
            comments.append(f"// Implements: {', '.join(info.impl_traits)}")

    def _add_field_comments(self, fields: List[Dict[str, Any]], comments: List[str]) -> None:
        """フィールドのコメントを追加"""
        comments.append("// Fields:")
        for i, field in enumerate(fields):
            if isinstance(field, dict):
                field_name = field.get('name', '?')
                field_type = field.get('type', '?')
                visibility = "pub " if field.get('is_pub') else ""
                comments.append(f"//   {i+1}. {visibility}{field_name}: {field_type}")

    def _add_enum_comments(self, info: EnumElementInfo, comments: List[str]) -> None:
        """列挙型の詳細コメントを追加"""
        visibility = self._get_visibility(info)
        comments.append(f"// Definition: {visibility}enum {info.name or 'Anonymous'}")
        
        if info.type_params:
            comments.append(f"// Type Parameters: <{', '.join(info.type_params)}>")
        
        if info.variants:
            self._add_variant_comments(info.variants, comments)
        
        if hasattr(info, 'impl_traits') and info.impl_traits:
            comments.append(f"// Implements: {', '.join(info.impl_traits)}")

    def _add_variant_comments(self, variants: List[Dict[str, Any]], comments: List[str]) -> None:
        """バリアントのコメントを追加"""
        comments.append("// Variants:")
        for i, variant in enumerate(variants):
            if isinstance(variant, dict):
                variant_name = variant.get('name', '?')
                variant_type = variant.get('type', '')
                if variant_type:
                    comments.append(f"//   {i+1}. {variant_name}({variant_type})")
                else:
                    comments.append(f"//   {i+1}. {variant_name}")

    def _add_trait_comments(self, info: TraitElementInfo, comments: List[str]) -> None:
        """トレイトの詳細コメントを追加"""
        visibility = self._get_visibility(info)
        comments.append(f"// Definition: {visibility}trait {info.name or 'Anonymous'}")
        
        if info.type_params:
            comments.append(f"// Type Parameters: <{', '.join(info.type_params)}>")
        
        if info.super_traits:
            comments.append(f"// Super Traits: {', '.join(info.super_traits)}")
        
        if info.associated_types:
            comments.append(f"// Associated Types: {', '.join(info.associated_types)}")
        
        if info.methods:
            self._add_trait_method_comments(info.methods, comments)

    def _add_trait_method_comments(self, methods: List[Dict[str, Any]], comments: List[str]) -> None:
        """トレイトメソッドのコメントを追加"""
        comments.append("// Required Methods:")
        for i, method in enumerate(methods):
            if isinstance(method, dict):
                method_name = method.get('name', '?')
                method_sig = method.get('signature', '?')
                comments.append(f"//   {i+1}. {method_name}: {method_sig}")

    def _add_module_comments(self, info: ModuleElementInfo, comments: List[str]) -> None:
        """モジュールの詳細コメントを追加"""
        module_kind = 'Inline Module' if info.is_inline else 'File Module'
        visibility = self._get_visibility(info)
        
        comments.append(f"// Definition: {visibility}mod {info.name or 'Anonymous'}")
        comments.append(f"// Module Type: {module_kind}")
        
        if not info.is_inline and info.file_path:
            comments.append(f"// Module File: {os.path.basename(info.file_path)}")

    def _get_visibility(self, info: Any) -> str:
        """要素の可視性を取得"""
        if hasattr(info, 'signature') and info.signature:
            return "pub " if "pub " in info.signature else ""
        return ""

    def _add_context_comments(self, context_info: Dict[str, Any], comments: List[str]) -> None:
        """コンテキスト情報のコメントを追加"""
        comments.append("\n// Context Information:")
        
        # コンテキスト情報を分類
        categorized = self._categorize_context_info(context_info)
        
        # カテゴリー別にコメントを追加
        self._add_categorized_comments(categorized, comments)

    def _categorize_context_info(self, context_info: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """コンテキスト情報をカテゴリー別に分類"""
        categories = {
            'function_context': {},
            'param_context': {},
            'return_context': {},
            'type_context': {},
            'behavior_context': {},
            'misc_context': {}
        }
        
        # 関数特性のキー
        function_keys = {
            'is_constructor', 'is_getter', 'is_setter', 'is_boolean_getter',
            'is_conversion', 'is_public', 'is_unsafe', 'is_async', 'is_const',
            'is_display_operation', 'is_security_related', 'is_file_operation',
            'is_file_related', 'is_event_related', 'is_io_operation',
            'is_predicate_function', 'constructor_variant', 'operation_type',
            'operation_target', 'conversion_type', 'property_name'
        }
        
        # 型関連のキー
        type_keys = {
            'parent_type', 'constructs_type', 'target_type', 'source_type',
            'view_type', 'common_method_name_in_types', 'is_common_method_name'
        }
        
        # 動作関連のキー
        behavior_keys = {
            'mutates_state', 'consumes_self', 'has_mutable_self',
            'has_immutable_self', 'has_owned_self', 'access_pattern',
            'check_type', 'display_type', 'displays', 'security_operation',
            'file_type'
        }
        
        for k, v in context_info.items():
            if k in function_keys:
                categories['function_context'][k] = v
            elif k.startswith('has_') and k.endswith('_parameter') or k in ['parameters_list',
                                                                            'has_mutable_reference_param',
                                                                            'has_immutable_reference_param',
                                                                            'has_generic_param',
                                                                            'has_callback_param']:
                categories['param_context'][k] = v
            elif k.startswith('returns_') or k.endswith('_type') and not k in type_keys:
                categories['return_context'][k] = v
            elif k in type_keys:
                categories['type_context'][k] = v
            elif k in behavior_keys:
                categories['behavior_context'][k] = v
            else:
                categories['misc_context'][k] = v
        
        return categories

    def _add_categorized_comments(self, categorized: Dict[str, Dict[str, Any]], comments: List[str]) -> None:
        """カテゴリー別にコメントを追加"""
        category_names = {
            'function_context': "Function Characteristics",
            'param_context': "Parameter Characteristics",
            'return_context': "Return Value Characteristics",
            'type_context': "Type Relationships",
            'behavior_context': "Behavioral Characteristics",
            'misc_context': "Additional Context"
        }
        
        for category, items in categorized.items():
            if items:
                comments.append(f"// {category_names[category]}:")
                self._add_context_items(items, comments, category)

    def _add_context_items(self, items: Dict[str, Any], comments: List[str], category: str) -> None:
        """コンテキストアイテムをコメントに追加"""
        for k, v in items.items():
            if k == 'parameters_list' and category == 'param_context':
                continue  # パラメータリストは別途処理済み
            
            if isinstance(v, bool) and v:
                formatted_key = self._format_context_key(k, category)
                comments.append(f"//   - {formatted_key}")
            else:
                formatted_value = self._format_context_value(v)
                formatted_key = self._format_context_key(k, category)
                comments.append(f"//   - {formatted_key}: {formatted_value}")

    def _format_context_key(self, key: str, category: str) -> str:
        """コンテキストキーをフォーマット"""
        if category == 'param_context' and key.startswith('has_') and key.endswith('_parameter'):
            cleaned = key.replace('has_', '').replace('_parameter', '')
            return f"Has {cleaned} parameter"
        elif category == 'return_context' and key.startswith('returns_'):
            cleaned = key.replace('returns_', '')
            return f"Returns {cleaned}"
        else:
            # アンダースコアをスペースに変換し、適切に大文字化
            words = key.replace('_', ' ').split()
            formatted_words = []
            for i, word in enumerate(words):
                if i == 0 or word not in ['is', 'has', 'returns']:
                    formatted_words.append(word.capitalize())
                else:
                    formatted_words.append(word)
            return ' '.join(formatted_words)

    def _format_context_value(self, value: Any) -> str:
        """コンテキスト値をフォーマット"""
        try:
            v_str = json.dumps(value, ensure_ascii=False, indent=None, separators=(',', ':'))
        except TypeError:
            v_str = str(value)
        
        max_len = 100
        if len(v_str) > max_len:
            return f"{v_str[:max_len]}..."
        return v_str

    def _add_project_context_comments(self, comments: List[str]) -> None:
        """プロジェクトコンテキストのコメントを追加"""
        try:
            if hasattr(self, 'current_context') and self.current_context.get('all_type_names'):
                type_names = list(self.current_context.get('all_type_names'))
                if type_names:
                    comments.append("\n// Project Context:")
                    type_list = ', '.join(sorted(type_names)[:10])
                    if len(type_names) > 10:
                        type_list += ' (and more...)'
                    comments.append(f"//   - Known Types in File: {type_list}")
        except Exception:
            # エラーが発生しても続行
            pass

    def _build_prompt(self, comments: List[str], source_code: str) -> str:
        """コメントとソースコードからプロンプトを構築"""
        return "\n".join(comments) + "\n\n```rust\n" + source_code + "\n```"

    def _add_ai_hints(self, element: BaseElement, context_info: Dict[str, Any], prompt: str) -> str:
        """AI用のヒントを追加"""
        hint_comments = []
        
        if isinstance(element.info, FunctionElementInfo):
            self._add_function_hints(context_info, hint_comments)
        elif isinstance(element.info, (StructElementInfo, EnumElementInfo)):
            self._add_struct_enum_hints(element, hint_comments)
        
        if hint_comments:
            prompt += "\n\n" + "\n".join(hint_comments)
        
        return prompt

    def _add_function_hints(self, context_info: Dict[str, Any], hint_comments: List[str]) -> None:
        """関数用のヒントを追加"""
        hints = {
            'returns_result': "// Hint: This function returns a Result type. Consider documenting both success and error cases.",
            'returns_option': "// Hint: This function returns an Option type. Consider documenting both Some and None cases.",
            'is_async': "// Hint: This is an asynchronous function. Consider mentioning any potential await points or completion behavior.",
            'is_unsafe': "// Hint: This is an unsafe function. Document the safety requirements and invariants that callers must uphold."
        }
        
        for context_key, hint in hints.items():
            if context_info.get(context_key):
                hint_comments.append(hint)

    def _add_struct_enum_hints(self, element: BaseElement, hint_comments: List[str]) -> None:
        """構造体/列挙型用のヒントを追加"""
        info = element.info
        element_type = element.__class__.__name__.lower()
        
        fields_count = len(info.fields) if isinstance(info, StructElementInfo) and info.fields else 0
        variants_count = len(info.variants) if isinstance(info, EnumElementInfo) and info.variants else 0
        
        if fields_count > 5 or variants_count > 5:
            hint_comments.append(
                f"// Hint: This {element_type} has many fields/variants. "
                "Consider grouping them logically in the documentation."
            )

    def get_usage_stats(self) -> Dict[str, int]:
        """OpenAI APIの使用統計を取得する
        
        APIクライアントから使用したトークン数などの統計情報を取得します。
        
        Returns:
            APIの使用統計情報（プロンプトトークン数、完了トークン数、合計トークン数）
        """
        if hasattr(self.openai_client, 'get_usage_stats') and callable(self.openai_client.get_usage_stats):
             return self.openai_client.get_usage_stats()
        else: return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
