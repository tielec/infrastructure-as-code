"""
Shell固有のドキュメント生成処理
"""
import os
from typing import Dict, List, Optional, Union, Any

from common.base_generator import BaseDocGenerator, BaseElement, InsertionPoint
from common.openai_client import OpenAIClient
from common.file_utils import read_file, write_file, is_empty_or_comment_only
from languages.shell.elements import (
    FunctionElement, ScriptElement
)
from languages.shell.parser import ShellParser

class ShellDocGenerator(BaseDocGenerator):
    """シェルスクリプトのDoxygen生成を管理するクラス"""

    def __init__(self, openai_endpoint: str, openai_key: str, deployment_name: str):
        """
        Args:
            openai_endpoint (str): OpenAI APIのエンドポイント
            openai_key (str): OpenAI APIキー
            deployment_name (str): デプロイメント名
        """
        self.openai_client = OpenAIClient(openai_endpoint, openai_key, deployment_name)
        self.parser = ShellParser()
        self.system_prompt = (
            "あなたはシェルスクリプトのドキュメント生成の専門家です。"
            "Doxygen形式のコメントを生成してください。"
        )

    def process_file(self, file_path: str, templates: Dict[str, str], 
                     overwrite_doc: bool = False) -> None:
        """ファイルを処理し、Doxygenコメントを生成・挿入する

        Args:
            file_path (str): 処理対象のシェルスクリプトファイルパス
            templates (Dict[str, str]): テンプレート辞書 ("function", "script" のキーを持つ)
            overwrite_doc (bool, optional): 既存のDoxygenコメントを上書きするかどうか. Defaults to False.
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

        # スクリプト全体のDoxygen処理
        script_element = self.parser.extract_module_info(source, source_lines)
        self._process_element(script_element, file_path, templates["script"])

        # 関数の処理
        functions = self.parser.parse_file(file_path)
        for func in functions:
            try:
                # 既存のDoxygenをチェック
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                insertion = func.analyze_insertion_point(lines)
                if not overwrite_doc and insertion.has_existing_doc():
                    continue
                
                self._process_element(func, file_path, templates["function"])
            except Exception as e:
                print(f"Error processing {func.info.name}: {str(e)}")

    def _process_element(self, element: BaseElement, file_path: str, template: str) -> None:
        """個別のコード要素を処理する"""
        # 変更前のコードを表示
        print(f"\nProcessing {element.__class__.__name__}: {element.info.name}")
        print("\nSource code before:")
        print("="*80)
        print(element.info.code)
        print("="*80)

        # Doxygenコメントを生成
        doxygen = self.openai_client.generate_doc(
            element.info.code, template, self.system_prompt
        )
        formatted_doxygen = self._format_doc(doxygen)

        # 生成されたコメントを表示
        print("\nGenerated Doxygen comment:")
        print("="*80)
        print(formatted_doxygen)
        print("="*80)

        # ファイルを読み込み
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # コメントを挿入
        insertion = element.analyze_insertion_point(lines)
        self._insert_doc(lines, insertion, formatted_doxygen)

        # 変更後のコードを表示
        print("\nSource code after:")
        print("="*80)
        end_line = insertion.def_line + 30  # プレビューとして30行表示
        print(''.join(lines[max(0, insertion.def_line-2):min(end_line, len(lines))]))
        print("="*80)

        # ファイルに書き戻す
        write_file(file_path, lines)

    def _format_doc(self, raw_doc: str) -> str:
        """Doxygenコメントを整形する

        Args:
            raw_doc (str): OpenAI APIから返された生のDoxygen

        Returns:
            str: 整形されたDoxygen
        """
        # 余分なマークダウン記号や装飾を除去
        content = raw_doc.replace('```shell', '').replace('```', '').strip()
        
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
        
        # 行を分割して整形
        lines = content.splitlines()
        formatted_lines = []
        
        for line in lines:
            # 空行の処理
            if not line.strip():
                formatted_lines.append('##')
                continue
                
            # 不要な"## bash","## sh"行を削除
            clean_line = line.strip()
            
            # コメントマーカーの正規化（##の後のスペースを統一）
            if clean_line.startswith('##'):
                clean_line = '## ' + clean_line[2:].lstrip()
            else:
                clean_line = '## ' + clean_line
            
            # 空のコメント行は'##'のみに
            if clean_line == '## ':
                clean_line = '##'
            
            # "## bash","## sh"行は完全に除外
            if clean_line.lower().strip() in ['## bash', '##bash', '## sh', '##sh']:
                continue
            
            formatted_lines.append(clean_line)
        
        # 先頭と末尾の空のコメント行を削除
        while formatted_lines and formatted_lines[0] == '##':
            formatted_lines.pop(0)
        while formatted_lines and formatted_lines[-1] == '##':
            formatted_lines.pop()
        
        return '\n'.join(formatted_lines)

    def _insert_doc(self, lines: List[str], insertion: InsertionPoint, doc: str) -> None:
        """Doxygenコメントをファイルに挿入する

        Args:
            lines (List[str]): ファイルの行のリスト
            insertion (InsertionPoint): 挿入位置情報
            doc (str): 挿入するDoxygen
        """
        # 既存のコメントを削除
        if insertion.has_existing_doc():
            del lines[insertion.existing_doc_start:insertion.existing_doc_end + 1]
            insertion.def_line -= (insertion.existing_doc_end - insertion.existing_doc_start + 1)
        
        # 新しいコメントを準備（インデント調整）
        doxygen_lines = []
        for line in doc.split('\n'):
            if line.strip():
                doxygen_lines.append(insertion.base_indent + line + '\n')
            else:
                doxygen_lines.append('\n')
        
        lines[insertion.def_line:insertion.def_line] = doxygen_lines

    def get_usage_stats(self) -> Dict[str, int]:
        """APIの使用統計を取得する

        Returns:
            Dict[str, int]: トークン使用量の統計
        """
        return self.openai_client.get_usage_stats()
    
