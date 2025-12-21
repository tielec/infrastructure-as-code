import sys
import types
from pathlib import Path
from typing import Dict, Any, List

import pytest

# Ensure the src directory is importable for tests
ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Stub the openai module to avoid external dependency during imports
if "openai" not in sys.modules:
    openai_stub = types.ModuleType("openai")
    openai_stub.OpenAI = lambda *args, **kwargs: None
    sys.modules["openai"] = openai_stub

from pr_complexity_comment_generator import (
    ComplexityStatistics,
    ComplexityThresholds,
    FunctionMetrics,
    StatisticsCalculator,
)
from prompt_builder import PromptBuilder


def build_stats_from_analysis(analysis_result: Dict[str, Any], thresholds: ComplexityThresholds) -> ComplexityStatistics:
    """Build ComplexityStatistics based on the same calculation path used in production."""
    calculator = StatisticsCalculator()
    all_functions = analysis_result.get("all_functions", [])
    high_complexity, warning_level = calculator.classify_functions(all_functions, thresholds)
    avg_cyclo, avg_cogn, max_cyclo, max_cogn = calculator.calculate_averages(analysis_result.get("file_analyses", {}))

    return ComplexityStatistics(
        total_functions=analysis_result.get("total_functions", len(all_functions)),
        total_files=analysis_result.get("total_files_analyzed", 0),
        avg_cyclomatic=avg_cyclo,
        avg_cognitive=avg_cogn,
        max_cyclomatic=max_cyclo,
        max_cognitive=max_cogn,
        thresholds=thresholds,
        functions_above_threshold={
            "cyclomatic": sum(1 for func in high_complexity if func.get("cyclomatic", 0) > thresholds.cyclomatic),
            "cognitive": sum(1 for func in high_complexity if func.get("cognitive", 0) > thresholds.cognitive),
        },
        high_complexity_functions=high_complexity,
        warning_level_functions=warning_level,
    )


@pytest.fixture
def sample_thresholds() -> ComplexityThresholds:
    return ComplexityThresholds(
        cyclomatic=15,
        cognitive=20,
        cyclomatic_warning=10,
        cognitive_warning=14,
    )


@pytest.fixture
def sample_high_complexity_function() -> Dict[str, Any]:
    return {
        "name": "complex_function",
        "file": "src/main.py",
        "cyclomatic": 25,
        "cognitive": 35,
        "lines": 100,
        "start_line": 10,
        "end_line": 110,
    }


@pytest.fixture
def sample_warning_function() -> Dict[str, Any]:
    return {
        "name": "warning_function",
        "file": "src/utils.py",
        "cyclomatic": 12,
        "cognitive": 16,
        "lines": 50,
        "start_line": 1,
        "end_line": 51,
    }


@pytest.fixture
def sample_normal_function() -> Dict[str, Any]:
    return {
        "name": "simple_function",
        "file": "src/helpers.py",
        "cyclomatic": 3,
        "cognitive": 5,
        "lines": 15,
        "start_line": 1,
        "end_line": 16,
    }


@pytest.fixture
def sample_stats(sample_thresholds, sample_high_complexity_function, sample_warning_function) -> ComplexityStatistics:
    return ComplexityStatistics(
        total_functions=10,
        total_files=3,
        avg_cyclomatic=5.5,
        avg_cognitive=7.2,
        max_cyclomatic=25,
        max_cognitive=35,
        thresholds=sample_thresholds,
        functions_above_threshold={"cyclomatic": 1, "cognitive": 1},
        high_complexity_functions=[sample_high_complexity_function],
        warning_level_functions=[sample_warning_function],
    )


@pytest.fixture
def sample_analysis_result(sample_high_complexity_function, sample_warning_function, sample_normal_function) -> Dict[str, Any]:
    return {
        "pr_number": 123,
        "pr_title": "Feature: Add new functionality",
        "total_files_analyzed": 3,
        "total_functions": 10,
        "high_complexity_functions": [sample_high_complexity_function],
        "warning_level_functions": [sample_warning_function],
        "all_functions": [
            sample_high_complexity_function,
            sample_warning_function,
            sample_normal_function,
            {"name": "func4", "cognitive": 8, "cyclomatic": 6},
            {"name": "func5", "cognitive": 4, "cyclomatic": 2},
            {"name": "func6", "cognitive": 9, "cyclomatic": 7},
            {"name": "func7", "cognitive": 3, "cyclomatic": 2},
            {"name": "func8", "cognitive": 6, "cyclomatic": 4},
            {"name": "func9", "cognitive": 7, "cyclomatic": 5},
            {"name": "func10", "cognitive": 2, "cyclomatic": 1},
        ],
        "file_analyses": {
            "src/main.py": {"average_cyclomatic": 10, "average_cognitive": 12, "max_cyclomatic": 25, "max_cognitive": 35},
            "src/utils.py": {"average_cyclomatic": 8, "average_cognitive": 10, "max_cyclomatic": 12, "max_cognitive": 16},
            "src/helpers.py": {"average_cyclomatic": 2, "average_cognitive": 4, "max_cyclomatic": 4, "max_cognitive": 5},
        },
    }


@pytest.fixture
def empty_stats(sample_thresholds) -> ComplexityStatistics:
    return ComplexityStatistics(
        total_functions=0,
        total_files=0,
        avg_cyclomatic=0.0,
        avg_cognitive=0.0,
        max_cyclomatic=0,
        max_cognitive=0,
        thresholds=sample_thresholds,
        functions_above_threshold={"cyclomatic": 0, "cognitive": 0},
        high_complexity_functions=[],
        warning_level_functions=[],
    )


@pytest.fixture
def empty_analysis_result() -> Dict[str, Any]:
    return {
        "pr_number": 999,
        "pr_title": "Empty PR",
        "total_files_analyzed": 0,
        "total_functions": 0,
        "high_complexity_functions": [],
        "warning_level_functions": [],
        "all_functions": [],
        "file_analyses": {},
    }


@pytest.fixture
def no_complex_stats(sample_thresholds) -> ComplexityStatistics:
    return ComplexityStatistics(
        total_functions=3,
        total_files=1,
        avg_cyclomatic=1.0,
        avg_cognitive=2.0,
        max_cyclomatic=5,
        max_cognitive=4,
        thresholds=sample_thresholds,
        functions_above_threshold={"cyclomatic": 0, "cognitive": 0},
        high_complexity_functions=[],
        warning_level_functions=[],
    )


@pytest.fixture
def threshold_boundary_function() -> Dict[str, Any]:
    return {
        "name": "threshold_boundary_function",
        "file": "src/boundary.py",
        "cyclomatic": 15,
        "cognitive": 20,
        "lines": 45,
        "start_line": 1,
        "end_line": 46,
    }


@pytest.fixture
def warning_boundary_function() -> Dict[str, Any]:
    return {
        "name": "warning_boundary_function",
        "file": "src/warning.py",
        "cyclomatic": 10,
        "cognitive": 14,
        "lines": 30,
        "start_line": 1,
        "end_line": 31,
    }


@pytest.fixture
def below_warning_function() -> Dict[str, Any]:
    return {
        "name": "below_warning_function",
        "file": "src/simple.py",
        "cyclomatic": 9,
        "cognitive": 13,
        "lines": 20,
        "start_line": 1,
        "end_line": 21,
    }


@pytest.fixture
def boundary_analysis_result(threshold_boundary_function, warning_boundary_function, below_warning_function) -> Dict[str, Any]:
    return {
        "pr_number": 777,
        "pr_title": "Boundary PR",
        "total_files_analyzed": 1,
        "total_functions": 3,
        "all_functions": [threshold_boundary_function, warning_boundary_function, below_warning_function],
        "file_analyses": {
            "src/boundary.py": {
                "average_cyclomatic": 12,
                "average_cognitive": 14,
                "max_cyclomatic": 15,
                "max_cognitive": 20,
            }
        },
    }


@pytest.fixture
def boundary_stats(sample_thresholds, threshold_boundary_function, warning_boundary_function) -> ComplexityStatistics:
    return ComplexityStatistics(
        total_functions=3,
        total_files=1,
        avg_cyclomatic=10.0,
        avg_cognitive=12.0,
        max_cyclomatic=15,
        max_cognitive=20,
        thresholds=sample_thresholds,
        functions_above_threshold={"cyclomatic": 1, "cognitive": 1},
        high_complexity_functions=[threshold_boundary_function],
        warning_level_functions=[warning_boundary_function],
    )


@pytest.fixture
def single_function_analysis(sample_thresholds) -> Dict[str, Any]:
    func = {"name": "single_function", "cognitive": 7, "cyclomatic": 5, "file": "src/one.py", "lines": 12, "start_line": 1, "end_line": 12}
    return {
        "pr_number": 321,
        "pr_title": "Single Function",
        "total_files_analyzed": 1,
        "total_functions": 1,
        "all_functions": [func],
        "file_analyses": {
            "src/one.py": {
                "average_cyclomatic": 5,
                "average_cognitive": 7,
                "max_cyclomatic": 5,
                "max_cognitive": 7,
            }
        },
    }


@pytest.fixture
def single_function_stats(sample_thresholds, single_function_analysis) -> ComplexityStatistics:
    return build_stats_from_analysis(single_function_analysis, sample_thresholds)


@pytest.fixture
def large_analysis_result() -> Dict[str, Any]:
    all_functions = [
        {
            "name": f"function_{i}",
            "file": f"src/module_{i // 10}.py",
            "cyclomatic": (i % 20) + 1,
            "cognitive": (i % 25) + 1,
            "lines": 20 + (i % 30),
            "start_line": 1,
            "end_line": 20 + (i % 30),
        }
        for i in range(100)
    ]

    return {
        "pr_number": 456,
        "pr_title": "Large PR with many functions",
        "total_files_analyzed": 10,
        "total_functions": 100,
        "all_functions": all_functions,
        "file_analyses": {
            f"src/module_{i}.py": {
                "average_cyclomatic": 10 + i,
                "average_cognitive": 12 + i,
                "max_cyclomatic": 20 + i,
                "max_cognitive": 22 + i,
            }
            for i in range(10)
        },
    }


@pytest.fixture
def large_stats(sample_thresholds, large_analysis_result) -> ComplexityStatistics:
    return build_stats_from_analysis(large_analysis_result, sample_thresholds)


@pytest.fixture
def builder(sample_stats, sample_analysis_result) -> PromptBuilder:
    return PromptBuilder(sample_stats, sample_analysis_result)
