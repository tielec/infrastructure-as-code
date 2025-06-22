#!/usr/bin/env python3
"""
Doxygenドキュメント自動生成メインプログラム
"""
import argparse
import os
import sys
from typing import Dict, List, Optional

# Jenkinsの実行環境でも動作するようにパスを調整
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # auto-insert-doxygen-comment ディレクトリ

# モジュールのパスを追加
sys.path.insert(0, parent_dir)

# 明示的なインポートパスを使用
from src.languages.python.generator import PythonDocGenerator
from src.languages.shell.generator import ShellDocGenerator
from src.languages.rust.generator import RustDocGenerator
from src.languages.typescript.generator import TypeScriptDocGenerator
from src.common.file_utils import read_template

def parse_args():
    """コマンドライン引数をパースする"""
    parser = argparse.ArgumentParser(description='Generate documentation for code files using OpenAI API')
    
    # 共通の引数
    parser.add_argument('--file', required=True, help='Source file to process')
    parser.add_argument('--language', choices=['python', 'shell', 'rust', 'typescript'], required=True, help='Source language')
    parser.add_argument('--overwrite-docstring', action='store_true', help='Overwrite existing documentation')
    parser.add_argument('--model', default='gpt-4.1-mini', help='OpenAI model to use (default: gpt-4.1-mini)')
    
    # Python用の引数
    python_group = parser.add_argument_group('Python')
    python_group.add_argument('--python-class-template', help='Python class docstring template file')
    python_group.add_argument('--python-function-template', help='Python function docstring template file')
    python_group.add_argument('--python-module-template', help='Python module docstring template file')
    
    # Shell用の引数
    shell_group = parser.add_argument_group('Shell')
    shell_group.add_argument('--shell-function-template', help='Shell function documentation template file')
    shell_group.add_argument('--shell-script-template', help='Shell script documentation template file')
    
    # Rust用の引数
    rust_group = parser.add_argument_group('Rust')
    rust_group.add_argument('--rust-function-template', help='Rust function documentation template file')
    rust_group.add_argument('--rust-struct-template', help='Rust struct documentation template file')
    rust_group.add_argument('--rust-enum-template', help='Rust enum documentation template file')
    rust_group.add_argument('--rust-trait-template', help='Rust trait documentation template file')
    rust_group.add_argument('--rust-module-template', help='Rust module documentation template file')
    
    # TypeScript用の引数
    typescript_group = parser.add_argument_group('TypeScript')
    typescript_group.add_argument('--typescript-function-template', help='TypeScript function documentation template file')
    typescript_group.add_argument('--typescript-class-template', help='TypeScript class documentation template file')
    typescript_group.add_argument('--typescript-interface-template', help='TypeScript interface documentation template file')
    typescript_group.add_argument('--typescript-type-template', help='TypeScript type documentation template file')
    typescript_group.add_argument('--typescript-enum-template', help='TypeScript enum documentation template file')
    typescript_group.add_argument('--typescript-module-template', help='TypeScript module documentation template file')
    
    return parser.parse_args()

def load_templates(args, language: str) -> Dict[str, str]:
    """テンプレートを読み込む
    
    Args:
        args: コマンドライン引数
        language (str): 対象言語
        
    Returns:
        Dict[str, str]: テンプレート辞書
    """
    templates = {}
    
    if language == 'python':
        python_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'python')
        template_dir = os.path.join(python_dir, 'templates')
        
        class_template = args.python_class_template or os.path.join(template_dir, 'docstring_class_template.md')
        function_template = args.python_function_template or os.path.join(template_dir, 'docstring_function_template.md')
        module_template = args.python_module_template or os.path.join(template_dir, 'docstring_module_template.md')
        
        templates["class"] = read_template(class_template)
        templates["function"] = read_template(function_template)
        templates["module"] = read_template(module_template)
        
    elif language == 'shell':
        shell_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shell')
        template_dir = os.path.join(shell_dir, 'templates')
        
        function_template = args.shell_function_template or os.path.join(template_dir, 'shell_function_template.md')
        script_template = args.shell_script_template or os.path.join(template_dir, 'shell_script_template.md')
        
        templates["function"] = read_template(function_template)
        templates["script"] = read_template(script_template)
        
    elif language == 'rust':
        rust_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'rust')
        template_dir = os.path.join(rust_dir, 'templates')
        
        function_template = args.rust_function_template or os.path.join(template_dir, 'rust_function_template.md')
        struct_template = args.rust_struct_template or os.path.join(template_dir, 'rust_struct_template.md')
        enum_template = args.rust_enum_template or os.path.join(template_dir, 'rust_enum_template.md')
        trait_template = args.rust_trait_template or os.path.join(template_dir, 'rust_trait_template.md')
        module_template = args.rust_module_template or os.path.join(template_dir, 'rust_module_template.md')
        
        templates["function"] = read_template(function_template)
        templates["struct"] = read_template(struct_template)
        templates["enum"] = read_template(enum_template)
        templates["trait"] = read_template(trait_template)
        templates["module"] = read_template(module_template)
    
    elif language == 'typescript':
        typescript_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'typescript')
        template_dir = os.path.join(typescript_dir, 'templates')
        
        function_template = args.typescript_function_template or os.path.join(template_dir, 'typescript_function_template.md')
        class_template = args.typescript_class_template or os.path.join(template_dir, 'typescript_class_template.md')
        interface_template = args.typescript_interface_template or os.path.join(template_dir, 'typescript_interface_template.md')
        type_template = args.typescript_type_template or os.path.join(template_dir, 'typescript_type_template.md')
        enum_template = args.typescript_enum_template or os.path.join(template_dir, 'typescript_enum_template.md')
        module_template = args.typescript_module_template or os.path.join(template_dir, 'typescript_module_template.md')
        
        templates["function"] = read_template(function_template)
        templates["class"] = read_template(class_template)
        templates["interface"] = read_template(interface_template)
        templates["type"] = read_template(type_template)
        templates["enum"] = read_template(enum_template)
        templates["module"] = read_template(module_template)
    
    return templates

def get_generator(language: str, openai_endpoint: str, openai_key: str, model: str, **kwargs):
    """言語に応じたジェネレーターを取得する
    
    Args:
        language (str): 対象言語
        openai_endpoint (str): OpenAI APIのエンドポイント
        openai_key (str): OpenAI APIキー
        model (str): OpenAIモデル名
        
    Returns:
        BaseDocGenerator: ドキュメント生成器
    """
    if language == 'python':
        return PythonDocGenerator(openai_endpoint, openai_key, model)
    elif language == 'shell':
        return ShellDocGenerator(openai_endpoint, openai_key, model)
    elif language == 'rust':
        return RustDocGenerator(openai_endpoint, openai_key, model)
    elif language == 'typescript':
        return TypeScriptDocGenerator(openai_endpoint, openai_key, model)
    else:
        raise ValueError(f"Unsupported language: {language}")

def get_file_extension(language: str) -> str:
    """言語に応じたファイル拡張子を取得する"""
    if language == 'python':
        return '.py'
    elif language == 'shell':
        return '.sh'
    elif language == 'rust':
        return '.rs'
    elif language == 'typescript':
        return '.ts'
    else:
        return ''

def validate_file(file_path: str, language: str) -> bool:
    """ファイルが適切な言語のものかを検証する"""
    expected_ext = get_file_extension(language)
    _, ext = os.path.splitext(file_path)
    
    if language == 'shell' and ext in ['.sh', '.bash']:
        return True
    
    if language == 'typescript' and ext in ['.ts', '.tsx']:
        return True
    
    return ext == expected_ext

def main():
    """メイン関数"""
    args = parse_args()
    
    # 環境変数から認証情報を取得
    openai_key = os.getenv('OPENAI_API_KEY')
    openai_endpoint = os.getenv('OPENAI_API_ENDPOINT')
    deployment_name = os.getenv('OPENAI_DEPLOYMENT_NAME', args.model)

    if not all([openai_key, openai_endpoint]):
        print("Error: Required environment variables not set")
        print("Make sure OPENAI_API_KEY and OPENAI_API_ENDPOINT are set")
        sys.exit(1)

    # ファイルの検証
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        sys.exit(1)
        
    if not validate_file(args.file, args.language):
        print(f"Warning: File extension does not match language '{args.language}'")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    try:
        # テンプレートを読み込む
        templates = load_templates(args, args.language)
        
        # ジェネレーターを取得
        generator = get_generator(args.language, openai_endpoint, openai_key, deployment_name)
        
        # ファイル処理
        generator.process_file(args.file, templates, args.overwrite_docstring)
        
        # 使用統計を出力
        usage = generator.get_usage_stats()
        print("\nTotal Token Usage:")
        print("-"*80)
        print(f"Prompt Tokens  : {usage['prompt_tokens']}")
        print(f"Completion     : {usage['completion_tokens']}")
        print(f"Total Tokens   : {usage['total_tokens']}")
        print("-"*80)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
