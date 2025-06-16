"""
Python コードを解析するためのパーサークラス
"""
import ast
from typing import Dict, List, Optional, Union, Any

from common.base_generator import ElementParser
from languages.python.elements import (
    PythonElementInfo, FunctionElementInfo, ClassElementInfo, ModuleElementInfo,
    FunctionElement, ClassElement, ModuleElement
)

class NodeTransformer(ast.NodeTransformer):
    """ASTノードに親ノードへの参照を追加するトランスフォーマー"""
    
    def visit(self, node):
        """ノードを訪問し、親への参照を追加する"""
        for child in ast.iter_child_nodes(node):
            child.parent = node
        return super().visit(node)

class PythonParser(ElementParser):
    """Pythonコードを解析するパーサークラス"""
    
    def parse_file(self, file_path: str) -> List[Union[FunctionElement, ClassElement]]:
        """Pythonファイルを解析し、関数とクラスの要素を抽出する
        
        Args:
            file_path (str): 解析対象のPythonファイルパス
            
        Returns:
            List[Union[FunctionElement, ClassElement]]: 抽出された関数とクラスの要素のリスト
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
            source_lines = source.splitlines()

        tree = ast.parse(source)
        elements = []

        # 関数とクラスを抽出
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                element = self._create_function_element(node, source_lines)
                elements.append(element)
            elif isinstance(node, ast.ClassDef):
                element = self._create_class_element(node, source_lines)
                elements.append(element)

        return elements
    
    def extract_module_info(self, source: str, source_lines: List[str]) -> ModuleElement:
        """モジュール情報を抽出する
        
        Args:
            source (str): ソースコード全体
            source_lines (List[str]): ソースコードの行のリスト
            
        Returns:
            ModuleElement: モジュール情報を含むModuleElement
        """
        tree = ast.parse(source)
        # ASTノードに親への参照を追加
        transformer = NodeTransformer()
        transformer.visit(tree)
        
        # インポート文を収集
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for name in node.names:
                    imports.append(f"from {module} import {name.name}")

        # クラスと関数を収集（トップレベルのみ）
        classes = []
        functions = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)

        info = ModuleElementInfo(
            name="module",  # モジュール名は後で設定可能
            code=source,
            start_line=0,
            source_lines=source_lines,
            indent="",
            imports=imports,
            classes=classes,
            functions=functions
        )

        return ModuleElement(info)

    def _create_function_element(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], 
                            source_lines: List[str]) -> FunctionElement:
        """関数のASTノードからFunctionElementを作成する"""
        start_line = node.lineno - 1
        end_line = node.end_lineno
        function_lines = source_lines[start_line:end_line]
        indent = ' ' * (len(function_lines[0]) - len(function_lines[0].lstrip()))

        # デコレータのリストを収集
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    decorators.append(decorator.func.id)
                elif isinstance(decorator.func, ast.Attribute):
                    # ネストされた属性の場合の再帰的な処理
                    def get_full_attribute_name(attr_node):
                        if isinstance(attr_node, ast.Name):
                            return attr_node.id
                        elif isinstance(attr_node, ast.Attribute):
                            return f"{get_full_attribute_name(attr_node.value)}.{attr_node.attr}"
                        return str(attr_node)  # その他のケース
                    
                    decorators.append(get_full_attribute_name(decorator.func))

        info = FunctionElementInfo(
            name=node.name,
            code='\n'.join(function_lines),
            start_line=start_line,
            source_lines=function_lines,
            indent=indent,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            decorators=decorators
        )

        return FunctionElement(info)

    def _create_class_element(self, node: ast.ClassDef, source_lines: List[str]) -> ClassElement:
        """クラスのASTノードからClassElementを作成する"""
        start_line = node.lineno - 1
        if node.decorator_list:
            start_line = min(decorator.lineno for decorator in node.decorator_list) - 1
        end_line = node.end_lineno

        class_lines = source_lines[start_line:end_line]
        indent = ' ' * (len(class_lines[0]) - len(class_lines[0].lstrip()))

        # メソッドのリストを収集
        methods = []
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(child.name)

        # デコレータのリストを収集
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    decorators.append(decorator.func.id)
                elif isinstance(decorator.func, ast.Attribute):
                    # ネストされた属性の場合の再帰的な処理
                    def get_full_attribute_name(attr_node):
                        if isinstance(attr_node, ast.Name):
                            return attr_node.id
                        elif isinstance(attr_node, ast.Attribute):
                            return f"{get_full_attribute_name(attr_node.value)}.{attr_node.attr}"
                        return str(attr_node)  # その他のケース
                    
                    decorators.append(get_full_attribute_name(decorator.func))

        info = ClassElementInfo(
            name=node.name,
            code='\n'.join(class_lines),
            start_line=start_line,
            source_lines=class_lines,
            indent=indent,
            methods=methods,
            decorators=decorators
        )

        return ClassElement(info)
