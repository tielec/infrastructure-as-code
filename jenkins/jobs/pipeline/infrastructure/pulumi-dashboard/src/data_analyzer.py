#!/usr/bin/env python3
"""
data_analyzer.py - Pulumiステートデータの分析モジュール
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta


def analyze_resource_trends(states, history_data=None):
    """リソースのトレンドを分析"""
    trends = {}
    
    if history_data:
        # 履歴データからトレンドを計算
        for project, history in history_data.items():
            project_trends = {
                'resource_count_history': [],
                'dates': []
            }
            
            for timestamp, data in sorted(history.items()):
                project_trends['dates'].append(timestamp)
                project_trends['resource_count_history'].append(
                    data.get('resource_count', 0)
                )
            
            trends[project] = project_trends
    
    return trends


def calculate_cost_estimates(states):
    """簡易的なコスト見積もりを計算"""
    # リソースタイプごとの仮想的な月額コスト（USD）
    cost_map = {
        'aws:ec2/instance:Instance': 50,
        'aws:rds/instance:Instance': 100,
        'aws:s3/bucket:Bucket': 5,
        'aws:lambda/function:Function': 10,
        'aws:ecs/service:Service': 30,
        'aws:elasticloadbalancingv2/loadBalancer:LoadBalancer': 25,
        'aws:cloudfront/distribution:Distribution': 15,
        'aws:dynamodb/table:Table': 20,
    }
    
    total_estimate = 0
    resource_costs = defaultdict(float)
    
    for state in states:
        for resource_type in state.get('resource_types', []):
            type_name = resource_type['type']
            count = resource_type['count']
            
            # コストマップからコストを取得（デフォルトは5ドル）
            unit_cost = cost_map.get(type_name, 5)
            cost = unit_cost * count
            
            resource_costs[type_name] += cost
            total_estimate += cost
    
    return {
        'total_monthly_estimate': total_estimate,
        'resource_breakdown': dict(resource_costs)
    }


def detect_anomalies(states):
    """異常を検出（例：長期間更新されていないスタック）"""
    anomalies = []
    now = datetime.now()
    
    for state in states:
        last_updated = state.get('last_updated')
        if last_updated:
            try:
                # ISO形式のタイムスタンプをパース
                update_time = datetime.fromisoformat(
                    last_updated.replace('Z', '+00:00')
                )
                days_since_update = (now - update_time).days
                
                # 30日以上更新されていない場合は警告
                if days_since_update > 30:
                    anomalies.append({
                        'type': 'stale_stack',
                        'project': state['project'],
                        'stack': state['stack'],
                        'days_since_update': days_since_update,
                        'severity': 'warning' if days_since_update < 90 else 'critical'
                    })
            except:
                pass
        
        # リソース数が異常に多い場合
        if state.get('resources', 0) > 100:
            anomalies.append({
                'type': 'high_resource_count',
                'project': state['project'],
                'stack': state['stack'],
                'resource_count': state['resources'],
                'severity': 'info'
            })
    
    return anomalies


def generate_statistics(states):
    """統計情報を生成"""
    if not states:
        return {}
    
    resource_counts = [s.get('resources', 0) for s in states]
    
    stats = {
        'average_resources_per_stack': sum(resource_counts) / len(resource_counts) if resource_counts else 0,
        'max_resources_in_stack': max(resource_counts) if resource_counts else 0,
        'min_resources_in_stack': min(resource_counts) if resource_counts else 0,
        'stacks_with_no_resources': len([r for r in resource_counts if r == 0]),
        'most_common_resource_types': get_most_common_resource_types(states, top_n=5)
    }
    
    return stats


def get_most_common_resource_types(states, top_n=5):
    """最も一般的なリソースタイプを取得"""
    type_counts = defaultdict(int)
    
    for state in states:
        for resource_type in state.get('resource_types', []):
            type_counts[resource_type['type']] += resource_type['count']
    
    # 上位N個を取得
    sorted_types = sorted(
        type_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:top_n]
    
    return [{'type': t, 'count': c} for t, c in sorted_types]


if __name__ == '__main__':
    # テスト用
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            states = json.load(f)
        
        stats = generate_statistics(states)
        anomalies = detect_anomalies(states)
        
        print("Statistics:")
        print(json.dumps(stats, indent=2))
        
        print("\nAnomalies:")
        print(json.dumps(anomalies, indent=2))