"""
Data processing utilities for Pulumi reports
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Tuple


class DataProcessor:
    """Pulumiデータの処理を担当"""
    
    def __init__(self, artifacts_dir: str):
        self.artifacts_dir = Path(artifacts_dir)
        # Pre-action データ
        self.pre_stack_export = {}
        self.pre_stack_config = {}
        self.pre_stack_outputs = {}
        self.pre_resources = []
        self.pre_resource_types = {}
        self.pre_resource_providers = {}
        
        # Post-action データ
        self.stack_export = {}
        self.stack_config = {}
        self.stack_history = []
        self.stack_outputs = {}
        self.resources = []
        self.resource_types = {}
        self.resource_providers = {}
        
        # 比較データ
        self.resources_with_change_status = []
        self.change_summary = {}
        self.metrics_comparison = {}
        self.stats = {}
        
    def load_json_data(self):
        """JSONファイルを読み込む（実行前後の比較対応）"""
        # Post-action データを読み込む（主データ）
        self.stack_export = self._load_json('stack-export-post-action.json')
        self.stack_config = self._load_json('stack-config-post-action.json')
        self.stack_outputs = self._load_json('stack-outputs-post-action.json')
        
        # Pre-action データを読み込む
        self.pre_stack_export = self._load_json('stack-export-pre-action.json')
        self.pre_stack_config = self._load_json('stack-config-pre-action.json')
        self.pre_stack_outputs = self._load_json('stack-outputs-pre-action.json')
        
        # 履歴はpost-actionの最新版を優先的に使用
        self.stack_history = self._load_json('stack-history-post-action.json')
        
        # post-actionが見つからない場合はpre-actionを試す
        if not self.stack_history:
            self.stack_history = self._load_json('stack-history-pre-action.json')
        
    def _load_json(self, filename: str) -> Any:
        """JSONファイルを安全に読み込む"""
        filepath = self.artifacts_dir / filename
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load {filename}: {e}")
            return {} if not filename.endswith('.json') or 'history' not in filename else []
    
    def process_resources(self):
        """リソース情報を処理（実行前後の比較対応）"""
        # Pre-action リソースを処理
        pre_deployment = self.pre_stack_export.get('deployment', {})
        pre_resources = pre_deployment.get('resources', [])
        self.pre_resources = [r for r in pre_resources if r.get('type') != 'pulumi:pulumi:Stack']
        
        # Post-action リソースを処理
        deployment = self.stack_export.get('deployment', {})
        resources = deployment.get('resources', [])
        self.resources = [r for r in resources if r.get('type') != 'pulumi:pulumi:Stack']
        
        # リソースタイプ別に集計（post-action）
        self._aggregate_resources()
        
        # Pre-action リソースも集計
        self._aggregate_pre_resources()
        
        # リソースの変更状態を計算
        self._calculate_resource_changes()
        
        # 統計情報
        self.stats = {
            'total_resources': len(self.resources),
            'resource_types_count': len(self.resource_types),
            'resource_providers_count': len(self.resource_providers),
            'deployment_time': deployment.get('manifest', {}).get('time', 'N/A'),
            'pulumi_version': deployment.get('manifest', {}).get('version', 'N/A')
        }
    
    def _aggregate_resources(self):
        """Post-action リソースを集計"""
        self.resource_types = {}
        self.resource_providers = {}
        
        for resource in self.resources:
            resource_type = resource.get('type', 'unknown')
            
            # プロバイダー別の集計
            provider = resource_type.split(':')[0] if ':' in resource_type else 'unknown'
            self.resource_providers[provider] = self.resource_providers.get(provider, 0) + 1
            
            # タイプ別の集計（短縮名）
            short_type = resource_type.split(':')[-1] if ':' in resource_type else resource_type
            self.resource_types[short_type] = self.resource_types.get(short_type, 0) + 1
    
    def _aggregate_pre_resources(self):
        """Pre-action リソースを集計"""
        self.pre_resource_types = {}
        self.pre_resource_providers = {}
        
        for resource in self.pre_resources:
            resource_type = resource.get('type', 'unknown')
            
            # プロバイダー別の集計
            provider = resource_type.split(':')[0] if ':' in resource_type else 'unknown'
            self.pre_resource_providers[provider] = self.pre_resource_providers.get(provider, 0) + 1
            
            # タイプ別の集計（短縮名）
            short_type = resource_type.split(':')[-1] if ':' in resource_type else resource_type
            self.pre_resource_types[short_type] = self.pre_resource_types.get(short_type, 0) + 1
    
    def _calculate_resource_changes(self):
        """リソースの変更状態を計算"""
        # URNをキーとしてリソースマップを作成
        pre_resources_map = {r.get('urn'): r for r in self.pre_resources}
        post_resources_map = {r.get('urn'): r for r in self.resources}
        
        # すべてのURNを収集
        all_urns = set(pre_resources_map.keys()) | set(post_resources_map.keys())
        
        # 変更サマリーの初期化
        added_count = 0
        updated_count = 0
        deleted_count = 0
        unchanged_count = 0
        
        # 各リソースの変更状態を判定
        self.resources_with_change_status = []
        
        for urn in all_urns:
            pre_resource = pre_resources_map.get(urn)
            post_resource = post_resources_map.get(urn)
            
            if pre_resource and post_resource:
                # 両方に存在する場合
                resource = post_resource.copy()
                
                # 更新を検出（簡易的にmodifiedタイムスタンプで判定）
                pre_modified = pre_resource.get('modified', '')
                post_modified = post_resource.get('modified', '')
                
                if pre_modified != post_modified:
                    resource['change_status'] = 'updated'
                    updated_count += 1
                else:
                    resource['change_status'] = 'unchanged'
                    unchanged_count += 1
                    
            elif post_resource and not pre_resource:
                # Post-actionのみに存在 = 追加
                resource = post_resource.copy()
                resource['change_status'] = 'added'
                added_count += 1
                
            elif pre_resource and not post_resource:
                # Pre-actionのみに存在 = 削除
                resource = pre_resource.copy()
                resource['change_status'] = 'deleted'
                deleted_count += 1
            else:
                continue
                
            self.resources_with_change_status.append(resource)
        
        # 変更サマリーを保存
        self.change_summary = {
            'before_total': len(self.pre_resources),
            'after_total': len(self.resources),
            'added': added_count,
            'updated': updated_count,
            'deleted': deleted_count,
            'unchanged': unchanged_count
        }
        
        # メトリクス比較を計算
        self.metrics_comparison = {
            'before_total': len(self.pre_resources),
            'after_total': len(self.resources),
            'total_diff': len(self.resources) - len(self.pre_resources),
            'before_types': len(self.pre_resource_types),
            'after_types': len(self.resource_types),
            'types_diff': len(self.resource_types) - len(self.pre_resource_types),
            'before_providers': len(self.pre_resource_providers),
            'after_providers': len(self.resource_providers),
            'providers_diff': len(self.resource_providers) - len(self.pre_resource_providers)
        }
        
        # リソースを作成日時でソート（新しい順）
        self.resources_with_change_status.sort(
            key=lambda r: r.get('created', ''),
            reverse=True
        )
    
    def prepare_deployment_data(self) -> Dict[str, List]:
        """デプロイメントデータを準備"""
        history = self.stack_history[:20]
        history.reverse()  # 古い順に並べ替え
        
        data = {
            'timestamps': [],
            'success_rate': [],
            'creates': [],
            'updates': [],
            'deletes': [],
            'total_changes': []
        }
        
        for i, h in enumerate(history):
            # タイムスタンプ
            start_time = h.get('startTime', '')
            if start_time:
                date_part = start_time.split('T')[0]
                data['timestamps'].append(f"{date_part}\n#{i+1}")
            else:
                data['timestamps'].append(f'Deploy #{i+1}')
            
            # 成功率
            result = h.get('result', 'unknown')
            data['success_rate'].append(1 if result == 'succeeded' else 0)
            
            # 変更数
            changes = h.get('resourceChanges', {})
            create_count = changes.get('create', 0)
            update_count = changes.get('update', 0) + changes.get('replace', 0)
            delete_count = changes.get('delete', 0)
            
            data['creates'].append(create_count)
            data['updates'].append(update_count)
            data['deletes'].append(delete_count)
            data['total_changes'].append(create_count + update_count + delete_count)
        
        # 移動平均を計算（履歴が3件以上の場合のみ）
        if len(data['success_rate']) >= 3:
            data['success_ma'] = self._calculate_moving_average(data['success_rate'], 3)
        else:
            data['success_ma'] = data['success_rate'].copy()
        
        return data
    
    def _calculate_moving_average(self, values: List[float], window: int) -> List[float]:
        """移動平均を計算"""
        ma = []
        for i in range(len(values)):
            if i < window - 1:
                ma.append(sum(values[:i+1]) / (i+1))
            else:
                ma.append(sum(values[i-window+1:i+1]) / window)
        return ma
    
    def calculate_deployment_stats(self) -> Dict[str, float]:
        """デプロイメント統計を計算（最新の履歴を含む）"""
        if not self.stack_history:
            return {
                'total_deployments': 0,
                'success_count': 0,
                'failure_count': 0,
                'success_rate': 0,
                'avg_changes': 0
            }
        
        total = len(self.stack_history)
        success_count = sum(1 for h in self.stack_history if h.get('result') == 'succeeded')
        failure_count = total - success_count
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        # 平均変更数
        total_changes = 0
        for h in self.stack_history:
            changes = h.get('resourceChanges', {})
            total_changes += sum(changes.get(k, 0) for k in ['create', 'update', 'replace', 'delete'])
        
        avg_changes = total_changes / total if total > 0 else 0
        
        return {
            'total_deployments': total,
            'success_count': success_count,
            'failure_count': failure_count,
            'success_rate': round(success_rate, 1),
            'avg_changes': round(avg_changes, 1)
        }
    
    def get_total_resources_including_deleted(self) -> int:
        """削除されたリソースも含む総数を取得"""
        return len(self.resources_with_change_status)
