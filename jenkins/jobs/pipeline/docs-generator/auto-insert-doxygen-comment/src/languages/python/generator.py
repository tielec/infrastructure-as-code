"""
Python固有のドキュメント生成処理
"""
import os
from typing import Dict, List, Optional, Union, Any

from common.base_generator import BaseDocGenerator, BaseElement, InsertionPoint
from common.openai_client import OpenAIClient
from common.file_utils import read_file, write_file, is_empty_or_comment_only
from languages.python.elements import (
    FunctionElement, ClassElement, ModuleElement
)
from languages.python.parser import PythonParser

class PythonDocGenerator(BaseDocGenerator):
    """Pythonコードのdocstring生成を管理するクラス"""

    def __init__(self, openai_endpoint: str, openai_key: str, deployment_name: str):
        """
        Args:
            openai_endpoint (str): OpenAI APIのエンドポイント
            openai_key (str): OpenAI APIキー
            deployment_name (str): デプロイメント名
        """
        self.openai_client = OpenAIClient(openai_endpoint, openai_key, deployment_name)
        self.parser = PythonParser()
        self.system_prompt = (
            "あなたはPythonドキュメント生成の専門家です。"
            "Doxygen形式のdocstringを生成してください。"
        )

    def process_file(self, file_path: str, templates: Dict[str, str], 
                     overwrite_doc: bool = False) -> None:
        """ファイルを処理し、docstringを生成・挿入する

        Args:
            file_path (str): 処理対象のPythonファイルパス
            templates (Dict[str, str]): テンプレート辞書 ("class", "function", "module" のキーを持つ)
            overwrite_doc (bool, optional): 既存のdocstringを上書きするかどうか. Defaults to False.
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

        # モジュールレベルのdocstring処理
        module_element = self.parser.extract_module_info(source, source_lines)
        
        # モジュールレベルのdocstringが存在しないか上書きする場合のみ処理
        has_docstring = self._check_existing_module_docstring(source_lines)
        if not has_docstring or overwrite_doc:
            self._process_element(module_element, file_path, templates["module"])

        # クラスと関数の処理
        elements = self.parser.parse_file(file_path)
        for element in elements:
            try:
                # 既存のdocstringをチェック
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                insertion = element.analyze_insertion_point(lines)
                if not overwrite_doc and insertion.has_existing_doc():
                    continue
                
                template_key = "class" if isinstance(element, ClassElement) else "function"
                self._process_element(element, file_path, templates[template_key])
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

        # docstringを生成
        docstring = self.openai_client.generate_doc(
            element.info.code, template, self.system_prompt
        )
        formatted_docstring = self._format_doc(docstring)

        # 生成されたdocstringを表示
        print("\nGenerated docstring:")
        print("="*80)
        print(formatted_docstring)
        print("="*80)

        # ファイルを読み込み
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # docstringを挿入
        insertion = element.analyze_insertion_point(lines)
        original_length = len(lines)
        self._insert_doc(lines, insertion, formatted_docstring)

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
            # 関数/クラスの場合は定義から次の定義までを表示
            end_line = insertion.def_line
            base_indent_level = len(element.info.indent)
            
            while end_line < len(lines):
                current_line = lines[end_line]
                if current_line.strip():
                    current_indent = len(current_line) - len(current_line.lstrip())
                    if current_indent <= base_indent_level and end_line > insertion.def_line:
                        break
                end_line += 1

            print(''.join(lines[insertion.def_line:end_line]))
        
        print("="*80)

        # ファイルに書き戻す
        write_file(file_path, lines)

    def _format_doc(self, raw_doc: str) -> str:
        """生のdocstringを整形する

        Args:
            raw_doc (str): OpenAI APIから返された生のdocstring

        Returns:
            str: 整形されたdocstring
        """
        # マーカーの除去と文字列のクリーニング
        content = raw_doc.replace('```python', '').replace('```', '').strip()
        content = content.replace('"""!', '').replace('"""', '').strip()
        
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
        
        # 行に分割して整形
        lines = content.splitlines()
        formatted = ['"""!\n']
        
        for line in lines:
            # 空行または@で始まる行は特別処理
            if not line.strip() or line.strip().startswith('@'):
                formatted.append(line + '\n')
            else:
                # それ以外の行は末尾に\nを追加
                if not line.endswith('\\n'):
                    line += '\\n'
                formatted.append(line + '\n')
        
        formatted.append('"""')
        return ''.join(formatted)

    def _insert_doc(self, lines: List[str], insertion: InsertionPoint, doc: str) -> None:
        """docstringをファイルに挿入する

        Args:
            lines (List[str]): ファイルの行のリスト
            insertion (InsertionPoint): 挿入位置情報
            doc (str): 挿入するdocstring
        """
        # 既存のdocstringを削除
        if insertion.has_existing_doc():
            del lines[insertion.existing_doc_start:insertion.existing_doc_end + 1]
        
        # 新しいdocstringを準備（インデント調整）
        docstring_lines = []
        for line in doc.split('\n'):
            if line.strip():
                docstring_lines.append(insertion.base_indent + line + '\n')
            else:
                docstring_lines.append('\n')
        
        # docstringを挿入
        lines[insertion.body_start:insertion.body_start] = docstring_lines

    def _check_existing_module_docstring(self, source_lines: List[str]) -> bool:
        """モジュールレベルのdocstringが存在するかをチェック"""
        if not source_lines:
            return False
            
        # 空行をスキップ
        i = 0
        while i < len(source_lines) and not source_lines[i].strip():
            i += 1
            
        if i >= len(source_lines):
            return False
            
        # docstringをチェック
        line = source_lines[i].strip()
        return line.startswith('"""') or line.startswith("'''")

    def get_usage_stats(self) -> Dict[str, int]:
        """APIの使用統計を取得する

        Returns:
            Dict[str, int]: トークン使用量の統計
        """
        return self.openai_client.get_usage_stats()
