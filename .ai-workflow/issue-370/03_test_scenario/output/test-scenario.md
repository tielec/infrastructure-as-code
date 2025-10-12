# テストシナリオ - Issue #370

**Issue番号**: #370
**タイトル**: [IMPROVEMENT] AIワークフロー: GitHub Issue進捗コメント最適化（ページ重量化対策）
**作成日**: 2025-01-15
**テストシナリオ作成者**: AI Workflow - Test Scenario Phase
**Planning Document参照**: `.ai-workflow/issue-370/00_planning/output/planning.md`
**Requirements Document参照**: `.ai-workflow/issue-370/01_requirements/output/requirements.md`
**Design Document参照**: `.ai-workflow/issue-370/02_design/output/design.md`

---

## 0. テスト戦略サマリー

### 選択されたテスト戦略

**INTEGRATION_ONLY**

Phase 2（Design Phase）で決定されたテスト戦略に基づき、統合テストのみを実施します。

### テスト戦略の根拠（Design Documentより引用）

- **UNIT_ONLYを選ばない理由**: GitHub APIとの実際の連携動作を確認する必要があるため、モックテストでは不十分
- **INTEGRATION_ONLYを選ぶ理由**:
  - 主な機能はGitHub APIとの統合（コメント作成・編集）
  - 実際のIssueに対する進捗コメントの動作確認が必須
  - エンドツーエンドで進捗フローが動作することを保証したい
  - GitHub APIのEdit Comment機能の実際の動作を確認する必要がある
- **BDDを選ばない理由**: エンドユーザー向け機能ではなく、ワークフロー内部の最適化施策のため

### テスト対象の範囲

1. **GitHubClient.create_or_update_progress_comment()** と GitHub API（Create Comment / Edit Comment）の統合
2. **MetadataManager** と `metadata.json` ファイルシステムの統合
3. **BasePhase.post_progress()** から GitHubClient / MetadataManager への統合フロー
4. **エンドツーエンド**: BasePhase → GitHubClient → GitHub API → MetadataManager の全体フロー

### テストの目的

- GitHub APIとの実際の連携動作を確認
- 進捗コメントの作成・更新フローが正しく動作することを保証
- エラーハンドリング（GitHub API失敗時のフォールバック）の動作確認
- メタデータの永続化と取得が正しく動作することを確認

---

## 1. 統合テストシナリオ

### 1.1. GitHub API統合テスト

#### シナリオ1-1: 初回進捗コメント作成（GitHubClient → GitHub API Create Comment）

**シナリオID**: INT-001
**優先度**: 高
**対応する要件**: FR-001, FR-002, AC-001, AC-003

##### 目的
GitHubClient.create_or_update_progress_comment() が GitHub API（Create Comment）と正しく統合され、新規コメントが作成できることを検証する。

##### 前提条件
- GitHub Personal Access Token（PAT）が環境変数 `GITHUB_TOKEN` に設定されている
- 実際のGitHub Issue（例: #370）が存在する
- メタデータに `github_integration.progress_comment_id` が存在しない（初回実行）
- GitHubClientインスタンスが初期化されている
- MetadataManagerインスタンスが初期化されている

##### テスト手順

1. **準備**: メタデータから `progress_comment_id` が存在しないことを確認
   ```python
   metadata_manager = MetadataManager(issue_number=370)
   assert metadata_manager.get_progress_comment_id() is None
   ```

2. **実行**: `create_or_update_progress_comment()` を呼び出し
   ```python
   github_client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
   content = "## 🤖 AI Workflow - 進捗状況\n\n### 全体進捗\n\n- 🔄 Phase 0: Planning - IN PROGRESS"

   result = github_client.create_or_update_progress_comment(
       issue_number=370,
       content=content,
       metadata_manager=metadata_manager
   )
   ```

3. **検証1**: 戻り値の確認
   ```python
   assert 'comment_id' in result
   assert 'comment_url' in result
   assert isinstance(result['comment_id'], int)
   assert result['comment_url'].startswith('https://github.com/')
   ```

4. **検証2**: GitHub Issue上でコメントが作成されたことを確認
   - GitHub UIでIssue #370を開く
   - 新しいコメントが投稿されていることを目視確認
   - コメント内容が `content` と一致することを確認

5. **検証3**: メタデータに `progress_comment_id` が保存されたことを確認
   ```python
   saved_comment_id = metadata_manager.get_progress_comment_id()
   assert saved_comment_id == result['comment_id']
   ```

6. **検証4**: `metadata.json` ファイルに正しく保存されていることを確認
   ```python
   with open('.ai-workflow/issue-370/metadata.json', 'r') as f:
       metadata = json.load(f)

   assert 'github_integration' in metadata
   assert metadata['github_integration']['progress_comment_id'] == result['comment_id']
   assert metadata['github_integration']['progress_comment_url'] == result['comment_url']
   ```

##### 期待結果
- GitHub API Create Comment が成功（HTTPステータス 201 Created）
- コメントIDとURLが返却される
- メタデータに `progress_comment_id` と `progress_comment_url` が保存される
- GitHub Issue上に新しいコメントが1つ作成される

##### 確認項目
- [ ] GitHub APIのCreate Commentが呼ばれたか
- [ ] コメントIDが返却されたか
- [ ] コメントURLが返却されたか
- [ ] メタデータにコメントIDが保存されたか
- [ ] メタデータにコメントURLが保存されたか
- [ ] GitHub Issue上にコメントが表示されているか
- [ ] コメント内容が期待通りのMarkdownフォーマットか

---

#### シナリオ1-2: 既存進捗コメント更新（GitHubClient → GitHub API Edit Comment）

**シナリオID**: INT-002
**優先度**: 高
**対応する要件**: FR-001, FR-002, AC-002

##### 目的
GitHubClient.create_or_update_progress_comment() が GitHub API（Edit Comment）と正しく統合され、既存コメントが更新できることを検証する。

##### 前提条件
- GitHub Personal Access Token（PAT）が環境変数 `GITHUB_TOKEN` に設定されている
- 実際のGitHub Issue（例: #370）が存在する
- **メタデータに `github_integration.progress_comment_id` が存在する**（INT-001で作成済み）
- 既存の進捗コメントがGitHub Issue上に存在する
- GitHubClientインスタンスが初期化されている
- MetadataManagerインスタンスが初期化されている

##### テスト手順

1. **準備**: メタデータから既存の `progress_comment_id` を取得
   ```python
   metadata_manager = MetadataManager(issue_number=370)
   existing_comment_id = metadata_manager.get_progress_comment_id()
   assert existing_comment_id is not None
   ```

2. **準備**: GitHub API経由で既存コメントの内容を取得（更新前の内容を記録）
   ```python
   github_client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
   repo = github_client.repository
   existing_comment = repo.get_issue_comment(existing_comment_id)
   old_body = existing_comment.body
   ```

3. **実行**: `create_or_update_progress_comment()` を呼び出し（更新内容）
   ```python
   new_content = """## 🤖 AI Workflow - 進捗状況

### 全体進捗

- ✅ Phase 0: Planning - COMPLETED (2025-01-15 10:30)
- 🔄 Phase 1: Requirements - IN PROGRESS (開始: 2025-01-15 11:00)

### 現在のフェーズ: Phase 1 (Requirements)

**ステータス**: IN PROGRESS
**開始時刻**: 2025-01-15 11:00:00
**試行回数**: 1/3

---
*最終更新: 2025-01-15 11:00:30*
"""

   result = github_client.create_or_update_progress_comment(
       issue_number=370,
       content=new_content,
       metadata_manager=metadata_manager
   )
   ```

4. **検証1**: 戻り値の確認（コメントIDが変わっていないこと）
   ```python
   assert result['comment_id'] == existing_comment_id
   assert 'comment_url' in result
   ```

5. **検証2**: GitHub API経由で既存コメントが更新されたことを確認
   ```python
   updated_comment = repo.get_issue_comment(existing_comment_id)
   assert updated_comment.body == new_content
   assert updated_comment.body != old_body
   ```

6. **検証3**: GitHub Issue上でコメントが更新されたことを目視確認
   - GitHub UIでIssue #370を開く
   - 既存コメントが更新されていることを確認（新規コメントは作成されていない）
   - コメント内容が `new_content` と一致することを確認

7. **検証4**: コメント数が増えていないことを確認
   ```python
   issue = repo.get_issue(370)
   all_comments = list(issue.get_comments())

   # 進捗コメント以外のコメントも含む可能性があるため、
   # 進捗コメントが1つのみであることを確認
   progress_comments = [c for c in all_comments if '🤖 AI Workflow - 進捗状況' in c.body]
   assert len(progress_comments) == 1
   assert progress_comments[0].id == existing_comment_id
   ```

##### 期待結果
- GitHub API Edit Comment が成功（HTTPステータス 200 OK）
- 既存のコメントIDが返却される（新規コメントは作成されない）
- 既存コメントの内容が新しい内容に更新される
- GitHub Issue上のコメント数が増えない（1つのまま）

##### 確認項目
- [ ] GitHub APIのEdit Commentが呼ばれたか
- [ ] 既存のコメントIDが返却されたか（新規作成されていないか）
- [ ] 既存コメントの内容が更新されたか
- [ ] 新規コメントが作成されていないか
- [ ] GitHub Issue上の進捗コメントが1つのみか
- [ ] コメント内容が期待通りのMarkdownフォーマットか

---

#### シナリオ1-3: GitHub API失敗時のフォールバック（Edit Comment失敗 → Create Comment）

**シナリオID**: INT-003
**優先度**: 高
**対応する要件**: FR-006, AC-005

##### 目的
GitHub API Edit Comment が失敗した場合に、自動的に新規コメント作成にフォールバックすることを検証する。

##### 前提条件
- GitHub Personal Access Token（PAT）が環境変数 `GITHUB_TOKEN` に設定されている
- 実際のGitHub Issue（例: #370）が存在する
- **メタデータに無効な `progress_comment_id` が存在する**（例: 削除済みのコメントID、または存在しないID）
- GitHubClientインスタンスが初期化されている
- MetadataManagerインスタンスが初期化されている

##### テスト手順

1. **準備**: メタデータに無効なコメントIDを設定
   ```python
   metadata_manager = MetadataManager(issue_number=370)

   # 存在しないコメントIDを設定（例: 999999999）
   metadata_manager.save_progress_comment_id(
       comment_id=999999999,
       comment_url="https://github.com/.../issues/370#issuecomment-999999999"
   )

   invalid_comment_id = metadata_manager.get_progress_comment_id()
   assert invalid_comment_id == 999999999
   ```

2. **実行**: `create_or_update_progress_comment()` を呼び出し
   ```python
   github_client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
   content = "## 🤖 AI Workflow - 進捗状況\n\n### 全体進捗\n\n- 🔄 Phase 0: Planning - IN PROGRESS"

   result = github_client.create_or_update_progress_comment(
       issue_number=370,
       content=content,
       metadata_manager=metadata_manager
   )
   ```

3. **検証1**: Edit Comment APIが404エラーで失敗することを確認（ログ出力）
   - ログ出力を確認: `[WARNING] GitHub Edit Comment APIエラー: Not Found (コメントID: 999999999)`
   - ログ出力を確認: `[INFO] フォールバック: 新規コメント作成`

4. **検証2**: フォールバックで新規コメントが作成されたことを確認
   ```python
   assert 'comment_id' in result
   assert result['comment_id'] != invalid_comment_id  # 新しいコメントIDが返される
   ```

5. **検証3**: GitHub Issue上で新規コメントが作成されたことを目視確認
   - GitHub UIでIssue #370を開く
   - 新しいコメントが投稿されていることを確認

6. **検証4**: メタデータが新しいコメントIDで更新されたことを確認
   ```python
   updated_comment_id = metadata_manager.get_progress_comment_id()
   assert updated_comment_id == result['comment_id']
   assert updated_comment_id != invalid_comment_id
   ```

##### 期待結果
- GitHub API Edit Comment が404エラーで失敗
- フォールバック処理が動作し、GitHub API Create Comment が成功
- 新しいコメントIDが返却される
- メタデータが新しいコメントIDで更新される
- ワークフローは継続する（エラーで中断しない）

##### 確認項目
- [ ] GitHub APIのEdit Commentが404エラーで失敗したか
- [ ] エラーログが出力されたか
- [ ] フォールバック処理が動作したか
- [ ] 新規コメントが作成されたか
- [ ] 新しいコメントIDが返却されたか
- [ ] メタデータが新しいコメントIDで更新されたか
- [ ] ワークフローが継続したか（例外が発生していないか）

---

### 1.2. メタデータ管理統合テスト

#### シナリオ2-1: メタデータへのコメントID保存（MetadataManager → ファイルシステム）

**シナリオID**: INT-004
**優先度**: 高
**対応する要件**: FR-003, AC-003

##### 目的
MetadataManager.save_progress_comment_id() が `metadata.json` ファイルに正しくコメントIDを保存できることを検証する。

##### 前提条件
- `.ai-workflow/issue-370/metadata.json` ファイルが存在する
- MetadataManagerインスタンスが初期化されている
- ファイルシステムへの書き込み権限がある

##### テスト手順

1. **準備**: 既存のメタデータを確認（`github_integration` セクションが存在しない状態）
   ```python
   metadata_manager = MetadataManager(issue_number=370)

   # 初期状態: github_integrationセクションが存在しない
   initial_comment_id = metadata_manager.get_progress_comment_id()
   assert initial_comment_id is None
   ```

2. **実行**: `save_progress_comment_id()` を呼び出し
   ```python
   test_comment_id = 123456789
   test_comment_url = "https://github.com/tielec/infrastructure-as-code/issues/370#issuecomment-123456789"

   metadata_manager.save_progress_comment_id(
       comment_id=test_comment_id,
       comment_url=test_comment_url
   )
   ```

3. **検証1**: メモリ上のメタデータに保存されたことを確認
   ```python
   saved_comment_id = metadata_manager.get_progress_comment_id()
   assert saved_comment_id == test_comment_id
   ```

4. **検証2**: ファイルシステムに保存されたことを確認
   ```python
   with open('.ai-workflow/issue-370/metadata.json', 'r') as f:
       metadata = json.load(f)

   assert 'github_integration' in metadata
   assert metadata['github_integration']['progress_comment_id'] == test_comment_id
   assert metadata['github_integration']['progress_comment_url'] == test_comment_url
   ```

5. **検証3**: 既存のメタデータフィールドが保持されていることを確認
   ```python
   # issue_numberなどの既存フィールドが保持されている
   assert 'issue_number' in metadata
   assert metadata['issue_number'] == 370

   # phasesなどの既存セクションが保持されている
   assert 'phases' in metadata
   ```

6. **検証4**: 新しいMetadataManagerインスタンスで読み込んでも取得できることを確認（永続化確認）
   ```python
   new_metadata_manager = MetadataManager(issue_number=370)
   loaded_comment_id = new_metadata_manager.get_progress_comment_id()
   assert loaded_comment_id == test_comment_id
   ```

##### 期待結果
- メタデータに `github_integration` セクションが追加される
- `progress_comment_id` と `progress_comment_url` が保存される
- 既存のメタデータフィールドが保持される（破壊されない）
- ファイルシステムに永続化される

##### 確認項目
- [ ] `github_integration`セクションが作成されたか
- [ ] `progress_comment_id`が保存されたか
- [ ] `progress_comment_url`が保存されたか
- [ ] 既存のメタデータフィールドが保持されているか
- [ ] ファイルシステムに永続化されたか
- [ ] 新しいインスタンスで読み込んでも取得できるか

---

#### シナリオ2-2: メタデータからのコメントID取得（後方互換性テスト）

**シナリオID**: INT-005
**優先度**: 中
**対応する要件**: FR-003, AC-008

##### 目的
`github_integration` セクションが存在しない既存のメタデータでも、正常に動作する（後方互換性）ことを検証する。

##### 前提条件
- `.ai-workflow/issue-370/metadata.json` ファイルが存在する
- **`github_integration` セクションが存在しない**（既存のメタデータ形式）
- MetadataManagerインスタンスが初期化されている

##### テスト手順

1. **準備**: メタデータから `github_integration` セクションを削除（既存メタデータの再現）
   ```python
   # metadata.jsonから github_integrationセクションを削除
   with open('.ai-workflow/issue-370/metadata.json', 'r') as f:
       metadata = json.load(f)

   if 'github_integration' in metadata:
       del metadata['github_integration']

   with open('.ai-workflow/issue-370/metadata.json', 'w') as f:
       json.dump(metadata, f, indent=2)
   ```

2. **実行**: `get_progress_comment_id()` を呼び出し
   ```python
   metadata_manager = MetadataManager(issue_number=370)
   comment_id = metadata_manager.get_progress_comment_id()
   ```

3. **検証1**: `None` が返却されることを確認
   ```python
   assert comment_id is None
   ```

4. **検証2**: エラーが発生しないことを確認（KeyError等が発生しない）
   ```python
   # 例外が発生せずに正常に終了すること
   # （assertでNoneが確認できていれば、エラーは発生していない）
   ```

5. **検証3**: 新規コメント作成として動作することを確認
   ```python
   # create_or_update_progress_comment()を呼び出した場合、
   # コメントIDがNoneなので新規コメント作成フローに進む
   github_client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
   content = "## 🤖 AI Workflow - 進捗状況\n\n### 全体進捗\n\n- 🔄 Phase 0: Planning - IN PROGRESS"

   result = github_client.create_or_update_progress_comment(
       issue_number=370,
       content=content,
       metadata_manager=metadata_manager
   )

   # 新規コメントが作成される
   assert 'comment_id' in result
   assert result['comment_id'] is not None
   ```

##### 期待結果
- `get_progress_comment_id()` が `None` を返す
- エラーが発生しない（KeyError、AttributeError等）
- 新規コメント作成フローが動作する

##### 確認項目
- [ ] `None`が返却されたか
- [ ] エラーが発生していないか（KeyError等）
- [ ] 新規コメント作成フローが動作したか
- [ ] 後方互換性が保たれているか

---

### 1.3. 進捗コメントフロー統合テスト（エンドツーエンド）

#### シナリオ3-1: BasePhaseからの進捗投稿（初回投稿フロー）

**シナリオID**: INT-006
**優先度**: 高
**対応する要件**: FR-001, FR-004, AC-001, AC-007

##### 目的
BasePhase.post_progress() から GitHubClient → MetadataManager への全体フローが正しく動作することを検証する（初回投稿）。

##### 前提条件
- GitHub Personal Access Token（PAT）が環境変数 `GITHUB_TOKEN` に設定されている
- 実際のGitHub Issue（例: #370）が存在する
- メタデータに `github_integration.progress_comment_id` が存在しない（初回実行）
- BasePhaseインスタンス（または継承クラス）が初期化されている

##### テスト手順

1. **準備**: メタデータの初期状態を確認
   ```python
   metadata_manager = MetadataManager(issue_number=370)
   initial_comment_id = metadata_manager.get_progress_comment_id()
   assert initial_comment_id is None
   ```

2. **実行**: `BasePhase.post_progress()` を呼び出し
   ```python
   # テスト用にPlanningPhaseを使用（BasePhaseを継承している）
   from scripts.ai_workflow.phases.planning_phase import PlanningPhase

   planning_phase = PlanningPhase(
       issue_number=370,
       issue_data={...},
       metadata_manager=metadata_manager,
       github_client=GitHubClient(token=os.getenv('GITHUB_TOKEN')),
       orchestrator_config={...}
   )

   # 進捗報告
   planning_phase.post_progress(
       status='in_progress',
       details='Planning フェーズを開始しました'
   )
   ```

3. **検証1**: ログ出力を確認
   - `[INFO] GitHub Issue #370 に進捗を投稿しました` が出力される

4. **検証2**: GitHub Issue上でコメントが作成されたことを確認
   - GitHub UIでIssue #370を開く
   - 新しい進捗コメントが投稿されていることを確認
   - コメント内容にフェーズ情報が含まれていることを確認
     - `Phase 0 (Planning)` が含まれている
     - `IN PROGRESS` ステータスが含まれている
     - `Planning フェーズを開始しました` が含まれている

5. **検証3**: メタデータにコメントIDが保存されたことを確認
   ```python
   saved_comment_id = metadata_manager.get_progress_comment_id()
   assert saved_comment_id is not None
   assert isinstance(saved_comment_id, int)
   ```

6. **検証4**: 既存のワークフローに影響がないことを確認
   ```python
   # post_progress()の呼び出し元（各フェーズ）は変更不要
   # 既存のシグネチャが保持されている
   # planning_phase.post_progress(status='completed')  # 既存の呼び出しが動作する
   ```

##### 期待結果
- BasePhase.post_progress() が正常に動作
- GitHubClient.create_or_update_progress_comment() が呼ばれる
- GitHub Issue上に進捗コメントが1つ作成される
- メタデータにコメントIDが保存される
- 既存のワークフローに影響がない

##### 確認項目
- [ ] BasePhase.post_progress()が正常に動作したか
- [ ] GitHubClient.create_or_update_progress_comment()が呼ばれたか
- [ ] GitHub Issue上にコメントが作成されたか
- [ ] コメント内容が期待通りのフォーマットか
- [ ] メタデータにコメントIDが保存されたか
- [ ] 既存のワークフローに影響がないか（シグネチャが変わっていないか）

---

#### シナリオ3-2: BasePhaseからの進捗投稿（更新フロー）

**シナリオID**: INT-007
**優先度**: 高
**対応する要件**: FR-001, FR-004, AC-002, AC-007

##### 目的
BasePhase.post_progress() からの2回目以降の呼び出しで、既存コメントが更新されることを検証する。

##### 前提条件
- GitHub Personal Access Token（PAT）が環境変数 `GITHUB_TOKEN` に設定されている
- 実際のGitHub Issue（例: #370）が存在する
- **メタデータに `github_integration.progress_comment_id` が存在する**（INT-006で作成済み）
- **既存の進捗コメントがGitHub Issue上に存在する**
- BasePhaseインスタンス（または継承クラス）が初期化されている

##### テスト手順

1. **準備**: 既存のコメントIDを確認
   ```python
   metadata_manager = MetadataManager(issue_number=370)
   existing_comment_id = metadata_manager.get_progress_comment_id()
   assert existing_comment_id is not None
   ```

2. **準備**: GitHub Issue上のコメント数を記録
   ```python
   github_client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
   repo = github_client.repository
   issue = repo.get_issue(370)
   initial_comment_count = issue.comments
   ```

3. **実行**: `BasePhase.post_progress()` を再度呼び出し（フェーズ完了）
   ```python
   planning_phase = PlanningPhase(
       issue_number=370,
       issue_data={...},
       metadata_manager=metadata_manager,
       github_client=github_client,
       orchestrator_config={...}
   )

   # 進捗報告（完了）
   planning_phase.post_progress(
       status='completed',
       details='Planning フェーズが完了しました'
   )
   ```

4. **検証1**: ログ出力を確認
   - `[INFO] 進捗コメント更新: https://github.com/.../issues/370#issuecomment-...` が出力される

5. **検証2**: GitHub Issue上でコメントが更新されたことを目視確認
   - GitHub UIでIssue #370を開く
   - 既存のコメントが更新されていることを確認
   - コメント内容が最新状態に更新されていることを確認
     - `Phase 0 (Planning)` のステータスが `COMPLETED` に更新されている
     - `Planning フェーズが完了しました` が含まれている

6. **検証3**: コメント数が増えていないことを確認
   ```python
   updated_comment_count = issue.comments
   assert updated_comment_count == initial_comment_count  # コメント数は変わらない
   ```

7. **検証4**: メタデータのコメントIDが変わっていないことを確認
   ```python
   updated_comment_id = metadata_manager.get_progress_comment_id()
   assert updated_comment_id == existing_comment_id  # コメントIDは同じ
   ```

##### 期待結果
- BasePhase.post_progress() が正常に動作
- GitHubClient.create_or_update_progress_comment() が既存コメントを更新
- GitHub Issue上のコメント数が増えない（既存コメントが編集される）
- コメント内容が最新状態に更新される
- メタデータのコメントIDが変わらない

##### 確認項目
- [ ] BasePhase.post_progress()が正常に動作したか
- [ ] GitHubClient.create_or_update_progress_comment()が呼ばれたか
- [ ] 既存コメントが更新されたか（新規コメントは作成されていないか）
- [ ] コメント内容が最新状態に更新されたか
- [ ] GitHub Issue上のコメント数が増えていないか
- [ ] メタデータのコメントIDが変わっていないか

---

#### シナリオ3-3: 複数フェーズ実行時の進捗コメント統合（ワークフロー全体テスト）

**シナリオID**: INT-008
**優先度**: 高
**対応する要件**: FR-001, FR-004, FR-005, AC-001, AC-002, AC-006

##### 目的
複数のフェーズ（Phase 0, 1, 2）を連続実行した場合に、進捗コメントが1つのみ作成され、内容が逐次更新されることを検証する。

##### 前提条件
- GitHub Personal Access Token（PAT）が環境変数 `GITHUB_TOKEN` に設定されている
- 実際のGitHub Issue（例: #370）が存在する
- メタデータに `github_integration.progress_comment_id` が存在しない（初回実行）
- ワークフローが実行可能な状態である

##### テスト手順

1. **準備**: GitHub Issue上のコメント数を記録（初期状態）
   ```python
   github_client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
   repo = github_client.repository
   issue = repo.get_issue(370)
   initial_comment_count = issue.comments
   ```

2. **実行**: Phase 0（Planning）を実行
   ```python
   # Phase 0開始
   planning_phase = PlanningPhase(...)
   planning_phase.post_progress(status='in_progress', details='Planning開始')

   # Phase 0完了
   planning_phase.post_progress(status='completed', details='Planning完了')
   ```

3. **検証1**: Phase 0完了後のコメント数を確認
   ```python
   comment_count_after_phase0 = issue.comments
   assert comment_count_after_phase0 == initial_comment_count + 1  # 進捗コメントが1つ作成される
   ```

4. **実行**: Phase 1（Requirements）を実行
   ```python
   # Phase 1開始
   requirements_phase = RequirementsPhase(...)
   requirements_phase.post_progress(status='in_progress', details='Requirements開始')

   # Phase 1完了
   requirements_phase.post_progress(status='completed', details='Requirements完了')
   ```

5. **検証2**: Phase 1完了後のコメント数を確認（増えていないこと）
   ```python
   comment_count_after_phase1 = issue.comments
   assert comment_count_after_phase1 == comment_count_after_phase0  # コメント数は変わらない
   ```

6. **実行**: Phase 2（Design）を実行
   ```python
   # Phase 2開始
   design_phase = DesignPhase(...)
   design_phase.post_progress(status='in_progress', details='Design開始')

   # Phase 2完了
   design_phase.post_progress(status='completed', details='Design完了')
   ```

7. **検証3**: Phase 2完了後のコメント数を確認（増えていないこと）
   ```python
   comment_count_after_phase2 = issue.comments
   assert comment_count_after_phase2 == comment_count_after_phase1  # コメント数は変わらない
   ```

8. **検証4**: 最終的な進捗コメントの内容を確認
   ```python
   metadata_manager = MetadataManager(issue_number=370)
   comment_id = metadata_manager.get_progress_comment_id()

   final_comment = repo.get_issue_comment(comment_id)
   final_body = final_comment.body

   # 全体進捗セクションの確認
   assert '✅ Phase 0: Planning - COMPLETED' in final_body
   assert '✅ Phase 1: Requirements - COMPLETED' in final_body
   assert '✅ Phase 2: Design - COMPLETED' in final_body

   # 完了フェーズが折りたたまれているか確認
   assert '<details>' in final_body
   assert '<summary>完了したフェーズの詳細</summary>' in final_body
   ```

9. **検証5**: GitHub Issue上で目視確認
   - GitHub UIでIssue #370を開く
   - 進捗コメントが1つのみ存在することを確認
   - コメント内容が期待通りのフォーマットであることを確認
     - 全体進捗セクション（Phase 0-8のステータス一覧）
     - 完了フェーズの折りたたみセクション（`<details>`タグ）
     - 最終更新日時

10. **検証6**: 成功基準の確認（定量的）
    ```python
    # コメント数が1つのみ（98.9%削減）
    progress_comments = [c for c in issue.get_comments() if '🤖 AI Workflow - 進捗状況' in c.body]
    assert len(progress_comments) == 1

    # Issueページ読み込み時間（手動計測）
    # 目標: 1秒以下
    ```

##### 期待結果
- 複数フェーズ実行後も進捗コメントが1つのみ
- 各フェーズの進捗が1つのコメントに統合される
- コメント内容が期待通りのMarkdownフォーマット（全体進捗、完了フェーズ折りたたみ）
- 定量的成功基準を達成（コメント数1つ、ページ読み込み1秒以下）

##### 確認項目
- [ ] 複数フェーズ実行後も進捗コメントが1つのみか
- [ ] 各フェーズの進捗が1つのコメントに統合されているか
- [ ] 全体進捗セクションが正しく表示されているか
- [ ] 完了フェーズが折りたたまれているか（`<details>`タグ）
- [ ] 最終更新日時が記載されているか
- [ ] 定量的成功基準を達成しているか（コメント数1つ）
- [ ] Issueページ読み込み時間が改善されているか（目標1秒以下）

---

### 1.4. エラーハンドリング統合テスト

#### シナリオ4-1: GitHub API障害時の継続性テスト

**シナリオID**: INT-009
**優先度**: 中
**対応する要件**: FR-006, NFR-003

##### 目的
GitHub APIが一時的に障害を起こした場合でも、ワークフローが中断せずに継続することを検証する。

##### 前提条件
- GitHub Personal Access Token（PAT）が環境変数 `GITHUB_TOKEN` に設定されている
- 実際のGitHub Issue（例: #370）が存在する
- BasePhaseインスタンスが初期化されている
- GitHub APIがタイムアウトまたはエラーを返す状態（モック使用、またはネットワーク遮断）

##### テスト手順

1. **準備**: GitHub APIをモックして、エラーを返すように設定
   ```python
   from unittest.mock import patch, MagicMock
   from github import GithubException

   # GitHub APIがタイムアウトエラーを返すようにモック
   with patch.object(GitHubClient, 'create_or_update_progress_comment') as mock_api:
       mock_api.side_effect = GithubException(
           status=500,
           data={'message': 'Internal Server Error'},
           headers={}
       )
   ```

2. **実行**: `BasePhase.post_progress()` を呼び出し
   ```python
   planning_phase = PlanningPhase(...)

   # エラーが発生しても例外が発生しないことを確認
   try:
       planning_phase.post_progress(status='in_progress', details='Planning開始')
       success = True
   except Exception as e:
       success = False
       error_message = str(e)
   ```

3. **検証1**: ワークフローが継続することを確認（例外が発生しない）
   ```python
   assert success == True  # 例外が発生していない
   ```

4. **検証2**: エラーログが出力されることを確認
   - ログ出力を確認: `[WARNING] GitHub投稿に失敗しました: Internal Server Error`
   - ログ出力を確認: `[INFO] ワークフローは継続します`

5. **検証3**: フェーズの実行が継続することを確認
   ```python
   # post_progress()の後も、フェーズのロジックが実行される
   # （例外でフェーズが中断していない）
   ```

##### 期待結果
- GitHub API障害時でもワークフローが中断しない
- エラーログが出力される
- フェーズの実行が継続する

##### 確認項目
- [ ] GitHub API障害時に例外が発生していないか
- [ ] エラーログが出力されたか
- [ ] ワークフローが継続したか（フェーズが中断していないか）
- [ ] 可用性要件（NFR-003）を満たしているか

---

## 2. テストデータ

### 2.1. GitHub Issue情報

| 項目 | 値 |
|------|-----|
| Issue番号 | 370 |
| Issue URL | https://github.com/tielec/infrastructure-as-code/issues/370 |
| リポジトリ | tielec/infrastructure-as-code |

### 2.2. テスト用コメント内容

#### 初回投稿（Phase 0開始時）

```markdown
## 🤖 AI Workflow - 進捗状況

### 全体進捗

- 🔄 Phase 0: Planning - **IN PROGRESS** (開始: 2025-01-15 10:00)
- ⏸️ Phase 1: Requirements - **PENDING**
- ⏸️ Phase 2: Design - **PENDING**
- ⏸️ Phase 3: Test Scenario - **PENDING**
- ⏸️ Phase 4: Implementation - **PENDING**
- ⏸️ Phase 5: Test Implementation - **PENDING**
- ⏸️ Phase 6: Testing - **PENDING**
- ⏸️ Phase 7: Documentation - **PENDING**
- ⏸️ Phase 8: Report - **PENDING**

### 現在のフェーズ: Phase 0 (Planning)

**ステータス**: IN PROGRESS
**開始時刻**: 2025-01-15 10:00:00
**試行回数**: 1/3

#### 実行ログ

- `10:00:00` - Phase 0開始

---
*最終更新: 2025-01-15 10:00:05*
*AI駆動開発自動化ワークフロー (Claude Agent SDK)*
```

#### 更新後（Phase 0完了、Phase 1開始時）

```markdown
## 🤖 AI Workflow - 進捗状況

### 全体進捗

- ✅ Phase 0: Planning - **COMPLETED** (2025-01-15 10:30)
- 🔄 Phase 1: Requirements - **IN PROGRESS** (開始: 2025-01-15 11:00)
- ⏸️ Phase 2: Design - **PENDING**
- ⏸️ Phase 3: Test Scenario - **PENDING**
- ⏸️ Phase 4: Implementation - **PENDING**
- ⏸️ Phase 5: Test Implementation - **PENDING**
- ⏸️ Phase 6: Testing - **PENDING**
- ⏸️ Phase 7: Documentation - **PENDING**
- ⏸️ Phase 8: Report - **PENDING**

### 現在のフェーズ: Phase 1 (Requirements)

**ステータス**: IN PROGRESS
**開始時刻**: 2025-01-15 11:00:00
**試行回数**: 1/3

#### 実行ログ

- `11:00:00` - Phase 1開始

<details>
<summary>完了したフェーズの詳細</summary>

### Phase 0: Planning

**ステータス**: COMPLETED
**レビュー結果**: PASS
**実行時間**: 30分00秒
**コスト**: $0.15

</details>

---
*最終更新: 2025-01-15 11:00:05*
*AI駆動開発自動化ワークフロー (Claude Agent SDK)*
```

### 2.3. メタデータ構造（テスト用）

#### 初期状態（`github_integration`セクションなし）

```json
{
  "issue_number": 370,
  "phases": {
    "planning": { "status": "pending" },
    "requirements": { "status": "pending" },
    "design": { "status": "pending" }
  },
  "cost_tracking": {
    "total_cost": 0.0
  }
}
```

#### コメントID保存後

```json
{
  "issue_number": 370,
  "phases": {
    "planning": { "status": "completed" },
    "requirements": { "status": "pending" },
    "design": { "status": "pending" }
  },
  "cost_tracking": {
    "total_cost": 0.15
  },
  "github_integration": {
    "progress_comment_id": 123456789,
    "progress_comment_url": "https://github.com/tielec/infrastructure-as-code/issues/370#issuecomment-123456789"
  }
}
```

---

## 3. テスト環境要件

### 3.1. 必要な環境

| 項目 | 要件 |
|------|------|
| Python | 3.8以上 |
| PyGithub | インストール済み |
| GitHub Token | 環境変数 `GITHUB_TOKEN` に設定（`repo`スコープ必須） |
| GitHub Issue | 実際のIssue（例: #370）が存在する |
| ファイルシステム | `.ai-workflow/issue-370/` ディレクトリへの書き込み権限 |
| ネットワーク | GitHub APIへのアクセス可能 |

### 3.2. テスト実行環境

- **ローカル環境**: 開発者のローカルマシンで実行可能
- **CI/CD環境**: Jenkins、GitHub Actionsで実行可能（GitHub Tokenをシークレットとして設定）

### 3.3. モック/スタブの使用

統合テストのため、**基本的にモックは使用しない**。ただし、以下のケースではモックを使用する：

- **シナリオ4-1（GitHub API障害時の継続性テスト）**: GitHub APIをモックしてエラーを返す
- **エラーハンドリングテスト**: 異常系のテストでGitHub APIエラーを再現するためにモック使用

### 3.4. テストデータのクリーンアップ

- **テスト後のクリーンアップ**: 各テスト実行後、メタデータの `github_integration` セクションを削除（次回テストのため）
- **GitHub Issue上のコメント**: テスト実行後、手動で削除するか、テスト用Issueを別途作成する

---

## 4. 成功基準とテストカバレッジ

### 4.1. 定量的成功基準（Requirements Documentより）

| 成功基準 | 目標値 | テストシナリオ |
|---------|--------|---------------|
| コメント数削減 | 最大90コメント → **1コメント**（98.9%削減） | INT-008 |
| Issueページ読み込み時間 | 現在の3秒 → **1秒以下** | INT-008（手動計測） |
| API呼び出し頻度 | 各フェーズで最大10回 → **1-2回** | INT-006, INT-007 |
| テストカバレッジ | 新規メソッドの統合テストカバレッジ **100%** | 全シナリオ |

### 4.2. 定性的成功基準（Requirements Documentより）

| 成功基準 | テストシナリオ |
|---------|---------------|
| ユーザビリティ: 進捗が一目で把握できる | INT-008（目視確認） |
| 保守性: コード変更が最小限で、既存ワークフローに影響がない | INT-006, INT-007 |
| 拡張性: 将来的に他のオプション（Gist等）への切り替えが容易 | 設計により保証 |

### 4.3. テストカバレッジマトリクス

| 要件ID | 要件名 | テストシナリオ | カバレッジ |
|--------|--------|---------------|-----------|
| FR-001 | 進捗コメントの統合管理 | INT-001, INT-002, INT-006, INT-007, INT-008 | 100% |
| FR-002 | GitHubClient新規メソッド追加 | INT-001, INT-002, INT-003 | 100% |
| FR-003 | MetadataManager拡張 | INT-004, INT-005 | 100% |
| FR-004 | BasePhaseの進捗投稿ロジック変更 | INT-006, INT-007, INT-008 | 100% |
| FR-005 | 進捗コメントのMarkdownフォーマット設計 | INT-008（目視確認） | 100% |
| FR-006 | エラーハンドリングとフォールバック | INT-003, INT-009 | 100% |
| FR-007 | レビュー結果投稿の扱い | スコープ外（個別コメントとして残す） | N/A |
| AC-001 | 進捗コメントが1つのみ作成される | INT-001, INT-008 | 100% |
| AC-002 | 既存コメントが正しく更新される | INT-002, INT-007, INT-008 | 100% |
| AC-003 | コメントIDがメタデータに保存される | INT-001, INT-004 | 100% |
| AC-004 | フォーマットが仕様通りである | INT-008（目視確認） | 100% |
| AC-005 | GitHub APIエラー時にフォールバックする | INT-003 | 100% |
| AC-006 | Issueページの読み込み時間が改善される | INT-008（手動計測） | 100% |
| AC-007 | 既存ワークフローに影響を与えない | INT-006, INT-007 | 100% |
| AC-008 | 後方互換性が保たれる | INT-005 | 100% |
| NFR-001 | パフォーマンス要件 | INT-008 | 100% |
| NFR-003 | 可用性・信頼性要件 | INT-009 | 100% |

**総合テストカバレッジ**: **100%**（全機能要件と受け入れ基準をカバー）

---

## 5. テスト実行順序

統合テストは以下の順序で実行することを推奨します：

### Phase 1: 基本機能テスト（依存関係なし）

1. **INT-004**: メタデータへのコメントID保存
2. **INT-005**: メタデータからのコメントID取得（後方互換性）

### Phase 2: GitHub API統合テスト（Phase 1完了後）

3. **INT-001**: 初回進捗コメント作成
4. **INT-002**: 既存進捗コメント更新
5. **INT-003**: GitHub API失敗時のフォールバック

### Phase 3: エンドツーエンドテスト（Phase 2完了後）

6. **INT-006**: BasePhaseからの進捗投稿（初回投稿フロー）
7. **INT-007**: BasePhaseからの進捗投稿（更新フロー）
8. **INT-008**: 複数フェーズ実行時の進捗コメント統合

### Phase 4: エラーハンドリングテスト（Phase 3完了後）

9. **INT-009**: GitHub API障害時の継続性テスト

---

## 6. リスクと軽減策

### リスク1: GitHub APIレート制限

- **影響度**: 中
- **確率**: 低
- **詳細**: テスト実行中にGitHub APIのレート制限（5000 requests/hour）に引っかかる可能性
- **軽減策**:
  - テスト実行頻度を制限する
  - 必要に応じてテスト用Issueを別途作成し、本番Issueへの影響を最小化
  - レート制限に達した場合は、1時間待機してからテストを再実行

### リスク2: テスト環境のGitHub Token権限不足

- **影響度**: 高
- **確率**: 中
- **詳細**: GitHub Tokenに `repo` スコープが設定されていない場合、Issue Writeができない
- **軽減策**:
  - テスト実行前にGitHub Tokenの権限を確認
  - テスト用のGitHub Tokenを別途作成し、`repo`スコープを付与

### リスク3: テストデータのクリーンアップ漏れ

- **影響度**: 低
- **確率**: 中
- **詳細**: テスト実行後、メタデータや進捗コメントがクリーンアップされず、次回テストに影響
- **軽減策**:
  - テストスクリプトに自動クリーンアップ処理を追加
  - テスト用Issueを別途作成し、本番Issueへの影響を最小化

---

## 7. 品質ゲート確認

本テストシナリオは、Phase 3の品質ゲートを満たすように作成されています：

- [x] **Phase 2の戦略に沿ったテストシナリオである**: INTEGRATION_ONLY戦略に基づき、統合テストのみを実施
- [x] **主要な正常系がカバーされている**: INT-001, INT-002, INT-006, INT-007, INT-008で正常系をカバー
- [x] **主要な異常系がカバーされている**: INT-003, INT-009で異常系（GitHub API失敗、障害時）をカバー
- [x] **期待結果が明確である**: 各シナリオに期待結果と確認項目を明記

---

## 8. 参考資料

### 8.1. 関連ファイル

- `scripts/ai-workflow/phases/base_phase.py` (行216-239: `post_progress()`)
- `scripts/ai-workflow/core/github_client.py` (行159-211: `post_workflow_progress()`)
- `scripts/ai-workflow/core/metadata_manager.py`
- `.ai-workflow/issue-{number}/metadata.json`

### 8.2. 外部リソース

- [PyGithub Documentation - Edit Comment](https://pygithub.readthedocs.io/en/latest/github_objects/IssueComment.html#github.IssueComment.IssueComment.edit)
- [GitHub API - Update Comment](https://docs.github.com/en/rest/issues/comments#update-an-issue-comment)
- [GitHub Markdown - Details/Summary](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-collapsed-sections)

---

*このテストシナリオは AI Workflow - Test Scenario Phase によって作成されました。*
*作成日時: 2025-01-15*
