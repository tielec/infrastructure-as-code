#!/usr/bin/env python3
"""
Rust Code Analysis HTML Report Generator
メトリクス解析結果からHTMLレポートを生成する
Jenkins HTML Publisher対応版
"""

import json
import os
import argparse
import html
from datetime import datetime
from pathlib import Path
import pandas as pd
import matplotlib
# Jenkins環境でのGUI問題を回避
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns


class RustReportGenerator:
    def __init__(self, args):
        self.report_dir = args.report_dir
        self.html_dir = args.html_dir
        self.template_dir = args.template_dir
        self.repo_name = args.repo_name
        self.branch = args.branch
        self.cyclomatic_threshold = int(args.cyclomatic_threshold)
        self.cognitive_threshold = int(args.cognitive_threshold)
        self.include_halstead = args.include_halstead == 'True'
        self.include_mi = args.include_mi == 'True'
        
        # Jenkins環境対応のためのmatplotlib設定
        try:
            plt.style.use('seaborn-v0_8-whitegrid')
        except:
            try:
                plt.style.use('seaborn-whitegrid')
            except:
                # seabornが使えない場合のフォールバック
                plt.style.use('default')
            
        # Jenkins環境でのフォント問題を回避
        try:
            # 利用可能なフォントを確認して設定
            import matplotlib.font_manager as fm
            available_fonts = [f.name for f in fm.fontManager.ttflist]
            
            # 優先順位でフォントを選択
            preferred_fonts = ['DejaVu Sans', 'Liberation Sans', 'sans-serif']
            selected_font = 'sans-serif'  # デフォルト
            
            for font in preferred_fonts:
                if font in available_fonts:
                    selected_font = font
                    break
            
            plt.rcParams['font.family'] = selected_font
            print(f"Using font: {selected_font}")
        except:
            # フォント設定でエラーが出た場合はデフォルトを使用
            plt.rcParams['font.family'] = 'sans-serif'
            print("Using default sans-serif font")
            
        # 高DPI対応
        plt.rcParams['figure.dpi'] = 100
        plt.rcParams['savefig.dpi'] = 100
        plt.rcParams['savefig.bbox'] = 'tight'
        
    def load_data(self):
        """処理済みデータを読み込む"""
        csv_path = Path(self.report_dir) / 'metrics_processed.csv'
        summary_path = Path(self.report_dir) / 'summary.json'
        complex_path = Path(self.report_dir) / 'complex_functions.json'
        
        # CSVデータ
        if csv_path.exists():
            try:
                self.df = pd.read_csv(csv_path)
                print(f"Loaded {len(self.df)} records from CSV")
            except Exception as e:
                print(f"Error loading CSV: {e}")
                self.df = pd.DataFrame()
        else:
            print("CSV file not found")
            self.df = pd.DataFrame()
        
        # サマリーデータ
        if summary_path.exists():
            try:
                with open(summary_path, 'r') as f:
                    self.summary = json.load(f)
                print("Summary data loaded successfully")
            except Exception as e:
                print(f"Error loading summary: {e}")
                self.summary = {}
        else:
            print("Summary file not found")
            self.summary = {}
        
        # 複雑な関数のリスト
        if complex_path.exists():
            try:
                with open(complex_path, 'r') as f:
                    self.complex_functions = json.load(f)
                print(f"Loaded {len(self.complex_functions)} complex functions")
            except Exception as e:
                print(f"Error loading complex functions: {e}")
                self.complex_functions = []
        else:
            print("Complex functions file not found")
            self.complex_functions = []
    
    def create_complexity_distribution_chart(self):
        """複雑度分布のチャートを作成"""
        if self.df.empty:
            return '<p style="text-align: center; color: #666; padding: 40px;">チャート生成用データがありません</p>'
        
        try:
            fig, axes = plt.subplots(1, 2, figsize=(14, 6))
            
            # Cyclomatic Complexity分布
            cyclomatic_data = self.df['CCN'].dropna()
            if not cyclomatic_data.empty and len(cyclomatic_data) > 0:
                axes[0].hist(cyclomatic_data, bins=min(30, len(cyclomatic_data.unique())), 
                           edgecolor='black', alpha=0.7, color='steelblue')
                axes[0].axvline(self.cyclomatic_threshold, color='red', linestyle='--', linewidth=2,
                               label=f'Threshold ({self.cyclomatic_threshold})')
                axes[0].set_xlabel('Cyclomatic Complexity', fontsize=12)
                axes[0].set_ylabel('Number of Functions', fontsize=12)
                axes[0].set_title('Cyclomatic Complexity Distribution', fontsize=14, fontweight='bold')
                axes[0].legend()
                axes[0].grid(True, alpha=0.3)
            else:
                axes[0].text(0.5, 0.5, 'No cyclomatic data', ha='center', va='center', 
                           transform=axes[0].transAxes)
            
            # Cognitive Complexity分布
            if 'cognitive' in self.df.columns:
                cognitive_data = self.df['cognitive'].dropna()
                if not cognitive_data.empty and len(cognitive_data) > 0:
                    axes[1].hist(cognitive_data, bins=min(30, len(cognitive_data.unique())), 
                               edgecolor='black', alpha=0.7, color='orange')
                    axes[1].axvline(self.cognitive_threshold, color='red', linestyle='--', linewidth=2,
                                   label=f'Threshold ({self.cognitive_threshold})')
                    axes[1].set_xlabel('Cognitive Complexity', fontsize=12)
                    axes[1].set_ylabel('Number of Functions', fontsize=12)
                    axes[1].set_title('Cognitive Complexity Distribution', fontsize=14, fontweight='bold')
                    axes[1].legend()
                    axes[1].grid(True, alpha=0.3)
                else:
                    axes[1].text(0.5, 0.5, 'No data', ha='center', va='center', 
                               transform=axes[1].transAxes)
            else:
                axes[1].text(0.5, 0.5, 'Cognitive complexity\nnot available', ha='center', va='center', 
                           transform=axes[1].transAxes)
            
            plt.tight_layout()
            
            # デバッグ: チャートの配置を確認
            print("Chart layout: Left=Cognitive Complexity (Orange), Right=Cyclomatic Complexity (Blue)")
            
            # 画像を保存
            img_path = Path(self.html_dir) / 'complexity_distribution.png'
            plt.savefig(img_path, dpi=100, bbox_inches='tight', facecolor='white', edgecolor='none')
            plt.close()
            
            return f'<img src="complexity_distribution.png" alt="複雑度分布" style="max-width: 100%; height: auto; display: block; margin: 0 auto;">'
            
        except Exception as e:
            print(f"Error creating complexity distribution chart: {e}")
            return '<p style="text-align: center; color: #666; padding: 40px;">複雑度分布チャートの生成エラー</p>'
    
    def create_language_breakdown_chart(self):
        """言語別の内訳チャートを作成"""
        if not self.summary.get('functions_by_language'):
            return '<p style="text-align: center; color: #666; padding: 40px;">言語データがありません</p>'
        
        try:
            languages = []
            counts = []
            complex_counts = []
            
            for lang, stats in self.summary['functions_by_language'].items():
                if stats['count'] > 0:  # 関数数が0でない言語のみ
                    languages.append(lang.capitalize())
                    counts.append(stats['count'])
                    complex_counts.append(stats['complex'])
            
            if not languages:
                return '<p style="text-align: center; color: #666; padding: 40px;">表示する言語データがありません</p>'
            
            fig, ax = plt.subplots(figsize=(12, 6))
            
            x = range(len(languages))
            width = 0.35
            
            bars1 = ax.bar([i - width/2 for i in x], counts, width, 
                          label='Total Functions', alpha=0.8, color='steelblue')
            bars2 = ax.bar([i + width/2 for i in x], complex_counts, width, 
                          label='Complex Functions', alpha=0.8, color='coral')
            
            ax.set_xlabel('Programming Language', fontsize=12)
            ax.set_ylabel('Number of Functions', fontsize=12)
            ax.set_title('Functions by Programming Language', fontsize=14, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(languages, rotation=45, ha='right')
            ax.legend()
            ax.grid(True, alpha=0.3, axis='y')
            
            # 値をバーの上に表示
            for bar in bars1:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height + height * 0.01,
                           f'{int(height)}', ha='center', va='bottom', fontsize=9)
            
            for bar in bars2:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height + height * 0.01,
                           f'{int(height)}', ha='center', va='bottom', fontsize=9, color='darkred')
            
            plt.tight_layout()
            
            # 画像を保存
            img_path = Path(self.html_dir) / 'language_breakdown.png'
            plt.savefig(img_path, dpi=100, bbox_inches='tight', facecolor='white', edgecolor='none')
            plt.close()
            
            return f'<img src="language_breakdown.png" alt="言語別内訳" style="max-width: 100%; height: auto; display: block; margin: 0 auto;">'
            
        except Exception as e:
            print(f"Error creating language breakdown chart: {e}")
            return '<p style="text-align: center; color: #666; padding: 40px;">言語別内訳チャートの生成エラー</p>'
    
    def get_complexity_class(self, value, threshold, is_cognitive=False):
        """複雑度に基づいてCSSクラスを決定"""
        try:
            val = float(value) if value else 0
        except (ValueError, TypeError):
            val = 0
            
        if is_cognitive:
            # 認知的複雑度の基準（説明文に合わせる）
            if val > 20:
                return 'complexity-high'
            elif val > 7:
                return 'complexity-medium'
            else:
                return 'complexity-low'
        else:
            # 循環的複雑度の基準
            if val > threshold:
                return 'complexity-high'
            elif val > 10:
                return 'complexity-medium'
            else:
                return 'complexity-low'
    
    def get_lines_class(self, lines):
        """行数に基づいてCSSクラスを決定"""
        try:
            lines_val = int(lines) if lines else 0
        except (ValueError, TypeError):
            lines_val = 0
            
        if lines_val > 100:
            return 'lines-high'
        elif lines_val > 50:
            return 'lines-medium'
        else:
            return 'lines-low'
        """Maintainability Indexに基づいてCSSクラスを決定"""
        try:
            mi_val = float(mi) if mi else 0
        except (ValueError, TypeError):
            mi_val = 0
            
        if mi_val >= 65:
            return 'mi-high'
        elif mi_val >= 20:
            return 'mi-medium'
        else:
            return 'mi-low'
    
    def generate_table_rows(self, limit=300):
        """テーブル行のHTMLを生成"""
        colspan = 4  # ファイル/関数名、認知的複雑度、循環的複雑度、行数
        if self.df.empty:
            return f'<tr><td colspan="{colspan}" class="no-data">データがありません</td></tr>'
        
        try:
            # データの確認とデバッグ出力
            print(f"DataFrame columns: {list(self.df.columns)}")
            
            # 認知的複雑度を優先してソート（認知的複雑度 > 循環的複雑度の順）
            if 'cognitive' in self.df.columns:
                df_sorted = self.df.sort_values(['cognitive', 'CCN'], ascending=[False, False]).head(limit)
                print(f"Sorted by cognitive complexity first, then cyclomatic complexity")
            else:
                df_sorted = self.df.sort_values('CCN', ascending=False).head(limit)
                print(f"Sorted by cyclomatic complexity only (cognitive not available)")
            
            print(f"Processing {len(df_sorted)} rows for table")
            
            rows = []
            for idx, item in df_sorted.iterrows():
                ccn = item.get('CCN', 0)
                cognitive = item.get('cognitive', 0)
                sloc = item.get('nloc', 0)
                
                ccn_class = self.get_complexity_class(ccn, self.cyclomatic_threshold)
                cognitive_class = self.get_complexity_class(cognitive, self.cognitive_threshold, True)
                lines_class = self.get_lines_class(sloc)
                
                # 安全な値の取得
                def safe_str(val, default=''):
                    return html.escape(str(val)) if val and str(val) != 'nan' else default
                
                def safe_int(val, default=0):
                    try:
                        return int(float(val)) if val and str(val) != 'nan' else default
                    except (ValueError, TypeError):
                        return default
                
                # ファイル名と関数名の処理
                file_name = safe_str(item.get('file', ''))
                full_function_name = safe_str(item.get('function_name', ''))
                
                # 関数名からファイル名部分を除去
                function_name = full_function_name
                if '::' in full_function_name and file_name:
                    # ファイル名の正規化（パスの統一）
                    normalized_file = file_name.replace('./', '')
                    
                    # 関数名がファイル名で始まっている場合は除去
                    if full_function_name.startswith(file_name + '::'):
                        function_name = full_function_name[len(file_name + '::'):]
                    elif full_function_name.startswith('./' + normalized_file + '::'):
                        function_name = full_function_name[len('./' + normalized_file + '::'):]
                    elif full_function_name.startswith(normalized_file + '::'):
                        function_name = full_function_name[len(normalized_file + '::'):]
                    
                    # さらに詳細なパターンマッチング
                    file_parts = normalized_file.replace('/', '::').replace('.py', '').replace('.rs', '').replace('.js', '').replace('.java', '').replace('.cpp', '').replace('.c', '').replace('.go', '').replace('.ts', '').replace('.php', '').replace('.rb', '').replace('.cs', '').replace('.kt', '').replace('.swift', '').replace('.scala', '')
                    if function_name.startswith(file_parts + '::'):
                        function_name = function_name[len(file_parts + '::'):]
                
                # 最終チェック：まだファイル名が残っている場合
                if file_name and function_name.startswith(file_name):
                    function_name = function_name[len(file_name):].lstrip('::')
                
                # 関数名が空の場合は元の名前を使用
                if not function_name.strip():
                    function_name = full_function_name
                
                # ファイル名と関数名を結合（改行で区切り）
                combined_name = f'<span class="file-path">{file_name}</span><br><span class="function-name">{function_name}</span>'
                
                row = f'''
                            <tr>
                                <td>{combined_name}</td>
                                <td><span class="complexity-value {cognitive_class}">{safe_int(cognitive)}</span></td>
                                <td><span class="complexity-value {ccn_class}">{safe_int(ccn)}</span></td>
                                <td><span class="lines-value {lines_class}">{safe_int(sloc)}</span></td>
                            </tr>'''
                rows.append(row)
            
            return ''.join(rows)
            
        except Exception as e:
            print(f"Error generating table rows: {e}")
            import traceback
            traceback.print_exc()
            return f'<tr><td colspan="{colspan}" class="no-data">テーブルデータの生成エラー</td></tr>'
    
    def load_template(self, template_file):
        """テンプレートファイルを読み込む"""
        template_path = Path(self.template_dir) / template_file
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading template {template_path}: {e}")
            # フォールバック用の基本テンプレート
            return """<!DOCTYPE html>
<html><head><title>Rust Code Analysis Report</title></head>
<body><h1>Error loading template</h1><p>{{TABLE_ROWS}}</p></body></html>"""
    
    def generate_report(self):
        """HTMLレポートを生成"""
        try:
            print("Loading data...")
            self.load_data()
            
            print("Creating charts...")
            complexity_chart = self.create_complexity_distribution_chart()
            language_chart = self.create_language_breakdown_chart()
            
            print("Generating table rows...")
            table_rows = self.generate_table_rows()
            
            print("Loading HTML template...")
            html_template = self.load_template('rust_report.html')
            
            # カラムヘッダーの動的生成（認知的複雑度を優先、シンプル版）
            column_headers = '''
                                <th>ファイル / 関数名</th>
                                <th>認知的複雑度</th>
                                <th>循環的複雑度</th>
                                <th>行数</th>'''
            
            # 安全な値の取得関数
            def safe_get(key, default='0'):
                value = self.summary.get(key, default)
                try:
                    if isinstance(value, (int, float)):
                        return str(value)
                    return str(value) if value else default
                except:
                    return default
            
            # プレースホルダーの置換
            replacements = {
                '{{REPO_NAME}}': html.escape(self.repo_name),
                '{{BRANCH}}': html.escape(self.branch),
                '{{TIMESTAMP}}': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                '{{TOTAL_FILES}}': safe_get('total_files'),
                '{{TOTAL_FUNCTIONS}}': safe_get('total_functions'),
                '{{COMPLEX_FUNCTIONS_CYCLOMATIC}}': safe_get('complex_functions_cyclomatic'),
                '{{COMPLEX_FUNCTIONS_COGNITIVE}}': safe_get('complex_functions_cognitive'),
                '{{AVERAGE_CYCLOMATIC}}': f"{float(safe_get('average_cyclomatic', 0)):.2f}",
                '{{AVERAGE_COGNITIVE}}': f"{float(safe_get('average_cognitive', 0)):.2f}",
                '{{MAX_CYCLOMATIC}}': str(int(float(safe_get('max_cyclomatic', 0)))),
                '{{MAX_COGNITIVE}}': str(int(float(safe_get('max_cognitive', 0)))),
                '{{CYCLOMATIC_THRESHOLD}}': str(self.cyclomatic_threshold),
                '{{COGNITIVE_THRESHOLD}}': str(self.cognitive_threshold),
                '{{COLUMN_HEADERS}}': column_headers,
                '{{TABLE_ROWS}}': table_rows,
                '{{COMPLEXITY_CHART}}': complexity_chart,
                '{{LANGUAGE_CHART}}': language_chart,
                '{{SHOW_HALSTEAD}}': 'block' if self.include_halstead else 'none',
                '{{SHOW_MI}}': 'block' if self.include_mi else 'none'
            }
            
            print("Applying replacements...")
            for placeholder, value in replacements.items():
                html_template = html_template.replace(placeholder, str(value))
            
            # HTMLファイルの保存
            output_path = Path(self.html_dir) / 'index.html'
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_template)
            
            print(f"HTML report generated successfully: {output_path}")
            print(f"Charts generated: {len([f for f in Path(self.html_dir).glob('*.png')])}")
            
        except Exception as e:
            print(f"Error generating report: {e}")
            # エラー時もシンプルなHTMLファイルを生成
            error_html = f"""<!DOCTYPE html>
<html><head><title>Report Generation Error</title></head>
<body><h1>Report Generation Error</h1><p>Error: {html.escape(str(e))}</p></body></html>"""
            output_path = Path(self.html_dir) / 'index.html'
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(error_html)


def main():
    parser = argparse.ArgumentParser(description='Generate Rust Code Analysis HTML report')
    parser.add_argument('--report-dir', required=True, help='Report directory')
    parser.add_argument('--html-dir', required=True, help='HTML output directory')
    parser.add_argument('--template-dir', required=True, help='Template directory')
    parser.add_argument('--repo-name', required=True, help='Repository name')
    parser.add_argument('--branch', required=True, help='Branch name')
    parser.add_argument('--cyclomatic-threshold', required=True, help='Cyclomatic complexity threshold')
    parser.add_argument('--cognitive-threshold', required=True, help='Cognitive complexity threshold')
    parser.add_argument('--include-halstead', required=True, help='Include Halstead metrics')
    parser.add_argument('--include-mi', required=True, help='Include Maintainability Index')
    
    args = parser.parse_args()
    
    generator = RustReportGenerator(args)
    generator.generate_report()


if __name__ == '__main__':
    main()
