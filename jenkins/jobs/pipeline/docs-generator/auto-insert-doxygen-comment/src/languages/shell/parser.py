"""
シェルスクリプトを解析するためのパーサークラス
"""
import re
from typing import Dict, List, Optional, Union, Any

from common.base_generator import ElementParser
from languages.shell.elements import (
    ShellElementInfo, FunctionElementInfo, ScriptElementInfo,
    FunctionElement, ScriptElement
)

class ShellParser(ElementParser):
    """シェルスクリプトを解析するパーサークラス"""
    
    def parse_file(self, file_path: str) -> List[FunctionElement]:
        """シェルスクリプトファイルを解析し、関数要素を抽出する
        
        Args:
            file_path (str): 解析対象のシェルスクリプトファイルパス
            
        Returns:
            List[FunctionElement]: 抽出された関数要素のリスト
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
            source_lines = source.splitlines(True)  # 改行文字を保持
        
        return self.extract_functions(source_lines)
    
    def extract_functions(self, source_lines: List[str]) -> List[FunctionElement]:
        """シェルスクリプトから関数を抽出する
        
        Args:
            source_lines (List[str]): ソースコードの行のリスト
            
        Returns:
            List[FunctionElement]: 抽出された関数要素のリスト
        """
        functions = []
        function_pattern = r'^(\s*)(function\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\)'
        
        i = 0
        while i < len(source_lines):
            line = source_lines[i]
            match = re.match(function_pattern, line)
            
            if match:
                indent, _, name = match.groups()
                start_line = i
                
                # 関数本体を探す
                code_lines = []
                brace_count = 0
                found_opening = False
                
                while i < len(source_lines):
                    current_line = source_lines[i]
                    code_lines.append(current_line)
                    
                    if '{' in current_line:
                        found_opening = True
                        brace_count += current_line.count('{')
                    if '}' in current_line:
                        brace_count -= current_line.count('}')
                    
                    if found_opening and brace_count == 0:
                        break
                        
                    i += 1
                
                # パラメータを抽出
                params = []
                for line in code_lines:
                    param_matches = re.findall(r'\$([1-9][0-9]*|\{[1-9][0-9]*\})', line)
                    params.extend(param_matches)
                
                params = sorted(list(set(params)))
                
                info = FunctionElementInfo(
                    name=name,
                    code=''.join(code_lines),
                    start_line=start_line,
                    source_lines=code_lines,
                    indent=indent if indent else '',
                    parameters=params
                )
                functions.append(FunctionElement(info))
            
            i += 1
        
        return functions
    
    def extract_module_info(self, source: str, source_lines: List[str]) -> ScriptElement:
        """スクリプト全体の情報を抽出する
        
        Args:
            source (str): ソースコード全体
            source_lines (List[str]): ソースコードの行のリスト
            
        Returns:
            ScriptElement: スクリプト情報を含むScriptElement
        """
        # 依存関係（sourceコマンドなど）を抽出
        dependencies = []
        source_pattern = r'source\s+([^\s;]+)'
        dependencies.extend(re.findall(source_pattern, source))
        
        # 関数名を収集
        functions = [func.info.name for func in self.extract_functions(source_lines)]
        
        info = ScriptElementInfo(
            name="script",
            code=source,
            start_line=0,
            source_lines=source_lines,
            indent="",
            functions=functions,
            dependencies=dependencies
        )
        
        return ScriptElement(info)
