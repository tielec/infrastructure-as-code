"""
DOT file processing for Pulumi dependency graphs

このモジュールは、Pulumiが生成したDOTファイル（依存関係グラフ）を処理し、
視覚的に改善された形式で出力する責務を担当します。

リファクタリング履歴（Issue #448）:
- UrnProcessor: URN/URIのパース処理を分離
- NodeLabelGenerator: ラベル生成ロジックを分離
- ResourceDependencyBuilder: 依存関係グラフ構築を分離
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
        """リソース間の依存関係を追加（汎用版）"""
        if len(resources) <= 1:
            return
            
        dot_lines.extend(['', '    // リソース間の依存関係'])
        
        # リソースのURNからIDへのマッピングを作成
        urn_to_node_id = DotFileGenerator._create_urn_to_node_mapping(resources)
        
        # 各リソースの依存関係を処理
        for i, resource in enumerate(resources):
            DotFileGenerator._add_dependencies_for_resource(
                i, resource, urn_to_node_id, dot_lines
            )
    
    @staticmethod
    def _create_urn_to_node_mapping(resources: List[Dict]) -> Dict[str, str]:
        """URNからノードIDへのマッピングを作成"""
        mapping = {}
        for i, resource in enumerate(resources):
            urn = resource.get('urn', '')
            mapping[urn] = f'resource_{i}'
        return mapping
    
    @staticmethod
    def _add_dependencies_for_resource(resource_index: int, resource: Dict, 
                                     urn_to_node_id: Dict[str, str], 
                                     dot_lines: List[str]):
        """単一リソースの依存関係を追加"""
        node_id = f'resource_{resource_index}'
        
        # 通常の依存関係を追加
        DotFileGenerator._add_direct_dependencies(
            node_id, resource, urn_to_node_id, dot_lines
        )
        
        # 親リソースへの依存を追加
        DotFileGenerator._add_parent_dependency(
            node_id, resource, urn_to_node_id, dot_lines
        )
        
        # プロパティ依存を追加
        DotFileGenerator._add_property_dependencies(
            node_id, resource, urn_to_node_id, dot_lines
        )
    
    @staticmethod
    def _add_direct_dependencies(node_id: str, resource: Dict, 
                               urn_to_node_id: Dict[str, str], 
                               dot_lines: List[str]):
        """直接的な依存関係を追加"""
        dependencies = resource.get('dependencies', [])
        for dep_urn in dependencies:
            if dep_urn in urn_to_node_id:
                dep_node_id = urn_to_node_id[dep_urn]
                dot_lines.append(
                    f'    "{node_id}" -> "{dep_node_id}" '
                    f'[style=solid, color="#9C27B0", fontsize="10"];'
                )
    
    @staticmethod
    def _add_parent_dependency(node_id: str, resource: Dict,
                             urn_to_node_id: Dict[str, str],
                             dot_lines: List[str]):
        """親リソースへの依存を追加"""
        parent = resource.get('parent')
        if parent and parent in urn_to_node_id:
            parent_node_id = urn_to_node_id[parent]
            dot_lines.append(
                f'    "{node_id}" -> "{parent_node_id}" '
                f'[style=dashed, color="#2196F3", label="parent", fontsize="10"];'
            )
    
    @staticmethod
    def _add_property_dependencies(node_id: str, resource: Dict,
                                 urn_to_node_id: Dict[str, str],
                                 dot_lines: List[str]):
        """プロパティ依存を追加"""
        prop_deps = resource.get('propertyDependencies', {})
        for prop_name, dep_urns in prop_deps.items():
            for dep_urn in dep_urns:
                if dep_urn in urn_to_node_id:
                    dep_node_id = urn_to_node_id[dep_urn]
                    # 短いプロパティ名を表示
                    short_prop = prop_name.split('.')[-1] if '.' in prop_name else prop_name
                    dot_lines.append(
                        f'    "{node_id}" -> "{dep_node_id}" '
                        f'[style=dotted, color="#FF5722", label="{short_prop}", fontsize="9"];'
                    )


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
    def parse_urn(urn: str) -> Dict[str, str]:
        """URNをパースして構成要素を抽出（既存の公開API - 後方互換性のため維持）

        URN形式: urn:pulumi:STACK::PROJECT::PROVIDER:MODULE/TYPE:TYPE::NAME

        Args:
            urn: Pulumi URN文字列

        Returns:
            URN構成要素の辞書

        Notes:
            - 内部実装は UrnProcessor に委譲
            - 既存の公開APIを維持するため、staticmethodとして保持
        """
        processor = UrnProcessor()
        return processor.parse_urn(urn)

    @staticmethod
    def _parse_provider_type(provider_type: str) -> Dict[str, str]:
        """プロバイダータイプ文字列を解析（内部実装 - 後方互換性のため維持）

        Args:
            provider_type: プロバイダータイプ文字列

        Returns:
            プロバイダー情報の辞書

        Notes:
            - 内部実装は UrnProcessor に委譲
            - 既存コードとの互換性のため維持
        """
        return UrnProcessor._parse_provider_type(provider_type)

    @staticmethod
    def create_readable_label(urn_info: Dict[str, str]) -> str:
        """URN情報から読みやすいラベルを生成（既存の公開API - 後方互換性のため維持）

        Args:
            urn_info: parse_urn() の戻り値形式の辞書

        Returns:
            改行区切りのラベル文字列

        Notes:
            - 内部実装は NodeLabelGenerator に委譲
            - 既存の公開APIを維持するため、staticmethodとして保持
        """
        generator = NodeLabelGenerator()
        return generator.create_readable_label(urn_info)

    @staticmethod
    def _format_resource_type(resource_type: str) -> str:
        """リソースタイプを読みやすい形式にフォーマット（内部実装 - 後方互換性のため維持）

        Args:
            resource_type: リソースタイプ文字列

        Returns:
            フォーマット済みのリソースタイプ

        Notes:
            - 内部実装は NodeLabelGenerator に委譲
            - 既存コードとの互換性のため維持
        """
        return NodeLabelGenerator._format_resource_type(resource_type)

    
    @staticmethod
    def is_stack_resource(urn: str) -> bool:
        """スタックリソースかどうかを判定"""
        return 'pulumi:pulumi:Stack' in urn
    
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
        """Pulumi生成グラフを拡張（Guard Clauseパターン適用）

        Args:
            dot_content: Pulumiが生成したDOTファイルの内容

        Returns:
            拡張されたDOTファイルの内容

        Notes:
            - リファクタリング（Issue #448）: ネストレベルを3以下に削減
            - Guard Clauseパターンを適用し、早期リターンでフロー制御を簡素化
        """
        lines = dot_content.split('\n')
        new_lines = []

        # URN情報をキャッシュ
        node_urn_map = {}
        stack_node_id = None

        # 各行を処理
        for i, line in enumerate(lines):
            # Guard Clause: グラフヘッダーの処理
            if i == 0 and 'strict digraph' in line:
                new_lines.extend(DotFileProcessor._add_graph_header(line))
                continue

            # 行を処理
            processed_line, node_info = DotFileProcessor._process_graph_line(
                line, node_urn_map, stack_node_id
            )

            # メタデータを更新
            if node_info:
                node_urn_map.update(node_info.get('node_urn_map', {}))
                if node_info.get('stack_node_id'):
                    stack_node_id = node_info['stack_node_id']

            # 処理済み行を追加
            if processed_line:
                new_lines.append(processed_line)

        return '\n'.join(new_lines)
    
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
        # ノード定義を処理
        if '[label="urn:pulumi:' in line and not line.strip().startswith('//'):
            return DotFileProcessor._process_node_definition(line)
        
        # エッジ（矢印）の処理
        elif '->' in line and stack_node_id and f'-> {stack_node_id}' in line:
            return DotFileProcessor._process_edge_definition(line, stack_node_id)
        
        return line, None
    
    @staticmethod
    def _process_node_definition(line: str) -> Tuple[str, Dict]:
        """ノード定義を処理（Guard Clauseパターン適用）

        Args:
            line: DOTファイルのノード定義行

        Returns:
            (処理済み行, メタデータ) のタプル

        Notes:
            - リファクタリング（Issue #448）: ネスト削減のためGuard Clauseを適用
            - URN抽出が失敗した場合は早期リターン
        """
        # ノードIDを抽出
        node_id = line.strip().split('[')[0].strip()

        # URNを抽出
        urn_match = re.search(r'label="([^"]+)"', line)

        # Guard Clause: URNが見つからない場合は早期リターン
        if not urn_match:
            return line, None

        urn = urn_match.group(1)
        urn_info = DotFileProcessor.parse_urn(urn)

        # ノード属性を生成
        node_attrs = DotFileProcessor._generate_node_attributes(urn, urn_info)

        # 新しいノード定義
        new_line = f'    {node_id} [{node_attrs}];'

        # メタデータを返す
        result_info = {'node_urn_map': {node_id: urn_info}}
        if DotFileProcessor.is_stack_resource(urn):
            result_info['stack_node_id'] = node_id

        return new_line, result_info
    
    @staticmethod
    def _generate_node_attributes(urn: str, urn_info: Dict) -> str:
        """ノード属性を生成"""
        if DotFileProcessor.is_stack_resource(urn):
            return DotFileProcessor._generate_stack_node_attributes(urn_info)
        else:
            return DotFileProcessor._generate_resource_node_attributes(urn_info)
    
    @staticmethod
    def _generate_stack_node_attributes(urn_info: Dict) -> str:
        """スタックノードの属性を生成"""
        new_label = f"Stack\\n{urn_info['stack']}"
        return f'label="{new_label}", fillcolor="#D1C4E9", color="#512DA8", shape=ellipse, fontsize="14"'
    
    @staticmethod
    def _generate_resource_node_attributes(urn_info: Dict) -> str:
        """リソースノードの属性を生成"""
        new_label = DotFileProcessor.create_readable_label(urn_info)
        provider_colors = DotFileProcessor.PROVIDER_COLORS.get(
            urn_info['provider'].lower(), 
            DotFileProcessor.DEFAULT_COLORS
        )
        fillcolor = provider_colors[0]
        color = provider_colors[1]
        return f'label="{new_label}", fillcolor="{fillcolor}", color="{color}", shape=box, fontsize="11"'
    
    @staticmethod
    def _process_edge_definition(line: str, stack_node_id: str) -> Tuple[str, None]:
        """エッジ定義を処理（スタックへの依存を逆転、Guard Clauseパターン適用）

        Args:
            line: DOTファイルのエッジ定義行
            stack_node_id: スタックノードのID

        Returns:
            (処理済み行, None) のタプル

        Notes:
            - リファクタリング（Issue #448）: Guard Clauseパターンを適用
            - 不正な形式の場合は早期リターン
        """
        parts = line.split('->')

        # Guard Clause: 不正な形式の場合は早期リターン
        if len(parts) != 2:
            return line, None

        from_node = parts[0].strip()
        to_part = parts[1].strip()

        # エッジ属性を抽出
        edge_attrs, to_node = DotFileProcessor._extract_edge_attributes(to_part)

        # Guard Clause: スタックノードでない場合は早期リターン
        if to_node != stack_node_id:
            return line, None

        # スタックから他のリソースへの矢印に変更
        new_line = f'    {stack_node_id} -> {from_node}'
        if edge_attrs:
            new_line += f' {edge_attrs}'
        new_line += ';'

        return new_line, None
    
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
        """単一ノードのラベルを処理（Guard Clauseパターン適用）

        Args:
            line: DOTファイルのノード定義行

        Returns:
            処理済みの行

        Notes:
            - リファクタリング（Issue #448）: Guard Clauseパターンを適用
            - ラベルが見つからない場合は早期リターン
        """
        match = re.search(r'\[label="([^"]+)"\]', line)

        # Guard Clause: ラベルが見つからない場合は早期リターン
        if not match:
            return line

        full_name = match.group(1)
        short_name = full_name.split('::')[-1]

        if len(short_name) > 30:
            short_name = short_name[:27] + '...'

        # プロバイダーに応じた色を設定
        fill_color, border_color = DotFileProcessor.DEFAULT_COLORS

        # プロバイダーを検出
        for provider_key in DotFileProcessor.PROVIDER_COLORS:
            if f'{provider_key}:' in full_name.lower():
                fill_color, border_color = DotFileProcessor.PROVIDER_COLORS[provider_key]
                if f'::{provider_key}:' in full_name.lower():
                    resource_type = full_name.split(f'::{provider_key}:')[1].split('::')[0]
                    short_name = f"{resource_type}\\n{short_name}"
                break

        return re.sub(
            r'\[label="[^"]+"\]',
            f'[label="{short_name}", fillcolor="{fill_color}", color="{border_color}"]',
            line
        )
    
    @staticmethod
    def _shorten_pulumi_label(line: str) -> str:
        """既存のメソッドを改善"""
        match = re.search(r'\[label="([^"]+)"\]', line)
        if not match:
            return line
        
        full_label = match.group(1)
        
        # URN形式の場合はparse_urnを使用
        if full_label.startswith('urn:pulumi:'):
            urn_info = DotFileProcessor.parse_urn(full_label)
            short_label = DotFileProcessor.create_readable_label(urn_info)
            
            # 色設定
            if DotFileProcessor.is_stack_resource(full_label):
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
