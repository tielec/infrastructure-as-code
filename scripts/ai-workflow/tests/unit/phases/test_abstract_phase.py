"""
Unit tests for phases/base/abstract_phase.py

Test Scenarios:
- AbstractPhaseクラスの初期化動作
- ディレクトリ作成の確認
- load_prompt()メソッドの動作
- 抽象メソッドの実装要求
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from phases.base.abstract_phase import AbstractPhase


# テスト用の具象クラス
class ConcretePhase(AbstractPhase):
    """AbstractPhaseを継承したテスト用の具象クラス"""

    def execute(self):
        """execute()の実装"""
        return {'success': True, 'output': 'test_output.md', 'error': None}

    def review(self):
        """review()の実装"""
        return {'result': 'PASS', 'feedback': 'Good', 'suggestions': []}


class TestAbstractPhase:
    """AbstractPhase クラスのユニットテスト"""

    @patch('phases.base.abstract_phase.Path.mkdir')
    def test_initialization_creates_directories(self, mock_mkdir):
        """初期化時に必要なディレクトリが作成されることを確認"""
        # Given: メタデータマネージャーとClaudeクライアントのモック
        mock_metadata = Mock()
        mock_metadata.workflow_dir = Path('/tmp/test/.ai-workflow/issue-376')
        mock_claude = Mock()

        # When: ConcretePhaseを初期化
        phase = ConcretePhase(
            phase_name='planning',
            working_dir=Path('/tmp/test'),
            metadata_manager=mock_metadata,
            claude_client=mock_claude
        )

        # Then: ディレクトリパスが正しく設定される
        assert phase.phase_name == 'planning'
        assert phase.working_dir == Path('/tmp/test')
        assert phase.metadata == mock_metadata
        assert phase.claude == mock_claude

        # フェーズ番号が'00'（planning）であることを確認
        expected_phase_dir = Path('/tmp/test/.ai-workflow/issue-376/00_planning')
        assert phase.phase_dir == expected_phase_dir
        assert phase.output_dir == expected_phase_dir / 'output'
        assert phase.execute_dir == expected_phase_dir / 'execute'
        assert phase.review_dir == expected_phase_dir / 'review'
        assert phase.revise_dir == expected_phase_dir / 'revise'

    def test_phase_numbers_mapping(self):
        """PHASE_NUMBERSマッピングが正しく定義されていることを確認"""
        # Given/When: PHASE_NUMBERSマッピング
        phase_numbers = AbstractPhase.PHASE_NUMBERS

        # Then: 全フェーズが定義されている
        assert phase_numbers['planning'] == '00'
        assert phase_numbers['requirements'] == '01'
        assert phase_numbers['design'] == '02'
        assert phase_numbers['test_scenario'] == '03'
        assert phase_numbers['implementation'] == '04'
        assert phase_numbers['test_implementation'] == '05'
        assert phase_numbers['testing'] == '06'
        assert phase_numbers['documentation'] == '07'
        assert phase_numbers['report'] == '08'
        assert phase_numbers['evaluation'] == '09'

    def test_get_phase_number_returns_correct_number(self):
        """get_phase_number()が正しいフェーズ番号を返すことを確認"""
        # Given: ConcretePhaseインスタンス
        mock_metadata = Mock()
        mock_metadata.workflow_dir = Path('/tmp/test/.ai-workflow/issue-376')
        mock_claude = Mock()

        phase = ConcretePhase(
            phase_name='design',
            working_dir=Path('/tmp/test'),
            metadata_manager=mock_metadata,
            claude_client=mock_claude
        )

        # When: get_phase_number()を呼び出す
        phase_number = phase.get_phase_number()

        # Then: '02'が返される
        assert phase_number == '02'

    @patch('phases.base.abstract_phase.Path.read_text')
    @patch('phases.base.abstract_phase.Path.exists')
    def test_load_prompt_reads_prompt_file(self, mock_exists, mock_read_text):
        """load_prompt()がプロンプトファイルを正しく読み込むことを確認"""
        # Given: プロンプトファイルが存在する
        mock_exists.return_value = True
        mock_read_text.return_value = "This is a test prompt"

        mock_metadata = Mock()
        mock_metadata.workflow_dir = Path('/tmp/test/.ai-workflow/issue-376')
        mock_claude = Mock()

        phase = ConcretePhase(
            phase_name='planning',
            working_dir=Path('/tmp/test'),
            metadata_manager=mock_metadata,
            claude_client=mock_claude
        )

        # When: load_prompt()を呼び出す
        prompt = phase.load_prompt('execute')

        # Then: プロンプトテキストが返される
        assert prompt == "This is a test prompt"
        mock_read_text.assert_called_once_with(encoding='utf-8')

    @patch('phases.base.abstract_phase.Path.exists')
    def test_load_prompt_raises_error_when_file_not_found(self, mock_exists):
        """load_prompt()がファイル不存在時にFileNotFoundErrorを発生させることを確認"""
        # Given: プロンプトファイルが存在しない
        mock_exists.return_value = False

        mock_metadata = Mock()
        mock_metadata.workflow_dir = Path('/tmp/test/.ai-workflow/issue-376')
        mock_claude = Mock()

        phase = ConcretePhase(
            phase_name='planning',
            working_dir=Path('/tmp/test'),
            metadata_manager=mock_metadata,
            claude_client=mock_claude
        )

        # When/Then: FileNotFoundErrorが発生
        with pytest.raises(FileNotFoundError, match="Prompt file not found"):
            phase.load_prompt('execute')

    def test_execute_is_implemented_in_concrete_class(self):
        """具象クラスでexecute()が実装されていることを確認"""
        # Given: ConcretePhaseインスタンス
        mock_metadata = Mock()
        mock_metadata.workflow_dir = Path('/tmp/test/.ai-workflow/issue-376')
        mock_claude = Mock()

        phase = ConcretePhase(
            phase_name='planning',
            working_dir=Path('/tmp/test'),
            metadata_manager=mock_metadata,
            claude_client=mock_claude
        )

        # When: execute()を呼び出す
        result = phase.execute()

        # Then: 実装された結果が返される
        assert result['success'] is True
        assert result['output'] == 'test_output.md'
        assert result['error'] is None

    def test_review_is_implemented_in_concrete_class(self):
        """具象クラスでreview()が実装されていることを確認"""
        # Given: ConcretePhaseインスタンス
        mock_metadata = Mock()
        mock_metadata.workflow_dir = Path('/tmp/test/.ai-workflow/issue-376')
        mock_claude = Mock()

        phase = ConcretePhase(
            phase_name='planning',
            working_dir=Path('/tmp/test'),
            metadata_manager=mock_metadata,
            claude_client=mock_claude
        )

        # When: review()を呼び出す
        result = phase.review()

        # Then: 実装された結果が返される
        assert result['result'] == 'PASS'
        assert result['feedback'] == 'Good'
        assert result['suggestions'] == []

    def test_cannot_instantiate_abstract_phase_directly(self):
        """AbstractPhaseを直接インスタンス化できないことを確認"""
        # Given: AbstractPhaseクラス
        mock_metadata = Mock()
        mock_metadata.workflow_dir = Path('/tmp/test/.ai-workflow/issue-376')
        mock_claude = Mock()

        # When/Then: TypeErrorが発生
        with pytest.raises(TypeError):
            AbstractPhase(
                phase_name='planning',
                working_dir=Path('/tmp/test'),
                metadata_manager=mock_metadata,
                claude_client=mock_claude
            )


class IncompletePhase(AbstractPhase):
    """execute()のみ実装した不完全なクラス（テスト用）"""

    def execute(self):
        return {'success': True}


class TestAbstractMethodsEnforcement:
    """抽象メソッドの実装要求のテスト"""

    def test_incomplete_phase_cannot_be_instantiated(self):
        """execute()のみ実装したクラスはインスタンス化できないことを確認"""
        # Given: review()を実装していないIncompletePhase
        mock_metadata = Mock()
        mock_metadata.workflow_dir = Path('/tmp/test/.ai-workflow/issue-376')
        mock_claude = Mock()

        # When/Then: TypeErrorが発生
        with pytest.raises(TypeError):
            IncompletePhase(
                phase_name='planning',
                working_dir=Path('/tmp/test'),
                metadata_manager=mock_metadata,
                claude_client=mock_claude
            )

    def test_content_parser_is_initialized(self):
        """ContentParserが初期化されることを確認"""
        # Given: ConcretePhaseインスタンス
        mock_metadata = Mock()
        mock_metadata.workflow_dir = Path('/tmp/test/.ai-workflow/issue-376')
        mock_claude = Mock()

        phase = ConcretePhase(
            phase_name='planning',
            working_dir=Path('/tmp/test'),
            metadata_manager=mock_metadata,
            claude_client=mock_claude
        )

        # When/Then: content_parserが初期化されている
        assert hasattr(phase, 'content_parser')
        assert phase.content_parser is not None
