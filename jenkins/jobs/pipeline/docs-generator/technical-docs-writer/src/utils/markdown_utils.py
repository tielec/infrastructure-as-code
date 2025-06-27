"""!
Markdown処理ユーティリティモジュール

Markdownドキュメントの操作、編集、結合などの機能を提供します。
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from config import SectionType
from .logger import logger


def extract_markdown_headings(markdown_text: str) -> List[Tuple[int, str, str]]:
    """
    Markdownテキストから見出しを抽出します。
    
    Args:
        markdown_text: 処理するMarkdownテキスト
        
    Returns:
        List[Tuple[int, str, str]]: (レベル, 見出しテキスト, 見出し全体) のリスト
    """
    # 見出しを抽出する正規表現
    # '#' の数でレベルを判断し、続くテキストを取得
    heading_pattern = r'^(#{1,6})\s+(.+?)(?:\s+#+)?$'
    headings = []
    
    for line in markdown_text.split('\n'):
        match = re.match(heading_pattern, line)
        if match:
            level = len(match.group(1))  # '#' の数がレベル
            text = match.group(2).strip()
            headings.append((level, text, line))
    
    return headings


def adjust_heading_levels(markdown_text: str, base_level: int = 0) -> str:
    """
    Markdownテキストの見出しレベルを調整します。
    
    Args:
        markdown_text: 処理するMarkdownテキスト
        base_level: 基準となるレベル（これに相対的に調整）
        
    Returns:
        str: 見出しレベルが調整されたMarkdownテキスト
    """
    if base_level < 0:
        logger.warning(f"Invalid base_level: {base_level}, using 0")
        base_level = 0
    
    lines = markdown_text.split('\n')
    result = []
    
    heading_pattern = r'^(#{1,6})\s+(.+?)(?:\s+#+)?$'
    
    for line in lines:
        match = re.match(heading_pattern, line)
        if match:
            current_level = len(match.group(1))
            text = match.group(2).strip()
            
            # 基準レベルを足して新しいレベルを計算
            new_level = current_level + base_level
            
            # Markdownの見出しレベルは最大6
            new_level = min(6, max(1, new_level))
            
            # 新しい見出しを作成
            result.append('#' * new_level + ' ' + text)
        else:
            result.append(line)
    
    return '\n'.join(result)


def find_first_heading_level(markdown_text: str) -> int:
    """
    Markdownテキスト内の最初の見出しのレベルを取得します。
    
    Args:
        markdown_text: 処理するMarkdownテキスト
        
    Returns:
        int: 最初の見出しのレベル、見出しがない場合は0
    """
    heading_pattern = r'^(#{1,6})\s+.+'
    lines = markdown_text.split('\n')
    
    for line in lines:
        match = re.match(heading_pattern, line)
        if match:
            return len(match.group(1))
    
    return 0


def normalize_heading_levels(markdown_text: str) -> str:
    """
    Markdownテキストの見出しレベルを正規化します。
    最初の見出しをレベル1にして、他の見出しを相対的に調整します。
    
    Args:
        markdown_text: 処理するMarkdownテキスト
        
    Returns:
        str: 見出しレベルが正規化されたMarkdownテキスト
    """
    first_level = find_first_heading_level(markdown_text)
    if first_level <= 1:
        return markdown_text  # 既に正規化されているか、見出しがない
    
    # 最初のレベルを1にするための調整値を計算
    adjustment = 1 - first_level
    return adjust_heading_levels(markdown_text, adjustment)


def merge_markdown_documents(documents: List[str], add_separator: bool = True,
                           normalize_levels: bool = True) -> str:
    """
    複数のMarkdownドキュメントを結合します。
    
    Args:
        documents: 結合するMarkdownドキュメントのリスト
        add_separator: セクション間に区切り線を追加するかどうか
        normalize_levels: 見出しレベルを正規化するかどうか
        
    Returns:
        str: 結合されたMarkdownドキュメント
    """
    if not documents:
        return ""
    
    processed_docs = []
    
    for doc in documents:
        if not doc:
            continue
            
        # 各ドキュメントの見出しレベルを正規化
        if normalize_levels:
            doc = normalize_heading_levels(doc)
            
        # 先頭と末尾の空行を整理
        doc = doc.strip()
        processed_docs.append(doc)
    
    # 区切り文字を決定
    separator = "\n\n---\n\n" if add_separator else "\n\n"
    
    # ドキュメントを結合
    return separator.join(processed_docs)


def extract_toc(markdown_text: str) -> List[Tuple[int, str, str]]:
    """
    Markdownテキストから目次を抽出します。
    
    Args:
        markdown_text: 処理するMarkdownテキスト
        
    Returns:
        List[Tuple[int, str, str]]: (レベル, 見出しテキスト, アンカーリンク) のリスト
    """
    headings = extract_markdown_headings(markdown_text)
    toc_entries = []
    
    for level, text, _ in headings:
        # GitHubスタイルのアンカーリンクを生成
        # スペースをハイフンに変換し、英数字以外を削除
        anchor = text.lower()
        anchor = re.sub(r'[^\w\- ]', '', anchor)  # 英数字、ハイフン、スペース以外を削除
        anchor = re.sub(r'\s+', '-', anchor)      # スペースをハイフンに変換
        
        toc_entries.append((level, text, f"#{anchor}"))
    
    return toc_entries


def generate_toc(markdown_text: str, max_level: int = 3) -> str:
    """
    Markdownテキストから目次を生成します。
    
    Args:
        markdown_text: 処理するMarkdownテキスト
        max_level: 含める最大見出しレベル
        
    Returns:
        str: 目次のMarkdownテキスト
    """
    toc_entries = extract_toc(markdown_text)
    toc_lines = []
    
    for level, text, anchor in toc_entries:
        if level <= max_level:
            # インデントを適用
            indent = '  ' * (level - 1)
            toc_lines.append(f"{indent}- [{text}]({anchor})")
    
    if not toc_lines:
        return ""
        
    return "## 目次\n\n" + "\n".join(toc_lines)


def inject_toc(markdown_text: str, max_level: int = 3) -> str:
    """
    Markdownテキストに目次を挿入します。
    既存の目次がある場合は置換します。
    
    Args:
        markdown_text: 処理するMarkdownテキスト
        max_level: 含める最大見出しレベル
        
    Returns:
        str: 目次が挿入されたMarkdownテキスト
    """
    # 既存の目次セクションを探す
    toc_pattern = r'## 目次\s*\n\n(?:[ \t]*- \[.+?\]\(#.+?\)\s*\n)*'
    
    toc_content = generate_toc(markdown_text, max_level)
    if not toc_content:
        return markdown_text
    
    # 既存の目次があれば置換、なければ最初の見出しの前に挿入
    if re.search(toc_pattern, markdown_text):
        return re.sub(toc_pattern, toc_content + '\n\n', markdown_text)
    else:
        # 最初の見出しを探す
        first_heading_match = re.search(r'^#', markdown_text, re.MULTILINE)
        if first_heading_match:
            # 見出しの前に目次を挿入
            index = first_heading_match.start()
            return markdown_text[:index] + toc_content + '\n\n' + markdown_text[index:]
        else:
            # 見出しがなければ先頭に追加
            return toc_content + '\n\n' + markdown_text


def extract_code_blocks(markdown_text: str) -> List[Tuple[str, str]]:
    """
    Markdownテキストからコードブロックを抽出します。
    
    Args:
        markdown_text: 処理するMarkdownテキスト
        
    Returns:
        List[Tuple[str, str]]: (言語, コード) のリスト
    """
    # バッククォート3つで囲まれたコードブロックを抽出
    code_block_pattern = r'```(\w*)\n([\s\S]*?)\n```'
    code_blocks = re.findall(code_block_pattern, markdown_text)
    
    return code_blocks


def replace_mermaid_diagrams(markdown_text: str) -> str:
    """
    Mermaid記法の修正を行います。
    （特に空白や特殊文字を含むテキストをダブルクォートで囲むなど）
    
    Args:
        markdown_text: 処理するMarkdownテキスト
        
    Returns:
        str: 修正されたMarkdownテキスト
    """
    # mermaidブロックを抽出
    mermaid_pattern = r'```mermaid\n([\s\S]*?)\n```'
    
    def process_mermaid(match):
        mermaid_content = match.group(1)
        
        # ノード定義の修正（空白や特殊文字を含むテキストをダブルクォートで囲む）
        node_pattern = r'(\w+)(\[[^\]]+\])'
        
        def process_node(node_match):
            node_id = node_match.group(1)
            node_text = node_match.group(2)
            
            # 既にダブルクォートで囲まれていない場合のみ処理
            if not (node_text.startswith('["') and node_text.endswith('"]')):
                # 角括弧の中身を抽出
                text_content = node_text[1:-1]
                
                # 空白や特殊文字が含まれる場合はダブルクォートで囲む
                if re.search(r'[\s\(\)\-]', text_content):
                    return f'{node_id}["{text_content}"]'
            
            return node_match.group(0)
        
        # ノード定義を修正
        processed_content = re.sub(node_pattern, process_node, mermaid_content)
        
        return f"```mermaid\n{processed_content}\n```"
    
    # mermaidブロックを処理
    return re.sub(mermaid_pattern, process_mermaid, markdown_text)


class MarkdownSectionSplitter:
    """Markdownドキュメントをセクションに分割するクラス"""
    
    def __init__(self, section_headings_config: Dict[SectionType, str]):
        """
        Args:
            section_headings_config: セクションタイプと見出し文字列の対応辞書
        """
        self.section_headings_config = section_headings_config
        self.heading_to_section = self._create_heading_mapping()
        
    def _create_heading_mapping(self) -> Dict[str, SectionType]:
        """見出しテキストとセクションタイプのマッピングを作成"""
        mapping = {}
        for section_type, heading_text in self.section_headings_config.items():
            mapping[heading_text.lower()] = section_type
        return mapping
    
    def _is_toc_heading(self, line: str) -> bool:
        """目次の見出しかどうかを判定"""
        return line.strip().lower() == "## 目次"
    
    def _is_level1_heading(self, line: str) -> bool:
        """レベル1の見出しかどうかを判定"""
        stripped = line.strip()
        return stripped.startswith("# ") and not stripped.startswith("## ")
    
    def _is_level2_heading(self, line: str) -> bool:
        """レベル2の見出しかどうかを判定"""
        return line.strip().startswith("## ")
    
    def _extract_heading_text(self, line: str) -> str:
        """見出し行から見出しテキストを抽出"""
        return line.strip()[3:].strip()  # "## " を除去
    
    def _find_section_type(self, heading_text: str) -> Optional[SectionType]:
        """見出しテキストから対応するセクションタイプを探す"""
        heading_lower = heading_text.lower()
        return self.heading_to_section.get(heading_lower)
    
    def _is_end_of_toc(self, line: str, next_line: Optional[str], in_toc: bool) -> bool:
        """目次セクションの終了を判定"""
        if not in_toc:
            return False
            
        stripped = line.strip()
        
        # 次のレベル2見出しで終了
        if stripped.startswith("## "):
            return True
            
        # 空行の後の非インデント行で終了
        if not stripped and next_line:
            next_stripped = next_line.strip()
            if next_stripped and not next_line.startswith((' ', '\t', '-', '*')):
                return True
                
        return False
    
    def _save_section(self, sections: Dict[SectionType, str], 
                     section_type: Optional[SectionType], 
                     lines: List[str]) -> None:
        """セクションを辞書に保存"""
        if not section_type or not lines:
            return
            
        content = '\n'.join(lines).strip()
        if content:
            sections[section_type] = content
            logger.debug(f"Saved section: {section_type.value} ({len(content)} chars)")
    
    def split(self, markdown_text: str) -> Dict[SectionType, str]:
        """
        Markdownドキュメントをセクションごとに分割します。
        
        Args:
            markdown_text: 結合済みのMarkdownテキスト全体
            
        Returns:
            Dict[SectionType, str]: セクションタイプをキー、対応するセクションのMarkdown文字列を値とする辞書
        """
        logger.info("Starting to split markdown document into sections")
        
        sections = {}
        state = self._create_parsing_state(markdown_text)
        
        for i, line in enumerate(state.lines):
            state.current_line_index = i
            self._process_line(line, state, sections)
        
        # 最後のセクションを保存
        self._save_section(sections, state.current_section_type, state.current_section_lines)
        self._log_results(sections)
        
        return sections
    
    def _create_parsing_state(self, markdown_text: str):
        """パース状態を管理するオブジェクトを作成"""
        class ParsingState:
            def __init__(self, lines):
                self.lines = lines
                self.current_section_type = None
                self.current_section_lines = []
                self.in_toc = False
                self.current_line_index = 0
                
            def get_next_line(self):
                """次の行を取得（存在しない場合はNone）"""
                next_index = self.current_line_index + 1
                return self.lines[next_index] if next_index < len(self.lines) else None
        
        return ParsingState(markdown_text.split('\n'))
    
    def _process_line(self, line: str, state, sections: Dict[SectionType, str]) -> None:
        """1行を処理"""
        # 目次セクションの処理
        if self._handle_toc_section(line, state):
            return
        
        # レベル1の見出しはスキップ
        if self._is_level1_heading(line):
            return
        
        # レベル2の見出しを処理
        if self._is_level2_heading(line):
            self._handle_section_heading(line, state, sections)
        else:
            # セクション内容を収集
            self._collect_section_content(line, state)
    
    def _handle_toc_section(self, line: str, state) -> bool:
        """目次セクションの処理を行い、処理した場合はTrueを返す"""
        if self._is_toc_heading(line):
            state.in_toc = True
            return True
        
        if state.in_toc:
            next_line = state.get_next_line()
            if self._is_end_of_toc(line, next_line, state.in_toc):
                state.in_toc = False
                # レベル2見出しでない場合はスキップ
                return not self._is_level2_heading(line)
            return True
        
        return False
    
    def _handle_section_heading(self, line: str, state, sections: Dict[SectionType, str]) -> None:
        """セクション見出しを処理"""
        # 前のセクションを保存
        self._save_section(sections, state.current_section_type, state.current_section_lines)
        
        # 新しいセクションの開始
        heading_text = self._extract_heading_text(line)
        found_section_type = self._find_section_type(heading_text)
        
        if found_section_type:
            state.current_section_type = found_section_type
            state.current_section_lines = []
            logger.debug(f"Found section heading: {heading_text} -> {found_section_type.value}")
        else:
            # 未知の見出しは現在のセクションに含める
            self._handle_unknown_heading(line, heading_text, state)
    
    def _handle_unknown_heading(self, line: str, heading_text: str, state) -> None:
        """未知の見出しを処理"""
        if state.current_section_type:
            state.current_section_lines.append(line)
        logger.warning(f"Unknown section heading: {heading_text}")
    
    def _collect_section_content(self, line: str, state) -> None:
        """セクション内容を収集"""
        if state.current_section_type:
            state.current_section_lines.append(line)
    
    def _log_results(self, sections: Dict[SectionType, str]) -> None:
        """処理結果のログ出力"""
        section_names = ', '.join([s.value for s in sections.keys()])
        logger.info(f"Successfully split document into {len(sections)} sections: {section_names}")
        
        # 存在しないセクションについて警告
        missing_sections = set(self.section_headings_config.keys()) - set(sections.keys())
        if missing_sections:
            missing_names = ', '.join([s.value for s in missing_sections])
            logger.warning(f"Following sections were not found in the document: {missing_names}")


def split_markdown_into_sections(markdown_text: str, section_headings_config: Dict[SectionType, str]) -> Dict[SectionType, str]:
    """
    結合済みのMarkdownドキュメントをセクションごとに分割します。
    
    Args:
        markdown_text: 結合済みのMarkdownテキスト全体
        section_headings_config: セクションタイプと見出し文字列の対応辞書（SECTION_HEADINGS）
        
    Returns:
        Dict[SectionType, str]: セクションタイプをキー、対応するセクションのMarkdown文字列を値とする辞書
    """
    splitter = MarkdownSectionSplitter(section_headings_config)
    return splitter.split(markdown_text)
