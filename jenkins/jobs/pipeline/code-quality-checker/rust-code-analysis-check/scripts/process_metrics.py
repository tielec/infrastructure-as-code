#!/usr/bin/env python3
"""
Rust Code Analysis Metrics Processor
rust-code-analysisの出力を処理し、集計データを生成する
"""

import json
import os
import argparse
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd


class MetricsProcessor:
    def __init__(self, args):
        self.json_dir = args.json_dir
        self.metrics_dir = args.metrics_dir
        self.output_dir = args.output_dir
        self.cyclomatic_threshold = int(args.cyclomatic_threshold)
        self.cognitive_threshold = int(args.cognitive_threshold)
        self.min_lines = int(args.min_lines)
        
    def load_json_file(self, filepath: str) -> Dict[str, Any]:
        """JSONファイルを読み込む"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            return {}
    
    def extract_metrics_from_file(self, data: Dict[str, Any], filepath: str = "") -> List[Dict[str, Any]]:
        """rust-code-analysisの出力から関数レベルのメトリクスを抽出"""
        metrics = []
        
        def process_space(space: Dict[str, Any], file_path: str, parent_name: str = ""):
            """再帰的にスペース（関数、クラスなど）を処理"""
            if not isinstance(space, dict):
                return
            
            # メトリクスの取得
            metrics_data = space.get('metrics', {})
            
            # 関数名の構築
            name = space.get('name', 'unknown')
            if parent_name:
                full_name = f"{parent_name}::{name}"
            else:
                full_name = name
            
            # 関数の場合のみメトリクスを記録
            kind = space.get('kind', '')
            if kind in ['function', 'method', 'constructor', 'destructor']:
                cyclomatic = metrics_data.get('cyclomatic', {}).get('sum', 0)
                cognitive = metrics_data.get('cognitive', {}).get('sum', 0)
                sloc = metrics_data.get('loc', {}).get('sloc', 0)
                
                # Halsteadメトリクス
                halstead = metrics_data.get('halstead', {})
                halstead_volume = halstead.get('volume', 0)
                halstead_difficulty = halstead.get('difficulty', 0)
                halstead_effort = halstead.get('effort', 0)
                
                # Maintainability Index
                mi = metrics_data.get('mi', {}).get('mi_original', 0)
                
                metric_entry = {
                    'file': file_path,
                    'function': full_name,
                    'kind': kind,
                    'cyclomatic': cyclomatic,
                    'cognitive': cognitive,
                    'sloc': sloc,
                    'halstead_volume': halstead_volume,
                    'halstead_difficulty': halstead_difficulty,
                    'halstead_effort': halstead_effort,
                    'maintainability_index': mi,
                    'start_line': space.get('start_line', 0),
                    'end_line': space.get('end_line', 0)
                }
                
                metrics.append(metric_entry)
            
            # 子要素の処理
            spaces = space.get('spaces', [])
            if isinstance(spaces, list):
                for child_space in spaces:
                    process_space(child_space, file_path, full_name)
        
        # ルートレベルの処理
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    file_name = item.get('name', filepath)
                    process_space(item, file_name)
        elif isinstance(data, dict):
            file_name = data.get('name', filepath)
            process_space(data, file_name)
        
        return metrics
    
    def process_all_metrics(self) -> pd.DataFrame:
        """すべてのメトリクスファイルを処理"""
        all_metrics = []
        
        # メトリクスディレクトリ内のすべてのJSONファイルを処理
        metrics_path = Path(self.metrics_dir)
        for json_file in metrics_path.glob('*.json'):
            data = self.load_json_file(str(json_file))
            if data:
                metrics = self.extract_metrics_from_file(data, str(json_file.stem))
                all_metrics.extend(metrics)
        
        # 全体解析ファイルも処理
        all_metrics_file = Path(self.json_dir) / 'metrics_all.json'
        if all_metrics_file.exists():
            data = self.load_json_file(str(all_metrics_file))
            if data:
                metrics = self.extract_metrics_from_file(data)
                all_metrics.extend(metrics)
        
        # DataFrameに変換
        df = pd.DataFrame(all_metrics)
        
        # 重複の除去（同じファイル・関数の組み合わせ）
        if not df.empty:
            df = df.drop_duplicates(subset=['file', 'function', 'start_line'])
        
        return df
    
    def calculate_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """統計情報を計算"""
        if df.empty:
            return {
                'total_files': 0,
                'total_functions': 0,
                'complex_functions_cyclomatic': 0,
                'complex_functions_cognitive': 0,
                'average_cyclomatic': 0,
                'average_cognitive': 0,
                'max_cyclomatic': 0,
                'max_cognitive': 0,
                'average_maintainability': 0,
                'functions_by_language': {}
            }
        
        # 言語別の統計
        language_stats = {}
        for _, row in df.iterrows():
            # ファイル拡張子から言語を推定
            file_ext = Path(row['file']).suffix.lower()
            lang_map = {
                '.rs': 'rust',
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.java': 'java',
                '.cpp': 'cpp',
                '.c': 'c',
                '.go': 'go',
                '.php': 'php',
                '.rb': 'ruby',
                '.cs': 'csharp',
                '.kt': 'kotlin',
                '.swift': 'swift',
                '.scala': 'scala'
            }
            lang = lang_map.get(file_ext, 'other')
            
            if lang not in language_stats:
                language_stats[lang] = {'count': 0, 'complex': 0}
            
            language_stats[lang]['count'] += 1
            if row['cyclomatic'] > self.cyclomatic_threshold or row['cognitive'] > self.cognitive_threshold:
                language_stats[lang]['complex'] += 1
        
        # 全体統計
        stats = {
            'total_files': df['file'].nunique(),
            'total_functions': len(df),
            'complex_functions_cyclomatic': len(df[df['cyclomatic'] > self.cyclomatic_threshold]),
            'complex_functions_cognitive': len(df[df['cognitive'] > self.cognitive_threshold]),
            'average_cyclomatic': df['cyclomatic'].mean(),
            'average_cognitive': df['cognitive'].mean(),
            'max_cyclomatic': df['cyclomatic'].max(),
            'max_cognitive': df['cognitive'].max(),
            'average_maintainability': df['maintainability_index'].mean(),
            'functions_by_language': language_stats
        }
        
        return stats
    
    def save_processed_data(self, df: pd.DataFrame, stats: Dict[str, Any]):
        """処理済みデータを保存"""
        output_path = Path(self.output_dir)
        
        # CSV形式で保存（Lizard形式と互換性を持たせる）
        csv_path = output_path / 'metrics_processed.csv'
        if not df.empty:
            # カラム名をLizard形式に合わせる
            df_export = df.copy()
            df_export = df_export.rename(columns={
                'cyclomatic': 'CCN',
                'sloc': 'nloc',
                'function': 'function_name'
            })
            
            # 必要なカラムを追加
            df_export['PARAM'] = 0  # rust-code-analysisはパラメータ数を提供しないため
            df_export['token_count'] = 0
            df_export['length'] = df_export['nloc']
            df_export['location'] = df_export['file'] + ':' + df_export['start_line'].astype(str)
            df_export['long_name'] = df_export['function_name']
            
            # Lizardと同じカラム順序
            columns_order = ['nloc', 'CCN', 'token_count', 'PARAM', 'length', 'location', 
                        'file', 'function_name', 'long_name', 'start_line', 'end_line']
            
            # 追加のメトリクス（重要：カラム名を確認）
            additional_metrics = ['cognitive', 'halstead_volume', 'halstead_difficulty', 
                                'halstead_effort', 'maintainability_index']
            for col in additional_metrics:
                if col in df_export.columns:
                    columns_order.append(col)
                    print(f"Added metric column: {col}")
                else:
                    print(f"Warning: Expected column '{col}' not found in data")
            
            # データの存在確認
            print(f"DataFrame shape: {df_export.shape}")
            print(f"Available columns: {list(df_export.columns)}")
            print(f"Final column order: {columns_order}")
            
            # 存在するカラムのみを選択
            existing_columns = [col for col in columns_order if col in df_export.columns]
            df_export = df_export[existing_columns]
            
            # サンプルデータの確認
            if len(df_export) > 0:
                sample_row = df_export.iloc[0]
                print("Sample row data:")
                for col in ['cognitive', 'halstead_volume', 'halstead_difficulty', 'maintainability_index']:
                    if col in sample_row:
                        print(f"  {col}: {sample_row[col]}")
            
            df_export.to_csv(csv_path, index=False)
        
        # 統計情報をJSON形式で保存
        summary_path = output_path / 'summary.json'
        with open(summary_path, 'w') as f:
            json.dump(stats, f, indent=2)
        
        # 複雑な関数のリストを保存
        complex_functions_path = output_path / 'complex_functions.json'
        if not df.empty:
            complex_df = df[
                (df['cyclomatic'] > self.cyclomatic_threshold) | 
                (df['cognitive'] > self.cognitive_threshold)
            ].sort_values(['cyclomatic', 'cognitive'], ascending=False)
            
            complex_list = complex_df.to_dict('records')
            with open(complex_functions_path, 'w') as f:
                json.dump(complex_list, f, indent=2)
        
        print(f"Processed data saved:")
        print(f"  - CSV: {csv_path}")
        print(f"  - Summary: {summary_path}")
        print(f"  - Complex functions: {complex_functions_path}")
        print(f"  - Total functions analyzed: {stats['total_functions']}")
        print(f"  - Complex functions (cyclomatic): {stats['complex_functions_cyclomatic']}")
        print(f"  - Complex functions (cognitive): {stats['complex_functions_cognitive']}")


def main():
    parser = argparse.ArgumentParser(description='Process rust-code-analysis metrics')
    parser.add_argument('--json-dir', required=True, help='Directory containing JSON files')
    parser.add_argument('--metrics-dir', required=True, help='Directory containing individual metric files')
    parser.add_argument('--output-dir', required=True, help='Output directory')
    parser.add_argument('--cyclomatic-threshold', required=True, help='Cyclomatic complexity threshold')
    parser.add_argument('--cognitive-threshold', required=True, help='Cognitive complexity threshold')
    parser.add_argument('--min-lines', required=True, help='Minimum lines threshold')
    
    args = parser.parse_args()
    
    processor = MetricsProcessor(args)
    
    # メトリクスの処理
    df = processor.process_all_metrics()
    
    # 統計の計算
    stats = processor.calculate_statistics(df)
    
    # データの保存
    processor.save_processed_data(df, stats)


if __name__ == '__main__':
    main()
