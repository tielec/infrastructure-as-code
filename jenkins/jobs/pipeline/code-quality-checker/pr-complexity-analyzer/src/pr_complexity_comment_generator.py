#!/usr/bin/env python3
"""
PR複雑度解析結果に基づくコメント生成スクリプト
OpenAI APIを使用して、複雑度解析結果から意味のあるPRコメントを生成します。
"""

import json
import os
import argparse
import logging
import re
from typing import Dict, Any, List, Tuple, Optional
from openai import OpenAI
from datetime import datetime
from dataclasses import dataclass
import time

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ComplexityThresholds:
    """複雑度の閾値設定"""
    cyclomatic: int
    cognitive: int
    cyclomatic_warning: int
    cognitive_warning: int


@dataclass
class FunctionMetrics:
    """関数のメトリクス情報"""
    name: str
    file: str
    cyclomatic: int
    cognitive: int
    lines: int
    start_line: int
    end_line: int


@dataclass
class ComplexityStatistics:
    """複雑度統計情報"""
    total_functions: int
    total_files: int
    avg_cyclomatic: float
    avg_cognitive: float
    max_cyclomatic: int
    max_cognitive: int
    thresholds: ComplexityThresholds
    functions_above_threshold: Dict[str, int]
    high_complexity_functions: List[Dict[str, Any]]
    warning_level_functions: List[Dict[str, Any]]


@dataclass
class OpenAIConfig:
    """OpenAI API設定"""
    api_key: str
    model: str = "gpt-4.1"
    temperature: float = 0.7
    max_tokens: int = 3000
    debug_mode: bool = False


class StatisticsCalculator:
    """統計情報の計算を担当するクラス"""
    
    @staticmethod
    def calculate_thresholds(analysis_result: Dict[str, Any]) -> ComplexityThresholds:
        """閾値情報を計算"""
        thresholds = analysis_result.get('thresholds', {})
        cyclomatic_threshold = thresholds.get('cyclomatic', 15)
        cognitive_threshold = thresholds.get('cognitive', 20)
        
        return ComplexityThresholds(
            cyclomatic=cyclomatic_threshold,
            cognitive=cognitive_threshold,
            cyclomatic_warning=int(cyclomatic_threshold * 0.7),
            cognitive_warning=int(cognitive_threshold * 0.7)
        )
    
    @staticmethod
    def classify_functions(all_functions: List[Dict[str, Any]], 
                         thresholds: ComplexityThresholds) -> Tuple[List[Dict], List[Dict]]:
        """関数を複雑度レベルで分類"""
        high_complexity = []
        warning_level = []
        
        for func in all_functions:
            cogn = func.get('cognitive', 0)
            cyclo = func.get('cyclomatic', 0)
            
            if cogn > thresholds.cognitive or cyclo > thresholds.cyclomatic:
                high_complexity.append(func)
            elif (thresholds.cognitive_warning <= cogn <= thresholds.cognitive or
                  thresholds.cyclomatic_warning <= cyclo <= thresholds.cyclomatic):
                warning_level.append(func)
        
        return high_complexity, warning_level
    
    @staticmethod
    def calculate_averages(file_analyses: Dict[str, Any]) -> Tuple[float, float, int, int]:
        """ファイル解析データから平均値と最大値を計算"""
        if not file_analyses:
            return 0.0, 0.0, 0, 0
        
        # 各メトリクスのリストを収集
        metrics = StatisticsCalculator._collect_metrics(file_analyses)
        
        # 平均値と最大値を計算
        avg_cyclomatic = StatisticsCalculator._calculate_average(metrics['avg_cyclo'])
        avg_cognitive = StatisticsCalculator._calculate_average(metrics['avg_cogn'])
        max_cyclomatic = max(metrics['max_cyclo']) if metrics['max_cyclo'] else 0
        max_cognitive = max(metrics['max_cogn']) if metrics['max_cogn'] else 0
        
        return avg_cyclomatic, avg_cognitive, max_cyclomatic, max_cognitive
    
    @staticmethod
    def _collect_metrics(file_analyses: Dict[str, Any]) -> Dict[str, List[float]]:
        """ファイル解析データからメトリクスを収集"""
        metrics = {
            'avg_cyclo': [],
            'avg_cogn': [],
            'max_cyclo': [],
            'max_cogn': []
        }
        
        for file_data in file_analyses.values():
            if file_data.get('average_cyclomatic', 0) > 0:
                metrics['avg_cyclo'].append(file_data['average_cyclomatic'])
            if file_data.get('average_cognitive', 0) > 0:
                metrics['avg_cogn'].append(file_data['average_cognitive'])
            metrics['max_cyclo'].append(file_data.get('max_cyclomatic', 0))
            metrics['max_cogn'].append(file_data.get('max_cognitive', 0))
        
        return metrics
    
    @staticmethod
    def _calculate_average(values: List[float]) -> float:
        """リストの平均値を計算"""
        return sum(values) / len(values) if values else 0.0


class CommentFormatter:
    """コメントフォーマットを担当するクラス"""
    
    @staticmethod
    def format_function_header(func: Dict[str, Any], index: int) -> List[str]:
        """関数のヘッダー情報をフォーマット"""
        return [
            f"\n{index}. **{func.get('name', 'Unknown')}**",
            f"   - ファイル: {func.get('file', 'Unknown')}",
            f"   - 行: {func.get('start_line', 0)}-{func.get('end_line', 0)}",
        ]
    
    @staticmethod
    def format_complexity_metrics(func: Dict[str, Any], thresholds: ComplexityThresholds) -> List[str]:
        """複雑度メトリクスをフォーマット"""
        return [
            f"   - 認知的複雑度: {func.get('cognitive', 0)} (閾値: {thresholds.cognitive})",
            f"   - 循環的複雑度: {func.get('cyclomatic', 0)} (閾値: {thresholds.cyclomatic})",
            f"   - コード行数: {func.get('lines', 0)}",
        ]
    
    @staticmethod
    def format_warning_metrics(func: Dict[str, Any], thresholds: ComplexityThresholds) -> List[str]:
        """警告レベルのメトリクスをフォーマット"""
        return [
            f"   - 認知的複雑度: {func.get('cognitive', 0)} "
            f"(警告: {thresholds.cognitive_warning}, 閾値: {thresholds.cognitive})",
            f"   - 循環的複雑度: {func.get('cyclomatic', 0)} "
            f"(警告: {thresholds.cyclomatic_warning}, 閾値: {thresholds.cyclomatic})",
        ]
    
    @staticmethod
    def create_summary_section(stats: ComplexityStatistics, pr_info: Dict[str, Any]) -> List[str]:
        """サマリーセクションを作成"""
        return [
            "# 🔍 コード複雑度解析レポート",
            "",
            "## 📊 解析サマリー",
            f"PR #{pr_info.get('pr_number', 'N/A')}の複雑度解析が完了しました。",
            f"- 解析ファイル数: {stats.total_files}",
            f"- 総関数数: {stats.total_functions}",
            f"- 平均循環的複雑度: {stats.avg_cyclomatic:.2f}",
            f"- 平均認知的複雑度: {stats.avg_cognitive:.2f}",
            "",
        ]
    
    @staticmethod
    def create_threshold_section(thresholds: ComplexityThresholds) -> List[str]:
        """閾値セクションを作成"""
        return [
            "## 📏 複雑度の閾値",
            f"- 認知的複雑度: 警告 {thresholds.cognitive_warning}, 閾値 {thresholds.cognitive}",
            f"- 循環的複雑度: 警告 {thresholds.cyclomatic_warning}, 閾値 {thresholds.cyclomatic}",
            "",
        ]
    
    @staticmethod
    def create_recommendations_section(has_complex_functions: bool) -> List[str]:
        """推奨事項セクションを作成"""
        if has_complex_functions:
            return [
                "",
                "## 💡 推奨事項",
                "1. 🔴 閾値を超える関数は優先的にリファクタリングしてください",
                "2. 単一責任の原則に従って関数を分割することを検討してください",
                "3. 条件分岐が多い場合は、早期リターンやガード句を活用してください",
                "4. ネストレベルを減らすために、処理を別関数に抽出してください",
            ]
        else:
            return [
                "",
                "## 💡 推奨事項",
                "- 現在の良好な状態を維持してください",
                "- 新機能追加時も複雑度を意識した実装を心がけてください",
                "- 定期的なコードレビューで複雑度をモニタリングしてください",
            ]


class PRComplexityCommentGenerator:
    """PR複雑度解析結果からコメントを生成するクラス"""
    
    def __init__(self, debug_mode: bool = False, save_prompt: bool = False):
        """初期化"""
        # OpenAI設定を構築
        self.config = OpenAIConfig(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
            debug_mode=debug_mode
        )
        
        # OpenAIクライアントを初期化
        self.client = OpenAI(
            api_key=self.config.api_key
        )
        
        self.stats_calculator = StatisticsCalculator()
        self.comment_formatter = CommentFormatter()
        self.save_prompt = save_prompt
        self.show_prompt = False  # コンソールにプロンプトを表示するかどうか
        
        # 設定をログ出力
        self._log_configuration()
    
    def _log_configuration(self):
        """現在の設定をログ出力"""
        logger.info("=== OpenAI API Configuration ===")
        logger.info(f"Model: {self.config.model}")
        logger.info(f"Temperature: {self.config.temperature}")
        logger.info(f"Max Tokens: {self.config.max_tokens}")
        logger.info(f"Debug Mode: {self.config.debug_mode}")
        logger.info("================================")
        
    def generate_comment(self, analysis_result: Dict[str, Any]) -> str:
        """
        解析結果からPRコメントを生成
        
        Args:
            analysis_result: 複雑度解析結果
            
        Returns:
            生成されたコメント
        """
        # 統計情報を準備
        stats = self._prepare_statistics(analysis_result)
        
        # プロンプトを構築
        prompt = self._build_prompt(analysis_result, stats)
        
        # プロンプトの表示と保存
        self._handle_prompt_output(prompt)
        
        # OpenAI APIを呼び出してコメントを生成
        try:
            content = self._call_openai_api(prompt)
            return self._clean_markdown_tags(content)
        except Exception as e:
            return self._handle_api_error(e, analysis_result, stats)
    
    def _handle_prompt_output(self, prompt: str) -> None:
        """プロンプトの表示と保存を処理"""
        # プロンプトをコンソールに表示（オプション）
        if self.show_prompt:
            print("\n" + "="*60)
            print("PROMPT TO OPENAI:")
            print("="*60)
            print(prompt)
            print("="*60 + "\n")
        
        # デバッグモードまたはプロンプト保存が有効な場合
        if self.config.debug_mode or self.save_prompt:
            self._save_prompt_to_file(prompt)
        
        # プロンプトの文字数とトークン概算をログ出力（常に表示）
        prompt_length = len(prompt)
        estimated_tokens = prompt_length // 4  # 概算：1トークン≒4文字
        logger.info(f"Prompt length: {prompt_length} characters (estimated ~{estimated_tokens} tokens)")
    
    def _call_openai_api(self, prompt: str) -> str:
        """OpenAI APIを呼び出してレスポンスを取得"""
        logger.info("Calling OpenAI API...")
        start_time = time.time()
        
        messages = [
            {
                "role": "system",
                "content": "あなたはコードレビューの専門家です。複雑度解析結果を分析し、開発者に有用な具体的なフィードバックを提供します。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # APIパラメータをログ出力
        if self.config.debug_mode:
            logger.debug(f"Messages: {json.dumps(messages, ensure_ascii=False, indent=2)}")
        
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        
        # API呼び出しの詳細をログ出力
        self._log_api_response_details(response, start_time)
        
        content = response.choices[0].message.content
        
        # デバッグモードの場合、生成されたコンテンツも保存
        if self.config.debug_mode:
            self._save_response_to_file(content)
        
        return content
    
    def _log_api_response_details(self, response: Any, start_time: float) -> None:
        """APIレスポンスの詳細をログ出力"""
        elapsed_time = time.time() - start_time
        logger.info(f"API call completed in {elapsed_time:.2f} seconds")
        logger.info(f"Usage - Prompt tokens: {response.usage.prompt_tokens}")
        logger.info(f"Usage - Completion tokens: {response.usage.completion_tokens}")
        logger.info(f"Usage - Total tokens: {response.usage.total_tokens}")
    
    def _handle_api_error(self, error: Exception, analysis_result: Dict[str, Any], 
                         stats: ComplexityStatistics) -> str:
        """APIエラーを処理してフォールバックコメントを生成"""
        logger.error(f"OpenAI API呼び出しエラー: {error}")
        logger.error(f"Error type: {type(error).__name__}")
        return self._generate_fallback_comment(analysis_result, stats)
    
    def _save_prompt_to_file(self, prompt: str):
        """プロンプトをファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"openai_prompt_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=== OpenAI API Prompt ===\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Model: {self.config.model}\n")
                f.write(f"Temperature: {self.config.temperature}\n")
                f.write(f"Max Tokens: {self.config.max_tokens}\n")
                f.write("========================\n\n")
                f.write(prompt)
            logger.info(f"Prompt saved to: {filename}")
        except Exception as e:
            logger.error(f"Failed to save prompt: {e}")
    
    def _save_response_to_file(self, response: str):
        """レスポンスをファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"openai_response_{timestamp}.md"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response)
            logger.info(f"Response saved to: {filename}")
        except Exception as e:
            logger.error(f"Failed to save response: {e}")
    
    def _clean_markdown_tags(self, content: str) -> str:
        """
        生成されたコンテンツから不要なマークダウンタグを削除
        
        Args:
            content: 元のコンテンツ
            
        Returns:
            クリーンアップされたコンテンツ
        """
        if not content:
            return content
            
        # コンテンツを行に分割
        lines = content.split('\n')
        
        # 最初と最後の```markdownタグを削除
        if lines and lines[0].strip().lower() in ['```markdown', '```md', '```']:
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
            
        # 再度チェック（複数の```タグがある場合）
        cleaned_content = '\n'.join(lines)
        
        # 正規表現で残りの```markdownタグを削除（コードブロック内のものは保持）
        # パターン: 行頭の```markdown または ```md を削除
        cleaned_content = re.sub(r'^```(?:markdown|md)\s*\n', '', cleaned_content, flags=re.MULTILINE)
        cleaned_content = re.sub(r'\n```\s*$', '', cleaned_content, flags=re.MULTILINE)
        
        # 連続する空行を1つに削減
        cleaned_content = re.sub(r'\n\n\n+', '\n\n', cleaned_content)
        
        # 先頭と末尾の空白を削除
        cleaned_content = cleaned_content.strip()
        
        return cleaned_content
    
    def _prepare_statistics(self, analysis_result: Dict[str, Any]) -> ComplexityStatistics:
        """統計情報を準備（リファクタリング済み）"""
        # 閾値を計算
        thresholds = self.stats_calculator.calculate_thresholds(analysis_result)
        
        # 基本統計情報を取得
        total_functions = analysis_result.get('total_functions', 0)
        total_files = analysis_result.get('total_files_analyzed', 0)
        
        # 全関数情報を取得
        all_functions = analysis_result.get('all_functions', [])
        
        # 関数を分類
        if all_functions:
            high_complexity, warning_level = self.stats_calculator.classify_functions(
                all_functions, thresholds
            )
        else:
            # フォールバック：high_complexity_functionsのみを使用
            high_complexity = analysis_result.get('high_complexity_functions', [])
            warning_level = []
        
        # 平均値と最大値を計算
        avg_cyclo, avg_cogn, max_cyclo, max_cogn = self.stats_calculator.calculate_averages(
            analysis_result.get('file_analyses', {})
        )
        
        return ComplexityStatistics(
            total_functions=total_functions,
            total_files=total_files,
            avg_cyclomatic=avg_cyclo,
            avg_cognitive=avg_cogn,
            max_cyclomatic=max_cyclo,
            max_cognitive=max_cogn,
            thresholds=thresholds,
            functions_above_threshold={
                'cyclomatic': analysis_result.get('high_complexity_functions_cyclomatic', 0),
                'cognitive': analysis_result.get('high_complexity_functions_cognitive', 0)
            },
            high_complexity_functions=high_complexity,
            warning_level_functions=warning_level
        )
    
    def _build_prompt(self, analysis_result: Dict[str, Any], stats: ComplexityStatistics) -> str:
        """OpenAI API用のプロンプトを構築"""
        
        # 高複雑度関数の詳細リスト
        high_complexity_details = self._format_function_details(
            stats.high_complexity_functions,
            stats.warning_level_functions,
            stats.thresholds
        )
        
        # 全関数の概要を追加
        all_functions_summary = self._format_all_functions_summary(
            analysis_result.get('all_functions', []),
            stats.thresholds
        )
        
        # 閾値を超える関数がない場合の追加指示
        no_complex_functions_instructions = ""
        if stats.functions_above_threshold['cognitive'] == 0 and stats.functions_above_threshold['cyclomatic'] == 0:
            no_complex_functions_instructions = """
# 特記事項
閾値を超える関数は検出されませんでした。以下の観点でフィードバックを提供してください：
- 現在の良好な実装パターンを具体的に評価
- 最も複雑度が高い関数（閾値未満でも）について、将来的な改善の余地があるか検討
- チーム全体で共有すべきベストプラクティスの抽出
- 今後の開発で維持すべき品質基準の提案
"""
        
        prompt = f"""以下のコード複雑度解析結果に基づいて、GitHub PRコメントを生成してください。

# 解析結果サマリー
- 解析ファイル数: {stats.total_files}
- 総関数数: {stats.total_functions}
- 平均循環的複雑度: {stats.avg_cyclomatic:.2f}
- 平均認知的複雑度: {stats.avg_cognitive:.2f}
- 最大循環的複雑度: {stats.max_cyclomatic}
- 最大認知的複雑度: {stats.max_cognitive}

# 設定された閾値
- 循環的複雑度の閾値: {stats.thresholds.cyclomatic} (警告レベル: {stats.thresholds.cyclomatic_warning})
- 認知的複雑度の閾値: {stats.thresholds.cognitive} (警告レベル: {stats.thresholds.cognitive_warning})

# 閾値を超える関数
- 循環的複雑度が閾値を超える関数: {stats.functions_above_threshold['cyclomatic']}個
- 認知的複雑度が閾値を超える関数: {stats.functions_above_threshold['cognitive']}個

# 関数の詳細情報
{high_complexity_details}

# 全関数の概要
{all_functions_summary}
{no_complex_functions_instructions}
# PR情報
- PR番号: #{analysis_result.get('pr_number', 'N/A')}
- タイトル: {analysis_result.get('pr_title', 'N/A')}

以下の形式でMarkdownコメントを生成してください：

1. **解析サマリー**: 全体的な評価を2-3文で簡潔に（平均値と最大値に基づいて）
   - 平均複雑度が低い場合は、その良好な状態を評価
   - 最大複雑度も閾値内の場合は、それも明記

2. **重要な発見事項**:
   - 🚨 **優先的に対応が必要な関数**: 認知的複雑度が閾値を超える関数（{stats.thresholds.cognitive}以上）を具体的にリストし、なぜ複雑なのか、どうリファクタリングすべきか提案
   - ⚠️ **注意が必要な領域**: 警告レベル（認知的: {stats.thresholds.cognitive_warning}-{stats.thresholds.cognitive-1}、循環的: {stats.thresholds.cyclomatic_warning}-{stats.thresholds.cyclomatic-1}）の関数を具体的にリスト
   - ✅ **良好な実装**: 特に複雑度が低く、良い実装パターンとなっている関数を2-3個具体的に挙げて評価

3. **具体的な改善提案**: 
   - 高複雑度関数がある場合：
     * 関数の分割（単一責任の原則）
     * 条件分岐の簡略化
     * ネストレベルの削減
     * 早期リターンの活用
   - 高複雑度関数がない場合：
     * 現在の良好な実装を維持するためのガイドライン
     * さらなる改善の余地がある関数への提案（あれば）
     * チーム全体で共有すべきコーディング規約

4. **メトリクス詳細**: 主要な数値を表形式でまとめる
   | メトリクス | 値 | 評価 |
   |----------|-----|------|
   | 平均認知的複雑度 | X.XX | 🟢/🟡/🔴 |
   | 平均循環的複雑度 | X.XX | 🟢/🟡/🔴 |
   | 最大認知的複雑度 | XX | 🟢/🟡/🔴 |
   | 最大循環的複雑度 | XX | 🟢/🟡/🔴 |

5. **次のステップ**: 
   - 高複雑度関数がある場合：優先順位付けされたアクション項目
   - 高複雑度関数がない場合：品質を維持するための推奨事項

重要な注意事項:
- 必ず具体的な関数名と複雑度の数値を含めてください
- 警告レベルの関数も具体的な名前と数値を含めて記載してください
- 認知的複雑度を循環的複雑度より優先して説明してください（認知的複雑度の方が実際の理解しやすさを表すため）
- 改善提案は実装可能で具体的なものにしてください
- 閾値を超える関数がない場合でも、建設的で有用なフィードバックを提供してください
- トーンは建設的で協力的に保ってください
- 出力にマークダウンのコードブロック記号（```）を含めないでください
- 純粋なMarkdown形式で出力してください（```markdownなどのタグは不要）"""
        
        return prompt
    
    def _format_function_details(self, high_complexity_functions: List[Dict], 
                               warning_functions: List[Dict],
                               thresholds: ComplexityThresholds) -> str:
        """関数の詳細情報をフォーマット（リファクタリング済み）"""
        if not high_complexity_functions and not warning_functions:
            return "## 閾値を超える関数・警告レベルの関数はありません"
        
        result = []
        
        # 高複雑度関数をフォーマット
        if high_complexity_functions:
            result.extend(self._format_high_complexity_functions(high_complexity_functions, thresholds))
        
        # 警告レベル関数をフォーマット
        if warning_functions:
            result.extend(self._format_warning_level_functions(warning_functions, thresholds))
        
        return "\n".join(result)
    
    def _format_all_functions_summary(self, all_functions: List[Dict], 
                                    thresholds: ComplexityThresholds) -> str:
        """全関数の概要をフォーマット"""
        if not all_functions:
            return "関数の詳細情報が取得できませんでした。"
        
        result = [f"総関数数: {len(all_functions)}個"]
        
        # 複雑度の分布を追加
        result.extend(self._format_complexity_distribution(all_functions))
        
        # 最も複雑な関数を追加
        result.extend(self._format_most_complex_functions(all_functions))
        
        # 最も単純な関数を追加
        result.extend(self._format_simplest_functions(all_functions))
        
        return "\n".join(result)
    
    def _format_complexity_distribution(self, all_functions: List[Dict]) -> List[str]:
        """複雑度の分布をフォーマット"""
        distribution = self._calculate_complexity_distribution(all_functions)
        
        result = ["\n複雑度の分布:"]
        for level, count in distribution.items():
            if count > 0:
                percentage = (count / len(all_functions)) * 100
                result.append(f"- {level}: {count}個 ({percentage:.1f}%)")
        
        return result
    
    def _calculate_complexity_distribution(self, all_functions: List[Dict]) -> Dict[str, int]:
        """複雑度の分布を計算"""
        distribution = {
            '低（認知的 < 5）': 0,
            '中（認知的 5-9）': 0,
            '高（認知的 10-14）': 0,
            '警告（認知的 15-19）': 0,
            '危険（認知的 20+）': 0
        }
        
        for func in all_functions:
            cognitive = func.get('cognitive', 0)
            if cognitive < 5:
                distribution['低（認知的 < 5）'] += 1
            elif cognitive < 10:
                distribution['中（認知的 5-9）'] += 1
            elif cognitive < 15:
                distribution['高（認知的 10-14）'] += 1
            elif cognitive < 20:
                distribution['警告（認知的 15-19）'] += 1
            else:
                distribution['危険（認知的 20+）'] += 1
        
        return distribution
    
    def _format_most_complex_functions(self, all_functions: List[Dict]) -> List[str]:
        """最も複雑な関数をフォーマット"""
        # 複雑度でソート（認知的複雑度優先）
        sorted_functions = sorted(all_functions, 
                                key=lambda x: (x.get('cognitive', 0), x.get('cyclomatic', 0)), 
                                reverse=True)
        
        result = ["\n最も複雑な関数（上位5個）:"]
        for i, func in enumerate(sorted_functions[:5], 1):
            result.append(self._format_function_summary(i, func))
        
        return result
    
    def _format_simplest_functions(self, all_functions: List[Dict]) -> List[str]:
        """最も単純な関数をフォーマット"""
        # 単純な関数をソート
        simple_functions = sorted(all_functions, 
                                key=lambda x: (x.get('cognitive', 0), x.get('cyclomatic', 0)))
        
        # 非常に単純な関数（認知的複雑度 <= 3）のみをフィルタリング
        very_simple_functions = [func for func in simple_functions if func.get('cognitive', 0) <= 3]
        
        if len(very_simple_functions) >= 3:
            result = ["\n最も単純で良好な実装（例）:"]
            for i, func in enumerate(very_simple_functions[:3], 1):
                result.append(self._format_function_summary(i, func))
            return result
        
        return []
    
    def _format_function_summary(self, index: int, func: Dict[str, Any]) -> str:
        """個別の関数サマリーをフォーマット"""
        name = func.get('name', 'Unknown')
        cognitive = func.get('cognitive', 0)
        cyclomatic = func.get('cyclomatic', 0)
        return f"{index}. `{name}` (認知的: {cognitive}, 循環的: {cyclomatic})"
    
    def _format_high_complexity_functions(self, functions: List[Dict], 
                                        thresholds: ComplexityThresholds) -> List[str]:
        """高複雑度関数をフォーマット"""
        result = ["## 🔴 閾値を超える関数（優先的な対応が必要）:"]
        
        sorted_functions = sorted(functions, key=lambda x: x.get('cognitive', 0), reverse=True)
        
        for i, func in enumerate(sorted_functions[:10], 1):
            result.extend(self.comment_formatter.format_function_header(func, i))
            result.extend(self.comment_formatter.format_complexity_metrics(func, thresholds))
        
        return result
    
    def _format_warning_level_functions(self, functions: List[Dict], 
                                      thresholds: ComplexityThresholds) -> List[str]:
        """警告レベル関数をフォーマット"""
        result = ["\n## 🟡 警告レベルの関数（将来的な改善を検討）:"]
        
        sorted_functions = sorted(functions, key=lambda x: x.get('cognitive', 0), reverse=True)
        
        for i, func in enumerate(sorted_functions[:10], 1):
            result.extend(self.comment_formatter.format_function_header(func, i))
            result.extend(self.comment_formatter.format_warning_metrics(func, thresholds))
        
        return result
    
    def _generate_fallback_comment(self, analysis_result: Dict[str, Any], 
                                  stats: ComplexityStatistics) -> str:
        """APIエラー時のフォールバックコメント生成（リファクタリング済み）"""
        comment = []
        
        # サマリーセクション
        comment.extend(self.comment_formatter.create_summary_section(stats, analysis_result))
        
        # 閾値セクション
        comment.extend(self.comment_formatter.create_threshold_section(stats.thresholds))
        
        # 重要な発見事項セクション
        comment.extend(self._create_findings_section(stats))
        
        # 推奨事項セクション
        has_complex = (stats.functions_above_threshold['cognitive'] > 0 or 
                      stats.functions_above_threshold['cyclomatic'] > 0)
        comment.extend(self.comment_formatter.create_recommendations_section(has_complex))
        
        return "\n".join(comment)
    
    def _create_findings_section(self, stats: ComplexityStatistics) -> List[str]:
        """発見事項セクションを作成"""
        findings = ["## 🎯 重要な発見事項"]
        
        # 高複雑度関数
        if stats.high_complexity_functions:
            findings.extend(self._format_critical_functions(stats))
        
        # 警告レベル関数
        if stats.warning_level_functions:
            findings.extend(self._format_warning_functions(stats))
        
        # 全て良好な場合
        if not stats.high_complexity_functions and not stats.warning_level_functions:
            findings.extend([
                "## ✅ 良好な実装",
                "すべての関数の複雑度が適切に管理されています。",
                ""
            ])
        
        return findings
    
    def _format_critical_functions(self, stats: ComplexityStatistics) -> List[str]:
        """重要度の高い関数をフォーマット"""
        result = ["\n### 🚨 優先的に対応が必要な関数"]
        
        sorted_funcs = sorted(stats.high_complexity_functions, 
                            key=lambda x: x.get('cognitive', 0), reverse=True)
        
        for i, func in enumerate(sorted_funcs[:5], 1):
            result.extend([
                f"\n**{i}. {func.get('name', 'Unknown')}**",
                f"- 認知的複雑度: {func.get('cognitive', 0)} (閾値: {stats.thresholds.cognitive})",
                f"- 循環的複雑度: {func.get('cyclomatic', 0)} (閾値: {stats.thresholds.cyclomatic})",
                f"- ファイル: `{func.get('file', 'Unknown')}`",
                f"- 改善提案: この関数は複雑度が高いため、機能ごとに小さな関数に分割することを推奨します。"
            ])
        
        return result
    
    def _format_warning_functions(self, stats: ComplexityStatistics) -> List[str]:
        """警告レベルの関数をフォーマット"""
        result = ["\n### ⚠️ 注意が必要な領域"]
        
        for i, func in enumerate(stats.warning_level_functions[:3], 1):
            result.append(
                f"{i}. `{func.get('name', 'Unknown')}` - "
                f"認知的: {func.get('cognitive', 0)}, "
                f"循環的: {func.get('cyclomatic', 0)}"
            )
        
        return result


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='PR複雑度解析コメント生成')
    parser.add_argument('--analysis-result', required=True, help='解析結果JSONファイル')
    parser.add_argument('--output', required=True, help='出力ファイル')
    parser.add_argument('--debug', action='store_true', help='デバッグモードを有効化')
    parser.add_argument('--save-prompt', action='store_true', help='プロンプトをファイルに保存')
    parser.add_argument('--show-prompt', action='store_true', help='プロンプトをコンソールに表示')
    
    args = parser.parse_args()
    
    # ログレベルの設定
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 解析結果を読み込み
    logger.info(f"Loading analysis result from {args.analysis_result}")
    with open(args.analysis_result, 'r', encoding='utf-8') as f:
        analysis_result = json.load(f)
    
    # コメント生成
    generator = PRComplexityCommentGenerator(
        debug_mode=args.debug,
        save_prompt=args.save_prompt
    )
    
    # プロンプトの表示オプション
    if args.show_prompt:
        generator.show_prompt = True
    
    comment = generator.generate_comment(analysis_result)
    
    # 結果を保存
    result = {
        'comment': comment,
        'generated_at': datetime.now().isoformat(),
        'analysis_summary': {
            'total_files_analyzed': analysis_result.get('total_files_analyzed', 0),
            'total_functions': analysis_result.get('total_functions', 0),
            'high_complexity_cyclomatic': analysis_result.get('high_complexity_functions_cyclomatic', 0),
            'high_complexity_cognitive': analysis_result.get('high_complexity_functions_cognitive', 0)
        },
        'generation_metadata': {
            'model': generator.config.model,
            'temperature': generator.config.temperature,
            'max_tokens': generator.config.max_tokens
        }
    }
    
    # プロンプトをメタデータに含める（オプション）
    if args.save_prompt or args.show_prompt or args.debug:
        # プロンプトを再生成して結果に含める
        stats = generator._prepare_statistics(analysis_result)
        prompt = generator._build_prompt(analysis_result, stats)
        result['generation_metadata']['prompt'] = prompt
        result['generation_metadata']['prompt_length'] = len(prompt)
        result['generation_metadata']['estimated_prompt_tokens'] = len(prompt) // 4
    
    logger.info(f"Saving comment to {args.output}")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # サマリーを表示
    print(f"\nComment generated successfully!")
    print(f"- Model used: {generator.config.model}")
    print(f"- Files analyzed: {result['analysis_summary']['total_files_analyzed']}")
    print(f"- Total functions: {result['analysis_summary']['total_functions']}")
    print(f"- High complexity functions (cyclomatic): {result['analysis_summary']['high_complexity_cyclomatic']}")
    print(f"- High complexity functions (cognitive): {result['analysis_summary']['high_complexity_cognitive']}")


if __name__ == '__main__':
    main()
