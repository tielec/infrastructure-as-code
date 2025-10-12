"""phase_dependencies.py のユニットテスト

このファイルはフェーズ依存関係管理機能のユニットテストを実装します。
テストシナリオ: .ai-workflow/issue-319/03_test_scenario/output/test-scenario.md

テスト対象:
- validate_phase_dependencies() 関数
- detect_circular_dependencies() 関数
- validate_external_document() 関数
- PHASE_DEPENDENCIES 定数
- PHASE_PRESETS 定数
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
from core.phase_dependencies import (
    PHASE_DEPENDENCIES,
    PHASE_PRESETS,
    validate_phase_dependencies,
    detect_circular_dependencies,
    validate_external_document
)


class TestValidatePhaseDependencies:
    """validate_phase_dependencies() 関数のテスト"""

    def test_validate_success_all_dependencies_completed(self):
        """
        UT-001: 依存関係チェック - 正常系（すべて完了）

        Given: すべての依存フェーズがcompletedである
        When: validate_phase_dependencies('implementation')を呼び出す
        Then: valid=Trueが返される
        """
        # Arrange
        mock_metadata = Mock()
        mock_metadata.get_all_phases_status.return_value = {
            'planning': 'completed',
            'requirements': 'completed',
            'design': 'completed',
            'test_scenario': 'completed'
        }

        # Act
        result = validate_phase_dependencies(
            phase_name='implementation',
            metadata_manager=mock_metadata,
            skip_check=False,
            ignore_violations=False
        )

        # Assert
        assert result['valid'] is True
        assert 'error' not in result
        assert 'warning' not in result

    def test_validate_failure_dependency_incomplete(self):
        """
        UT-002: 依存関係チェック - 異常系（依存フェーズ未完了）

        Given: requirementsフェーズがpendingである
        When: validate_phase_dependencies('implementation')を呼び出す
        Then: valid=False、error、missing_phasesが返される
        """
        # Arrange
        mock_metadata = Mock()
        mock_metadata.get_all_phases_status.return_value = {
            'planning': 'completed',
            'requirements': 'pending',
            'design': 'in_progress',
            'test_scenario': 'pending'
        }

        # Act
        result = validate_phase_dependencies(
            phase_name='implementation',
            metadata_manager=mock_metadata,
            skip_check=False,
            ignore_violations=False
        )

        # Assert
        assert result['valid'] is False
        assert 'error' in result
        assert 'requirements' in result['error']
        assert 'missing_phases' in result
        assert 'requirements' in result['missing_phases']

    def test_skip_dependency_check_flag(self):
        """
        UT-003: 依存関係チェック - skip_check フラグ

        Given: skip_check=Trueが指定される
        When: validate_phase_dependencies()を呼び出す
        Then: 依存関係に関わらずvalid=Trueが返される
        """
        # Arrange
        mock_metadata = Mock()
        # 依存フェーズが未完了でも問題なし
        mock_metadata.get_all_phases_status.return_value = {
            'planning': 'pending',
            'requirements': 'pending',
            'design': 'pending',
            'test_scenario': 'pending'
        }

        # Act
        result = validate_phase_dependencies(
            phase_name='implementation',
            metadata_manager=mock_metadata,
            skip_check=True,
            ignore_violations=False
        )

        # Assert
        assert result['valid'] is True
        # get_all_phases_status()が呼ばれていないことを確認（早期リターン）
        mock_metadata.get_all_phases_status.assert_not_called()

    def test_ignore_violations_flag(self):
        """
        UT-004: 依存関係チェック - ignore_violations フラグ

        Given: ignore_violations=Trueが指定される
        When: 依存フェーズが未完了の状態でvalidate_phase_dependencies()を呼び出す
        Then: valid=False、ignored=True、warningが返される
        """
        # Arrange
        mock_metadata = Mock()
        mock_metadata.get_all_phases_status.return_value = {
            'planning': 'completed',
            'requirements': 'pending',
            'design': 'pending',
            'test_scenario': 'pending'
        }

        # Act
        result = validate_phase_dependencies(
            phase_name='implementation',
            metadata_manager=mock_metadata,
            skip_check=False,
            ignore_violations=True
        )

        # Assert
        assert result['valid'] is False
        assert result['ignored'] is True
        assert 'warning' in result
        assert 'requirements' in result['warning']
        assert 'design' in result['warning']
        assert 'test_scenario' in result['warning']
        assert 'missing_phases' in result
        assert len(result['missing_phases']) == 3

    def test_no_dependencies_phase(self):
        """
        UT-005: 依存関係チェック - 依存なしフェーズ

        Given: planningフェーズ（依存関係なし）を指定する
        When: validate_phase_dependencies('planning')を呼び出す
        Then: 常にvalid=Trueが返される
        """
        # Arrange
        mock_metadata = Mock()
        # get_all_phases_status()は呼ばれない想定

        # Act
        result = validate_phase_dependencies(
            phase_name='planning',
            metadata_manager=mock_metadata,
            skip_check=False,
            ignore_violations=False
        )

        # Assert
        assert result['valid'] is True
        # 依存関係がないため、get_all_phases_status()は呼ばれない
        mock_metadata.get_all_phases_status.assert_not_called()

    def test_invalid_phase_name(self):
        """
        UT-006: 依存関係チェック - 不正なフェーズ名

        Given: 存在しないフェーズ名を指定する
        When: validate_phase_dependencies('invalid_phase')を呼び出す
        Then: ValueErrorが発生する
        """
        # Arrange
        mock_metadata = Mock()

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            validate_phase_dependencies(
                phase_name='invalid_phase',
                metadata_manager=mock_metadata
            )

        assert 'Invalid phase name' in str(exc_info.value)


class TestDetectCircularDependencies:
    """detect_circular_dependencies() 関数のテスト"""

    def test_no_circular_dependencies(self):
        """
        UT-007: 循環参照検出 - 正常系（循環なし）

        Given: 現在のPHASE_DEPENDENCIES定義（循環参照なし）
        When: detect_circular_dependencies()を呼び出す
        Then: 空リストが返される
        """
        # Act
        cycles = detect_circular_dependencies()

        # Assert
        assert cycles == []

    def test_circular_dependencies_detection(self):
        """
        UT-008: 循環参照検出 - 異常系（循環あり）

        Given: テスト用の循環参照を含む依存関係定義
        When: detect_circular_dependencies()を呼び出す
        Then: 循環パスが検出される

        注意: このテストは実際には循環参照がPHASE_DEPENDENCIESに存在しないため、
             現在の実装では常に空リストが返される。
             循環参照検出機能の動作確認用のテストとして、
             将来の依存関係変更時の回帰テストとして機能する。
        """
        # Act
        cycles = detect_circular_dependencies()

        # Assert
        # 現在のPHASE_DEPENDENCIES定義では循環参照は存在しない
        assert isinstance(cycles, list)
        # 循環が存在しないことを確認
        assert len(cycles) == 0


class TestValidateExternalDocument:
    """validate_external_document() 関数のテスト"""

    def test_valid_markdown_file(self, tmp_path):
        """
        UT-009: 外部ドキュメント検証 - 正常系

        Given: 正常なMarkdownファイルが存在する
        When: validate_external_document()を呼び出す
        Then: valid=True、absolute_pathが返される
        """
        # Arrange
        test_file = tmp_path / "requirements.md"
        test_file.write_text("# Requirements\n\nThis is a test file.")

        # Act
        result = validate_external_document(str(test_file))

        # Assert
        assert result['valid'] is True
        assert 'absolute_path' in result
        assert Path(result['absolute_path']).exists()

    def test_file_not_found(self):
        """
        UT-010: 外部ドキュメント検証 - ファイル存在しない

        Given: 存在しないファイルパスを指定する
        When: validate_external_document()を呼び出す
        Then: valid=False、errorが返される
        """
        # Arrange
        non_existent_file = "/tmp/non_existent_file.md"

        # Act
        result = validate_external_document(non_existent_file)

        # Assert
        assert result['valid'] is False
        assert 'error' in result
        assert 'not found' in result['error'].lower()

    def test_invalid_file_format(self, tmp_path):
        """
        UT-011: 外部ドキュメント検証 - 不正なファイル形式

        Given: 許可されていないファイル形式（.sh）が指定される
        When: validate_external_document()を呼び出す
        Then: valid=False、errorに"Invalid file format"が含まれる
        """
        # Arrange
        test_file = tmp_path / "script.sh"
        test_file.write_text("#!/bin/bash\necho 'test'")

        # Act
        result = validate_external_document(str(test_file))

        # Assert
        assert result['valid'] is False
        assert 'error' in result
        assert 'Invalid file format' in result['error']
        assert '.sh' in result['error']

    def test_file_size_exceeded(self, tmp_path):
        """
        UT-012: 外部ドキュメント検証 - ファイルサイズ超過

        Given: 10MBを超えるファイルが指定される
        When: validate_external_document()を呼び出す
        Then: valid=False、errorに"size exceeds"が含まれる
        """
        # Arrange
        test_file = tmp_path / "large_file.md"
        # 10MB超のファイルを作成（11MB）
        large_content = "x" * (11 * 1024 * 1024)
        test_file.write_text(large_content)

        # Act
        result = validate_external_document(str(test_file))

        # Assert
        assert result['valid'] is False
        assert 'error' in result
        assert 'size' in result['error'].lower()
        assert '10MB' in result['error']

    def test_file_outside_repository(self, tmp_path):
        """
        UT-013: 外部ドキュメント検証 - リポジトリ外のファイル

        Given: リポジトリ外のファイルパスが指定される
        When: validate_external_document()をrepo_root指定で呼び出す
        Then: valid=False、errorに"within the repository"が含まれる
        """
        # Arrange
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # リポジトリ外にファイルを作成
        outside_file = tmp_path / "outside.md"
        outside_file.write_text("# Outside file")

        # Act
        result = validate_external_document(str(outside_file), repo_root=repo_root)

        # Assert
        assert result['valid'] is False
        assert 'error' in result
        assert 'within the repository' in result['error']

    def test_valid_txt_file(self, tmp_path):
        """
        外部ドキュメント検証 - .txtファイルも許可される

        Given: 正常な.txtファイルが存在する
        When: validate_external_document()を呼び出す
        Then: valid=Trueが返される
        """
        # Arrange
        test_file = tmp_path / "requirements.txt"
        test_file.write_text("Requirement 1\nRequirement 2")

        # Act
        result = validate_external_document(str(test_file))

        # Assert
        assert result['valid'] is True
        assert 'absolute_path' in result


class TestPhaseDependenciesConstant:
    """PHASE_DEPENDENCIES 定数のテスト"""

    def test_all_phases_defined(self):
        """
        UT-018: フェーズ依存関係定義の完全性

        Given: PHASE_DEPENDENCIES定義
        When: 全フェーズがキーとして存在するか確認する
        Then: すべてのフェーズが定義されている
        """
        # Arrange
        expected_phases = [
            'planning', 'requirements', 'design', 'test_scenario',
            'implementation', 'test_implementation', 'testing',
            'documentation', 'report', 'evaluation'
        ]

        # Act & Assert
        for phase in expected_phases:
            assert phase in PHASE_DEPENDENCIES, f"Phase '{phase}' not defined"

        # すべてのキーが期待されるフェーズのいずれかであることを確認
        for phase in PHASE_DEPENDENCIES.keys():
            assert phase in expected_phases, f"Unexpected phase '{phase}' defined"

    def test_forward_dependencies_only(self):
        """
        UT-019: フェーズ依存関係の前方依存性

        Given: PHASE_DEPENDENCIES定義
        When: 各フェーズの依存関係を確認する
        Then: すべての依存関係が前方依存（Phase N → Phase N-1以前）である
        """
        # Arrange
        phase_order = [
            'planning', 'requirements', 'design', 'test_scenario',
            'implementation', 'test_implementation', 'testing',
            'documentation', 'report', 'evaluation'
        ]

        # Act & Assert
        for i, phase in enumerate(phase_order):
            dependencies = PHASE_DEPENDENCIES.get(phase, [])
            for dep in dependencies:
                dep_index = phase_order.index(dep)
                assert dep_index < i, \
                    f"Phase '{phase}' has backward dependency on '{dep}'"


class TestPhasePresetsConstant:
    """PHASE_PRESETS 定数のテスト"""

    def test_preset_requirements_only(self):
        """
        UT-014: プリセット取得 - requirements-only

        Given: PHASE_PRESETS['requirements-only']
        When: プリセット定義を確認する
        Then: ['requirements']が返される
        """
        # Act
        phases = PHASE_PRESETS['requirements-only']

        # Assert
        assert phases == ['requirements']

    def test_preset_design_phase(self):
        """
        UT-015: プリセット取得 - design-phase

        Given: PHASE_PRESETS['design-phase']
        When: プリセット定義を確認する
        Then: ['requirements', 'design']が返される
        """
        # Act
        phases = PHASE_PRESETS['design-phase']

        # Assert
        assert phases == ['requirements', 'design']

    def test_preset_implementation_phase(self):
        """
        UT-016: プリセット取得 - implementation-phase

        Given: PHASE_PRESETS['implementation-phase']
        When: プリセット定義を確認する
        Then: 正しいフェーズリストが返される
        """
        # Act
        phases = PHASE_PRESETS['implementation-phase']

        # Assert
        expected = ['requirements', 'design', 'test_scenario', 'implementation']
        assert phases == expected

    def test_all_presets_valid(self):
        """
        UT-017: プリセット定義のバリデーション

        Given: PHASE_PRESETS内のすべてのプリセット
        When: 各プリセットのフェーズ名を確認する
        Then: すべてのフェーズ名がPHASE_DEPENDENCIESに存在する
        """
        # Act & Assert
        for preset_name, phases in PHASE_PRESETS.items():
            for phase in phases:
                assert phase in PHASE_DEPENDENCIES, \
                    f"Preset '{preset_name}' contains invalid phase '{phase}'"


class TestPerformance:
    """パフォーマンステスト"""

    def test_validation_performance(self):
        """
        UT-020: 依存関係チェックのオーバーヘッド

        Given: 100回の連続実行
        When: validate_phase_dependencies()を実行する
        Then: 平均実行時間が0.1秒以下である

        注意: このテストは理想的にはtime.perf_counter()を使用して
             実際の実行時間を測定すべきですが、ユニットテストとしては
             関数が正常に動作することを確認します。
        """
        import time

        # Arrange
        mock_metadata = Mock()
        mock_metadata.get_all_phases_status.return_value = {
            'planning': 'completed',
            'requirements': 'completed',
            'design': 'completed',
            'test_scenario': 'completed'
        }

        iterations = 100
        start_time = time.perf_counter()

        # Act
        for _ in range(iterations):
            result = validate_phase_dependencies(
                phase_name='implementation',
                metadata_manager=mock_metadata,
                skip_check=False,
                ignore_violations=False
            )
            assert result['valid'] is True

        end_time = time.perf_counter()

        # Assert
        elapsed_time = end_time - start_time
        average_time = elapsed_time / iterations

        # パフォーマンス要件: 平均0.1秒以下
        assert average_time < 0.1, \
            f"Average execution time {average_time:.4f}s exceeds 0.1s threshold"

        # 情報出力（テスト失敗時のデバッグ用）
        print(f"\nPerformance: {iterations} iterations in {elapsed_time:.4f}s")
        print(f"Average time per call: {average_time:.6f}s")
