#!/usr/bin/env python3
"""
SSM Parameter Processing Script
SSMパラメータデータを処理し、ダッシュボード用に整形
"""

import json
import os
import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

def load_parameters_list(data_dir: str) -> List[Dict[str, Any]]:
    """パラメータリストを読み込む"""
    params_file = os.path.join(data_dir, 'parameters_list.json')
    with open(params_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('Parameters', [])

def load_parameter_detail(data_dir: str, param_name: str) -> Dict[str, Any]:
    """個別パラメータの詳細を読み込む"""
    param_hash = hashlib.md5(param_name.encode()).hexdigest()
    param_file = os.path.join(data_dir, f'param_{param_hash}.json')
    
    if os.path.exists(param_file):
        with open(param_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('Parameter', {})
    
    return {'Value': '[ERROR]', 'Type': 'Unknown'}

def load_parameter_tags(data_dir: str, param_name: str) -> List[Dict[str, str]]:
    """パラメータのタグを読み込む"""
    param_hash = hashlib.md5(param_name.encode()).hexdigest()
    tags_file = os.path.join(data_dir, f'tags_{param_hash}.json')
    
    if os.path.exists(tags_file):
        with open(tags_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('TagList', [])
    
    return []

def parse_hierarchy(param_name: str) -> Dict[str, Any]:
    """パラメータ名から階層構造を解析"""
    # 先頭と末尾のスラッシュを除去
    clean_name = param_name.strip('/')
    
    if not clean_name:
        return {
            'Level': 0,
            'Path': '/',
            'Leaf': '',
            'FullPath': '/'
        }
    
    parts = clean_name.split('/')
    
    return {
        'Level': len(parts) - 1,
        'Path': '/'.join(parts[:-1]) if len(parts) > 1 else '/',
        'Leaf': parts[-1],
        'FullPath': param_name,
        'Parts': parts
    }

def format_timestamp(timestamp_str: str) -> str:
    """タイムスタンプを読みやすい形式に変換"""
    if not timestamp_str:
        return '-'
    
    try:
        # ISO形式のタイムスタンプをパース
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        # 日本時間で表示（必要に応じて調整）
        return dt.strftime('%Y/%m/%d %H:%M:%S')
    except:
        return timestamp_str

def apply_filters(params: List[Dict], filters: Dict) -> List[Dict]:
    """フィルタを適用"""
    filtered = params
    
    # 名前フィルタ
    name_filter = filters.get('NAME_FILTER', '*')
    if name_filter and name_filter != '*':
        pattern = name_filter.replace('*', '.*')
        filtered = [p for p in filtered if re.match(pattern, p['Name'])]
    
    # タイプフィルタ
    type_filter = filters.get('TYPE_FILTER', 'All')
    if type_filter and type_filter != 'All':
        filtered = [p for p in filtered if p['Type'] == type_filter]
    
    # パスフィルタ
    path_filter = filters.get('PARAMETER_PATH', '/')
    if path_filter and path_filter != '/':
        filtered = [p for p in filtered if p['Name'].startswith(path_filter)]
    
    return filtered

def apply_sorting(params: List[Dict], sort_by: str) -> List[Dict]:
    """ソート処理"""
    if sort_by == 'LastModified':
        return sorted(params, key=lambda x: x.get('LastModified', ''), reverse=True)
    elif sort_by == 'Type':
        return sorted(params, key=lambda x: (x.get('Type', ''), x.get('Name', '')))
    else:  # Name (default)
        return sorted(params, key=lambda x: x.get('Name', ''))

def calculate_statistics(params: List[Dict]) -> Dict[str, Any]:
    """統計情報を計算"""
    stats = {
        'total': len(params),
        'by_type': {},
        'by_tier': {},
        'by_path': {},
        'by_level': {}
    }
    
    for param in params:
        # タイプ別
        param_type = param.get('Type', 'Unknown')
        stats['by_type'][param_type] = stats['by_type'].get(param_type, 0) + 1
        
        # ティア別
        tier = param.get('Tier', 'Standard')
        stats['by_tier'][tier] = stats['by_tier'].get(tier, 0) + 1
        
        # パス別
        path = param['Hierarchy']['Path']
        stats['by_path'][path] = stats['by_path'].get(path, 0) + 1
        
        # 階層レベル別
        level = param['Hierarchy']['Level']
        stats['by_level'][level] = stats['by_level'].get(level, 0) + 1
    
    return stats

def build_hierarchy_tree(params: List[Dict]) -> Dict[str, Any]:
    """階層ツリー構造を構築"""
    tree = {}
    
    for param in params:
        parts = param['Hierarchy']['Parts']
        current = tree
        
        # パスを辿ってツリーを構築
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {'_children': {}, '_params': []}
            current = current[part]['_children']
        
        # 最後の要素（パラメータ名）を追加
        if parts:
            leaf = parts[-1]
            if leaf not in current:
                current[leaf] = {'_children': {}, '_params': []}
            current[leaf]['_params'].append(param)
    
    return tree

def process_parameters(data_dir: str, environment: str, filters: Dict) -> Dict[str, Any]:
    """メイン処理"""
    print("パラメータデータを処理中...")
    
    # パラメータリストの読み込み
    params_list = load_parameters_list(data_dir)
    print(f"  {len(params_list)} 個のパラメータを読み込みました")
    
    processed_params = []
    
    # 各パラメータの処理
    for param_info in params_list:
        param_name = param_info['Name']
        
        # 詳細データの読み込み
        param_detail = load_parameter_detail(data_dir, param_name)
        
        # タグの読み込み
        tags = load_parameter_tags(data_dir, param_name)
        
        # 階層構造の解析
        hierarchy = parse_hierarchy(param_name)
        
        # 処理済みパラメータの構築
        processed_param = {
            'Name': param_name,
            'Value': param_detail.get('Value', ''),
            'Type': param_info.get('Type', 'String'),
            'Description': param_info.get('Description', ''),
            'LastModified': param_info.get('LastModifiedDate', ''),
            'LastModifiedFormatted': format_timestamp(param_info.get('LastModifiedDate', '')),
            'Version': param_info.get('Version', 1),
            'Tier': param_info.get('Tier', 'Standard'),
            'Tags': tags,
            'Hierarchy': hierarchy,
            'ARN': param_info.get('ARN', ''),
            'DataType': param_info.get('DataType', 'text')
        }
        
        processed_params.append(processed_param)
    
    # フィルタリング
    print("フィルタを適用中...")
    processed_params = apply_filters(processed_params, filters)
    print(f"  フィルタ後: {len(processed_params)} 個のパラメータ")
    
    # ソート
    sort_by = filters.get('SORT_BY', 'Name')
    print(f"ソート中: {sort_by}")
    processed_params = apply_sorting(processed_params, sort_by)
    
    # 統計情報の計算
    print("統計情報を計算中...")
    statistics = calculate_statistics(processed_params)
    
    # 階層ツリーの構築
    print("階層ツリーを構築中...")
    hierarchy_tree = build_hierarchy_tree(processed_params)
    
    # 結果の構築
    result = {
        'timestamp': datetime.now().isoformat(),
        'environment': environment,
        'filters': filters,
        'statistics': statistics,
        'parameters': processed_params,
        'hierarchy_tree': hierarchy_tree,
        'unique_paths': sorted(list(statistics['by_path'].keys()))
    }
    
    # 結果の保存
    output_file = os.path.join(data_dir, 'processed_parameters.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, default=str, ensure_ascii=False)
    
    print(f"✅ {len(processed_params)} 個のパラメータを処理しました")
    print(f"   出力: {output_file}")
    
    return result

def main():
    """メイン関数"""
    # 環境変数から設定を取得
    data_dir = os.environ.get('DATA_DIR', 'data')
    environment = os.environ.get('ENVIRONMENT', 'unknown')
    
    # フィルタ設定
    filters = {
        'NAME_FILTER': os.environ.get('NAME_FILTER', '*'),
        'TYPE_FILTER': os.environ.get('TYPE_FILTER', 'All'),
        'PARAMETER_PATH': os.environ.get('PARAMETER_PATH', '/'),
        'SORT_BY': os.environ.get('SORT_BY', 'Name'),
        'SHOW_SECURE_VALUES': os.environ.get('SHOW_SECURE_VALUES', 'false') == 'true'
    }
    
    # 処理実行
    process_parameters(data_dir, environment, filters)

if __name__ == '__main__':
    main()