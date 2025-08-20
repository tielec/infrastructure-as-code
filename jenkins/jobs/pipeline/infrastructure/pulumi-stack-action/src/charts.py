"""
Chart generation for Pulumi reports
"""

from pathlib import Path
from typing import Dict, List
import matplotlib.pyplot as plt
import seaborn as sns


class ChartGenerator:
    """チャート生成の共通処理"""
    
    @staticmethod
    def save_figure(fig: plt.Figure, output_dir: Path, filename: str) -> str:
        """図を保存"""
        img_path = output_dir / filename
        fig.savefig(img_path, dpi=100, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        return filename
    
    @staticmethod
    def create_empty_chart(message: str, output_dir: Path) -> str:
        """空のチャートを作成"""
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, message, ha='center', va='center', 
               fontsize=12, color='#666', transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        filename = f'empty_chart_{hash(message) % 10000}.png'
        return ChartGenerator.save_figure(fig, output_dir, filename)


class ResourceDistributionChart:
    """リソース分布チャートの作成"""
    
    @staticmethod
    def create(resource_providers: Dict[str, int], resource_types: Dict[str, int], 
              output_dir: Path) -> str:
        """リソースプロバイダー分布の円グラフを作成"""
        if not resource_providers:
            return ChartGenerator.create_empty_chart(
                'No resources available', output_dir
            )
        
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            
            # プロバイダー別円グラフ
            ResourceDistributionChart._create_provider_pie_chart(ax1, resource_providers)
            
            # タイプ別棒グラフ
            ResourceDistributionChart._create_type_bar_chart(ax2, resource_types)
            
            plt.tight_layout()
            return ChartGenerator.save_figure(fig, output_dir, 'resource_distribution.png')
            
        except Exception as e:
            print(f"Error creating resource distribution chart: {e}")
            return None
    
    @staticmethod
    def _create_provider_pie_chart(ax, resource_providers: Dict[str, int]):
        """プロバイダー別円グラフを作成"""
        providers = list(resource_providers.keys())
        provider_counts = list(resource_providers.values())
        colors = plt.cm.Set3(range(len(providers)))
        
        wedges, texts, autotexts = ax.pie(
            provider_counts, labels=providers, autopct='%1.1f%%',
            colors=colors, startangle=90, textprops={'fontsize': 9}
        )
        ax.set_title('Resource Distribution by Provider', 
                    fontsize=12, fontweight='bold', pad=20)
    
    @staticmethod
    def _create_type_bar_chart(ax, resource_types: Dict[str, int]):
        """リソースタイプ別棒グラフを作成"""
        sorted_types = sorted(resource_types.items(), 
                            key=lambda x: x[1], reverse=True)[:10]
        if not sorted_types:
            return
            
        types, counts = zip(*sorted_types)
        
        bars = ax.barh(range(len(types)), counts, color=plt.cm.Purples(0.6))
        ax.set_yticks(range(len(types)))
        ax.set_yticklabels(types)
        ax.set_xlabel('Count', fontsize=10)
        ax.set_title('Top 10 Resource Types', fontsize=12, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, axis='x')
        
        # 値をバーの横に表示
        for bar, count in zip(bars, counts):
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                   str(count), ha='left', va='center', fontsize=9)


class DeploymentTrendsChart:
    """デプロイメントトレンドチャートの作成"""
    
    @staticmethod
    def create(stack_history: List[Dict], deployment_data: Dict[str, List], 
              output_dir: Path) -> str:
        """デプロイメント成功率と変更数の推移チャート"""
        if not stack_history:
            return ChartGenerator.create_empty_chart(
                'No history data available', output_dir
            )
        
        try:
            # 単一デプロイの場合は特別な処理
            if len(stack_history) == 1:
                return DeploymentTrendsChart._create_single_deployment_chart(
                    stack_history, deployment_data, output_dir
                )
            
            # 複数デプロイの場合は通常のトレンドチャート
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
            
            # 成功率のグラフ
            DeploymentTrendsChart._create_success_rate_chart(ax1, deployment_data)
            
            # 変更数のグラフ
            DeploymentTrendsChart._create_resource_changes_chart(ax2, deployment_data)
            
            plt.tight_layout()
            return ChartGenerator.save_figure(fig, output_dir, 'deployment_trends.png')
            
        except Exception as e:
            print(f"Error creating deployment trends chart: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def _create_single_deployment_chart(stack_history: List[Dict], 
                                      data: Dict[str, List], 
                                      output_dir: Path) -> str:
        """単一デプロイ用のチャート"""
        fig, ax = plt.subplots(figsize=(8, 5))
        
        # 現在のデプロイ情報を表示
        deployment = stack_history[0]
        result = deployment.get('result', 'unknown')
        changes = deployment.get('resourceChanges', {})
        
        # メトリクスデータ
        metrics = {
            'Status': 'Success' if result == 'succeeded' else 'Failed',
            'Created': changes.get('create', 0),
            'Updated': changes.get('update', 0) + changes.get('replace', 0),
            'Deleted': changes.get('delete', 0),
            'Unchanged': changes.get('same', 0)
        }
        
        # 棒グラフ
        labels = list(metrics.keys())
        values = list(metrics.values())
        
        # Statusは別扱い
        status_color = '#4CAF50' if metrics['Status'] == 'Success' else '#F44336'
        colors = [status_color, '#4CAF50', '#FF9800', '#F44336', '#9E9E9E']
        
        bars = ax.bar(range(len(labels)), 
                      [1 if i == 0 else v for i, v in enumerate(values)],
                      color=colors, alpha=0.8)
        
        # 値をバーの上に表示
        for i, (bar, label, value) in enumerate(zip(bars, labels, values)):
            if i == 0:  # Status
                ax.text(bar.get_x() + bar.get_width()/2., 0.5,
                       value, ha='center', va='center',
                       fontsize=14, fontweight='bold', color='white')
            else:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                       str(value), ha='center', va='bottom',
                       fontsize=12, fontweight='bold')
        
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=11)
        ax.set_ylabel('Count', fontsize=12)
        ax.set_title('Deployment Summary', fontsize=14, fontweight='bold', pad=20)
        ax.set_ylim(0, max(max(values[1:]) * 1.2, 10) if values[1:] else 10)
        ax.grid(True, alpha=0.3, axis='y')
        
        # タイムスタンプを追加
        timestamp = data['timestamps'][0] if data['timestamps'] else 'N/A'
        ax.text(0.98, 0.02, f'Deployment: {timestamp}', 
               transform=ax.transAxes, ha='right', va='bottom',
               fontsize=9, color='#666')
        
        return ChartGenerator.save_figure(fig, output_dir, 'deployment_trends.png')
    
    @staticmethod
    def _create_success_rate_chart(ax, data: Dict[str, List]):
        """成功率チャートを作成"""
        x = range(len(data['timestamps']))
        success_pct = [s * 100 for s in data['success_rate']]
        success_ma_pct = [s * 100 for s in data['success_ma']]
        
        ax.plot(x, success_pct, 'o-', color='#4CAF50', 
               label='Success Rate', markersize=6)
        
        # 移動平均は3件以上の場合のみ表示
        if len(data['timestamps']) >= 3:
            ax.plot(x, success_ma_pct, '--', color='#2196F3', 
                   label='3-Deploy Moving Avg', linewidth=2)
        
        ax.fill_between(x, 0, success_pct, alpha=0.3, color='#4CAF50')
        
        ax.set_ylabel('Success Rate (%)', fontsize=10)
        ax.set_title('Deployment Success Rate Trend', fontsize=12, fontweight='bold')
        ax.set_ylim(-5, 105)
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3)
    
    @staticmethod
    def _create_resource_changes_chart(ax, data: Dict[str, List]):
        """リソース変更チャートを作成"""
        x = range(len(data['timestamps']))
        width = 0.6
        
        # 積み上げ棒グラフ
        ax.bar(x, data['creates'], width, label='Create', 
              color='#4CAF50', alpha=0.8)
        ax.bar(x, data['updates'], width, bottom=data['creates'], 
              label='Update/Replace', color='#FF9800', alpha=0.8)
        ax.bar(x, data['deletes'], width,
              bottom=[c + u for c, u in zip(data['creates'], data['updates'])],
              label='Delete', color='#F44336', alpha=0.8)
        
        # 合計変更数のライン
        ax_twin = ax.twinx()
        ax_twin.plot(x, data['total_changes'], 'k-', marker='D', 
                    markersize=5, label='Total Changes', linewidth=2)
        
        ax.set_xlabel('Deployment', fontsize=10)
        ax.set_ylabel('Resource Changes', fontsize=10)
        ax_twin.set_ylabel('Total Changes', fontsize=10)
        ax.set_title('Resource Changes per Deployment', fontsize=12, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(data['timestamps'], rotation=45, ha='right', fontsize=7)
        ax.legend(loc='upper left')
        ax_twin.legend(loc='upper right')
        ax.grid(True, alpha=0.3, axis='y')


class ResourceSummaryChart:
    """リソースサマリーチャートの作成（実行前後の比較対応）"""
    
    @staticmethod
    def create(stats: Dict[str, int], stack_outputs: Dict, stack_config: Dict,
              action_type: str, output_dir: Path, change_summary: Dict = None) -> str:
        """リソースサマリーチャート（実行前後の比較表示）"""
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # 実行前後の比較データがある場合
            if change_summary:
                ResourceSummaryChart._create_comparison_chart(
                    ax, stats, stack_outputs, stack_config, action_type, change_summary
                )
            else:
                # 従来の単一状態表示
                ResourceSummaryChart._create_simple_chart(
                    ax, stats, stack_outputs, stack_config, action_type
                )
            
            plt.tight_layout()
            return ChartGenerator.save_figure(fig, output_dir, 'resource_summary.png')
            
        except Exception as e:
            print(f"Error creating resource summary chart: {e}")
            return None
    
    @staticmethod
    def _create_comparison_chart(ax, stats: Dict[str, int], stack_outputs: Dict, 
                               stack_config: Dict, action_type: str, 
                               change_summary: Dict):
        """実行前後の比較チャートを作成"""
        # 変更内訳のデータ
        change_categories = ['Added', 'Updated', 'Deleted', 'Unchanged']
        change_values = [
            change_summary.get('added', 0),
            change_summary.get('updated', 0),
            change_summary.get('deleted', 0),
            change_summary.get('unchanged', 0)
        ]
        change_colors = ['#4CAF50', '#FF9800', '#F44336', '#9E9E9E']
        
        # 実行前後の総数
        before_total = change_summary.get('before_total', 0)
        after_total = change_summary.get('after_total', 0)
        
        # figureを取得
        fig = ax.figure
        
        # 2つのサブプロット：左は変更内訳、右はメトリクス
        ax1 = plt.subplot(1, 2, 1)
        ax2 = plt.subplot(1, 2, 2)
        
        # 左側：変更内訳の円グラフ
        wedges, texts, autotexts = ax1.pie(
            change_values, labels=change_categories, colors=change_colors,
            autopct=lambda pct: f'{int(pct/100.*sum(change_values))}' if pct > 0 else '',
            startangle=90, textprops={'fontsize': 10}
        )
        
        ax1.set_title(f'Resource Changes\n{before_total} → {after_total} resources', 
                     fontsize=12, fontweight='bold')
        
        # 右側：メトリクスバー
        metrics = {
            'Stack\nOutputs': len(stack_outputs) if stack_outputs else 0,
            'Config\nItems': len(stack_config) if stack_config else 0,
            'Resource\nTypes': stats['resource_types_count'],
            'Providers': stats['resource_providers_count']
        }
        
        labels = list(metrics.keys())
        values = list(metrics.values())
        colors = ['#B39DDB', '#D1C4E9', '#9575CD', '#7E57C2']
        
        bars = ax2.bar(labels, values, color=colors[:len(labels)], 
                       edgecolor='black', linewidth=1)
        
        # 値をバーの上に表示
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    str(value), ha='center', va='bottom', 
                    fontsize=12, fontweight='bold')
        
        ax2.set_ylabel('Count', fontsize=11)
        ax2.set_title('Stack Metrics (Post-Action)', fontsize=12, fontweight='bold')
        ax2.set_ylim(0, max(values) * 1.2 if values else 10)
        ax2.grid(True, alpha=0.3, axis='y')
        
        # アクションタイプを表示
        fig.suptitle(f'Stack Summary - {action_type.upper()} Action', 
                    fontsize=14, fontweight='bold',
                    color='#F44336' if action_type == 'destroy' else '#4CAF50')
    
    @staticmethod
    def _create_simple_chart(ax, stats: Dict[str, int], stack_outputs: Dict, 
                           stack_config: Dict, action_type: str):
        """従来のシンプルなチャート（後方互換性のため）"""
        metrics = {
            'Total\nResources': stats['total_resources'],
            'Resource\nTypes': stats['resource_types_count'],
            'Providers': stats['resource_providers_count'],
            'Stack\nOutputs': len(stack_outputs) if stack_outputs else 0,
            'Config\nItems': len(stack_config) if stack_config else 0
        }
        
        labels = list(metrics.keys())
        values = list(metrics.values())
        
        colors = ['#512DA8', '#7E57C2', '#9575CD', '#B39DDB', '#D1C4E9']
        bars = ax.bar(labels, values, color=colors[:len(labels)], 
                      edgecolor='black', linewidth=1)
        
        # 値をバーの上に表示
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                   str(value), ha='center', va='bottom', 
                   fontsize=14, fontweight='bold')
        
        ax.set_ylabel('Count', fontsize=12)
        title = ('Stack Summary (Before Destruction)' if action_type == 'destroy' 
                else 'Stack Summary')
        color = '#F44336' if action_type == 'destroy' else 'black'
        ax.set_title(title, fontsize=14, fontweight='bold', color=color)
        ax.set_ylim(0, max(values) * 1.2 if values else 10)
        ax.grid(True, alpha=0.3, axis='y')
        
        # アクションタイプラベルを追加
        action_text = 'DESTROYED' if action_type == 'destroy' else 'DEPLOYED'
        color = '#F44336' if action_type == 'destroy' else '#4CAF50'
        
        ax.text(0.98, 0.98, action_text, transform=ax.transAxes,
               fontsize=12, fontweight='bold', color=color,
               ha='right', va='top',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))
