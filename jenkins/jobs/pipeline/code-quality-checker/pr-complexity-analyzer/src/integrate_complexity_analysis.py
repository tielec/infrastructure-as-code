#!/usr/bin/env python3
"""
PR Complexity Analysis Integration
rust-code-analysisの出力を処理し、PR内の複雑度を分析する
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
import sys
import traceback


@dataclass
class FunctionMetrics:
    """関数のメトリクス情報"""
    file: str
    name: str
    start_line: int
    end_line: int
    cyclomatic: int
    cognitive: int
    sloc: int
    halstead_volume: float = 0.0
    halstead_difficulty: float = 0.0
    maintainability_index: float = 0.0
    
    def is_complex(self, cyclomatic_threshold: int, cognitive_threshold: int) -> bool:
        """複雑度が閾値を超えているかチェック"""
        return self.cyclomatic > cyclomatic_threshold or self.cognitive > cognitive_threshold


@dataclass
class FileAnalysis:
    """ファイル単位の解析結果"""
    filename: str
    functions: List[FunctionMetrics] = field(default_factory=list)
    total_functions: int = 0
    complex_functions_cyclomatic: int = 0
    complex_functions_cognitive: int = 0
    max_cyclomatic: int = 0
    max_cognitive: int = 0
    average_cyclomatic: float = 0.0
    average_cognitive: float = 0.0


class MetricsExtractor:
    """メトリクス抽出を担当するクラス"""
    
    @staticmethod
    def get_metric_value(metrics_data: Dict[str, Any], metric_name: str, default: Any = 0) -> Any:
        """メトリクスデータから安全に値を取得"""
        metric = metrics_data.get(metric_name, {})
        if isinstance(metric, dict):
            return metric.get('sum', metric.get('value', default))
        return default
    
    @staticmethod
    def extract_function_data(space: Dict[str, Any], file_path: str, parent_name: str) -> Optional[FunctionMetrics]:
        """単一の関数からメトリクスを抽出"""
        kind = space.get('kind', '')
        if kind not in ['function', 'method', 'constructor', 'destructor']:
            return None
        
        name = space.get('name', 'unknown')
        full_name = f"{parent_name}::{name}" if parent_name else name
        
        metrics_data = space.get('metrics', {})
        
        return FunctionMetrics(
            file=file_path,
            name=full_name,
            start_line=space.get('start_line', 0),
            end_line=space.get('end_line', 0),
            cyclomatic=MetricsExtractor.get_metric_value(metrics_data, 'cyclomatic'),
            cognitive=MetricsExtractor.get_metric_value(metrics_data, 'cognitive'),
            sloc=MetricsExtractor.get_metric_value(metrics_data.get('loc', {}), 'sloc'),
            halstead_volume=MetricsExtractor.get_metric_value(metrics_data.get('halstead', {}), 'volume'),
            halstead_difficulty=MetricsExtractor.get_metric_value(metrics_data.get('halstead', {}), 'difficulty'),
            maintainability_index=MetricsExtractor.get_metric_value(metrics_data.get('mi', {}), 'mi_original')
        )


class SpaceProcessor:
    """スペース（関数、クラスなど）の処理を担当するクラス"""
    
    def __init__(self):
        self.metrics_extractor = MetricsExtractor()
        self.functions = []
    
    def process_space(self, space: Dict[str, Any], file_path: str, parent_name: str = "") -> None:
        """スペースを処理してメトリクスを抽出"""
        if not isinstance(space, dict):
            return
        
        # 現在のスペースから関数メトリクスを抽出
        func_metrics = self._extract_current_space_metrics(space, file_path, parent_name)
        if func_metrics:
            self.functions.append(func_metrics)
            self._log_function_found(func_metrics)
        
        # 子スペースを処理
        self._process_child_spaces(space, file_path, parent_name)
    
    def _extract_current_space_metrics(self, space: Dict[str, Any], file_path: str, parent_name: str) -> Optional[FunctionMetrics]:
        """現在のスペースからメトリクスを抽出"""
        return self.metrics_extractor.extract_function_data(space, file_path, parent_name)
    
    def _process_child_spaces(self, space: Dict[str, Any], file_path: str, parent_name: str) -> None:
        """子スペースを再帰的に処理"""
        spaces = space.get('spaces', [])
        if not isinstance(spaces, list):
            return
        
        name = space.get('name', 'unknown')
        full_name = f"{parent_name}::{name}" if parent_name else name
        
        for child_space in spaces:
            self.process_space(child_space, file_path, full_name)
    
    def _log_function_found(self, func_metrics: FunctionMetrics) -> None:
        """見つかった関数のログを出力"""
        print(f"Found function: {func_metrics.name} in {func_metrics.file} "
              f"(cyclo: {func_metrics.cyclomatic}, cogn: {func_metrics.cognitive})")
    
    def get_functions(self) -> List[FunctionMetrics]:
        """抽出された関数のリストを返す"""
        return self.functions


class ComplexityAnalyzer:
    def __init__(self, cyclomatic_threshold: int = 15, cognitive_threshold: int = 20):
        self.cyclomatic_threshold = cyclomatic_threshold
        self.cognitive_threshold = cognitive_threshold
        
    def load_metrics(self, metrics_file: str) -> Dict[str, Any]:
        """rust-code-analysisの出力を読み込む"""
        try:
            with open(metrics_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    print(f"Warning: Metrics file {metrics_file} is empty")
                    return []
                
                data = json.loads(content)
                self._log_loaded_data(data)
                return data
                
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from {metrics_file}: {e}")
            print(f"File content (first 200 chars): {content[:200] if 'content' in locals() else 'Unable to read'}")
            return []
        except Exception as e:
            print(f"Error loading metrics file {metrics_file}: {e}")
            return []
    
    def _log_loaded_data(self, data: Any) -> None:
        """読み込んだデータのログを出力"""
        print(f"Loaded metrics data type: {type(data)}")
        if isinstance(data, list):
            print(f"Number of items: {len(data)}")
        elif isinstance(data, dict):
            print(f"Keys: {list(data.keys())}")
    
    def extract_function_metrics(self, data: Dict[str, Any]) -> List[FunctionMetrics]:
        """rust-code-analysisの出力から関数メトリクスを抽出"""
        processor = SpaceProcessor()
        
        # データの処理
        self._process_data(data, processor)
        
        functions = processor.get_functions()
        print(f"Total functions extracted: {len(functions)}")
        return functions
    
    def _process_data(self, data: Any, processor: SpaceProcessor) -> None:
        """データ構造に応じて処理を分岐"""
        if isinstance(data, list):
            self._process_list_data(data, processor)
        elif isinstance(data, dict):
            self._process_dict_data(data, processor)
    
    def _process_list_data(self, data: List[Any], processor: SpaceProcessor) -> None:
        """リスト形式のデータを処理"""
        for item in data:
            if isinstance(item, dict):
                file_name = item.get('name', '')
                print(f"Processing file: {file_name}")
                processor.process_space(item, file_name)
    
    def _process_dict_data(self, data: Dict[str, Any], processor: SpaceProcessor) -> None:
        """辞書形式のデータを処理"""
        file_name = data.get('name', '')
        print(f"Processing single file: {file_name}")
        processor.process_space(data, file_name)
    
    def analyze_files(self, functions: List[FunctionMetrics], changed_files: List[str]) -> Dict[str, FileAnalysis]:
        """ファイル単位で解析結果をまとめる"""
        file_analyses = {}
        
        print(f"Analyzing {len(functions)} functions from {len(changed_files)} changed files")
        
        for func in functions:
            if not self._is_function_in_changed_files(func, changed_files):
                print(f"Skipping function in {func.file} (not in changed files)")
                continue
            
            # ファイル解析の更新
            self._update_file_analysis(file_analyses, func)
        
        # 平均値の計算
        self._calculate_averages(file_analyses)
        
        print(f"File analyses created: {len(file_analyses)}")
        return file_analyses
    
    def _is_function_in_changed_files(self, func: FunctionMetrics, changed_files: List[str]) -> bool:
        """関数が変更されたファイルに含まれているかチェック"""
        for cf in changed_files:
            if func.file.endswith(cf) or cf.endswith(func.file) or func.file == cf:
                return True
        return False
    
    def _update_file_analysis(self, file_analyses: Dict[str, FileAnalysis], func: FunctionMetrics) -> None:
        """ファイル解析を更新"""
        if func.file not in file_analyses:
            file_analyses[func.file] = FileAnalysis(filename=func.file)
        
        analysis = file_analyses[func.file]
        analysis.functions.append(func)
        analysis.total_functions += 1
        
        # 複雑度チェック
        if func.cyclomatic > self.cyclomatic_threshold:
            analysis.complex_functions_cyclomatic += 1
        if func.cognitive > self.cognitive_threshold:
            analysis.complex_functions_cognitive += 1
        
        # 最大値の更新
        analysis.max_cyclomatic = max(analysis.max_cyclomatic, func.cyclomatic)
        analysis.max_cognitive = max(analysis.max_cognitive, func.cognitive)
    
    def _calculate_averages(self, file_analyses: Dict[str, FileAnalysis]) -> None:
        """各ファイルの平均値を計算"""
        for analysis in file_analyses.values():
            if analysis.total_functions > 0:
                analysis.average_cyclomatic = sum(f.cyclomatic for f in analysis.functions) / analysis.total_functions
                analysis.average_cognitive = sum(f.cognitive for f in analysis.functions) / analysis.total_functions
    
    def generate_summary(self, file_analyses: Dict[str, FileAnalysis], pr_info: Dict[str, Any]) -> Dict[str, Any]:
        """全体のサマリーを生成"""
        all_functions = self._collect_all_functions(file_analyses)
        high_complexity_functions = self._get_high_complexity_functions(all_functions)
        
        # 全関数の情報も保存（警告レベルの関数を特定できるように）
        all_functions_data = [
            {
                'file': f.file,
                'name': f.name,
                'cyclomatic': f.cyclomatic,
                'cognitive': f.cognitive,
                'lines': f.sloc,
                'start_line': f.start_line,
                'end_line': f.end_line
            }
            for f in all_functions
        ]
        
        return {
            'pr_number': pr_info.get('number'),
            'pr_title': pr_info.get('title'),
            'total_files_analyzed': len(file_analyses),
            'total_functions': len(all_functions),
            'high_complexity_functions_cyclomatic': sum(1 for f in all_functions if f.cyclomatic > self.cyclomatic_threshold),
            'high_complexity_functions_cognitive': sum(1 for f in all_functions if f.cognitive > self.cognitive_threshold),
            'thresholds': {
                'cyclomatic': self.cyclomatic_threshold,
                'cognitive': self.cognitive_threshold
            },
            'file_analyses': self._create_file_analyses_summary(file_analyses),
            'high_complexity_functions': high_complexity_functions[:20],  # 上位20件
            'all_functions': all_functions_data  # 全関数の情報を追加
        }
    
    def _collect_all_functions(self, file_analyses: Dict[str, FileAnalysis]) -> List[FunctionMetrics]:
        """全ての関数を収集"""
        all_functions = []
        for analysis in file_analyses.values():
            all_functions.extend(analysis.functions)
        return all_functions
    
    def _get_high_complexity_functions(self, functions: List[FunctionMetrics]) -> List[Dict[str, Any]]:
        """高複雑度関数のリストを生成"""
        high_complexity = [
            {
                'file': f.file,
                'name': f.name,
                'cyclomatic': f.cyclomatic,
                'cognitive': f.cognitive,
                'lines': f.sloc,
                'start_line': f.start_line,
                'end_line': f.end_line
            }
            for f in functions
            if f.is_complex(self.cyclomatic_threshold, self.cognitive_threshold)
        ]
        
        # 認知的複雑度でソート
        high_complexity.sort(key=lambda x: x['cognitive'], reverse=True)
        return high_complexity
    
    def _create_file_analyses_summary(self, file_analyses: Dict[str, FileAnalysis]) -> Dict[str, Any]:
        """ファイル解析のサマリーを作成"""
        return {
            filename: {
                'total_functions': analysis.total_functions,
                'complex_functions_cyclomatic': analysis.complex_functions_cyclomatic,
                'complex_functions_cognitive': analysis.complex_functions_cognitive,
                'max_cyclomatic': analysis.max_cyclomatic,
                'max_cognitive': analysis.max_cognitive,
                'average_cyclomatic': round(analysis.average_cyclomatic, 2),
                'average_cognitive': round(analysis.average_cognitive, 2)
            }
            for filename, analysis in file_analyses.items()
        }


def main():
    parser = argparse.ArgumentParser(description='Analyze complexity metrics for PR')
    parser.add_argument('--metrics-file', required=True, help='rust-code-analysis output JSON file')
    parser.add_argument('--pr-info', required=True, help='PR info JSON file')
    parser.add_argument('--pr-diff', required=True, help='PR diff JSON file')
    parser.add_argument('--output', required=True, help='Output JSON file')
    parser.add_argument('--cyclomatic-threshold', type=int, default=15, help='Cyclomatic complexity threshold')
    parser.add_argument('--cognitive-threshold', type=int, default=20, help='Cognitive complexity threshold')
    
    args = parser.parse_args()
    
    try:
        # 解析器の初期化
        analyzer = ComplexityAnalyzer(
            cyclomatic_threshold=args.cyclomatic_threshold,
            cognitive_threshold=args.cognitive_threshold
        )
        
        # PR情報の読み込み
        print(f"Loading PR info from {args.pr_info}")
        with open(args.pr_info, 'r', encoding='utf-8') as f:
            pr_info = json.load(f)
        
        # PR差分の読み込み（変更されたファイルのリストを取得）
        print(f"Loading PR diff from {args.pr_diff}")
        with open(args.pr_diff, 'r', encoding='utf-8') as f:
            pr_diff = json.load(f)
        
        changed_files = [item['filename'] for item in pr_diff]
        
        # メトリクスの読み込みと解析
        print(f"Loading metrics from {args.metrics_file}")
        metrics_data = analyzer.load_metrics(args.metrics_file)
        
        if not metrics_data:
            print("Warning: No metrics data found. Creating empty result.")
            # 空の結果を作成
            summary = {
                'pr_number': pr_info.get('number'),
                'pr_title': pr_info.get('title'),
                'total_files_analyzed': 0,
                'total_functions': 0,
                'high_complexity_functions_cyclomatic': 0,
                'high_complexity_functions_cognitive': 0,
                'thresholds': {
                    'cyclomatic': args.cyclomatic_threshold,
                    'cognitive': args.cognitive_threshold
                },
                'file_analyses': {},
                'high_complexity_functions': []
            }
        else:
            functions = analyzer.extract_function_metrics(metrics_data)
            
            print(f"Total functions found: {len(functions)}")
            print(f"Changed files: {len(changed_files)}")
            
            # ファイル単位の解析
            file_analyses = analyzer.analyze_files(functions, changed_files)
            
            # サマリーの生成
            summary = analyzer.generate_summary(file_analyses, pr_info)
        
        # 結果の保存
        print(f"Saving results to {args.output}")
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\nAnalysis complete:")
        print(f"- Files analyzed: {summary['total_files_analyzed']}")
        print(f"- Total functions: {summary['total_functions']}")
        print(f"- High complexity functions (cyclomatic): {summary['high_complexity_functions_cyclomatic']}")
        print(f"- High complexity functions (cognitive): {summary['high_complexity_functions_cognitive']}")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
