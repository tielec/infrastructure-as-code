"""
Main report generator for Pulumi deployments
"""

from pathlib import Path
from typing import Dict
from jinja2 import Environment, FileSystemLoader

from config import MatplotlibConfig
from data_processor import DataProcessor
from graph_processor import DependencyGraphProcessor
from charts import ResourceDistributionChart, DeploymentTrendsChart, ResourceSummaryChart


class PulumiReportGenerator:
    def __init__(self, args):
        self.artifacts_dir = args.artifacts_dir
        self.output_dir = args.output_dir
        self.template_dir = args.template_dir
        self.stack_name = args.stack_name
        self.project_path = args.project_path
        self.branch = args.branch
        self.build_number = args.build_number
        self.timestamp = args.timestamp
        self.action_type = args.action_type
        
        # Matplotlibの設定
        MatplotlibConfig.setup()
        
        # データプロセッサーとグラフプロセッサーの初期化
        self.data_processor = DataProcessor(self.artifacts_dir)
        self.graph_processor = DependencyGraphProcessor(self.artifacts_dir, self.output_dir)
    
    def generate_report(self):
        """HTMLレポートを生成"""
        print("Loading JSON data...")
        self.data_processor.load_json_data()
        
        print("Processing resources...")
        self.data_processor.process_resources()
        
        print("Processing dependency graph...")
        # 依存関係グラフはpost-actionのリソースを使用
        dependency_graph = self.graph_processor.process_graph(
            self.data_processor.resources,  # post-action resources
            self.data_processor.resource_providers,  # post-action providers
            self.stack_name
        )
        
        print("Creating charts...")
        resource_chart = self._create_resource_distribution_chart()
        trends_chart = self._create_deployment_trends_chart()
        summary_chart = self._create_resource_summary_chart()
        
        print("Generating HTML report...")
        self._generate_html_report(
            dependency_graph, resource_chart, trends_chart, summary_chart
        )
    
    def _create_resource_distribution_chart(self) -> str:
        """リソース分布チャートを作成（post-actionのデータを使用）"""
        return ResourceDistributionChart.create(
            self.data_processor.resource_providers,
            self.data_processor.resource_types,
            Path(self.output_dir)
        )
    
    def _create_deployment_trends_chart(self) -> str:
        """デプロイメントトレンドチャートを作成"""
        deployment_data = self.data_processor.prepare_deployment_data()
        return DeploymentTrendsChart.create(
            self.data_processor.stack_history,
            deployment_data,
            Path(self.output_dir)
        )
    
    def _create_resource_summary_chart(self) -> str:
        """リソースサマリーチャートを作成（実行前後の比較対応）"""
        return ResourceSummaryChart.create(
            self.data_processor.stats,
            self.data_processor.stack_outputs,
            self.data_processor.stack_config,
            self.action_type,
            Path(self.output_dir),
            self.data_processor.change_summary  # 新しいパラメータ
        )
    
    def _generate_html_report(self, dependency_graph: str, resource_chart: str,
                            trends_chart: str, summary_chart: str):
        """HTMLレポートを生成"""
        # Jinja2環境の設定
        env = Environment(loader=FileSystemLoader(self.template_dir))
        template = env.get_template('pulumi_report.html')
        
        # テンプレートに渡すデータ
        context = self._prepare_template_context(
            dependency_graph, resource_chart, trends_chart, summary_chart
        )
        
        # HTMLの生成と保存
        html_content = template.render(**context)
        output_path = Path(self.output_dir) / 'index.html'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Report generated successfully: {output_path}")
    
    def _prepare_template_context(self, dependency_graph: str, resource_chart: str,
                                trends_chart: str, summary_chart: str) -> Dict:
        """テンプレートコンテキストを準備"""
        latest_deployment = self.data_processor.stack_history[0] if self.data_processor.stack_history else {}
        deployment_stats = self.data_processor.calculate_deployment_stats()
        
        # 基本コンテキスト（既存）
        context = {
            'stack_name': self.stack_name,
            'project_path': self.project_path,
            'branch': self.branch,
            'build_number': self.build_number,
            'timestamp': self.timestamp,
            'action_type': self.action_type,
            'total_resources': self.data_processor.stats['total_resources'],
            'resource_types_count': self.data_processor.stats['resource_types_count'],
            'resource_providers_count': self.data_processor.stats['resource_providers_count'],
            'deployment_time': self.data_processor.stats['deployment_time'],
            'pulumi_version': self.data_processor.stats['pulumi_version'],
            'resources': self.data_processor.resources,  # 互換性のため残す
            'resource_types': self.data_processor.resource_types,
            'resource_providers': self.data_processor.resource_providers,
            'stack_config': self.data_processor.stack_config,
            'stack_outputs': self.data_processor.stack_outputs,
            'deployment_history': self.data_processor.stack_history[:10],
            'latest_deployment': latest_deployment,
            'deployment_stats': deployment_stats,
            'resource_chart': resource_chart,
            'trends_chart': trends_chart,
            'summary_chart': summary_chart,
            'dependency_graph': dependency_graph
        }
        
        # 新しい実行前後比較データを追加
        context.update({
            'change_summary': self.data_processor.change_summary,
            'metrics_comparison': self.data_processor.metrics_comparison,
            'resources_with_change_status': self.data_processor.resources_with_change_status,
            'total_resources_all': self.data_processor.get_total_resources_including_deleted()
        })
        
        return context
