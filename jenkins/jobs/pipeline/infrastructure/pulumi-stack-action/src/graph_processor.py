"""
Dependency graph processing for Pulumi resources
"""

import subprocess
import traceback
from pathlib import Path
from typing import Optional, List, Dict

from dot_processor import DotFileGenerator, DotFileProcessor


class DependencyGraphProcessor:
    """依存関係グラフの処理を担当"""
    
    def __init__(self, artifacts_dir: str, output_dir: str):
        self.artifacts_dir = Path(artifacts_dir)
        self.output_dir = Path(output_dir)
    
    def process_graph(self, resources: List[Dict], 
                     resource_providers: Dict[str, int], 
                     stack_name: str) -> Optional[str]:
        """依存関係グラフを処理"""
        dot_file = self.artifacts_dir / 'stack-graph-post-action.dot'
        
        # DOTファイルの検証
        if not self._validate_dot_file(dot_file):
            return self._generate_simple_dependency_graph(
                stack_name, resources, resource_providers
            )
        
        try:
            # DOTファイルの処理
            with open(dot_file, 'r', encoding='utf-8') as f:
                dot_content = f.read()
            
            # 空のグラフチェック
            if DotFileProcessor.is_empty_graph(dot_content):
                print("Warning: Empty or minimal dependency graph, generating from resources")
                return self._generate_simple_dependency_graph(
                    stack_name, resources, resource_providers
                )
            
            # スタイルを適用
            dot_content = DotFileProcessor.apply_graph_styling(dot_content)
            
            # レンダリング
            return self._render_dot_to_png(dot_content)
            
        except Exception as e:
            print(f"Error processing dependency graph: {e}")
            traceback.print_exc()
            return self._generate_simple_dependency_graph(
                stack_name, resources, resource_providers
            )
    
    def _validate_dot_file(self, dot_file: Path) -> bool:
        """DOTファイルの妥当性を検証"""
        if not dot_file.exists():
            print("stack-graph.dot not found")
            return False
            
        file_size = dot_file.stat().st_size
        print(f"Found stack-graph.dot, size: {file_size} bytes")
        
        if file_size < 20:
            print("Warning: stack-graph.dot is too small")
            return False
            
        # 内容を確認（デバッグ用）
        with open(dot_file, 'r', encoding='utf-8') as f:
            content_preview = f.read(200)
            print(f"DOT file preview: {content_preview}")
            
        return True
    
    def _render_dot_to_png(self, dot_content: str) -> Optional[str]:
        """DOTコンテンツをPNGとSVGにレンダリング"""
        temp_dot = self.output_dir / 'temp_graph.dot'
        output_png = self.output_dir / 'dependency_graph.png'
        output_svg = self.output_dir / 'dependency_graph.svg'
        output_png_hd = self.output_dir / 'dependency_graph_hd.png'
        
        try:
            # 一時DOTファイルを作成
            with open(temp_dot, 'w', encoding='utf-8') as f:
                f.write(dot_content)
            
            # SVG形式でレンダリング（スケーラブル）
            result_svg = subprocess.run(
                ['dot', '-Tsvg', '-Gfontsize=14', '-Nfontsize=12', 
                 '-Efontsize=10', str(temp_dot), '-o', str(output_svg)],
                capture_output=True,
                text=True
            )
            
            # 通常解像度のPNG（プレビュー用）- ノードが3行になることを考慮してサイズ調整
            result = subprocess.run(
                ['dot', '-Tpng', '-Gdpi=150', '-Gsize=14,18!', 
                '-Gfontsize=14', '-Nfontsize=11', '-Efontsize=10',
                '-Nheight=1.2', '-Nwidth=3.5',  # ノードサイズを大きく
                '-Goverlap=false', '-Gsplines=ortho',
                str(temp_dot), '-o', str(output_png)],
                capture_output=True,
                text=True
            )
            
            # 高解像度PNG（詳細表示用）
            result_hd = subprocess.run(
                ['dot', '-Tpng', '-Gdpi=300', '-Gsize=20,28!',
                 '-Gfontsize=16', '-Nfontsize=14', '-Efontsize=12',
                 str(temp_dot), '-o', str(output_png_hd)],
                capture_output=True,
                text=True
            )
            
            # 失敗時は代替レイアウトエンジンを試す
            if result.returncode != 0:
                print(f"Error running dot command: {result.stderr}")
                # sfdpを試す（大規模グラフ用）
                result = subprocess.run(
                    ['sfdp', '-Tpng', '-Gdpi=150', '-Goverlap=false',
                     '-Gfontsize=14', '-Nfontsize=12',
                     str(temp_dot), '-o', str(output_png)],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    # fdpを試す
                    result = subprocess.run(
                        ['fdp', '-Tpng', '-Gdpi=150',
                         '-Gfontsize=14', '-Nfontsize=12',
                         str(temp_dot), '-o', str(output_png)],
                        capture_output=True,
                        text=True
                    )
            
            # SVGが成功していればそれを優先
            if result_svg.returncode == 0 and output_svg.exists():
                return 'dependency_graph.svg'
            else:
                return 'dependency_graph.png' if output_png.exists() else None
            
        except Exception as e:
            print(f"Error rendering DOT file: {e}")
            traceback.print_exc()
            return None
        finally:
            # 一時ファイルを削除
            if temp_dot.exists():
                temp_dot.unlink()
    
    def _generate_simple_dependency_graph(self, stack_name: str, 
                                        resources: List[Dict], 
                                        resource_providers: Dict[str, int]) -> Optional[str]:
        """リソース情報から簡単な依存関係グラフを生成"""
        if not resources:
            return None
            
        try:
            # DOTファイルを生成
            dot_lines = DotFileGenerator.create_dot_file(
                stack_name, resources, resource_providers
            )
            
            # レンダリング
            dot_content = '\n'.join(dot_lines)
            return self._render_dot_to_png(dot_content)
            
        except Exception as e:
            print(f"Error generating simple dependency graph: {e}")
            traceback.print_exc()
            return None
