"""
DOT file processing for Pulumi dependency graphs
"""

import re
from typing import Dict, List, Tuple
from urn_processor import UrnProcessor
from node_label_generator import NodeLabelGenerator
from resource_dependency_builder import ResourceDependencyBuilder


class DotFileGenerator:
    """DOTファイル生成の責務を分離"""
    
    DOT_HEADER = """digraph G {{
    graph [rankdir=TB, bgcolor="white", pad="0.5", nodesep="0.8", ranksep="1.2", fontsize="14"];
    node [shape=box, style="rounded,filled", fontname="Arial", fontsize="12", margin="0.3,0.15"];
    edge [color="#512DA8", penwidth="1.5", arrowsize="0.8", fontsize="10"];
"""
    
    # プロバイダー別の色設定（拡張可能）
    PROVIDER_COLORS = {
        'aws': ('#FFF3E0', '#EF6C00'),
        'azure': ('#E3F2FD', '#0078D4'),
        'azuread': ('#E8F5E9', '#0078D4'),
        'gcp': ('#E8F5E9', '#4285F4'),
        'google': ('#E8F5E9', '#4285F4'),
        'kubernetes': ('#E8EAF6', '#326DE6'),
        'docker': ('#E3F2FD', '#2496ED'),
        'pulumi': ('#F3E5F5', '#6A1B9A'),
        'random': ('#FFF9C4', '#FBC02D'),
        'tls': ('#FFEBEE', '#D32F2F'),
        'github': ('#F5F5F5', '#24292E'),
        'cloudflare': ('#FFF8E1', '#F48120'),
        'datadog': ('#F3E5F5', '#632CA6'),
        'postgresql': ('#E8F5E9', '#336791'),
        'mysql': ('#E3F2FD', '#00758F'),
        'vault': ('#F5F5F5', '#000000'),
    }
    DEFAULT_COLORS = ('#E3F2FD', '#1565C0')
    
    @staticmethod
    def escape_dot_string(s: str) -> str:
        """DOT形式の文字列をエスケープ"""
        if not s:
            return s
        # ダブルクォートとバックスラッシュをエスケープ
        s = str(s).replace('\\', '\\\\')
        s = s.replace('"', '\\"')
        # 改行を\nに変換
        s = s.replace('\n', '\\n')
        s = s.replace('\r', '')
        # 特殊文字をエスケープ
        s = s.replace('\t', '\\t')
        return s
    
    @staticmethod
    def create_dot_file(stack_name: str, resources: List[Dict], 
                       resource_providers: Dict[str, int]) -> List[str]:
        """DOTファイルの内容を生成"""
        dot_lines = [DotFileGenerator.DOT_HEADER]
        
        # スタックノードを追加
        dot_lines.extend(DotFileGenerator._add_stack_node(stack_name))
        
        # プロバイダーノードを追加
        provider_nodes = DotFileGenerator._add_provider_nodes(
            resource_providers, dot_lines
        )
        
        # スタックからプロバイダーへの接続
        DotFileGenerator._add_stack_to_provider_connections(
            provider_nodes, dot_lines
        )
        
        # リソースを追加
        DotFileGenerator._add_resources(
            resources[:20], provider_nodes, dot_lines
        )
        
        # リソース間の依存関係を追加
        DotFileGenerator._add_resource_dependencies(resources[:20], dot_lines)
        
        dot_lines.append('}')
        return dot_lines
    
    @staticmethod
    def _add_stack_node(stack_name: str) -> List[str]:
        """スタックノードのDOT記述を生成"""
        escaped_name = DotFileGenerator.escape_dot_string(stack_name)
        return [
            f'    "Stack" [label="Stack: {escaped_name}", fillcolor="#D1C4E9", '
            f'color="#512DA8", shape=ellipse, fontsize="14"];',
            ''
        ]
    
    @staticmethod
    def _add_provider_nodes(resource_providers: Dict[str, int], 
                           dot_lines: List[str]) -> Dict[str, str]:
        """プロバイダーノードを追加"""
        provider_nodes = {}
        
        for provider, count in resource_providers.items():
            fill_color, border_color = DotFileGenerator.PROVIDER_COLORS.get(
                provider.lower(), DotFileGenerator.DEFAULT_COLORS
            )
            node_id = f'provider_{provider}'
            provider_nodes[provider] = node_id
            
            escaped_provider = DotFileGenerator.escape_dot_string(provider.upper())
            dot_lines.append(
                f'    "{node_id}" [label="{escaped_provider} Provider\\n'
                f'({count} resources)", fillcolor="{fill_color}", '
                f'color="{border_color}", shape=folder, fontsize="12"];'
            )
        
        dot_lines.append('')
        return provider_nodes
    
    @staticmethod
    def _add_stack_to_provider_connections(provider_nodes: Dict[str, str], 
                                          dot_lines: List[str]):
        """スタックからプロバイダーへの接続を追加"""
        for provider_node in provider_nodes.values():
            dot_lines.append(f'    "Stack" -> "{provider_node}";')
        dot_lines.append('')
    
    @staticmethod
    def _add_resources(resources: List[Dict], provider_nodes: Dict[str, str], 
                      dot_lines: List[str]):
        """リソースノードを追加"""
        for i, resource in enumerate(resources):
            resource_type = resource.get('type', 'unknown')
            provider = resource_type.split(':')[0] if ':' in resource_type else 'unknown'
            resource_name = resource.get('urn', '').split('::')[-1]
            short_type = resource_type.split(':')[-1] if ':' in resource_type else resource_type
            
            fill_color, border_color = DotFileGenerator.PROVIDER_COLORS.get(
                provider.lower(), DotFileGenerator.DEFAULT_COLORS
            )
            node_id = f'resource_{i}'
            
            # ラベルをエスケープ
            escaped_type = DotFileGenerator.escape_dot_string(short_type)
            escaped_name = DotFileGenerator.escape_dot_string(resource_name)
            
            label = f"{escaped_type}\\n{escaped_name}"
            if len(label) > 40:
                label = f"{escaped_type}\\n{escaped_name[:30]}..."
            
            dot_lines.append(
                f'    "{node_id}" [label="{label}", fillcolor="{fill_color}", '
                f'color="{border_color}"];'
            )
            
            if provider in provider_nodes:
                dot_lines.append(f'    "{provider_nodes[provider]}" -> "{node_id}";')
    
    @staticmethod
    def _add_resource_dependencies(resources: List[Dict], dot_lines: List[str]):
        """リソース間の依存関係を追加（ResourceDependencyBuilderに委譲）"""
        ResourceDependencyBuilder.add_resource_dependencies(resources, dot_lines)


class DotFileProcessor:
    """DOTファイル処理の責務を分離"""
    
    STYLE_SETTINGS = """digraph G {
    graph [rankdir=TB, bgcolor="white", pad="0.5", nodesep="0.8", ranksep="1.2", splines=ortho, fontsize="14"];
    node [shape=box, style="rounded,filled", fillcolor="#E3F2FD", color="#1565C0", fontname="Arial", fontsize="12", margin="0.3,0.15"];
    edge [color="#512DA8", penwidth="1.5", arrowsize="0.8", fontname="Arial", fontsize="10"];
"""
    
    # DotFileGeneratorの色設定を参照
    PROVIDER_COLORS = DotFileGenerator.PROVIDER_COLORS
    DEFAULT_COLORS = DotFileGenerator.DEFAULT_COLORS
    
    @staticmethod
    def is_empty_graph(dot_content: str) -> bool:
        """空のグラフかどうかをチェック"""
        return any([
            'digraph G {}' in dot_content,
            len(dot_content.strip()) < 30,
            # Pulumiのグラフは'strict digraph'で始まることがある
            (dot_content.count('{') == 1 and dot_content.count('}') == 1 and 'digraph' not in dot_content)
        ])
    
    
    @staticmethod
    def apply_graph_styling(dot_content: str) -> str:
        """グラフスタイルを適用（Pulumi生成グラフ用）"""
        # Pulumiのグラフは'strict digraph'で始まることがある
        if 'strict digraph' in dot_content:
            # Pulumiが生成したグラフはそのまま使用
            return DotFileProcessor._enhance_pulumi_graph(dot_content)
        elif 'digraph G {' in dot_content:
            # 自前で生成したグラフにスタイルを適用
            dot_content = dot_content.replace('digraph G {', DotFileProcessor.STYLE_SETTINGS)
            return DotFileProcessor._process_node_labels(dot_content)
        return dot_content
    
    @staticmethod
    def _enhance_pulumi_graph(dot_content: str) -> str:
        """Pulumi生成グラフを拡張"""
        lines = dot_content.split('\n')
        new_lines = []

        # URN情報をキャッシュ
        node_urn_map = {}
        stack_node_id = None

        # 各行を処理
        for i, line in enumerate(lines):
            # ヘッダー行の処理（早期処理）
            if i == 0 and 'strict digraph' in line:
                new_lines.extend(DotFileProcessor._add_graph_header(line))
                continue

            # 通常行の処理
            processed_line, node_info = DotFileProcessor._process_graph_line(
                line, node_urn_map, stack_node_id
            )

            # node_info更新（ヘルパーメソッドに委譲）
            if node_info:
                stack_node_id = DotFileProcessor._update_node_info(
                    node_info, node_urn_map, stack_node_id
                )

            # 処理済み行の追加
            if processed_line:
                new_lines.append(processed_line)

        return '\n'.join(new_lines)

    @staticmethod
    def _update_node_info(
        node_info: Dict,
        node_urn_map: Dict,
        stack_node_id: str
    ) -> str:
        """node_info辞書からnode_urn_mapとstack_node_idを更新

        Args:
            node_info (Dict): ノード情報辞書
            node_urn_map (Dict): URNマッピング（破壊的更新）
            stack_node_id (str): 現在のスタックノードID

        Returns:
            str: 更新後のstack_node_id
        """
        # URNマッピング更新
        node_urn_map.update(node_info.get('node_urn_map', {}))

        # stack_node_id更新（あれば）
        new_stack_node_id = node_info.get('stack_node_id')
        if new_stack_node_id:
            return new_stack_node_id

        return stack_node_id
    
    @staticmethod
    def _add_graph_header(first_line: str) -> List[str]:
        """グラフヘッダーを追加"""
        return [
            first_line,
            '    graph [rankdir=TB, bgcolor="white", pad="0.5", nodesep="1.2", ranksep="2.0", fontsize="14"];',
            '    node [shape=box, style="rounded,filled", fontname="Arial", fontsize="11", margin="0.4,0.2", height=1.0];',
            '    edge [fontname="Arial", fontsize="10", penwidth="1.5"];'
        ]
    
    @staticmethod
    def _process_graph_line(line: str, node_urn_map: Dict, stack_node_id: str) -> Tuple[str, Dict]:
        """グラフの各行を処理"""
        # ノード定義行の判定
        if DotFileProcessor._is_node_definition_line(line):
            return DotFileProcessor._process_node_definition(line)

        # スタックへのエッジ行の判定
        if DotFileProcessor._is_edge_to_stack_line(line, stack_node_id):
            return DotFileProcessor._process_edge_definition(line, stack_node_id)

        # その他の行はそのまま返す
        return line, None

    @staticmethod
    def _is_node_definition_line(line: str) -> bool:
        """ノード定義行かどうかを判定

        Args:
            line (str): DOT形式の行

        Returns:
            bool: ノード定義行の場合True
        """
        # コメント行はスキップ
        if line.strip().startswith('//'):
            return False

        # URNラベルを持つノード定義
        return '[label="urn:pulumi:' in line

    @staticmethod
    def _is_edge_to_stack_line(line: str, stack_node_id: str) -> bool:
        """スタックへのエッジ行かどうかを判定

        Args:
            line (str): DOT形式の行
            stack_node_id (str): スタックノードID

        Returns:
            bool: スタックへのエッジ行の場合True
        """
        # stack_node_idがない場合はFalse
        if not stack_node_id:
            return False

        # エッジ記号とスタックノードへの接続を確認
        return '->' in line and f'-> {stack_node_id}' in line
    
    @staticmethod
    def _process_node_definition(line: str) -> Tuple[str, Dict]:
        """ノード定義を処理"""
        # ノードIDを抽出
        node_id = line.strip().split('[')[0].strip()

        # URNを抽出
        urn_match = re.search(r'label="([^"]+)"', line)
        if not urn_match:
            return line, None

        urn = urn_match.group(1)
        urn_info = UrnProcessor.parse_urn(urn)

        # NodeLabelGeneratorでノード属性を生成
        node_attrs = NodeLabelGenerator.generate_node_label(urn, urn_info)

        # 新しいノード定義
        new_line = f'    {node_id} [{node_attrs}];'

        # メタデータを返す
        result_info = {'node_urn_map': {node_id: urn_info}}
        if UrnProcessor.is_stack_resource(urn):
            result_info['stack_node_id'] = node_id

        return new_line, result_info

    @staticmethod
    def _process_edge_definition(line: str, stack_node_id: str) -> Tuple[str, None]:
        """エッジ定義を処理（スタックへの依存を逆転）"""
        parts = line.split('->')
        if len(parts) != 2:
            return line, None
        
        from_node = parts[0].strip()
        to_part = parts[1].strip()
        
        # エッジ属性を抽出
        edge_attrs, to_node = DotFileProcessor._extract_edge_attributes(to_part)
        
        # スタックから他のリソースへの矢印に変更
        if to_node == stack_node_id:
            new_line = f'    {stack_node_id} -> {from_node}'
            if edge_attrs:
                new_line += f' {edge_attrs}'
            new_line += ';'
            return new_line, None
        
        return line, None
    
    @staticmethod
    def _extract_edge_attributes(to_part: str) -> Tuple[str, str]:
        """エッジ属性を抽出"""
        edge_attrs = ''
        if '[' in to_part:
            attrs_start = to_part.find('[')
            attrs_end = to_part.find(']')
            if attrs_start != -1 and attrs_end != -1:
                edge_attrs = to_part[attrs_start:attrs_end+1]
            to_node = to_part[:attrs_start].strip()
        else:
            to_node = to_part.rstrip(';').strip()
        
        return edge_attrs, to_node
    
    @staticmethod
    def _process_node_labels(dot_content: str) -> str:
        """ノードラベルを処理"""
        lines = dot_content.split('\n')
        new_lines = []
        
        for line in lines:
            if ' [label=' in line and ']' in line:
                line = DotFileProcessor._process_single_node(line)
            new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    @staticmethod
    def _process_single_node(line: str) -> str:
        """単一ノードのラベルを処理"""
        # ラベル抽出
        match = re.search(r'\[label="([^"]+)"\]', line)
        if not match:
            return line

        full_name = match.group(1)
        short_name = full_name.split('::')[-1]

        # 長いラベルの省略
        if len(short_name) > 30:
            short_name = short_name[:27] + '...'

        # プロバイダー別色設定を取得
        fill_color, border_color, short_name = DotFileProcessor._detect_provider_colors(
            full_name, short_name
        )

        # ラベル置換
        return re.sub(
            r'\[label="[^"]+"\]',
            f'[label="{short_name}", fillcolor="{fill_color}", color="{border_color}"]',
            line
        )

    @staticmethod
    def _detect_provider_colors(full_name: str, short_name: str) -> Tuple[str, str, str]:
        """プロバイダー別色設定を検出

        Args:
            full_name (str): 完全なリソース名
            short_name (str): 短縮リソース名

        Returns:
            Tuple[str, str, str]: (fill_color, border_color, updated_short_name)
        """
        # デフォルト色
        fill_color, border_color = DotFileProcessor.DEFAULT_COLORS

        # プロバイダーを検出
        for provider_key in DotFileProcessor.PROVIDER_COLORS:
            if f'{provider_key}:' not in full_name.lower():
                continue

            # プロバイダー色を適用
            fill_color, border_color = DotFileProcessor.PROVIDER_COLORS[provider_key]

            # リソースタイプを抽出（あれば）
            if f'::{provider_key}:' in full_name.lower():
                resource_type = full_name.split(f'::{provider_key}:')[1].split('::')[0]
                short_name = f"{resource_type}\\n{short_name}"

            break

        return fill_color, border_color, short_name
    
    @staticmethod
    def _shorten_pulumi_label(line: str) -> str:
        """既存のメソッドを改善"""
        match = re.search(r'\[label="([^"]+)"\]', line)
        if not match:
            return line

        full_label = match.group(1)

        # URN形式の場合はUrnProcessorを使用
        if full_label.startswith('urn:pulumi:'):
            urn_info = UrnProcessor.parse_urn(full_label)
            short_label = UrnProcessor.create_readable_label(urn_info)

            # 色設定
            if UrnProcessor.is_stack_resource(full_label):
                fillcolor = '#D1C4E9'
                color = '#512DA8'
            else:
                provider_colors = DotFileProcessor.PROVIDER_COLORS.get(
                    urn_info['provider'].lower(),
                    DotFileProcessor.DEFAULT_COLORS
                )
                fillcolor = provider_colors[0]
                color = provider_colors[1]
        else:
            # URN形式でない場合は既存の処理
            short_label = full_label[:40] if len(full_label) > 40 else full_label
            fillcolor, color = DotFileProcessor.DEFAULT_COLORS

        return re.sub(
            r'\[label="[^"]+"\]',
            f'[label="{short_label}", fillcolor="{fillcolor}", color="{color}"]',
            line
        )
