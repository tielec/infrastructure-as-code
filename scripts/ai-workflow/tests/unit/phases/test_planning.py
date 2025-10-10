"""PlanningPhaseのUnitテスト"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
from core.metadata_manager import MetadataManager
from core.workflow_state import WorkflowState
from core.claude_agent_client import ClaudeAgentClient
from core.github_client import GitHubClient
from phases.planning import PlanningPhase


class TestPlanningPhase:
    """PlanningPhaseクラスのUnitテスト"""

    @pytest.fixture
    def setup_phase(self, tmp_path):
        """フェーズのセットアップ（モック使用）"""
        # metadata.jsonを作成
        metadata_path = tmp_path / 'metadata.json'
        WorkflowState.create_new(
            metadata_path=metadata_path,
            issue_number='313',
            issue_url='https://github.com/tielec/infrastructure-as-code/issues/313',
            issue_title='[FEATURE] Phase 0 (Planning): プロジェクトマネージャ役割の追加'
        )

        # working_dirを作成
        working_dir = tmp_path / 'working'
        working_dir.mkdir()

        # プロンプトディレクトリを作成
        prompts_dir = working_dir / 'prompts' / 'planning'
        prompts_dir.mkdir(parents=True)

        # execute.txtプロンプトを作成
        execute_prompt = prompts_dir / 'execute.txt'
        execute_prompt.write_text('Test execute prompt\n{issue_info}\n{issue_number}', encoding='utf-8')

        # review.txtプロンプトを作成
        review_prompt = prompts_dir / 'review.txt'
        review_prompt.write_text('Test review prompt\n{planning_document_path}', encoding='utf-8')

        # revise.txtプロンプトを作成
        revise_prompt = prompts_dir / 'revise.txt'
        revise_prompt.write_text('Test revise prompt\n{planning_document_path}\n{review_feedback}\n{issue_info}\n{issue_number}', encoding='utf-8')

        # メタデータマネージャー
        metadata_manager = MetadataManager(metadata_path)

        # モッククライアント
        claude_client = Mock(spec=ClaudeAgentClient)
        claude_client.working_dir = working_dir
        github_client = Mock(spec=GitHubClient)

        # フェーズインスタンス
        phase = PlanningPhase(
            working_dir=working_dir,
            metadata_manager=metadata_manager,
            claude_client=claude_client,
            github_client=github_client
        )

        return {
            'phase': phase,
            'metadata_manager': metadata_manager,
            'claude_client': claude_client,
            'github_client': github_client,
            'prompts_dir': prompts_dir,
            'tmp_path': tmp_path
        }

    def test_init(self, setup_phase):
        """
        初期化のテスト

        検証項目:
        - phase_nameが'planning'であること
        - フェーズディレクトリが'00_planning'であること
        - サブディレクトリが作成されていること
        """
        # Arrange & Act
        phase = setup_phase['phase']

        # Assert
        assert phase.phase_name == 'planning'
        assert phase.phase_dir.name == '00_planning'
        assert phase.output_dir.exists()
        assert phase.execute_dir.exists()
        assert phase.review_dir.exists()
        assert phase.revise_dir.exists()

    def test_format_issue_info_正常系(self, setup_phase):
        """
        Issue情報のフォーマット（正常系）

        検証項目:
        - Issue情報が正しくフォーマットされること
        """
        # Arrange
        phase = setup_phase['phase']
        issue_info = {
            'number': 313,
            'title': '[FEATURE] Phase 0追加',
            'state': 'open',
            'url': 'https://github.com/test/repo/issues/313',
            'labels': ['enhancement'],
            'body': '## 概要\nPhase 0を追加する'
        }

        # Act
        result = phase._format_issue_info(issue_info)

        # Assert
        assert '313' in result
        assert '[FEATURE] Phase 0追加' in result
        assert 'open' in result
        assert 'enhancement' in result
        assert '## 概要' in result

    def test_format_issue_info_ラベルなし(self, setup_phase):
        """
        Issue情報のフォーマット（ラベルなし）

        検証項目:
        - ラベルが空の場合でもエラーにならないこと
        """
        # Arrange
        phase = setup_phase['phase']
        issue_info = {
            'number': 313,
            'title': '[FEATURE] Phase 0追加',
            'state': 'open',
            'url': 'https://github.com/test/repo/issues/313',
            'labels': [],
            'body': '## 概要\nPhase 0を追加する'
        }

        # Act
        result = phase._format_issue_info(issue_info)

        # Assert
        assert 'なし' in result
        assert '313' in result

    def test_format_issue_info_本文null(self, setup_phase):
        """
        Issue情報のフォーマット（本文null）

        検証項目:
        - 本文がnullの場合でもエラーにならないこと
        """
        # Arrange
        phase = setup_phase['phase']
        issue_info = {
            'number': 313,
            'title': '[FEATURE] Phase 0追加',
            'state': 'open',
            'url': 'https://github.com/test/repo/issues/313',
            'labels': ['enhancement'],
            'body': None
        }

        # Act
        result = phase._format_issue_info(issue_info)

        # Assert
        assert '313' in result
        assert '(本文なし)' in result

    def test_extract_design_decisions_すべて抽出成功(self, setup_phase):
        """
        戦略判断の抽出（すべて抽出成功）

        検証項目:
        - 3つの戦略が正しく抽出されること
        """
        # Arrange
        phase = setup_phase['phase']
        planning_content = """
## 実装戦略判断

### 実装戦略: CREATE

**判断根拠**:
- 新規フェーズの追加

### テスト戦略: UNIT_INTEGRATION

**判断根拠**:
- Unitテストの必要性

### テストコード戦略: CREATE_TEST

**判断根拠**:
- 新規テストファイルの作成
"""

        # Act
        result = phase._extract_design_decisions(planning_content)

        # Assert
        assert result['implementation_strategy'] == 'CREATE'
        assert result['test_strategy'] == 'UNIT_INTEGRATION'
        assert result['test_code_strategy'] == 'CREATE_TEST'

    def test_extract_design_decisions_一部のみ抽出(self, setup_phase):
        """
        戦略判断の抽出（一部のみ抽出）

        検証項目:
        - 実装戦略のみ記載されている場合、その部分だけ抽出されること
        """
        # Arrange
        phase = setup_phase['phase']
        planning_content = """
### 実装戦略: EXTEND

**判断根拠**: 既存機能の拡張
"""

        # Act
        result = phase._extract_design_decisions(planning_content)

        # Assert
        assert result['implementation_strategy'] == 'EXTEND'
        assert 'test_strategy' not in result
        assert 'test_code_strategy' not in result

    def test_extract_design_decisions_抽出失敗(self, setup_phase):
        """
        戦略判断の抽出（抽出失敗）

        検証項目:
        - 戦略情報が存在しない場合、空の辞書が返されること
        """
        # Arrange
        phase = setup_phase['phase']
        planning_content = """
## タスク分割

### Phase 1: 要件定義
- サブタスク1
"""

        # Act
        result = phase._extract_design_decisions(planning_content)

        # Assert
        assert result == {}

    def test_extract_design_decisions_大文字小文字混在(self, setup_phase):
        """
        戦略判断の抽出（大文字小文字混在）

        検証項目:
        - 戦略名の大文字小文字が混在していても正しく抽出されること
        """
        # Arrange
        phase = setup_phase['phase']
        planning_content = """
### 実装戦略: create
### テスト戦略: unit_integration
"""

        # Act
        result = phase._extract_design_decisions(planning_content)

        # Assert
        assert result['implementation_strategy'] == 'CREATE'
        assert result['test_strategy'] == 'UNIT_INTEGRATION'

    def test_extract_design_decisions_無効な戦略名(self, setup_phase):
        """
        戦略判断の抽出（無効な戦略名）

        検証項目:
        - 無効な戦略名が記載されている場合、抽出されないこと
        """
        # Arrange
        phase = setup_phase['phase']
        planning_content = """
### 実装戦略: INVALID_STRATEGY
"""

        # Act
        result = phase._extract_design_decisions(planning_content)

        # Assert
        assert result == {}

    def test_execute_正常系(self, setup_phase):
        """
        execute()メソッド（正常系）

        検証項目:
        - planning.mdが生成されること
        - metadata.jsonに戦略が保存されること
        """
        # Arrange
        phase = setup_phase['phase']
        claude_client = setup_phase['claude_client']
        github_client = setup_phase['github_client']
        metadata_manager = setup_phase['metadata_manager']

        # モックの返り値を設定
        claude_client.execute_task_sync.return_value = ['Test message']
        github_client.get_issue_info.return_value = {
            'number': 313,
            'title': '[FEATURE] Phase 0追加',
            'state': 'open',
            'url': 'https://github.com/test/repo/issues/313',
            'labels': ['enhancement'],
            'body': '## 概要\nPhase 0を追加する'
        }

        # planning.mdを作成
        planning_md = phase.output_dir / 'planning.md'
        planning_md.write_text("""
### 実装戦略: CREATE
### テスト戦略: UNIT_INTEGRATION
### テストコード戦略: CREATE_TEST
""", encoding='utf-8')

        # Act
        result = phase.execute()

        # Assert
        assert result['success'] is True
        assert planning_md.exists()
        assert metadata_manager.data['design_decisions']['implementation_strategy'] == 'CREATE'
        assert metadata_manager.data['design_decisions']['test_strategy'] == 'UNIT_INTEGRATION'
        assert metadata_manager.data['design_decisions']['test_code_strategy'] == 'CREATE_TEST'

    def test_execute_Issue取得失敗(self, setup_phase):
        """
        execute()メソッド（Issue取得失敗）

        検証項目:
        - Issue情報の取得に失敗した場合、エラーが返されること
        """
        # Arrange
        phase = setup_phase['phase']
        github_client = setup_phase['github_client']

        # GitHub APIがエラーを返す
        github_client.get_issue_info.side_effect = Exception('GitHub API error')

        # Act
        result = phase.execute()

        # Assert
        assert result['success'] is False
        assert 'GitHub API error' in result['error']

    def test_review_PASS(self, setup_phase):
        """
        review()メソッド（PASS）

        検証項目:
        - レビューが成功し、PASSが返されること
        """
        # Arrange
        phase = setup_phase['phase']
        claude_client = setup_phase['claude_client']

        # planning.mdを作成
        planning_md = phase.output_dir / 'planning.md'
        planning_md.write_text('Test planning content', encoding='utf-8')

        # モックの返り値を設定
        claude_client.execute_task_sync.return_value = ['**判定: PASS**\n計画が適切です。']

        # Act
        result = phase.review()

        # Assert
        assert result['result'] == 'PASS'
        assert '適切' in result['feedback']

    def test_review_planning_md存在しない(self, setup_phase):
        """
        review()メソッド（planning.md存在しない）

        検証項目:
        - planning.mdが存在しない場合、FAILが返されること
        """
        # Arrange
        phase = setup_phase['phase']

        # Act
        result = phase.review()

        # Assert
        assert result['result'] == 'FAIL'
        assert 'planning.mdが存在しません' in result['feedback']

    def test_revise_正常系(self, setup_phase):
        """
        revise()メソッド（正常系）

        検証項目:
        - planning.mdが修正されること
        - metadata.jsonの戦略が再抽出されること
        """
        # Arrange
        phase = setup_phase['phase']
        claude_client = setup_phase['claude_client']
        github_client = setup_phase['github_client']
        metadata_manager = setup_phase['metadata_manager']

        # 元のplanning.mdを作成
        planning_md = phase.output_dir / 'planning.md'
        planning_md.write_text('Original planning content', encoding='utf-8')

        # モックの返り値を設定
        claude_client.execute_task_sync.return_value = ['Test message']
        github_client.get_issue_info.return_value = {
            'number': 313,
            'title': '[FEATURE] Phase 0追加',
            'state': 'open',
            'url': 'https://github.com/test/repo/issues/313',
            'labels': ['enhancement'],
            'body': '## 概要\nPhase 0を追加する'
        }

        # 修正後のplanning.mdの内容を設定
        planning_md.write_text("""
### 実装戦略: REFACTOR
### テスト戦略: ALL
### テストコード戦略: BOTH_TEST
""", encoding='utf-8')

        # Act
        result = phase.revise(review_feedback='テスト改善提案')

        # Assert
        assert result['success'] is True
        assert metadata_manager.data['design_decisions']['implementation_strategy'] == 'REFACTOR'
