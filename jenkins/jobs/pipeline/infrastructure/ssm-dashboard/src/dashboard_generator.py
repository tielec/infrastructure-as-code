#!/usr/bin/env python3
"""
SSM Dashboard Generator
処理済みパラメータデータからHTMLダッシュボードを生成
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
import argparse

def load_processed_data(data_file: str) -> dict:
    """処理済みデータを読み込む"""
    with open(data_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_hierarchy_html(tree: dict, level: int = 0) -> str:
    """階層ツリーのHTML生成"""
    html = []
    indent = '  ' * level
    
    for key, value in sorted(tree.items()):
        if key.startswith('_'):
            continue
            
        params = value.get('_params', [])
        children = value.get('_children', {})
        
        if children:
            # フォルダ
            html.append(f'{indent}<div class="tree-node">')
            html.append(f'{indent}  <span class="tree-folder">📁 {key}/</span>')
            
            # 子要素を再帰的に処理
            child_html = generate_hierarchy_html(children, level + 1)
            if child_html:
                html.append(child_html)
            
            # このフォルダ直下のパラメータ
            for param in params:
                html.append(f'{indent}    <div class="tree-param">📄 {param["Hierarchy"]["Leaf"]}</div>')
            
            html.append(f'{indent}</div>')
        else:
            # リーフノード（パラメータ）
            for param in params:
                html.append(f'{indent}<div class="tree-param">📄 {key}</div>')
    
    return '\n'.join(html)

def truncate(value: str, length: int = 100) -> str:
    """文字列を指定長で切り詰める"""
    if len(value) <= length:
        return value
    return value[:length] + '...'

def generate_dashboard(data: dict, template_dir: str, output_dir: str, build_number: str = 'N/A'):
    """ダッシュボードHTML生成"""
    print("HTMLダッシュボードを生成中...")
    
    # Jinja2環境の設定
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )
    
    # カスタムフィルタの追加
    env.filters['truncate'] = truncate
    
    # テンプレートの読み込み
    template = env.get_template('dashboard.html')
    
    # 統計情報の準備
    stats = data['statistics']
    
    # フィルタ情報
    filters = data.get('filters', {})
    
    # コンテキストデータの準備
    context = {
        'environment': data['environment'],
        'timestamp': datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
        'build_number': build_number,
        
        # 統計情報
        'total_params': stats['total'],
        'string_count': stats['by_type'].get('String', 0),
        'secure_count': stats['by_type'].get('SecureString', 0),
        'list_count': stats['by_type'].get('StringList', 0),
        
        # フィルタ条件の表示
        'filter_path': filters.get('PARAMETER_PATH', '/'),
        'filter_name': filters.get('NAME_FILTER', '*'),
        'filter_type': filters.get('TYPE_FILTER', 'All'),
        'sort_by': filters.get('SORT_BY', 'Name'),
        
        # パラメータデータ（バージョンとティアを除外）
        'parameters': data['parameters'],
        
        # 設定
        'show_secure_values': filters.get('SHOW_SECURE_VALUES', False),
    }
    
    # HTML生成
    html_content = template.render(**context)
    
    # 出力ファイルパス
    output_file = os.path.join(output_dir, 'index.html')
    
    # HTMLファイルの書き込み
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # CSSファイルのコピー（すでにtemplatesディレクトリにある場合）
    css_source = os.path.join(template_dir, 'dashboard.css')
    css_dest = os.path.join(output_dir, 'dashboard.css')
    
    if os.path.exists(css_source):
        with open(css_source, 'r', encoding='utf-8') as src:
            css_content = src.read()
        with open(css_dest, 'w', encoding='utf-8') as dst:
            dst.write(css_content)
    
    print(f"✅ ダッシュボードを生成しました: {output_file}")
    
    # サマリー情報の表示
    print("\n=== ダッシュボード生成サマリー ===")
    print(f"環境: {data['environment']}")
    print(f"総パラメータ数: {stats['total']}")
    print(f"タイプ別:")
    for ptype, count in stats['by_type'].items():
        print(f"  - {ptype}: {count}")
    print(f"ティア別:")
    for tier, count in stats['by_tier'].items():
        print(f"  - {tier}: {count}")
    print(f"階層レベル別:")
    for level, count in sorted(stats.get('by_level', {}).items()):
        print(f"  - レベル {level}: {count}")
    print("================================")

def export_json(data: dict, output_dir: str, timestamp: str):
    """JSON形式でエクスポート"""
    output_file = os.path.join(output_dir, f'ssm_parameters_{timestamp}.json')
    
    export_data = {
        'exported_at': datetime.now().isoformat(),
        'environment': data['environment'],
        'statistics': data['statistics'],
        'parameters': data['parameters']
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ JSONエクスポート: {output_file}")

def export_csv(data: dict, output_dir: str, timestamp: str):
    """CSV形式でエクスポート"""
    import csv
    
    output_file = os.path.join(output_dir, f'ssm_parameters_{timestamp}.csv')
    
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        
        # ヘッダー（バージョンとティアを除外）
        writer.writerow([
            'Name', 'Value', 'Type', 'Description', 
            'LastModified', 'Path'
        ])
        
        # データ行
        for param in data['parameters']:
            writer.writerow([
                param['Name'],
                param['Value'],
                param['Type'],
                param.get('Description', ''),
                param.get('LastModifiedFormatted', ''),
                param['Hierarchy']['Path']
            ])
    
    print(f"✅ CSVエクスポート: {output_file}")

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='SSM Dashboard Generator')
    parser.add_argument('--data-dir', required=True, help='Data directory path')
    parser.add_argument('--output-dir', required=True, help='Output directory path')
    parser.add_argument('--template-dir', help='Template directory path')
    parser.add_argument('--environment', default='unknown', help='Environment name')
    parser.add_argument('--timestamp', help='Build timestamp')
    parser.add_argument('--build-number', default='N/A', help='Jenkins build number')
    parser.add_argument('--export-json', action='store_true', help='Export as JSON')
    parser.add_argument('--export-csv', action='store_true', help='Export as CSV')
    
    args = parser.parse_args()
    
    # データファイルのパス
    data_file = os.path.join(args.data_dir, 'processed_parameters.json')
    
    # データの読み込み
    data = load_processed_data(data_file)
    
    # テンプレートディレクトリの決定
    if args.template_dir:
        template_dir = args.template_dir
    else:
        # デフォルトはスクリプトと同じディレクトリの../templates
        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(script_dir, '..', 'templates')
    
    # ダッシュボード生成
    generate_dashboard(
        data=data,
        template_dir=template_dir,
        output_dir=args.output_dir,
        build_number=args.build_number
    )
    
    # エクスポート
    timestamp = args.timestamp or datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if args.export_json:
        export_json(data, args.output_dir, timestamp)
    
    if args.export_csv:
        export_csv(data, args.output_dir, timestamp)

if __name__ == '__main__':
    main()