"""
TypeScript固有のドキュメント生成処理
"""
import os
import re
from typing import Dict, List, Optional, Union, Any

from common.base_generator import BaseDocGenerator, BaseElement, InsertionPoint
from common.openai_client import OpenAIClient
from common.file_utils import read_file, write_file, is_empty_or_comment_only
from languages.typescript.elements import (
    FunctionElement, ClassElement, InterfaceElement, 
    TypeElement, EnumElement, ModuleElement
)
from languages.typescript.parser import TypeScriptParser

class TypeScriptDocGenerator(BaseDocGenerator):
    """TypeScriptコードのJSDocコメント生成を管理するクラス"""

    def __init__(self, openai_endpoint: str, openai_key: str, deployment_name: str):
        """
        Args:
            openai_endpoint (str): OpenAI APIのエンドポイント
            openai_key (str): OpenAI APIキー
            deployment_name (str): デプロイメント名
        """
        self.openai_client = OpenAIClient(openai_endpoint, openai_key, deployment_name)
        self.parser = TypeScriptParser()
        self.system_prompt = (
            "あなたはTypeScriptドキュメント生成の専門家です。"
            "JSDoc形式のドキュメントコメントを生成してください。"
        )

    def process_file(self, file_path: str, templates: Dict[str, str], 
                     overwrite_doc: bool = False) -> None:
        """ファイルを処理し、JSDocコメントを生成・挿入する

        Args:
            file_path (str): 処理対象のTypeScriptファイルパス
            templates (Dict[str, str]): テンプレート辞書 ("function", "class", "interface", "type", "enum", "module" のキーを持つ)
            overwrite_doc (bool, optional): 既存のJSDocコメントを上書きするかどうか. Defaults to False.
        """
        # ファイルが空かどうかチェック
        if os.path.getsize(file_path) == 0:
            print(f"Skipping empty file: {file_path}")
            return

        source, source_lines = read_file(file_path)
        
        # 空白文字やコメントのみのファイルをチェック
        if is_empty_or_comment_only(source):
            print(f"Skipping file with no code: {file_path}")
            return

        # モジュールレベルのドキュメント処理
        module_element = self.parser.extract_module_info(source, source_lines)
        
        # モジュールレベルのドキュメントが存在しないか上書きする場合のみ処理
        has_docstring = self._check_existing_module_docstring(source_lines)
        if not has_docstring or overwrite_doc:
            if "module" in templates:
                self._process_element(module_element, file_path, templates["module"])

        # 各要素を処理
        elements = self.parser.parse_file(file_path)
        
        # 要素の種類ごとにグループ化
        element_groups = {
            ClassElement: [],
            InterfaceElement: [],
            TypeElement: [],
            EnumElement: [],
            FunctionElement: []
        }
        
        for element in elements:
            for element_type in element_groups:
                if isinstance(element, element_type):
                    element_groups[element_type].append(element)
                    break
        
        # 優先順位に従って処理（型定義 -> クラス・インターフェース -> 関数）
        # 1. まず型定義と列挙型（他の要素から参照される可能性がある）
        self._process_elements_by_type(element_groups[TypeElement], file_path, templates, overwrite_doc, "type")
        self._process_elements_by_type(element_groups[EnumElement], file_path, templates, overwrite_doc, "enum")
        
        # 2. クラスとインターフェース
        self._process_elements_by_type(element_groups[ClassElement], file_path, templates, overwrite_doc, "class")
        self._process_elements_by_type(element_groups[InterfaceElement], file_path, templates, overwrite_doc, "interface")
        
        # 3. 関数
        self._process_elements_by_type(element_groups[FunctionElement], file_path, templates, overwrite_doc, "function")

    def _process_elements_by_type(self, elements, file_path, templates, overwrite_doc, template_key):
        """指定したタイプの要素を処理する"""
        if template_key not in templates:
            return
            
        template = templates[template_key]
        for element in elements:
            try:
                # 既存のドキュメントをチェック
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                insertion = element.analyze_insertion_point(lines)
                if not overwrite_doc and insertion.has_existing_doc():
                    continue
                
                self._process_element(element, file_path, template)
            except Exception as e:
                print(f"Error processing {element.info.name}: {str(e)}")

    def _process_element(self, element: BaseElement, file_path: str, template: str) -> None:
        """個別のコード要素を処理する"""
        # 変更前のコードを表示
        print(f"\nProcessing {element.__class__.__name__}: {element.info.name}")
        print("\nSource code before:")
        print("="*80)
        print(element.info.code)
        print("="*80)

        # JSDocコメントを生成
        jsdoc = self.openai_client.generate_doc(
            element.info.code, template, self.system_prompt
        )
        formatted_jsdoc = self._format_doc(jsdoc)

        # 生成されたコメントを表示
        print("\nGenerated JSDoc comment:")
        print("="*80)
        print(formatted_jsdoc)
        print("="*80)

        # ファイルを読み込み
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # コメントを挿入
        insertion = element.analyze_insertion_point(lines)
        original_length = len(lines)
        self._insert_doc(lines, insertion, formatted_jsdoc)

        # 変更後のコードを表示
        print("\nSource code after:")
        print("="*80)

        if isinstance(element, ModuleElement):
            # モジュールの場合は変更された部分（先頭部分）のみを表示
            preview_lines = 30
            preview = ''.join(lines[:preview_lines])
            print(preview)
            if len(lines) > preview_lines:
                print(f"\n... (and {len(lines) - preview_lines} more lines)")
        else:
            # 他の要素の場合は、要素定義と少し後の行を表示
            end_line = insertion.def_line + 20  # プレビューとして20行表示
            print(''.join(lines[max(0, insertion.def_line-2):min(end_line, len(lines))]))
        
        print("="*80)

        # ファイルに書き戻す
        write_file(file_path, lines)

    def _format_doc(self, raw_doc: str) -> str:
        """JSDocコメントを整形する

        Args:
            raw_doc (str): OpenAI APIから返された生のJSDoc

        Returns:
            str: 整形されたJSDoc
        """
        # すべてのコードブロックマーカーを検出して除去
        content = re.sub(r'```(?:javascript|typescript|js|ts)?\n?', '', raw_doc).strip()
        
        # 既存のJSDocコメントを検出
        jsdoc_pattern = r'/\*\*([\s\S]*?)\*/'
        jsdoc_match = re.search(jsdoc_pattern, content)
        
        if jsdoc_match:
            # JSDocコメントが既に含まれている場合、それを抽出して整形
            jsdoc_content = jsdoc_match.group(0)
            
            # 行を分割して整形
            lines = jsdoc_content.splitlines()
            formatted_lines = []
            
            for i, line in enumerate(lines):
                stripped_line = line.strip()
                
                # 最初の行と最後の行は保持
                if i == 0:
                    formatted_lines.append('/**')
                elif i == len(lines) - 1:
                    formatted_lines.append(' */')
                else:
                    if stripped_line and not stripped_line.startswith('*'):
                        # 先頭に * がない行には追加
                        formatted_lines.append(' * ' + stripped_line)
                    elif stripped_line.startswith('*'):
                        # * の後にスペースがない場合は追加
                        if len(stripped_line) > 1 and stripped_line[1] != ' ':
                            formatted_lines.append(' * ' + stripped_line[1:])
                        else:
                            formatted_lines.append(' ' + stripped_line)
                    else:
                        # 空行は * のみの行に
                        formatted_lines.append(' *')
            
            content = '\n'.join(formatted_lines)
        else:
            # JSDocコメントが含まれていない場合、新しく作成
            lines = content.splitlines()
            formatted_lines = []
            
            # JSDoc形式に整形
            formatted_lines.append('/**')
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('*'):
                    formatted_lines.append(' * ' + line)
                elif line.startswith('*'):
                    formatted_lines.append(' ' + line)
                else:
                    formatted_lines.append(' *')
            
            # 終了タグが含まれていなければ追加
            if not formatted_lines[-1].strip() == '*/':
                formatted_lines.append(' */')
            
            content = '\n'.join(formatted_lines)
        
        # 日本語テキストの正規化
        replacements = {
            '、': ',',
            '。': '.',
            '：': ':',
            '（': '(',
            '）': ')'
        }
        for jp, en in replacements.items():
            content = content.replace(jp, en)
        
        return content

    def _insert_doc(self, lines: List[str], insertion: InsertionPoint, doc: str) -> None:
        """JSDocコメントをファイルに挿入する

        Args:
            lines (List[str]): ファイルの行のリスト
            insertion (InsertionPoint): 挿入位置情報
            doc (str): 挿入するJSDoc
        """
        # 既存のコメントを削除
        if insertion.has_existing_doc():
            del lines[insertion.existing_doc_start:insertion.existing_doc_end + 1]
            # 挿入位置を調整
            shift = insertion.existing_doc_end - insertion.existing_doc_start + 1
            insertion.def_line -= shift
        
        # 新しいコメントを準備（インデント調整）
        jsdoc_lines = []
        for line in doc.split('\n'):
            if line.strip():
                jsdoc_lines.append(insertion.base_indent + line + '\n')
            else:
                jsdoc_lines.append('\n')
        
        # コメントを挿入
        lines[insertion.def_line:insertion.def_line] = jsdoc_lines

    def _check_existing_module_docstring(self, source_lines: List[str]) -> bool:
        """モジュールレベルのJSDocコメントが存在するかをチェック"""
        if not source_lines:
            return False
            
        # 空行をスキップ
        i = 0
        while i < len(source_lines) and not source_lines[i].strip():
            i += 1
            
        if i >= len(source_lines):
            return False
            
        # コメントの開始を確認
        return source_lines[i].strip().startswith('/**')

    def get_usage_stats(self) -> Dict[str, int]:
        """APIの使用統計を取得する

        Returns:
            Dict[str, int]: トークン使用量の統計
        """
        return self.openai_client.get_usage_stats()
