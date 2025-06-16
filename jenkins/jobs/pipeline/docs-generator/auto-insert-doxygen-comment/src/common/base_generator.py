"""
ドキュメント生成の共通基底クラスとインターフェース
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any, TypeVar, Generic, Protocol

@dataclass
class BaseElementInfo:
    """コード要素（関数やクラス）の基本情報を保持する基底データクラス"""
    name: str
    code: str
    start_line: int
    source_lines: List[str]
    indent: str

@dataclass
class InsertionPoint:
    """docstring/doxygen の挿入位置情報を保持するデータクラス"""
    def_line: int
    body_start: int
    existing_doc_start: int
    existing_doc_end: int
    base_indent: str

    def has_existing_doc(self) -> bool:
        """既存のドキュメントが存在するかどうかを確認"""
        return self.existing_doc_start >= 0 and self.existing_doc_end >= 0

T = TypeVar('T', bound=BaseElementInfo)

class ElementParser(Protocol):
    """要素解析のためのプロトコル"""

    def parse_file(self, file_path: str) -> List[Any]:
        """ファイルを解析して要素のリストを返す"""
        ...

    def extract_module_info(self, source: str, source_lines: List[str]) -> Any:
        """モジュール情報を抽出する"""
        ...

class BaseElement(ABC, Generic[T]):
    """コード要素を表す抽象基底クラス"""
    
    def __init__(self, info: T):
        self.info = info
    
    @abstractmethod
    def get_definition_pattern(self) -> str:
        """要素の定義パターン（正規表現）を返す"""
        pass
    
    @abstractmethod
    def get_doc_indent(self) -> str:
        """ドキュメントのインデントレベルを返す"""
        pass
    
    @abstractmethod
    def find_body_start(self, lines: List[str], def_line: int) -> int:
        """コード本体の開始行を見つける"""
        pass

    @abstractmethod
    def find_existing_doc(self, lines: List[str], def_line: int) -> tuple[int, int]:
        """既存のドキュメントの位置を探す"""
        pass

    def analyze_insertion_point(self, lines: List[str]) -> InsertionPoint:
        """ドキュメントの挿入位置を解析"""
        def_line = self._find_definition_line(lines)
        if def_line is None:
            raise ValueError(f"Could not find {self.__class__.__name__} {self.info.name}")
        
        body_start = self.find_body_start(lines, def_line)
        existing_doc_start, existing_doc_end = self.find_existing_doc(lines, def_line)
        base_indent = self.get_doc_indent()
        
        return InsertionPoint(
            def_line=def_line,
            body_start=body_start,
            existing_doc_start=existing_doc_start,
            existing_doc_end=existing_doc_end,
            base_indent=base_indent
        )
    
    def _find_definition_line(self, lines: List[str]) -> Optional[int]:
        """要素の定義行を探す"""
        import re
        pattern = self.get_definition_pattern()
        
        for i, line in enumerate(lines):
            if re.search(pattern, line.strip()):
                return i
        return None

class BaseDocGenerator(ABC):
    """ドキュメント生成の抽象基底クラス"""
    
    @abstractmethod
    def process_file(self, file_path: str, 
                    templates: Dict[str, str],
                    overwrite_doc: bool = False) -> None:
        """ファイルを処理し、ドキュメントを生成・挿入する"""
        pass
    
    @abstractmethod
    def _process_element(self, element: BaseElement, file_path: str, template: str) -> None:
        """個別のコード要素を処理する"""
        pass
    
    @abstractmethod
    def _format_doc(self, raw_doc: str) -> str:
        """生成されたドキュメントを整形する"""
        pass
    
    @abstractmethod
    def _insert_doc(self, lines: List[str], insertion: InsertionPoint, doc: str) -> None:
        """ドキュメントをファイルに挿入する"""
        pass
    
    def get_usage_stats(self) -> Dict[str, int]:
        """APIの使用統計を取得する

        Returns:
            Dict[str, int]: トークン使用量の統計
        """
        # デフォルト実装（サブクラスでオーバーライド可能）
        return {
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0
        }
