#!/usr/bin/env python3
import os
import sys
from typing import List, Dict, Optional, Any, Tuple


def calculate_metrics(data: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    データセットからメトリクスを計算します。
    
    Returns:
        Dict: 計算されたメトリクス
    """
    total = sum(item.get('value', 0) for item in data)
    avg = total / len(data) if data else 0
    
    return {
        'total': total,
        'average': avg,
        'count': len(data)
    }


class DataProcessor:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.processed_data = []
    
    def process_file(self, file_path: str) -> Tuple[bool, str]:
        """
        ファイルを処理してデータを抽出します。
        
        Args:
            file_path: 処理対象ファイルパス
        
        Returns:
            Tuple[bool, str]: 処理結果と説明メッセージ
        """
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            # 何らかの処理を実行
            lines = content.split('\n')
            self.processed_data = [
                {'line_number': i, 'content': line}
                for i, line in enumerate(lines, 1)
            ]
            
            return True, f"Successfully processed {len(lines)} lines"
        except Exception as e:
            return False, f"Error processing file: {str(e)}"
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        処理されたデータの統計情報を取得します。
        
        Returns:
            Dict: 統計情報を含む辞書
        """
        if not self.processed_data:
            return {'error': 'No data processed yet'}
        
        stats = {
            'lines_count': len(self.processed_data),
            'empty_lines': sum(1 for item in self.processed_data if not item['content'].strip()),
            'longest_line': max((len(item['content']) for item in self.processed_data), default=0)
        }
        
        return stats


def main():
    """
    メイン実行関数
    """
    if len(sys.argv) < 2:
        print("Usage: python example_module.py [file_path]")
        return
    
    file_path = sys.argv[1]
    processor = DataProcessor()
    success, message = processor.process_file(file_path)
    
    if success:
        print(f"Processing successful: {message}")
        stats = processor.get_statistics()
        print(f"Statistics: {stats}")
    else:
        print(f"Processing failed: {message}")


if __name__ == "__main__":
    main()
