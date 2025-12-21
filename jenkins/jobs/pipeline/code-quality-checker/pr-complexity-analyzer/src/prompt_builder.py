"""
プロンプト構築モジュール

OpenAI APIに送信するプロンプト文字列を構築します。
複雑度解析結果と統計情報を入力として受け取り、構造化された
Markdownコメント用のプロンプトを生成します。
"""

from typing import Any, Dict, List


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
    def format_complexity_metrics(func: Dict[str, Any], thresholds: "ComplexityThresholds") -> List[str]:
        """複雑度メトリクスをフォーマット"""
        return [
            f"   - 認知的複雑度: {func.get('cognitive', 0)} (閾値: {thresholds.cognitive})",
            f"   - 循環的複雑度: {func.get('cyclomatic', 0)} (閾値: {thresholds.cyclomatic})",
            f"   - コード行数: {func.get('lines', 0)}",
        ]
    
    @staticmethod
    def format_warning_metrics(func: Dict[str, Any], thresholds: "ComplexityThresholds") -> List[str]:
        """警告レベルのメトリクスをフォーマット"""
        return [
            f"   - 認知的複雑度: {func.get('cognitive', 0)} "
            f"(警告: {thresholds.cognitive_warning}, 閾値: {thresholds.cognitive})",
            f"   - 循環的複雑度: {func.get('cyclomatic', 0)} "
            f"(警告: {thresholds.cyclomatic_warning}, 閾値: {thresholds.cyclomatic})",
        ]
    
    @staticmethod
    def create_summary_section(stats: "ComplexityStatistics", pr_info: Dict[str, Any]) -> List[str]:
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
    def create_threshold_section(thresholds: "ComplexityThresholds") -> List[str]:
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
        return [
            "",
            "## 💡 推奨事項",
            "- 現在の良好な状態を維持してください",
            "- 新機能追加時も複雑度を意識した実装を心がけてください",
            "- 定期的なコードレビューで複雑度をモニタリングしてください",
        ]


class PromptBuilder:
    """
    OpenAI API用のプロンプトを構築するクラス

    複雑度解析結果からPRコメント生成用のプロンプトを構築します。
    プロンプトは以下のセクションで構成されます：
    - 解析サマリー
    - 閾値情報
    - 関数詳細
    - 全関数概要
    - 出力形式指示

    Attributes:
        stats (ComplexityStatistics): 複雑度統計情報
        analysis_result (Dict[str, Any]): 解析結果データ
    """

    def __init__(self, stats: "ComplexityStatistics", analysis_result: Dict[str, Any]) -> None:
        """
        PromptBuilderを初期化する

        Args:
            stats: 複雑度統計情報
            analysis_result: 解析結果の辞書データ
        """
        self.stats = stats
        self.analysis_result = analysis_result

    def build_prompt(self) -> str:
        """
        完全なプロンプト文字列を構築する

        Returns:
            OpenAI APIに送信するプロンプト文字列
        """
        sections = [
            self._build_analysis_summary_section(),
            self._build_thresholds_section(),
            self._build_functions_overview_section(),
            self._build_functions_detail_section(),
            self._build_all_functions_section(),
            self._build_pr_info_section(),
            self._build_no_complex_functions_section(),
            self._build_instructions_section(),
        ]
        return "\n\n".join(section for section in sections if section).strip()

    def _build_analysis_summary_section(self) -> str:
        """解析サマリーセクションを構築"""
        lines = [
            "以下のコード複雑度解析結果に基づいて、GitHub PRコメントを生成してください。",
            "",
            "# 解析結果サマリー",
            f"- 解析ファイル数: {self.stats.total_files}",
            f"- 総関数数: {self.stats.total_functions}",
            f"- 平均循環的複雑度: {self.stats.avg_cyclomatic:.2f}",
            f"- 平均認知的複雑度: {self.stats.avg_cognitive:.2f}",
            f"- 最大循環的複雑度: {self.stats.max_cyclomatic}",
            f"- 最大認知的複雑度: {self.stats.max_cognitive}",
        ]
        return "\n".join(lines)

    def _build_thresholds_section(self) -> str:
        """閾値情報セクションを構築"""
        thresholds = self.stats.thresholds
        lines = [
            "# 設定された閾値",
            f"- 循環的複雑度の閾値: {thresholds.cyclomatic} (警告レベル: {thresholds.cyclomatic_warning})",
            f"- 認知的複雑度の閾値: {thresholds.cognitive} (警告レベル: {thresholds.cognitive_warning})",
        ]
        return "\n".join(lines)

    def _build_functions_overview_section(self) -> str:
        """閾値を超える関数の概要を構築"""
        lines = [
            "# 閾値を超える関数",
            f"- 循環的複雑度が閾値を超える関数: {self.stats.functions_above_threshold['cyclomatic']}個",
            f"- 認知的複雑度が閾値を超える関数: {self.stats.functions_above_threshold['cognitive']}個",
        ]
        return "\n".join(lines)

    def _build_functions_detail_section(self) -> str:
        """関数詳細セクションを構築"""
        detail = self._format_function_details(
            self.stats.high_complexity_functions,
            self.stats.warning_level_functions,
        )
        return f"# 関数の詳細情報\n{detail}"

    def _build_all_functions_section(self) -> str:
        """全関数概要セクションを構築"""
        summary = self._format_all_functions_summary(self.analysis_result.get("all_functions", []))
        return f"# 全関数の概要\n{summary}"

    def _build_no_complex_functions_section(self) -> str:
        """複雑度が閾値未満の場合の特記事項セクションを構築"""
        if self.stats.functions_above_threshold["cognitive"] > 0 or self.stats.functions_above_threshold["cyclomatic"] > 0:
            return ""
        lines = [
            "# 特記事項",
            "閾値を超える関数は検出されませんでした。以下の観点でフィードバックを提供してください：",
            "- 現在の良好な実装パターンを具体的に評価",
            "- 最も複雑度が高い関数（閾値未満でも）について、将来的な改善の余地があるか検討",
            "- チーム全体で共有すべきベストプラクティスの抽出",
            "- 今後の開発で維持すべき品質基準の提案",
        ]
        return "\n".join(lines)

    def _build_pr_info_section(self) -> str:
        """PR情報セクションを構築"""
        lines = [
            "# PR情報",
            f"- PR番号: #{self.analysis_result.get('pr_number', 'N/A')}",
            f"- タイトル: {self.analysis_result.get('pr_title', 'N/A')}",
        ]
        return "\n".join(lines)

    def _build_instructions_section(self) -> str:
        """出力形式指示セクションを構築"""
        thresholds = self.stats.thresholds
        warning_cognitive_range = f"{thresholds.cognitive_warning}-{thresholds.cognitive - 1}"
        warning_cyclomatic_range = f"{thresholds.cyclomatic_warning}-{thresholds.cyclomatic - 1}"
        lines = [
            "以下の形式でMarkdownコメントを生成してください：",
            "",
            "1. **解析サマリー**: 全体的な評価を2-3文で簡潔に（平均値と最大値に基づいて）",
            "   - 平均複雑度が低い場合は、その良好な状態を評価",
            "   - 最大複雑度も閾値内の場合は、それも明記",
            "",
            "2. **重要な発見事項**:",
            f"   - 🚨 **優先的に対応が必要な関数**: 認知的複雑度が閾値を超える関数（{thresholds.cognitive}以上）を具体的にリストし、なぜ複雑なのか、どうリファクタリングすべきか提案",
            f"   - ⚠️ **注意が必要な領域**: 警告レベル（認知的: {warning_cognitive_range}、循環的: {warning_cyclomatic_range}）の関数を具体的にリスト",
            "   - ✅ **良好な実装**: 特に複雑度が低く、良い実装パターンとなっている関数を2-3個具体的に挙げて評価",
            "",
            "3. **具体的な改善提案**: ",
            "   - 高複雑度関数がある場合：",
            "     * 関数の分割（単一責任の原則）",
            "     * 条件分岐の簡略化",
            "     * ネストレベルの削減",
            "     * 早期リターンの活用",
            "   - 高複雑度関数がない場合：",
            "     * 現在の良好な実装を維持するためのガイドライン",
            "     * さらなる改善の余地がある関数への提案（あれば）",
            "     * チーム全体で共有すべきコーディング規約",
            "",
            "4. **メトリクス詳細**: 主要な数値を表形式でまとめる",
            "   | メトリクス | 値 | 評価 |",
            "   |----------|-----|------|",
            "   | 平均認知的複雑度 | X.XX | 🟢/🟡/🔴 |",
            "   | 平均循環的複雑度 | X.XX | 🟢/🟡/🔴 |",
            "   | 最大認知的複雑度 | XX | 🟢/🟡/🔴 |",
            "   | 最大循環的複雑度 | XX | 🟢/🟡/🔴 |",
            "",
            "5. **次のステップ**: ",
            "   - 高複雑度関数がある場合：優先順位付けされたアクション項目",
            "   - 高複雑度関数がない場合：品質を維持するための推奨事項",
            "",
            "重要な注意事項:",
            "- 必ず具体的な関数名と複雑度の数値を含めてください",
            "- 警告レベルの関数も具体的な名前と数値を含めて記載してください",
            "- 認知的複雑度を循環的複雑度より優先して説明してください（認知的複雑度の方が実際の理解しやすさを表すため）",
            "- 改善提案は実装可能で具体的なものにしてください",
            "- 閾値を超える関数がない場合でも、建設的で有用なフィードバックを提供してください",
            "- トーンは建設的で協力的に保ってください",
            "- 出力にマークダウンのコードブロック記号（```）を含めないでください",
            "- 純粋なMarkdown形式で出力してください（```markdownなどのタグは不要）",
        ]
        return "\n".join(lines)

    def _format_function_details(
        self,
        high_complexity_functions: List[Dict[str, Any]],
        warning_functions: List[Dict[str, Any]],
    ) -> str:
        """関数の詳細情報をフォーマット"""
        if not high_complexity_functions and not warning_functions:
            return "## 閾値を超える関数・警告レベルの関数はありません"

        sections: List[str] = []
        if high_complexity_functions:
            sections.extend(self._format_high_complexity_functions(high_complexity_functions))
        if warning_functions:
            sections.extend(self._format_warning_level_functions(warning_functions))
        return "\n".join(sections)

    def _format_all_functions_summary(self, all_functions: List[Dict[str, Any]]) -> str:
        """全関数の概要をフォーマット"""
        if not all_functions:
            return "関数の詳細情報が取得できませんでした。"

        lines = [f"総関数数: {len(all_functions)}個"]
        lines.extend(self._format_complexity_distribution(all_functions))
        lines.extend(self._format_most_complex_functions(all_functions))
        lines.extend(self._format_simplest_functions(all_functions))
        return "\n".join(lines)

    def _format_complexity_distribution(self, all_functions: List[Dict[str, Any]]) -> List[str]:
        """複雑度の分布をフォーマット"""
        distribution = self._calculate_complexity_distribution(all_functions)
        lines = ["", "複雑度の分布:"]
        for level, count in distribution.items():
            if count > 0:
                percentage = (count / len(all_functions)) * 100
                lines.append(f"- {level}: {count}個 ({percentage:.1f}%)")
        return lines

    def _calculate_complexity_distribution(self, all_functions: List[Dict[str, Any]]) -> Dict[str, int]:
        """複雑度の分布を計算"""
        distribution = {
            "低（認知的 < 5）": 0,
            "中（認知的 5-9）": 0,
            "高（認知的 10-14）": 0,
            "警告（認知的 15-19）": 0,
            "危険（認知的 20+）": 0,
        }

        for func in all_functions:
            cognitive = func.get("cognitive", 0)
            if cognitive < 5:
                distribution["低（認知的 < 5）"] += 1
            elif cognitive < 10:
                distribution["中（認知的 5-9）"] += 1
            elif cognitive < 15:
                distribution["高（認知的 10-14）"] += 1
            elif cognitive < 20:
                distribution["警告（認知的 15-19）"] += 1
            else:
                distribution["危険（認知的 20+）"] += 1

        return distribution

    def _format_most_complex_functions(self, all_functions: List[Dict[str, Any]]) -> List[str]:
        """最も複雑な関数をフォーマット"""
        sorted_functions = sorted(
            all_functions, key=lambda x: (x.get("cognitive", 0), x.get("cyclomatic", 0)), reverse=True
        )
        lines = ["", "最も複雑な関数（上位5個）:"]
        for index, func in enumerate(sorted_functions[:5], 1):
            lines.append(self._format_function_summary(index, func))
        return lines

    def _format_simplest_functions(self, all_functions: List[Dict[str, Any]]) -> List[str]:
        """最も単純な関数をフォーマット"""
        simple_functions = sorted(all_functions, key=lambda x: (x.get("cognitive", 0), x.get("cyclomatic", 0)))
        very_simple_functions = [func for func in simple_functions if func.get("cognitive", 0) <= 3]

        if len(very_simple_functions) < 3:
            return []

        lines = ["", "最も単純で良好な実装（例）:"]
        for index, func in enumerate(very_simple_functions[:3], 1):
            lines.append(self._format_function_summary(index, func))
        return lines

    def _format_function_summary(self, index: int, func: Dict[str, Any]) -> str:
        """個別の関数サマリーをフォーマット"""
        name = func.get("name", "Unknown")
        cognitive = func.get("cognitive", 0)
        cyclomatic = func.get("cyclomatic", 0)
        return f"{index}. `{name}` (認知的: {cognitive}, 循環的: {cyclomatic})"

    def _format_high_complexity_functions(self, functions: List[Dict[str, Any]]) -> List[str]:
        """高複雑度関数をフォーマット"""
        thresholds = self.stats.thresholds
        lines = ["## 🔴 閾値を超える関数（優先的な対応が必要）:"]
        sorted_functions = sorted(functions, key=lambda x: x.get("cognitive", 0), reverse=True)

        for index, func in enumerate(sorted_functions[:10], 1):
            lines.extend(self._format_function_header(func, index))
            lines.extend(self._format_complexity_metrics(func, thresholds))

        return lines

    def _format_warning_level_functions(self, functions: List[Dict[str, Any]]) -> List[str]:
        """警告レベル関数をフォーマット"""
        thresholds = self.stats.thresholds
        lines = ["", "## 🟡 警告レベルの関数（将来的な改善を検討）:"]
        sorted_functions = sorted(functions, key=lambda x: x.get("cognitive", 0), reverse=True)

        for index, func in enumerate(sorted_functions[:10], 1):
            lines.extend(self._format_function_header(func, index))
            lines.extend(self._format_warning_metrics(func, thresholds))

        return lines

    def _format_function_header(self, func: Dict[str, Any], index: int) -> List[str]:
        """関数ヘッダーをフォーマット"""
        return [
            f"\n{index}. **{func.get('name', 'Unknown')}**",
            f"   - ファイル: {func.get('file', 'Unknown')}",
            f"   - 行: {func.get('start_line', 0)}-{func.get('end_line', 0)}",
        ]

    def _format_complexity_metrics(self, func: Dict[str, Any], thresholds: "ComplexityThresholds") -> List[str]:
        """高複雑度関数のメトリクスをフォーマット"""
        return [
            f"   - 認知的複雑度: {func.get('cognitive', 0)} (閾値: {thresholds.cognitive})",
            f"   - 循環的複雑度: {func.get('cyclomatic', 0)} (閾値: {thresholds.cyclomatic})",
            f"   - コード行数: {func.get('lines', 0)}",
        ]

    def _format_warning_metrics(self, func: Dict[str, Any], thresholds: "ComplexityThresholds") -> List[str]:
        """警告レベル関数のメトリクスをフォーマット"""
        return [
            f"   - 認知的複雑度: {func.get('cognitive', 0)} "
            f"(警告: {thresholds.cognitive_warning}, 閾値: {thresholds.cognitive})",
            f"   - 循環的複雑度: {func.get('cyclomatic', 0)} "
            f"(警告: {thresholds.cyclomatic_warning}, 閾値: {thresholds.cyclomatic})",
        ]
