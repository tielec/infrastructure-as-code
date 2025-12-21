import time

import pytest

from pr_complexity_comment_generator import ComplexityStatistics, ComplexityThresholds, FunctionMetrics
from prompt_builder import PromptBuilder


def test_build_prompt_with_valid_data(builder):
    # TC-001: 基本的なプロンプト生成
    prompt = builder.build_prompt()
    assert isinstance(prompt, str)
    assert "# 解析結果サマリー" in prompt
    assert "# 設定された閾値" in prompt


def test_build_prompt_includes_analysis_summary(builder):
    # TC-002: 解析サマリーの値が含まれる
    prompt = builder.build_prompt()
    assert "- 総関数数: 10" in prompt
    assert "- 平均循環的複雑度: 5.50" in prompt
    assert "- 平均認知的複雑度: 7.20" in prompt


def test_build_prompt_includes_thresholds(builder):
    # TC-003: 閾値情報の表記
    prompt = builder.build_prompt()
    assert "循環的複雑度の閾値: 15" in prompt
    assert "認知的複雑度の閾値: 20" in prompt


def test_build_prompt_includes_high_complexity_functions(builder):
    # TC-004: 高複雑度関数の情報
    prompt = builder.build_prompt()
    assert "complex_function" in prompt
    assert "src/main.py" in prompt
    assert "35" in prompt or "25" in prompt


def test_build_prompt_includes_warning_functions(builder):
    # TC-005: 警告レベルの関数
    prompt = builder.build_prompt()
    assert "warning_function" in prompt
    assert "src/utils.py" in prompt


def test_build_prompt_with_no_complex_functions(no_complex_stats):
    # TC-006: 閾値を超える関数がない場合の特記事項
    analysis_result = {
        "pr_number": 1,
        "pr_title": "No Complex",
        "total_files_analyzed": 1,
        "total_functions": 3,
        "all_functions": [
            {"name": "simple_one", "cognitive": 2, "cyclomatic": 1, "file": "a.py", "lines": 10, "start_line": 1, "end_line": 10}
        ],
    }
    prompt = PromptBuilder(no_complex_stats, analysis_result).build_prompt()
    assert "閾値を超える関数は検出されませんでした" in prompt
    assert "特記事項" in prompt


def test_build_prompt_includes_instructions(builder):
    # TC-007: 出力指示の有無
    prompt = builder.build_prompt()
    assert "Markdown" in prompt or "markdown" in prompt
    assert "重要な注意事項" in prompt


def test_build_prompt_includes_pr_info(builder):
    # TC-008: PR情報
    prompt = builder.build_prompt()
    assert "# PR情報" in prompt
    assert "PR番号: #123" in prompt
    assert "Feature: Add new functionality" in prompt


def test_build_prompt_with_empty_functions(empty_stats, empty_analysis_result):
    # TC-009: 空データでも生成できる
    prompt = PromptBuilder(empty_stats, empty_analysis_result).build_prompt()
    assert isinstance(prompt, str)
    assert "関数の詳細情報が取得できませんでした。" in prompt


def test_build_prompt_with_missing_fields(sample_stats):
    # TC-010: 欠損フィールドにデフォルトが使われる
    analysis_result = {
        "total_files_analyzed": 3,
        "total_functions": 5,
        "all_functions": [],
        "file_analyses": {},
    }
    prompt = PromptBuilder(sample_stats, analysis_result).build_prompt()
    assert "PR番号: #N/A" in prompt
    assert "タイトル: N/A" in prompt


def test_build_prompt_with_none_values_raises(sample_thresholds):
    # TC-011: Noneを含む統計値はフォーマットエラーになる
    bad_stats = ComplexityStatistics(
        total_functions=None,  # type: ignore[arg-type]
        total_files=None,  # type: ignore[arg-type]
        avg_cyclomatic=None,  # type: ignore[arg-type]
        avg_cognitive=None,  # type: ignore[arg-type]
        max_cyclomatic=None,  # type: ignore[arg-type]
        max_cognitive=None,  # type: ignore[arg-type]
        thresholds=sample_thresholds,
        functions_above_threshold={"cyclomatic": 0, "cognitive": 0},
        high_complexity_functions=[],
        warning_level_functions=[],
    )
    with pytest.raises(TypeError):
        PromptBuilder(bad_stats, {}).build_prompt()


def test_build_prompt_with_invalid_thresholds():
    # TC-012: 無効な閾値でも値がそのまま反映される
    thresholds = ComplexityThresholds(cyclomatic=-1, cognitive=0, cyclomatic_warning=100, cognitive_warning=50)
    stats = ComplexityStatistics(
        total_functions=2,
        total_files=1,
        avg_cyclomatic=1.0,
        avg_cognitive=2.0,
        max_cyclomatic=2,
        max_cognitive=3,
        thresholds=thresholds,
        functions_above_threshold={"cyclomatic": 0, "cognitive": 0},
        high_complexity_functions=[],
        warning_level_functions=[],
    )
    prompt = PromptBuilder(stats, {"all_functions": []}).build_prompt()
    assert "-1" in prompt
    assert "100" in prompt


def test_complexity_at_threshold(boundary_stats, boundary_analysis_result):
    # TC-013: 閾値ちょうどの関数を含める
    prompt = PromptBuilder(boundary_stats, boundary_analysis_result).build_prompt()
    assert "threshold_boundary_function" in prompt


def test_complexity_at_warning_level(boundary_stats, boundary_analysis_result):
    # TC-014: 警告レベルちょうどの関数を含める
    prompt = PromptBuilder(boundary_stats, boundary_analysis_result).build_prompt()
    assert "warning_boundary_function" in prompt


def test_single_function(single_function_stats, single_function_analysis):
    # TC-015: 関数1件の場合でも生成できる
    prompt = PromptBuilder(single_function_stats, single_function_analysis).build_prompt()
    assert "single_function" in prompt
    assert isinstance(prompt, str)


def test_large_number_of_functions_performance(large_stats, large_analysis_result):
    # TC-016: 大量データでの性能
    builder = PromptBuilder(large_stats, large_analysis_result)
    start = time.perf_counter()
    prompt = builder.build_prompt()
    elapsed = time.perf_counter() - start
    assert elapsed < 2.5, f"Prompt generation took too long: {elapsed:.2f}s"
    assert len(prompt) > 0


def test_zero_avg_complexity(empty_stats, empty_analysis_result):
    # TC-017: 平均複雑度が0でも問題なく生成
    prompt = PromptBuilder(empty_stats, empty_analysis_result).build_prompt()
    assert isinstance(prompt, str)
    assert "平均循環的複雑度: 0.00" in prompt
    assert "平均認知的複雑度: 0.00" in prompt


def test_build_analysis_summary_section(builder):
    # TC-018: 解析サマリーセクションの内容
    section = builder._build_analysis_summary_section()
    assert "- 総関数数: 10" in section
    assert "- 解析ファイル数: 3" in section


def test_build_thresholds_section(builder):
    # TC-019: 閾値セクションの内容
    section = builder._build_thresholds_section()
    assert "閾値: 15" in section
    assert "閾値: 20" in section


def test_build_functions_detail_section(builder):
    # TC-020: 関数詳細セクション
    section = builder._build_functions_detail_section()
    assert "complex_function" in section
    assert "warning_function" in section


def test_build_all_functions_section(builder):
    # TC-021: 全関数概要セクション
    section = builder._build_all_functions_section()
    assert "総関数数" in section
    assert len(section) > 0


def test_build_instructions_section(builder):
    # TC-022: 出力指示セクション
    section = builder._build_instructions_section()
    assert "Markdown" in section or "markdown" in section
    assert "出力" in section


def test_format_function_details(builder, sample_high_complexity_function, sample_warning_function):
    # TC-023: 関数詳細フォーマット
    detail = builder._format_function_details([sample_high_complexity_function], [sample_warning_function])
    assert "complex_function" in detail
    assert "warning_function" in detail


def test_calculate_complexity_distribution(builder):
    # TC-024: 複雑度分布の計算
    functions = [
        {"cognitive": 4},
        {"cognitive": 8},
        {"cognitive": 12},
        {"cognitive": 17},
        {"cognitive": 23},
    ]
    distribution = builder._calculate_complexity_distribution(functions)
    assert distribution["低（認知的 < 5）"] == 1
    assert distribution["中（認知的 5-9）"] == 1
    assert distribution["高（認知的 10-14）"] == 1
    assert distribution["警告（認知的 15-19）"] == 1
    assert distribution["危険（認知的 20+）"] == 1


def test_format_most_complex_functions(builder):
    # TC-025: 最も複雑な関数のフォーマット
    functions = [
        {"name": "low", "cognitive": 3, "cyclomatic": 2},
        {"name": "mid", "cognitive": 10, "cyclomatic": 6},
        {"name": "high", "cognitive": 22, "cyclomatic": 12},
    ]
    lines = builder._format_most_complex_functions(functions)
    assert any("high" in line for line in lines)
    assert lines[1].startswith("最も複雑な関数")
    assert lines[2].startswith("1. `high`")


def test_complexity_thresholds_initialization(sample_thresholds):
    # TC-026: ComplexityThresholdsの初期化
    assert sample_thresholds.cyclomatic == 15
    assert sample_thresholds.cognitive == 20
    assert sample_thresholds.cyclomatic_warning == 10
    assert sample_thresholds.cognitive_warning == 14


def test_complexity_statistics_initialization(sample_stats):
    # TC-027: ComplexityStatisticsの初期化
    assert sample_stats.total_functions == 10
    assert isinstance(sample_stats.high_complexity_functions, list)
    assert isinstance(sample_stats.warning_level_functions, list)


def test_function_metrics_initialization():
    # TC-028: FunctionMetricsの初期化
    metrics = FunctionMetrics(
        name="test_function",
        file="test.py",
        cyclomatic=5,
        cognitive=8,
        lines=25,
        start_line=10,
        end_line=35,
    )
    assert metrics.name == "test_function"
    assert metrics.file == "test.py"
