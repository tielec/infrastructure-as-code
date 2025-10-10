# テストシナリオ

**Issue**: #310
**タイトル**: [ai-workflow] feat: 全フェーズの成果物をGitHub Issueコメントに投稿する機能を追加
**作成日**: 2025-10-10
**テスト戦略**: UNIT_INTEGRATION

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略

**UNIT_INTEGRATION**

Phase 2（設計フェーズ）で決定されたテスト戦略に基づき、以下の2種類のテストを実施します：

1. **Unitテスト**: 各フェーズの `execute()` メソッドが正しく `post_output()` を呼び出すか検証
2. **Integrationテスト**: `BasePhase.post_output()` → `GitHubClient.post_comment()` → GitHub API の統合フロー検証

### 1.2 テスト対象の範囲

| Phase | ファイルパス | 追加対象メソッド | 成果物ファイル |
|-------|------------|-----------------|--------------|
| Phase 1 | `scripts/ai-workflow/phases/requirements.py` | `execute()` | `requirements.md` |
| Phase 2 | `scripts/ai-workflow/phases/design.py` | `execute()` | `design.md` |
| Phase 3 | `scripts/ai-workflow/phases/test_scenario.py` | `execute()` | `test-scenario.md` |
| Phase 4 | `scripts/ai-workflow/phases/implementation.py` | `execute()` | `implementation.md` |
| Phase 5 | `scripts/ai-workflow/phases/testing.py` | `execute()` | `test-result.md` |
| Phase 7 | `scripts/ai-workflow/phases/report.py` | `execute()` (既存確認) | `report.md` |

### 1.3 テストの目的

- **機能要件の検証**: 各フェーズで成果物がGitHub Issueコメントに正しく投稿されること
- **エラーハンドリングの検証**: GitHub API投稿失敗時でもワークフローが継続すること
- **エンコーディングの検証**: UTF-8で日本語を含む成果物が文字化けせずに投稿されること
- **統合動作の検証**: BasePhase → GitHubClient → GitHub API の連携が正常に動作すること

---

## 2. Unitテストシナリオ

### 2.1 Phase 1: RequirementsPhase.execute()

#### テストケース 1-1: requirements_execute_正常系_成果物投稿成功

**目的**: Phase 1が正常に完了した場合、成果物がGitHub Issueに投稿されることを検証

**前提条件**:
- Phase 1の実行が正常に完了している
- `requirements.md` ファイルが生成されている
- `BasePhase.post_output()` メソッドが正常に動作する

**入力**:
- `output_file`: `.ai-workflow/issue-310/01_requirements/output/requirements.md`
- `output_content`: UTF-8エンコーディングで読み込まれた `requirements.md` の内容

**期待結果**:
- `post_output()` メソッドが呼び出される
- `post_output()` の引数は以下の通り:
  - `output_content`: `requirements.md` の内容
  - `title`: "要件定義書"
- `execute()` メソッドが `success=True` を返す

**テストデータ**:
```python
# モック対象
with patch.object(BasePhase, 'post_output') as mock_post_output:
    # execute() 実行
    result = requirements_phase.execute()

    # 検証
    mock_post_output.assert_called_once()
    args, kwargs = mock_post_output.call_args
    assert kwargs['title'] == "要件定義書"
    assert 'requirements.md' の内容が kwargs['output_content'] に含まれる
    assert result['success'] is True
```

---

#### テストケース 1-2: requirements_execute_異常系_GitHub投稿失敗

**目的**: GitHub API投稿失敗時でもワークフローが継続することを検証

**前提条件**:
- Phase 1の実行が正常に完了している
- `requirements.md` ファイルが生成されている
- `BasePhase.post_output()` が例外をスローする

**入力**:
- `output_file`: `.ai-workflow/issue-310/01_requirements/output/requirements.md`
- `BasePhase.post_output()` が `Exception("GitHub API Error")` をスロー

**期待結果**:
- WARNING ログが出力される: `[WARNING] 成果物のGitHub投稿に失敗しました: GitHub API Error`
- `execute()` メソッドが `success=True` を返す（ワークフロー継続）

**テストデータ**:
```python
# モック対象
with patch.object(BasePhase, 'post_output', side_effect=Exception("GitHub API Error")):
    with patch('builtins.print') as mock_print:
        # execute() 実行
        result = requirements_phase.execute()

        # 検証
        mock_print.assert_any_call("[WARNING] 成果物のGitHub投稿に失敗しました: GitHub API Error")
        assert result['success'] is True
```

---

#### テストケース 1-3: requirements_execute_異常系_成果物ファイル不存在

**目的**: 成果物ファイルが存在しない場合、`post_output()` が呼ばれないことを検証

**前提条件**:
- Phase 1の実行が失敗している
- `requirements.md` ファイルが生成されていない

**入力**:
- `output_file`: 存在しないファイルパス

**期待結果**:
- `post_output()` メソッドが呼ばれない
- `execute()` メソッドがエラーを返す（既存のエラーハンドリング）

**テストデータ**:
```python
# モック対象
with patch.object(BasePhase, 'post_output') as mock_post_output:
    with patch('pathlib.Path.exists', return_value=False):
        # execute() 実行
        result = requirements_phase.execute()

        # 検証
        mock_post_output.assert_not_called()
        assert result['success'] is False
```

---

#### テストケース 1-4: requirements_execute_正常系_UTF8エンコーディング

**目的**: UTF-8エンコーディングで日本語を含む成果物が正しく読み込まれることを検証

**前提条件**:
- Phase 1の実行が正常に完了している
- `requirements.md` ファイルに日本語が含まれている

**入力**:
- `output_file`: 日本語を含む `requirements.md`
- 内容例: "# 要件定義書\n\n## 1. 概要\n\n現在のAI駆動開発自動化ワークフロー..."

**期待結果**:
- `output_file.read_text(encoding='utf-8')` が呼ばれる
- 日本語が文字化けせずに `post_output()` に渡される

**テストデータ**:
```python
# モック対象
with patch.object(BasePhase, 'post_output') as mock_post_output:
    # execute() 実行
    result = requirements_phase.execute()

    # 検証
    args, kwargs = mock_post_output.call_args
    assert "要件定義書" in kwargs['output_content']
    assert "AI駆動開発自動化ワークフロー" in kwargs['output_content']  # 日本語が正しく含まれる
```

---

### 2.2 Phase 2: DesignPhase.execute()

#### テストケース 2-1: design_execute_正常系_既存変数再利用

**目的**: Phase 2で既存の `design_content` 変数が再利用され、ファイル読み込みが1回のみであることを検証

**前提条件**:
- Phase 2の実行が正常に完了している
- `design.md` ファイルが生成されている
- 88行目で既に `design_content = output_file.read_text(encoding='utf-8')` が実行されている

**入力**:
- `output_file`: `.ai-workflow/issue-310/02_design/output/design.md`
- `design_content`: 88行目で読み込まれた内容

**期待結果**:
- `output_file.read_text()` が1回のみ呼ばれる（88行目）
- `post_output()` が `design_content` 変数を使用して呼ばれる
- `post_output()` の引数:
  - `output_content`: `design_content` 変数の内容
  - `title`: "詳細設計書"

**テストデータ**:
```python
# モック対象
with patch('pathlib.Path.read_text') as mock_read_text:
    mock_read_text.return_value = "# 詳細設計書\n..."

    with patch.object(BasePhase, 'post_output') as mock_post_output:
        # execute() 実行
        result = design_phase.execute()

        # 検証
        assert mock_read_text.call_count == 1  # 1回のみ読み込み
        mock_post_output.assert_called_once()
        args, kwargs = mock_post_output.call_args
        assert kwargs['title'] == "詳細設計書"
        assert kwargs['output_content'] == "# 詳細設計書\n..."
```

---

#### テストケース 2-2: design_execute_正常系_戦略判断の保存後に投稿

**目的**: 戦略判断の保存（94-95行目）後に成果物投稿が実行されることを検証

**前提条件**:
- Phase 2の実行が正常に完了している
- `design.md` ファイルが生成されている
- `_extract_design_decisions()` が戦略判断を返す

**入力**:
- `design_content`: 戦略判断を含む `design.md` の内容
- `decisions`: `{'implementation_strategy': 'EXTEND', 'test_strategy': 'UNIT_INTEGRATION'}`

**期待結果**:
- `metadata.save()` が呼ばれた後に `post_output()` が呼ばれる
- 実行順序:
  1. `_extract_design_decisions()` → 2. `metadata.save()` → 3. `post_output()`

**テストデータ**:
```python
# モック対象
call_order = []

with patch.object(DesignPhase, '_extract_design_decisions', return_value={'implementation_strategy': 'EXTEND'}):
    with patch.object(MetadataManager, 'save', side_effect=lambda: call_order.append('metadata.save')):
        with patch.object(BasePhase, 'post_output', side_effect=lambda **kwargs: call_order.append('post_output')):
            # execute() 実行
            result = design_phase.execute()

            # 検証
            assert call_order == ['metadata.save', 'post_output']
```

---

### 2.3 Phase 3: TestScenarioPhase.execute()

#### テストケース 3-1: test_scenario_execute_正常系_成果物投稿成功

**目的**: Phase 3が正常に完了した場合、成果物がGitHub Issueに投稿されることを検証

**前提条件**:
- Phase 3の実行が正常に完了している
- `test-scenario.md` ファイルが生成されている

**入力**:
- `output_file`: `.ai-workflow/issue-310/03_test_scenario/output/test-scenario.md`

**期待結果**:
- `post_output()` メソッドが呼び出される
- `post_output()` の引数:
  - `output_content`: `test-scenario.md` の内容
  - `title`: "テストシナリオ"

**テストデータ**:
```python
# モック対象
with patch.object(BasePhase, 'post_output') as mock_post_output:
    # execute() 実行
    result = test_scenario_phase.execute()

    # 検証
    mock_post_output.assert_called_once()
    args, kwargs = mock_post_output.call_args
    assert kwargs['title'] == "テストシナリオ"
```

---

### 2.4 Phase 4: ImplementationPhase.execute()

#### テストケース 4-1: implementation_execute_正常系_成果物投稿成功

**目的**: Phase 4が正常に完了した場合、成果物がGitHub Issueに投稿されることを検証

**前提条件**:
- Phase 4の実行が正常に完了している
- `implementation.md` ファイルが生成されている

**入力**:
- `output_file`: `.ai-workflow/issue-310/04_implementation/output/implementation.md`

**期待結果**:
- `post_output()` メソッドが呼び出される
- `post_output()` の引数:
  - `output_content`: `implementation.md` の内容
  - `title`: "実装ログ"

**テストデータ**:
```python
# モック対象
with patch.object(BasePhase, 'post_output') as mock_post_output:
    # execute() 実行
    result = implementation_phase.execute()

    # 検証
    mock_post_output.assert_called_once()
    args, kwargs = mock_post_output.call_args
    assert kwargs['title'] == "実装ログ"
```

---

### 2.5 Phase 5: TestingPhase.execute()

#### テストケース 5-1: testing_execute_正常系_成果物投稿成功

**目的**: Phase 5が正常に完了した場合、成果物がGitHub Issueに投稿されることを検証

**前提条件**:
- Phase 5の実行が正常に完了している
- `test-result.md` ファイルが生成されている

**入力**:
- `output_file`: `.ai-workflow/issue-310/05_testing/output/test-result.md`

**期待結果**:
- `post_output()` メソッドが呼び出される
- `post_output()` の引数:
  - `output_content`: `test-result.md` の内容
  - `title`: "テスト結果"

**テストデータ**:
```python
# モック対象
with patch.object(BasePhase, 'post_output') as mock_post_output:
    # execute() 実行
    result = testing_phase.execute()

    # 検証
    mock_post_output.assert_called_once()
    args, kwargs = mock_post_output.call_args
    assert kwargs['title'] == "テスト結果"
```

---

### 2.6 Phase 7: ReportPhase.execute()

#### テストケース 7-1: report_execute_確認_既存実装の動作検証

**目的**: Phase 7で既に実装されている `post_output()` 呼び出しが正しく動作することを確認

**前提条件**:
- Phase 7の実行が正常に完了している
- `report.md` ファイルが生成されている
- 98-106行目で既に `post_output()` が実装されている

**入力**:
- `output_file`: `.ai-workflow/issue-310/07_report/output/report.md`

**期待結果**:
- `post_output()` メソッドが呼び出される
- `post_output()` の引数:
  - `output_content`: `report.md` の内容
  - `title`: "最終レポート"

**テストデータ**:
```python
# モック対象
with patch.object(BasePhase, 'post_output') as mock_post_output:
    # execute() 実行
    result = report_phase.execute()

    # 検証
    mock_post_output.assert_called_once()
    args, kwargs = mock_post_output.call_args
    assert kwargs['title'] == "最終レポート"
```

---

### 2.7 共通エラーハンドリング

#### テストケース E-1: 全フェーズ_異常系_例外スロー時のWARNINGログ

**目的**: すべてのフェーズで `post_output()` が例外をスローした場合、WARNING ログが出力されることを検証

**前提条件**:
- 各フェーズの実行が正常に完了している
- 成果物ファイルが生成されている
- `BasePhase.post_output()` が例外をスローする

**入力**:
- 各フェーズの `output_file`
- `BasePhase.post_output()` が `Exception("Test Exception")` をスロー

**期待結果**:
- WARNING ログが出力される: `[WARNING] 成果物のGitHub投稿に失敗しました: Test Exception`
- `execute()` メソッドが `success=True` を返す

**テストデータ**:
```python
# すべてのフェーズで共通のテスト
phases = [
    requirements_phase,
    design_phase,
    test_scenario_phase,
    implementation_phase,
    testing_phase,
    report_phase
]

for phase in phases:
    with patch.object(BasePhase, 'post_output', side_effect=Exception("Test Exception")):
        with patch('builtins.print') as mock_print:
            # execute() 実行
            result = phase.execute()

            # 検証
            mock_print.assert_any_call("[WARNING] 成果物のGitHub投稿に失敗しました: Test Exception")
            assert result['success'] is True
```

---

## 3. Integrationテストシナリオ

### 3.1 BasePhase.post_output() → GitHubClient.post_comment() 統合フロー

#### シナリオ 3.1-1: 成果物投稿_正常系_GitHub API成功

**目的**: `BasePhase.post_output()` から `GitHubClient.post_comment()` を経由してGitHub APIに成果物が正常に投稿されることを検証

**前提条件**:
- GitHub APIアクセス用のトークンが設定されている
- GitHub APIが正常にアクセス可能である
- テスト用のGitHub Issueが存在する（例: Issue #310）

**テスト手順**:
1. Phase 1の `execute()` メソッドを実行
2. `requirements.md` が生成される
3. `post_output(output_content=requirements_content, title="要件定義書")` が呼ばれる
4. `GitHubClient.post_comment(issue_number=310, body=formatted_comment)` が呼ばれる
5. GitHub API `POST /repos/{owner}/{repo}/issues/310/comments` が呼ばれる

**期待結果**:
- GitHub Issue #310に新しいコメントが投稿される
- コメントの内容:
  - タイトル: "要件定義書"
  - 本文: `requirements.md` の内容
  - フッター: "Phase: requirements"

**確認項目**:
- [ ] GitHub Issueにコメントが投稿されている
- [ ] コメントのタイトルが "要件定義書" である
- [ ] コメントの本文が `requirements.md` の内容と一致する
- [ ] コメントのフッターに "Phase: requirements" が含まれる
- [ ] HTTP レスポンスが 201 Created である

**テストデータ**:
```python
# 実環境テスト（モックなし）
# テスト用GitHub Issue: #310

# Phase 1を実行
requirements_phase = RequirementsPhase(issue_number=310)
result = requirements_phase.execute()

# GitHub APIから投稿されたコメントを取得
github_client = GitHubClient()
comments = github_client.get_comments(issue_number=310)

# 最新コメントを検証
latest_comment = comments[-1]
assert "要件定義書" in latest_comment['body']
assert "Phase: requirements" in latest_comment['body']
```

---

#### シナリオ 3.1-2: 成果物投稿_異常系_GitHub APIレート制限

**目的**: GitHub APIがレート制限エラーを返した場合、WARNING ログが出力され、ワークフローが継続することを検証

**前提条件**:
- GitHub APIアクセス用のトークンが設定されている
- GitHub APIがレート制限エラー（HTTP 403 Forbidden, rate limit exceeded）を返す

**テスト手順**:
1. Phase 1の `execute()` メソッドを実行
2. `post_output()` が呼ばれる
3. `GitHubClient.post_comment()` が GitHub API を呼び出す
4. GitHub API が HTTP 403 エラーを返す

**期待結果**:
- WARNING ログが出力される: `[WARNING] 成果物のGitHub投稿に失敗しました: ...`
- `execute()` メソッドが `success=True` を返す（ワークフロー継続）

**確認項目**:
- [ ] WARNING ログが出力されている
- [ ] `execute()` が `success=True` を返す
- [ ] ワークフローが継続する（次のフェーズに進める）

**テストデータ**:
```python
# GitHub APIレート制限をシミュレート
with patch.object(GitHubClient, 'post_comment', side_effect=Exception("API rate limit exceeded")):
    with patch('builtins.print') as mock_print:
        # Phase 1を実行
        result = requirements_phase.execute()

        # 検証
        mock_print.assert_any_call(contains="[WARNING] 成果物のGitHub投稿に失敗しました")
        assert result['success'] is True
```

---

#### シナリオ 3.1-3: 成果物投稿_異常系_ネットワーク障害

**目的**: ネットワーク障害が発生した場合、WARNING ログが出力され、ワークフローが継続することを検証

**前提条件**:
- ネットワークエラーが発生する（タイムアウト、接続エラー等）

**テスト手順**:
1. Phase 1の `execute()` メソッドを実行
2. `post_output()` が呼ばれる
3. `GitHubClient.post_comment()` が GitHub API を呼び出す
4. ネットワークエラー（ConnectionError, Timeout等）が発生

**期待結果**:
- WARNING ログが出力される
- `execute()` メソッドが `success=True` を返す

**確認項目**:
- [ ] WARNING ログが出力されている
- [ ] `execute()` が `success=True` を返す
- [ ] ワークフローが継続する

**テストデータ**:
```python
# ネットワークエラーをシミュレート
with patch.object(GitHubClient, 'post_comment', side_effect=ConnectionError("Network unreachable")):
    with patch('builtins.print') as mock_print:
        # Phase 1を実行
        result = requirements_phase.execute()

        # 検証
        mock_print.assert_any_call(contains="[WARNING] 成果物のGitHub投稿に失敗しました")
        assert result['success'] is True
```

---

### 3.2 全フェーズ統合テスト

#### シナリオ 3.2-1: 全フェーズ実行_正常系_すべての成果物が投稿される

**目的**: 全フェーズ（1, 2, 3, 4, 5, 7）を順次実行した場合、すべての成果物がGitHub Issueに投稿されることを検証

**前提条件**:
- GitHub APIアクセス用のトークンが設定されている
- テスト用のGitHub Issueが存在する
- 全フェーズが正常に実行可能である

**テスト手順**:
1. Phase 1 (requirements) を実行 → "要件定義書" 投稿
2. Phase 2 (design) を実行 → "詳細設計書" 投稿
3. Phase 3 (test_scenario) を実行 → "テストシナリオ" 投稿
4. Phase 4 (implementation) を実行 → "実装ログ" 投稿
5. Phase 5 (testing) を実行 → "テスト結果" 投稿
6. Phase 7 (report) を実行 → "最終レポート" 投稿

**期待結果**:
- GitHub Issueに6つのコメントが投稿される
- 各コメントのタイトルが正しい
- 各コメントの本文が対応する成果物の内容と一致する

**確認項目**:
- [ ] 6つのコメントが投稿されている
- [ ] コメント1: タイトル "要件定義書"
- [ ] コメント2: タイトル "詳細設計書"
- [ ] コメント3: タイトル "テストシナリオ"
- [ ] コメント4: タイトル "実装ログ"
- [ ] コメント5: タイトル "テスト結果"
- [ ] コメント6: タイトル "最終レポート"

**テストデータ**:
```python
# 実環境テスト（モックなし）
# テスト用GitHub Issue: #310

# 全フェーズを順次実行
phases = [
    RequirementsPhase(issue_number=310),
    DesignPhase(issue_number=310),
    TestScenarioPhase(issue_number=310),
    ImplementationPhase(issue_number=310),
    TestingPhase(issue_number=310),
    ReportPhase(issue_number=310)
]

expected_titles = [
    "要件定義書",
    "詳細設計書",
    "テストシナリオ",
    "実装ログ",
    "テスト結果",
    "最終レポート"
]

# 各フェーズを実行
for phase in phases:
    result = phase.execute()
    assert result['success'] is True

# GitHub APIから投稿されたコメントを取得
github_client = GitHubClient()
comments = github_client.get_comments(issue_number=310)

# 最新6件のコメントを検証
latest_comments = comments[-6:]
for i, comment in enumerate(latest_comments):
    assert expected_titles[i] in comment['body']
```

---

### 3.3 UTF-8エンコーディング統合テスト

#### シナリオ 3.3-1: 日本語成果物_正常系_文字化けなし

**目的**: 日本語を含む成果物がUTF-8エンコーディングで正しく読み込まれ、GitHub Issueに文字化けせずに投稿されることを検証

**前提条件**:
- 成果物ファイルに日本語が含まれている
- ファイルがUTF-8エンコーディングで保存されている

**テスト手順**:
1. Phase 1を実行（日本語を含む `requirements.md` を生成）
2. `output_file.read_text(encoding='utf-8')` で読み込み
3. `post_output()` で投稿
4. GitHub Issueに投稿されたコメントを確認

**期待結果**:
- GitHub Issueに投稿されたコメントに日本語が正しく表示される
- 文字化けが発生しない

**確認項目**:
- [ ] 日本語が正しく表示されている
- [ ] 特殊文字（例: 「」、『』、・）が正しく表示されている
- [ ] 改行が正しく処理されている

**テストデータ**:
```python
# 日本語を含む成果物を生成
requirements_content = """
# 要件定義書

## 1. 概要

現在のAI駆動開発自動化ワークフローでは、Phase 6（documentation）のみが成果物をGitHub Issueコメントに投稿している。

### 1.2 目的

全フェーズで成果物をGitHub Issueコメントに投稿することで、以下を実現する：

- **可視性の向上**: GitHub Issue上でワークフロー全体の進捗と成果物を即座に確認可能
- **レビュー効率化**: 成果物のレビューがGitHub上で容易に実施可能
"""

# Phase 1を実行
requirements_phase = RequirementsPhase(issue_number=310)
result = requirements_phase.execute()

# GitHub APIから投稿されたコメントを取得
github_client = GitHubClient()
comments = github_client.get_comments(issue_number=310)
latest_comment = comments[-1]

# 日本語が正しく含まれることを確認
assert "要件定義書" in latest_comment['body']
assert "AI駆動開発自動化ワークフロー" in latest_comment['body']
assert "可視性の向上" in latest_comment['body']
assert "レビュー効率化" in latest_comment['body']
```

---

## 4. テストデータ

### 4.1 正常データ

#### 4.1.1 Phase 1: requirements.md

```markdown
# 要件定義書

**Issue**: #310
**タイトル**: [ai-workflow] feat: 全フェーズの成果物をGitHub Issueコメントに投稿する機能を追加
**作成日**: 2025-10-10

## 1. 概要

### 1.1 背景

現在のAI駆動開発自動化ワークフローでは、Phase 6（documentation）のみが成果物をGitHub Issueコメントに投稿している。

### 1.2 目的

全フェーズで成果物をGitHub Issueコメントに投稿することで、可視性の向上を実現する。
```

#### 4.1.2 Phase 2: design.md

```markdown
# 詳細設計書

**Issue**: #310

## 1. アーキテクチャ設計

### 実装戦略: EXTEND

### テスト戦略: UNIT_INTEGRATION

## 2. 詳細設計

各フェーズの `execute()` メソッドに成果物投稿処理を追加する。
```

### 4.2 異常データ

#### 4.2.1 存在しないファイル

```python
# ファイルが存在しないケース
output_file = Path("/nonexistent/path/requirements.md")
```

#### 4.2.2 空ファイル

```python
# 空の成果物ファイル
output_file.write_text("", encoding='utf-8')
```

### 4.3 境界値データ

#### 4.3.1 大容量ファイル（将来対応）

```python
# 65,536文字を超える成果物（GitHub Issueコメントの上限）
large_content = "a" * 70000
```

**注**: 今回は大容量ファイルの対応はスコープ外。将来対応として、WARNING表示してスキップする処理を追加予定。

---

## 5. テスト環境要件

### 5.1 ローカルテスト環境

- **Python**: 3.8以上
- **必要なパッケージ**:
  - `pytest` (Unitテスト実行)
  - `pytest-mock` (モック機能)
  - `requests` (GitHub API呼び出し)
- **環境変数**:
  - `GITHUB_TOKEN`: GitHub APIアクセス用トークン（Integrationテスト用）
  - `GITHUB_REPOSITORY`: テスト対象リポジトリ（例: `tielec/infrastructure-as-code`）

### 5.2 CI/CD環境

- **GitHub Actions**: 自動テスト実行
- **テスト用GitHub Issue**: 事前に作成しておく（例: Issue #310）
- **Secrets**: `GITHUB_TOKEN` をGitHub Secretsに設定

### 5.3 モック/スタブの使用

#### Unitテストでモック化するコンポーネント:

| コンポーネント | モック理由 |
|--------------|----------|
| `BasePhase.post_output()` | GitHub API呼び出しを回避し、単体テストを高速化 |
| `GitHubClient.post_comment()` | 実際のGitHub APIを呼ばずに動作を検証 |
| `pathlib.Path.read_text()` | ファイルI/Oを回避し、テストデータを制御 |

#### Integrationテストでモック化しないコンポーネント:

- `BasePhase.post_output()`
- `GitHubClient.post_comment()`
- GitHub API

**理由**: 実際の統合動作を検証するため、モックを使用せず実環境でテストする。

---

## 6. 品質ゲート（Phase 3）

### 6.1 Phase 2の戦略に沿ったテストシナリオである

- [x] **UNIT_INTEGRATION戦略を採用**: Unitテストシナリオ（2.1-2.7）とIntegrationテストシナリオ（3.1-3.3）を作成
- [x] **各テスト種別の目的が明確**: Unitテストは各メソッドの単体動作を検証、Integrationテストは統合フローを検証
- [x] **テスト戦略の根拠が明確**: 設計書のテスト戦略（UNIT_INTEGRATION）に準拠

### 6.2 主要な正常系がカバーされている

- [x] **Phase 1-5, 7の成果物投稿成功ケース**: テストケース 1-1, 2-1, 3-1, 4-1, 5-1, 7-1
- [x] **Phase 2の既存変数再利用**: テストケース 2-1
- [x] **GitHub API正常レスポンス**: シナリオ 3.1-1
- [x] **全フェーズ統合実行**: シナリオ 3.2-1
- [x] **UTF-8エンコーディング**: テストケース 1-4、シナリオ 3.3-1

### 6.3 主要な異常系がカバーされている

- [x] **GitHub API投稿失敗**: テストケース 1-2
- [x] **成果物ファイル不存在**: テストケース 1-3
- [x] **例外スロー時のWARNINGログ**: テストケース E-1
- [x] **GitHub APIレート制限**: シナリオ 3.1-2
- [x] **ネットワーク障害**: シナリオ 3.1-3

### 6.4 期待結果が明確である

- [x] **各テストケースに期待結果を記載**: すべてのテストケースに「期待結果」セクションを記述
- [x] **確認項目のチェックリスト**: Integrationテストシナリオにチェックリスト形式で記載
- [x] **具体的な検証コード**: テストデータセクションに `assert` 文を使用した検証コードを記載

---

## 7. テスト実行計画

### 7.1 Unitテスト実行

```bash
# すべてのUnitテストを実行
pytest tests/unit/ -v

# 特定のフェーズのみ実行
pytest tests/unit/test_requirements_phase.py -v
pytest tests/unit/test_design_phase.py -v
```

### 7.2 Integrationテスト実行

```bash
# すべてのIntegrationテストを実行（実環境）
pytest tests/integration/ -v --github-token=$GITHUB_TOKEN

# 特定のシナリオのみ実行
pytest tests/integration/test_github_posting.py::test_post_output_success -v
```

### 7.3 テスト実行順序

1. **Unitテスト** → 2. **Integrationテスト** → 3. **全フェーズ統合テスト**

**理由**: Unitテストで基本動作を検証した後、Integrationテストで統合動作を確認し、最後に全フェーズを通しで実行する。

---

## 8. テストカバレッジ目標

### 8.1 コードカバレッジ

- **目標**: 追加コード（各フェーズの成果物投稿処理）のカバレッジ 100%
- **測定方法**: `pytest-cov` を使用

```bash
pytest tests/ --cov=scripts/ai-workflow/phases --cov-report=html
```

### 8.2 要件カバレッジ

| 要件ID | 要件名 | カバーするテストケース |
|--------|--------|---------------------|
| FR-01 | Phase 1の成果物投稿機能 | テストケース 1-1, 1-2, 1-3, 1-4 |
| FR-02 | Phase 2の成果物投稿機能 | テストケース 2-1, 2-2 |
| FR-03 | Phase 3の成果物投稿機能 | テストケース 3-1 |
| FR-04 | Phase 4の成果物投稿機能 | テストケース 4-1 |
| FR-05 | Phase 5の成果物投稿機能 | テストケース 5-1 |
| FR-06 | Phase 7の成果物投稿機能 | テストケース 7-1 |
| FR-07 | エラーハンドリング | テストケース 1-2, E-1, シナリオ 3.1-2, 3.1-3 |
| FR-08 | UTF-8エンコーディング対応 | テストケース 1-4, シナリオ 3.3-1 |

**カバレッジ**: 全機能要件（FR-01～FR-08）がテストケースでカバーされている ✅

---

## 9. テスト結果の記録

### 9.1 テスト結果フォーマット

```markdown
# テスト結果

**実行日**: 2025-10-10
**実行者**: [氏名]

## Unitテスト結果

| テストケース | 結果 | 備考 |
|------------|------|------|
| 1-1 | PASS | - |
| 1-2 | PASS | - |
| ... | ... | ... |

## Integrationテスト結果

| シナリオ | 結果 | 備考 |
|---------|------|------|
| 3.1-1 | PASS | - |
| 3.1-2 | PASS | - |
| ... | ... | ... |

## カバレッジ

- コードカバレッジ: 100%
- 要件カバレッジ: 100%
```

---

## 10. リスクと対策

### 10.1 テストリスク

| リスク | 影響度 | 対策 |
|--------|--------|------|
| GitHub APIレート制限によりIntegrationテストが失敗 | 中 | テスト実行頻度を制限し、必要に応じてモックに切り替え |
| テスト用GitHub Issueが大量のコメントで埋まる | 低 | テスト後にコメントを削除するクリーンアップ処理を追加 |
| UTF-8エンコーディングの環境依存性 | 低 | CI/CD環境でUTF-8を明示的に設定 |

---

## 11. 参照ドキュメント

- **要件定義書**: `.ai-workflow/issue-310/01_requirements/output/requirements.md`
- **詳細設計書**: `.ai-workflow/issue-310/02_design/output/design.md`
- **既存実装**:
  - `scripts/ai-workflow/phases/documentation.py` (Phase 6, 96-103行目)
  - `scripts/ai-workflow/phases/report.py` (Phase 7, 98-106行目)
- **基底クラス**: `scripts/ai-workflow/phases/base_phase.py` (post_output: 218-256行目)

---

**以上**
