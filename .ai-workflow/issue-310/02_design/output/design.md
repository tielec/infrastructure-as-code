# 詳細設計書

**Issue**: #310
**タイトル**: [ai-workflow] feat: 全フェーズの成果物をGitHub Issueコメントに投稿する機能を追加
**作成日**: 2025-10-10
**更新日**: 2025-10-10

---

## 1. アーキテクチャ設計

### 1.1 システム全体図

```
┌────────────────────────────────────────────────────────────┐
│                   BasePhase                                 │
│  - post_output(output_content, title) メソッド              │
│    └─> GitHubClient.post_comment() を呼び出し               │
└────────────────────────────────────────────────────────────┘
                           ↑
                           │ 継承
                           │
    ┌──────────────────────┴──────────────────────┐
    │                                              │
┌───┴─────────────────┐              ┌───────────┴─────────────┐
│  Phase 1-5          │              │  Phase 6, 7 (参考実装)   │
│  - requirements     │              │  - documentation         │
│  - design           │              │    (96-103行目)          │
│  - test_scenario    │              │  - report                │
│  - implementation   │              │    (98-106行目)          │
│  - testing          │              │                          │
│                     │              │  ✅ 既にpost_output()実装 │
│  ❌ post_output()未実装│              │                          │
└─────────────────────┘              └──────────────────────────┘
```

### 1.2 コンポーネント間の関係

```
各フェーズ execute() メソッド
         │
         ├─> 成果物ファイル生成 (*.md)
         │
         ├─> 成果物ファイル読み込み (UTF-8)
         │
         └─> BasePhase.post_output() 呼び出し
                    │
                    ├─> GitHubClient.post_comment() 呼び出し
                    │         │
                    │         └─> GitHub API リクエスト
                    │
                    └─> エラーハンドリング (try-except)
                              │
                              └─> WARNING ログ出力 (投稿失敗時)
```

### 1.3 データフロー

```
1. フェーズ実行
   └─> output_file = self.output_dir / '{成果物名}.md'

2. 成果物生成確認
   └─> if not output_file.exists(): return error

3. 成果物読み込み
   └─> output_content = output_file.read_text(encoding='utf-8')

4. GitHub投稿 (try-except)
   └─> self.post_output(output_content=output_content, title="{タイトル}")
         └─> GitHubClient.post_comment(issue_number, body)
               └─> GitHub API POST /repos/{owner}/{repo}/issues/{issue_number}/comments

5. エラーハンドリング
   └─> except Exception as e:
         └─> print(f"[WARNING] 成果物のGitHub投稿に失敗しました: {e}")
```

---

## 2. 実装戦略

### 実装戦略: EXTEND

**判断根拠**:
1. **既存ファイルへの修正**: 6つの既存フェーズクラス（requirements.py, design.py, test_scenario.py, implementation.py, testing.py, report.py）の `execute()` メソッドに処理を追加
2. **新規ファイル作成なし**: 新しいファイルの作成は不要
3. **既存機能との統合度が高い**: `BasePhase.post_output()` メソッド（既存）を活用し、既に Phase 6 (documentation.py) と Phase 7 (report.py) で実装済みのパターンを他のフェーズに展開する
4. **既存アーキテクチャへの準拠**: 既存の `BasePhase` クラスの共通機能を利用するため、アーキテクチャ変更は不要

---

## 3. テスト戦略

### テスト戦略: UNIT_INTEGRATION

**判断根拠**:
1. **Unitテストの必要性**:
   - 各フェーズの `execute()` メソッドが正しく `post_output()` を呼び出すか検証
   - 成果物ファイルが存在しない場合のエラーハンドリング検証
   - UTF-8エンコーディングの正しさを検証
   - try-except による例外ハンドリングの動作確認

2. **Integrationテストの必要性**:
   - `BasePhase.post_output()` → `GitHubClient.post_comment()` → GitHub API の統合フロー検証
   - 実際のGitHub Issueコメント投稿の成功確認（モックではなく実環境テスト）
   - ネットワークエラー・API制限エラー時のエラーハンドリング検証

3. **BDDテスト不要の理由**:
   - ユーザーストーリーは単純（「成果物をGitHub Issueに投稿する」）
   - 複雑なビジネスロジックや条件分岐が存在しない
   - Given-When-Then形式で記述するほどの複雑性がない

---

## 4. テストコード戦略

### テストコード戦略: EXTEND_TEST

**判断根拠**:
1. **既存テストファイルの有無**: 各フェーズクラスに対応するテストファイルが既に存在する可能性が高い（例: `tests/test_requirements.py`, `tests/test_design.py` など）
2. **既存テストとの関連性**: 各フェーズの `execute()` メソッドのテストケースが既に存在する場合、そこに GitHub 投稿のテストケースを追加するのが自然
3. **一貫性の維持**: 既存のテスト構造を踏襲することで、テストコードの一貫性を保つ

**注**: 既存テストファイルが存在しない場合は、新規にテストファイルを作成する必要がある（その場合は CREATE_TEST に切り替え）

---

## 5. 影響範囲分析

### 5.1 既存コードへの影響

| コンポーネント | 影響度 | 詳細 |
|---------------|--------|------|
| `BasePhase.post_output()` | **影響なし** | 既存メソッドをそのまま利用 |
| `GitHubClient.post_comment()` | **影響なし** | 既存メソッドをそのまま利用 |
| Phase 1 (requirements.py) | **低** | `execute()` メソッドに5-8行の処理追加 |
| Phase 2 (design.py) | **低** | `execute()` メソッドに5-8行の処理追加（既存変数再利用） |
| Phase 3 (test_scenario.py) | **低** | `execute()` メソッドに5-8行の処理追加 |
| Phase 4 (implementation.py) | **低** | `execute()` メソッドに5-8行の処理追加 |
| Phase 5 (testing.py) | **低** | `execute()` メソッドに5-8行の処理追加 |
| Phase 6 (documentation.py) | **影響なし** | 既に実装済み（参考実装） |
| Phase 7 (report.py) | **影響なし** | 既に実装済み（98-106行目で確認済み） |

### 5.2 依存関係の変更

**変更なし**: 既存の依存関係（`BasePhase` → `GitHubClient`）はそのまま維持

### 5.3 マイグレーション要否

**不要**: データベーススキーマやファイル構造の変更は不要

---

## 6. 変更・追加ファイルリスト

### 6.1 修正が必要な既存ファイル

| # | ファイルパス | 変更内容 | 行数 |
|---|-------------|---------|------|
| 1 | `scripts/ai-workflow/phases/requirements.py` | `execute()` メソッドに成果物投稿処理を追加 | +8行 |
| 2 | `scripts/ai-workflow/phases/design.py` | `execute()` メソッドに成果物投稿処理を追加（既存変数再利用） | +7行 |
| 3 | `scripts/ai-workflow/phases/test_scenario.py` | `execute()` メソッドに成果物投稿処理を追加 | +8行 |
| 4 | `scripts/ai-workflow/phases/implementation.py` | `execute()` メソッドに成果物投稿処理を追加 | +8行 |
| 5 | `scripts/ai-workflow/phases/testing.py` | `execute()` メソッドに成果物投稿処理を追加 | +8行 |
| 6 | `scripts/ai-workflow/phases/report.py` | 確認のみ（98-106行目で既に実装済み） | +0行 |

**合計**: 約 39行の追加

### 6.2 新規作成ファイル

**なし**

### 6.3 削除が必要なファイル

**なし**

---

## 7. 詳細設計

### 7.1 クラス設計

**変更なし**: 既存のクラス構造を維持

### 7.2 関数設計

#### 7.2.1 Phase 1: RequirementsPhase.execute()

**実装箇所**: `scripts/ai-workflow/phases/requirements.py` の `execute()` メソッド内

**追加位置**: 行71-76の後（`output_file` の存在確認後、`return` の前）

**追加コード**:
```python
# GitHub Issueに成果物を投稿
try:
    output_content = output_file.read_text(encoding='utf-8')
    self.post_output(
        output_content=output_content,
        title="要件定義書"
    )
except Exception as e:
    print(f"[WARNING] 成果物のGitHub投稿に失敗しました: {e}")
```

**パラメータ**:
- `output_content`: `requirements.md` の内容（UTF-8エンコーディング）
- `title`: "要件定義書"

---

#### 7.2.2 Phase 2: DesignPhase.execute()

**実装箇所**: `scripts/ai-workflow/phases/design.py` の `execute()` メソッド内

**追加位置**: 行94-95の後（戦略判断の保存後、コメントアウトされたステータス更新の前）

**実装上の注意点**:
- 行88で既に `design_content = output_file.read_text(encoding='utf-8')` で読み込まれているため、**既存の `design_content` 変数を再利用**する
- ファイルの二重読み込みを避けることでパフォーマンスを向上

**追加コード**:
```python
# GitHub Issueに成果物を投稿
try:
    # design_content 変数を再利用（88行目で既に読み込み済み）
    self.post_output(
        output_content=design_content,
        title="詳細設計書"
    )
except Exception as e:
    print(f"[WARNING] 成果物のGitHub投稿に失敗しました: {e}")
```

**パラメータ**:
- `output_content`: `design_content` 変数（88行目で読み込み済み）
- `title`: "詳細設計書"

---

#### 7.2.3 Phase 3: TestScenarioPhase.execute()

**実装箇所**: `scripts/ai-workflow/phases/test_scenario.py` の `execute()` メソッド内

**追加位置**: 行107-112の後（`output_file` の存在確認後、コメントアウトされたステータス更新の前）

**追加コード**:
```python
# GitHub Issueに成果物を投稿
try:
    output_content = output_file.read_text(encoding='utf-8')
    self.post_output(
        output_content=output_content,
        title="テストシナリオ"
    )
except Exception as e:
    print(f"[WARNING] 成果物のGitHub投稿に失敗しました: {e}")
```

**パラメータ**:
- `output_content`: `test-scenario.md` の内容（UTF-8エンコーディング）
- `title`: "テストシナリオ"

---

#### 7.2.4 Phase 4: ImplementationPhase.execute()

**実装箇所**: `scripts/ai-workflow/phases/implementation.py` の `execute()` メソッド内

**追加位置**: 行115-119の後（`output_file` の存在確認後、コメントアウトされたステータス更新の前）

**追加コード**:
```python
# GitHub Issueに成果物を投稿
try:
    output_content = output_file.read_text(encoding='utf-8')
    self.post_output(
        output_content=output_content,
        title="実装ログ"
    )
except Exception as e:
    print(f"[WARNING] 成果物のGitHub投稿に失敗しました: {e}")
```

**パラメータ**:
- `output_content`: `implementation.md` の内容（UTF-8エンコーディング）
- `title`: "実装ログ"

---

#### 7.2.5 Phase 5: TestingPhase.execute()

**実装箇所**: `scripts/ai-workflow/phases/testing.py` の `execute()` メソッド内

**追加位置**: 行89-93の後（`output_file` の存在確認後、コメントアウトされたステータス更新の前）

**追加コード**:
```python
# GitHub Issueに成果物を投稿
try:
    output_content = output_file.read_text(encoding='utf-8')
    self.post_output(
        output_content=output_content,
        title="テスト結果"
    )
except Exception as e:
    print(f"[WARNING] 成果物のGitHub投稿に失敗しました: {e}")
```

**パラメータ**:
- `output_content`: `test-result.md` の内容（UTF-8エンコーディング）
- `title`: "テスト結果"

---

#### 7.2.6 Phase 7: ReportPhase.execute()

**実装箇所**: `scripts/ai-workflow/phases/report.py` の `execute()` メソッド内

**現状**: 行98-106で既に実装済み（実装コードで確認済み）

**確認内容**:
- タイトル: "最終レポート" ✅
- ファイル: `report.md` ✅
- エンコーディング: UTF-8 ✅
- エラーハンドリング: try-except ✅

**実装コード（既存）**:
```python
# GitHub Issueに成果物を投稿
try:
    output_content = output_file.read_text(encoding='utf-8')
    self.post_output(
        output_content=output_content,
        title="最終レポート"
    )
except Exception as e:
    print(f"[WARNING] 成果物のGitHub投稿に失敗しました: {e}")
```

**追加作業**: なし（既に要件を満たしている）

---

### 7.3 データ構造設計

**変更なし**: 既存のデータ構造を維持

### 7.4 インターフェース設計

**変更なし**: 既存の `BasePhase.post_output()` メソッドのインターフェースをそのまま利用

**メソッドシグネチャ** (base_phase.py:218-229):
```python
def post_output(
    self,
    output_content: str,
    title: Optional[str] = None
):
    """
    GitHubに成果物の内容を投稿

    Args:
        output_content: 成果物の内容（Markdown形式）
        title: タイトル（省略可、指定しない場合はフェーズ名を使用）
    """
```

---

## 8. セキュリティ考慮事項

### 8.1 認証・認可

- **GitHub API トークン**: `GitHubClient` が環境変数またはクレデンシャルストアから取得（既存実装で担保）
- **Issue アクセス権限**: GitHub APIトークンの権限に依存（repo スコープが必要）

### 8.2 データ保護

- **成果物の機密情報**: レビュープロセスで成果物に機密情報が含まれないことを確認（運用でカバー）
- **トークンのログ出力**: エラーログにトークン情報が含まれないよう注意（既存の `GitHubClient` で担保）

### 8.3 セキュリティリスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| GitHub APIレート制限超過 | 中 | `GitHubClient` でレート制限を監視（将来対応） |
| 大容量ファイルの投稿失敗 | 低 | 65,536文字を超える場合はWARNINGを表示してスキップ（将来対応） |
| 機密情報の誤投稿 | 高 | レビュープロセスで成果物の内容を確認（運用でカバー） |
| ネットワーク障害 | 低 | try-except でキャッチし、ワークフローを継続 |

---

## 9. 非機能要件への対応

### 9.1 パフォーマンス要件

| 要件 | 目標 | 実装方法 |
|------|------|---------|
| GitHub API呼び出しは各フェーズの execute() 完了後に1回のみ実行 | 1回/フェーズ | `post_output()` を execute() 内で1回のみ呼び出し |
| API呼び出しによるフェーズ実行時間の増加は2秒以内 | ≤2秒 | 非同期処理は不要（GitHub APIレスポンスは通常1秒以内） |
| ファイル読み込みの最適化 | 最小限 | Phase 2では既存の `design_content` 変数を再利用し、二重読み込みを回避 |

### 9.2 スケーラビリティ

- **GitHub Issueコメント数の増加**: 1フェーズ1コメントのため、最大7コメント追加（許容範囲）
- **大容量ファイル対応**: 将来対応（65,536文字を超える場合の分割投稿機能）

### 9.3 保守性

- **DRY原則の遵守**: 各フェーズで同じパターン（try-except、UTF-8エンコーディング、title指定）を実装
- **共通機能の活用**: `BasePhase.post_output()` メソッドを使用
- **投稿タイトルの柔軟性**: 各フェーズで独自のタイトルを定義可能
- **コードの一貫性**: Phase 6, 7の既存実装パターンを踏襲

---

## 10. 実装の順序

### 推奨実装順序:

1. **Phase 7 (report.py) の確認**: 既に実装済み（98-106行目）であることを確認し、実装パターンを参考にする
2. **Phase 1 (requirements.py)**: 最もシンプルなフェーズから開始
3. **Phase 2 (design.py)**: `design_content` 変数の再利用パターンを実装
4. **Phase 3 (test_scenario.py)**: Phase 1 と同じパターン
5. **Phase 4 (implementation.py)**: Phase 1 と同じパターン
6. **Phase 5 (testing.py)**: Phase 1 と同じパターン

### 依存関係の考慮:

- **Phase 間の依存関係なし**: 各フェーズは独立して実装可能
- **Phase 6, 7 の参考**: Phase 6 (documentation.py) と Phase 7 (report.py) は既に実装済みのため、最初に確認してパターンを参考にする
- **並行実装可能**: Phase 1-5 は相互に依存しないため、並行して実装可能

---

## 11. テスト計画

### 11.1 Unitテスト

**対象**: 各フェーズの `execute()` メソッド

**テストケース**:

| # | テストケース | 期待結果 |
|---|-------------|---------|
| 1 | 成果物ファイルが存在する場合 | `post_output()` が呼ばれる |
| 2 | 成果物ファイルが存在しない場合 | `post_output()` が呼ばれない（エラーリターン） |
| 3 | UTF-8エンコーディングで成果物を読み込む | 文字化けなし |
| 4 | `post_output()` が例外をスローした場合 | WARNING ログが出力され、execute() は success=True を返す |
| 5 | Phase 2で既存変数を再利用 | `design_content` 変数を使用し、ファイル読み込みが1回のみ |

**モック対象**:
- `BasePhase.post_output()`: モック化して呼び出しを検証
- `GitHubClient.post_comment()`: モック化してAPI呼び出しを回避

### 11.2 Integrationテスト

**対象**: `BasePhase.post_output()` → `GitHubClient.post_comment()` → GitHub API

**テストケース**:

| # | テストケース | 期待結果 |
|---|-------------|---------|
| 1 | GitHub APIが正常にレスポンスを返す場合 | GitHub Issueに成果物がコメント投稿される |
| 2 | GitHub APIがレート制限エラーを返す場合 | WARNING ログが出力され、ワークフローは継続 |
| 3 | ネットワークエラーが発生した場合 | WARNING ログが出力され、ワークフローは継続 |

**実環境テスト**:
- テスト用のGitHub Issueを作成し、実際のAPI呼び出しを検証
- 投稿されたコメントの内容（タイトル、本文、フッター）を確認

---

## 12. リスク管理

### 12.1 技術的リスク

| リスク | 発生確率 | 影響度 | 対策 |
|--------|---------|--------|------|
| GitHub APIレート制限超過 | 低 | 中 | `GitHubClient` でレート制限を監視し、必要に応じて待機処理を追加（将来対応） |
| 大容量ファイルの投稿失敗 | 低 | 低 | 65,536文字を超える場合はWARNINGを表示してスキップ（将来対応） |
| ネットワーク障害 | 低 | 低 | try-except でキャッチし、ワークフローを継続 |
| 既存テストの破壊 | 中 | 中 | 既存テストを実行して回帰を確認 |
| Phase 2の変数参照エラー | 低 | 低 | 88行目の `design_content` 変数が確実に定義されることを確認 |

### 12.2 運用リスク

| リスク | 発生確率 | 影響度 | 対策 |
|--------|---------|--------|------|
| GitHub Issueが大量のコメントで埋まる | 低 | 低 | 1フェーズ1コメントのため、最大7コメント追加（許容範囲） |
| 機密情報の誤投稿 | 低 | 高 | レビュープロセスで成果物の内容を確認し、機密情報が含まれないことを検証 |

---

## 13. 受け入れ基準

### 13.1 機能受け入れ基準

| Phase | 成果物ファイル | 投稿タイトル | 検証方法 |
|-------|---------------|-------------|---------|
| Phase 1 | requirements.md | 要件定義書 | GitHub Issueコメントに投稿されることを確認 |
| Phase 2 | design.md | 詳細設計書 | GitHub Issueコメントに投稿されることを確認 |
| Phase 3 | test-scenario.md | テストシナリオ | GitHub Issueコメントに投稿されることを確認 |
| Phase 4 | implementation.md | 実装ログ | GitHub Issueコメントに投稿されることを確認 |
| Phase 5 | test-result.md | テスト結果 | GitHub Issueコメントに投稿されることを確認 |
| Phase 7 | report.md | 最終レポート | GitHub Issueコメントに投稿されることを確認（既存実装の確認） |

### 13.2 非機能受け入れ基準

- **エラーハンドリング**: GitHub API投稿失敗時にWARNINGログが出力され、ワークフローが継続することを確認
- **UTF-8エンコーディング**: 日本語を含む成果物が文字化けせずに投稿されることを確認
- **パフォーマンス**: 各フェーズの実行時間が投稿処理により2秒以上増加しないことを確認
- **コード品質**: Phase 2で `design_content` 変数が再利用され、ファイル読み込みが1回のみであることを確認

---

## 14. 品質ゲート（Phase 2）

- [x] **実装戦略の判断根拠が明記されている**: EXTEND戦略を選択し、既存ファイルへの修正理由を明記
- [x] **テスト戦略の判断根拠が明記されている**: UNIT_INTEGRATION戦略を選択し、各テスト種類の必要性を説明
- [x] **テストコード戦略の判断根拠が明記されている**: EXTEND_TEST戦略を選択し、既存テストファイルへの追加理由を明記
- [x] **既存コードへの影響範囲が分析されている**: 6つのフェーズクラスへの影響を表形式で整理
- [x] **変更が必要なファイルがリストアップされている**: 修正が必要な6ファイルを相対パスで記載
- [x] **設計が実装可能である**: 具体的な実装箇所（行数）、追加コード、パラメータを明記

---

## 15. 参照ドキュメント

- **既存実装**:
  - `scripts/ai-workflow/phases/documentation.py` (Phase 6, 96-103行目)
  - `scripts/ai-workflow/phases/report.py` (Phase 7, 98-106行目) ✅ 確認済み
- **基底クラス**: `scripts/ai-workflow/phases/base_phase.py` (post_output: 218-256行目)
- **GitHubクライアント**: `scripts/ai-workflow/core/github_client.py`
- **要件定義書**: `.ai-workflow/issue-310/01_requirements/output/requirements.md`
- **プロジェクトガイドライン**: `CLAUDE.md`
- **Issue**: https://github.com/tielec/infrastructure-as-code/issues/310

---

## 16. 実装時の注意事項

### 16.1 Phase 2 (design.py) の特殊対応

- **既存の `design_content` 変数を再利用**: 行88で既に `output_file.read_text(encoding='utf-8')` で読み込まれているため、重複読み込みを避ける

  ```python
  # 既存コード (88行目)
  design_content = output_file.read_text(encoding='utf-8')
  decisions = self._extract_design_decisions(design_content)

  if decisions:
      self.metadata.data['design_decisions'].update(decisions)
      self.metadata.save()
      print(f"[INFO] 戦略判断をmetadata.jsonに保存: {decisions}")

  # GitHub投稿処理 (95行目の後に追加)
  try:
      # design_content を再利用（88行目で既に読み込み済み）
      self.post_output(
          output_content=design_content,  # ← 再読み込みせず再利用
          title="詳細設計書"
      )
  except Exception as e:
      print(f"[WARNING] 成果物のGitHub投稿に失敗しました: {e}")
  ```

**理由**: パフォーマンス最適化のため、同じファイルを2回読み込まない

### 16.2 Phase 7 (report.py) の確認

- **既に実装済みであることを確認**: 行98-106で既に `post_output()` が実装されている（実装コードで確認済み）
- **確認項目**:
  1. タイトルが "最終レポート" であることを確認 ✅
  2. ファイル名が `report.md` であることを確認（Issue本文では `final-report.md` だが、実装では `report.md`） ✅
  3. エラーハンドリングが try-except で実装されていることを確認 ✅

**追加作業**: なし（既に要件を満たしている）

### 16.3 コメントの統一

- **既存コメント**: `# GitHub Issueに成果物を投稿` で統一（Phase 6, Phase 7で使用）
- **エラーメッセージ**: `[WARNING] 成果物のGitHub投稿に失敗しました: {e}` で統一

---

**以上**
