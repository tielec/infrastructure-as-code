#!/usr/bin/env python3
"""
dashboard_generator.py - Pulumiダッシュボード生成スクリプト
"""

import json
import os
import argparse
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def load_data(data_dir):
    """データファイルを読み込む"""
    data = {}
    
    # 処理済みステートデータ
    states_file = Path(data_dir) / 'processed_states.json'
    if states_file.exists():
        with open(states_file, 'r') as f:
            data['states'] = json.load(f)
    else:
        data['states'] = []
    
    # サマリーデータ
    summary_file = Path(data_dir) / 'summary.json'
    if summary_file.exists():
        with open(summary_file, 'r') as f:
            data['summary'] = json.load(f)
    else:
        data['summary'] = {
            'total_projects': 0,
            'total_stacks': 0,
            'total_resources': 0,
            'projects': [],
            'resource_summary': []
        }
    
    return data


def sort_data(data, sort_by, sort_order):
    """データをソート"""
    reverse = (sort_order == 'desc')
    
    # ステートデータのソート
    if 'states' in data:
        if sort_by == 'last_updated':
            data['states'] = sorted(
                data['states'],
                key=lambda x: x.get('last_updated') or '',
                reverse=reverse
            )
        elif sort_by == 'project_name':
            data['states'] = sorted(
                data['states'],
                key=lambda x: (x.get('project') or '', x.get('stack') or ''),
                reverse=reverse
            )
        elif sort_by == 'resource_count':
            data['states'] = sorted(
                data['states'],
                key=lambda x: x.get('resources', 0),
                reverse=reverse
            )
        elif sort_by == 'stack_name':
            data['states'] = sorted(
                data['states'],
                key=lambda x: x.get('stack') or '',
                reverse=reverse
            )
    
    # プロジェクトサマリーのソート
    if 'summary' in data and 'projects' in data['summary']:
        if sort_by == 'last_updated':
            data['summary']['projects'] = sorted(
                data['summary']['projects'],
                key=lambda x: x.get('last_updated') or '',
                reverse=reverse
            )
        elif sort_by in ['project_name', 'stack_name']:
            data['summary']['projects'] = sorted(
                data['summary']['projects'],
                key=lambda x: x.get('name') or '',
                reverse=reverse
            )
        elif sort_by == 'resource_count':
            data['summary']['projects'] = sorted(
                data['summary']['projects'],
                key=lambda x: x.get('total_resources', 0),
                reverse=reverse
            )
    
    return data


def format_timestamp(timestamp_str):
    """タイムスタンプを読みやすい形式に変換"""
    if not timestamp_str:
        return 'N/A'
    
    try:
        # ISO形式のタイムスタンプをパース
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        # yyyy/MM/dd HH:mm 形式で表示
        return dt.strftime('%Y/%m/%d %H:%M')
    except:
        return timestamp_str


def calculate_days_since_update(timestamp_str):
    """最終更新からの経過日数を計算"""
    if not timestamp_str:
        return None
    
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(dt.tzinfo)
        return (now - dt).days
    except:
        return None


def get_staleness_status(days):
    """更新からの経過日数に基づいてステータスを返す"""
    if days is None:
        return None
    if days > 90:
        return 'critical'  # 90日以上
    elif days > 30:
        return 'warning'   # 30日以上
    elif days > 7:
        return 'info'      # 7日以上
    else:
        return 'ok'


def simplify_resource_type(resource_type):
    """リソースタイプを簡略化（純粋な構造解析のみ）"""
    
    if not resource_type:
        return resource_type
    
    # 形式: provider:service/resource:Type を解析
    # 例: aws:s3/bucketV2:BucketV2
    parts = resource_type.split(':')
    if len(parts) >= 2:
        # 2番目の要素を取得 (service/resource)
        service_resource = parts[1]
        
        # / で分割
        if '/' in service_resource:
            service, resource = service_resource.split('/', 1)
            
            # サービス名とリソース名を表示（大文字変換のみ）
            service_display = service.upper() if len(service) <= 3 else service.title()
            resource_display = resource if len(resource) <= 20 else resource[:17] + '...'
            
            return f"{service_display}/{resource_display}"
        else:
            # リソース部分がない場合はサービス名のみ
            return service_resource.upper() if len(service_resource) <= 3 else service_resource.title()
    
    # パースできない場合は元の値を短縮して返す
    return resource_type if len(resource_type) <= 30 else resource_type[:27] + '...'


def extract_service_resource(resource_type):
    """リソースタイプからservice/resource部分のみ抽出"""
    
    if not resource_type:
        return resource_type
    
    # 形式: provider:service/resource:Type から service/resource を抽出
    # 例: aws:iam/rolePolicyAttachment:RolePolicyAttachment → iam/rolePolicyAttachment
    parts = resource_type.split(':')
    if len(parts) >= 2:
        # 2番目の要素を返す (service/resource)
        return parts[1]
    
    # パースできない場合は元の値を返す
    return resource_type


def generate_dashboard(data, template_dir, output_dir, environment, timestamp):
    """ダッシュボードHTMLを生成"""
    
    # テンプレート環境を設定
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=True
    )
    
    # カスタムフィルタを追加
    env.filters['format_timestamp'] = format_timestamp
    env.filters['simplify_resource_type'] = simplify_resource_type
    env.filters['extract_service_resource'] = extract_service_resource
    
    # テンプレートを読み込み
    template = env.get_template('dashboard.html')
    
    # データの前処理
    for state in data.get('states', []):
        state['formatted_time'] = format_timestamp(state.get('last_updated'))
        
        # 経過日数と警告ステータスを追加
        days_since = calculate_days_since_update(state.get('last_updated'))
        state['days_since_update'] = days_since
        state['staleness_status'] = get_staleness_status(days_since)
        
        # リソースタイプを簡略化し、重複を除去
        if state.get('resource_types'):
            # 簡略化したタイプでグループ化
            simplified_types = {}
            for rt in state['resource_types']:
                rt_type = rt.get('type', '')
                simple_type = simplify_resource_type(rt_type)
                
                if simple_type not in simplified_types:
                    # 新しい簡略化タイプの場合
                    simplified_types[simple_type] = {
                        'type': rt_type,  # 元のタイプ（ツールチップ用）
                        'simple_type': simple_type,
                        'count': rt.get('count', 0)
                    }
                else:
                    # 既存の簡略化タイプの場合はカウントを合算
                    simplified_types[simple_type]['count'] += rt.get('count', 0)
                    # 元のタイプリストを保持（複数の元タイプが同じ簡略タイプになる場合）
                    if 'original_types' not in simplified_types[simple_type]:
                        simplified_types[simple_type]['original_types'] = [simplified_types[simple_type]['type']]
                    simplified_types[simple_type]['original_types'].append(rt_type)
            
            # カウント順にソートしてリストに変換
            state['resource_types'] = sorted(
                simplified_types.values(), 
                key=lambda x: x['count'], 
                reverse=True
            )
    
    for project in data.get('summary', {}).get('projects', []):
        project['formatted_time'] = format_timestamp(project.get('last_updated'))
    
    # HTMLをレンダリング
    html_content = template.render(
        environment=environment,
        timestamp=timestamp,
        summary=data.get('summary', {}),
        states=data.get('states', [])
    )
    
    # 出力ディレクトリを作成
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # HTMLファイルを保存
    output_file = output_path / 'index.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Dashboard generated: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Generate Pulumi Dashboard')
    parser.add_argument('--data-dir', required=True, help='Data directory path')
    parser.add_argument('--output-dir', required=True, help='Output directory path')
    parser.add_argument('--environment', default='unknown', help='Environment name')
    parser.add_argument('--timestamp', default=None, help='Build timestamp')
    
    args = parser.parse_args()
    
    # データを読み込み
    data = load_data(args.data_dir)

    # デフォルトのソート（プロジェクト名順）
    data = sort_data(data, 'project_name', 'asc')
    
    # タイムスタンプの設定
    timestamp = args.timestamp or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # テンプレートディレクトリの設定
    template_dir = args.output_dir  # テンプレートは出力ディレクトリにコピーされている前提
    
    # ダッシュボードを生成
    generate_dashboard(
        data,
        template_dir,
        args.output_dir,
        args.environment,
        timestamp
    )


if __name__ == '__main__':
    main()