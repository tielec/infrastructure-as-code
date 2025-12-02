"""
ユニットテスト: models.py

テスト対象:
- PRInfo: PRの基本情報を保持するデータクラス
- FileChange: ファイル変更情報を保持するデータクラス
"""

import pytest
from pr_comment_generator.models import PRInfo, FileChange


class TestPRInfo:
    """PRInfoデータクラスのテスト"""

    def test_from_json_正常系(self):
        """
        Given: 有効なPR情報JSONデータが存在する
        When: PRInfo.from_json()を呼び出す
        Then: PRInfoオブジェクトが正しく生成される
        """
        # Given
        data = {
            "title": "Add new feature",
            "number": 123,
            "body": "This is a test PR",
            "user": {"login": "testuser"},
            "base": {"ref": "main", "sha": "abc123"},
            "head": {"ref": "feature-branch", "sha": "def456"}
        }

        # When
        pr_info = PRInfo.from_json(data)

        # Then
        assert pr_info.title == "Add new feature"
        assert pr_info.number == 123
        assert pr_info.body == "This is a test PR"
        assert pr_info.author == "testuser"
        assert pr_info.base_branch == "main"
        assert pr_info.head_branch == "feature-branch"
        assert pr_info.base_sha == "abc123"
        assert pr_info.head_sha == "def456"

    def test_from_json_異常系_欠損データ(self):
        """
        Given: 一部のフィールドが欠損しているJSONデータ
        When: PRInfo.from_json()を呼び出す
        Then: PRInfoオブジェクトが生成される（デフォルト値が設定される）
        """
        # Given
        data = {
            "title": "Add new feature",
            "number": 123
        }

        # When
        pr_info = PRInfo.from_json(data)

        # Then
        assert pr_info.title == "Add new feature"
        assert pr_info.number == 123
        assert pr_info.body == ""
        assert pr_info.author == ""
        assert pr_info.base_branch == ""
        assert pr_info.head_branch == ""

    def test_from_json_異常系_body_None(self):
        """
        Given: bodyがNoneのJSONデータ
        When: PRInfo.from_json()を呼び出す
        Then: bodyが空文字列に変換される
        """
        # Given
        data = {
            "title": "Test PR",
            "number": 456,
            "body": None
        }

        # When
        pr_info = PRInfo.from_json(data)

        # Then
        assert pr_info.body == ""


class TestFileChange:
    """FileChangeデータクラスのテスト"""

    def test_from_json_正常系(self):
        """
        Given: 有効なファイル変更JSONデータが存在する
        When: FileChange.from_json()を呼び出す
        Then: FileChangeオブジェクトが正しく生成される
        """
        # Given
        data = {
            "filename": "src/main.py",
            "status": "modified",
            "additions": 10,
            "deletions": 5,
            "changes": 15,
            "patch": "@@ -1,3 +1,4 @@\n+new line\n old line"
        }

        # When
        file_change = FileChange.from_json(data)

        # Then
        assert file_change.filename == "src/main.py"
        assert file_change.status == "modified"
        assert file_change.additions == 10
        assert file_change.deletions == 5
        assert file_change.changes == 15
        assert file_change.patch == "@@ -1,3 +1,4 @@\n+new line\n old line"

    def test_from_json_異常系_欠損データ(self):
        """
        Given: 一部のフィールドが欠損しているJSONデータ
        When: FileChange.from_json()を呼び出す
        Then: FileChangeオブジェクトが生成される（デフォルト値が設定される）
        """
        # Given
        data = {
            "filename": "src/utils.py"
        }

        # When
        file_change = FileChange.from_json(data)

        # Then
        assert file_change.filename == "src/utils.py"
        assert file_change.status == ""
        assert file_change.additions == 0
        assert file_change.deletions == 0
        assert file_change.changes == 0
        assert file_change.patch is None

    def test_from_json_正常系_patch_None(self):
        """
        Given: patchがNoneのJSONデータ
        When: FileChange.from_json()を呼び出す
        Then: FileChangeオブジェクトが生成され、patchがNoneのまま
        """
        # Given
        data = {
            "filename": "renamed_file.py",
            "status": "renamed",
            "additions": 0,
            "deletions": 0,
            "changes": 0,
            "patch": None
        }

        # When
        file_change = FileChange.from_json(data)

        # Then
        assert file_change.filename == "renamed_file.py"
        assert file_change.patch is None
