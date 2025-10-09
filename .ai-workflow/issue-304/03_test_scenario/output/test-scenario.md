# テストシナリオ: AI駆動開発自動化ワークフローMVP v1.0.0

## ドキュメント情報
- **Issue番号**: #304
- **バージョン**: v1.0.0 (MVP)
- **作成日**: 2025-10-09
- **ステータス**: Phase 3 - テストシナリオ
- **前提ドキュメント**:
  - [要件定義書](./../01_requirements/output/requirements.md)
  - [詳細設計書](./../02_design/output/design.md)

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略
**UNIT_ONLY（Unitテストのみ）**

### 1.2 テスト対象の範囲
Phase 2（DesignPhase）の実装に関連する以下のコンポーネント：

- **phases/design.py**: DesignPhaseクラス
  - `execute()`: 詳細設計書生成
  - `review()`: 設計書レビュー
  - `revise()`: 設計書修正
  - `_parse_review_result()`: レビュー結果パース
  - `_parse_design_decisions()`: 設計判断抽出

- **core/claude_agent_client.py**: ClaudeAgentClientクラス（既存コードの動作確認）
  - `execute_task_sync()`: 同期実行

- **core/metadata_manager.py**: MetadataManagerクラス（既存コードの動作確認）
  - `update_phase_status()`: フェーズステータス更新
  - `record_design_decisions()`: 設計判断記録

### 1.3 テストの目的
- DesignPhaseの各メソッドが正しく動作することを検証
- レビュー結果のパース処理が正確であることを検証
- 設計判断の抽出とmetadata.json記録が正しく行われることを検証
- エラーハンドリングが適切に機能することを検証
- 既存のBasePhaseとの統合が正しく機能することを検証

---

## 2. Unitテストシナリオ

### 2.1 DesignPhase.__init__()

#### テストケース1: DesignPhase_init_正常系
- **目的**: DesignPhaseが正しく初期化されることを検証
- **前提条件**:
  - ワークフローディレクトリが存在する
  - metadata.jsonが存在する
- **入力**:
  - `issue_number="304"`
  - その他デフォルトパラメータ
- **期待結果**:
  - `self.phase_name == "design"`
  - `self.issue_number == "304"`
  - `self.metadata`オブジェクトが正しく初期化される
  - `self.claude_client`オブジェクトが正しく初期化される
- **テストデータ**: 有効なmetadata.jsonファイル

#### テストケース2: DesignPhase_init_異常系_metadata不在
- **目的**: metadata.jsonが存在しない場合のエラーハンドリングを検証
- **前提条件**: ワークフローディレクトリが存在しない
- **入力**: `issue_number="999"`
- **期待結果**: `FileNotFoundError`が発生する
- **テストデータ**: なし

---

### 2.2 DesignPhase.execute()

#### テストケース3: DesignPhase_execute_正常系
- **目的**: 設計書が正常に生成されることを検証
- **前提条件**:
  - Phase 1が完了している（requirements.mdが存在）
  - Claude Agent SDKのモックが正常なレスポンスを返す
- **入力**: なし（selfのみ）
- **期待結果**:
  - 返り値: `{"success": True, "output": "...design.md", "error": None}`
  - `02_design/output/design.md`ファイルが作成される
  - ファイル内容に「# 詳細設計書」が含まれる
  - `metadata.json`の`design_decisions`が更新される
  - `execute/prompt.txt`にプロンプトが保存される
  - `execute/agent_log.md`にエージェントログが保存される
- **テストデータ**:
  - モックされたClaude APIレスポンス（有効な設計書Markdown）
  - requirements.mdファイル

#### テストケース4: DesignPhase_execute_異常系_requirements不在
- **目的**: 要件定義書が存在しない場合のエラーハンドリングを検証
- **前提条件**: requirements.mdが存在しない
- **入力**: なし
- **期待結果**:
  - 返り値: `{"success": False, "output": None, "error": "要件定義書が見つかりません"}`
  - design.mdは作成されない
- **テストデータ**: なし

#### テストケース5: DesignPhase_execute_異常系_Claude_API失敗
- **目的**: Claude API呼び出しが失敗した場合のエラーハンドリングを検証
- **前提条件**:
  - requirements.mdが存在する
  - Claude Agent SDKのモックがエラーを返す
- **入力**: なし
- **期待結果**:
  - 返り値: `{"success": False, "output": None, "error": "..."}`
  - エラーメッセージにAPI失敗の詳細が含まれる
- **テストデータ**: モックされたClaude APIエラーレスポンス

#### テストケース6: DesignPhase_execute_境界値_空のrequirements
- **目的**: 空の要件定義書の場合の動作を検証
- **前提条件**: requirements.mdが空ファイル
- **入力**: なし
- **期待結果**:
  - 返り値: `{"success": False, "output": None, "error": "要件定義書が空です"}`
- **テストデータ**: 空のrequirements.mdファイル

---

### 2.3 DesignPhase.review()

#### テストケース7: DesignPhase_review_正常系_PASS
- **目的**: レビューがPASSする場合の動作を検証
- **前提条件**:
  - design.mdが存在する
  - Claude Agent SDKのモックがPASS判定を返す
- **入力**: なし
- **期待結果**:
  - 返り値: `{"result": "PASS", "feedback": "...", "suggestions": []}`
  - `review/result.md`にレビュー結果が保存される
  - `review/agent_log.md`にエージェントログが保存される
- **テストデータ**:
  - モックされたClaude APIレスポンス（PASS判定）
  - 有効なdesign.mdファイル

#### テストケース8: DesignPhase_review_正常系_PASS_WITH_SUGGESTIONS
- **目的**: レビューがPASS（提案あり）の場合の動作を検証
- **前提条件**:
  - design.mdが存在する
  - Claude Agent SDKのモックがPASS_WITH_SUGGESTIONS判定を返す
- **入力**: なし
- **期待結果**:
  - 返り値: `{"result": "PASS_WITH_SUGGESTIONS", "feedback": "...", "suggestions": ["提案1", "提案2"]}`
  - `review/result.md`にレビュー結果と提案が保存される
- **テストデータ**: モックされたClaude APIレスポンス（PASS_WITH_SUGGESTIONS判定）

#### テストケース9: DesignPhase_review_正常系_FAIL
- **目的**: レビューがFAILする場合の動作を検証
- **前提条件**:
  - design.mdが存在する
  - Claude Agent SDKのモックがFAIL判定を返す
- **入力**: なし
- **期待結果**:
  - 返り値: `{"result": "FAIL", "feedback": "...", "suggestions": ["修正1", "修正2"]}`
  - `review/result.md`にレビュー結果と修正指摘が保存される
- **テストデータ**: モックされたClaude APIレスポンス（FAIL判定）

#### テストケース10: DesignPhase_review_異常系_design不在
- **目的**: design.mdが存在しない場合のエラーハンドリングを検証
- **前提条件**: design.mdが存在しない
- **入力**: なし
- **期待結果**:
  - 例外が発生する、またはエラーレスポンスが返される
- **テストデータ**: なし

#### テストケース11: DesignPhase_review_異常系_パース失敗
- **目的**: レビュー結果のパースが失敗した場合の動作を検証
- **前提条件**:
  - design.mdが存在する
  - Claude Agent SDKのモックが不正なフォーマットのレスポンスを返す
- **入力**: なし
- **期待結果**:
  - デフォルト値が返される、またはエラーが報告される
- **テストデータ**: モックされた不正フォーマットのClaude APIレスポンス

---

### 2.4 DesignPhase.revise()

#### テストケース12: DesignPhase_revise_正常系
- **目的**: 設計書が正常に修正されることを検証
- **前提条件**:
  - design.mdが存在する
  - requirements.mdが存在する
  - レビューフィードバックが提供される
  - Claude Agent SDKのモックが修正版設計書を返す
- **入力**: `review_feedback="実装戦略の判断根拠が不足しています"`
- **期待結果**:
  - 返り値: `{"success": True, "output": "...design.md", "error": None}`
  - design.mdが上書きされる
  - 修正版の内容に改善が反映されている
  - `revise/prompt.txt`にプロンプトが保存される
  - `revise/agent_log.md`にエージェントログが保存される
- **テストデータ**:
  - モックされたClaude APIレスポンス（修正版設計書）
  - 既存のdesign.mdファイル
  - requirements.mdファイル

#### テストケース13: DesignPhase_revise_異常系_空のフィードバック
- **目的**: 空のフィードバックの場合の動作を検証
- **前提条件**: design.mdが存在する
- **入力**: `review_feedback=""`
- **期待結果**:
  - 返り値: `{"success": False, "output": None, "error": "フィードバックが空です"}`
- **テストデータ**: なし

#### テストケース14: DesignPhase_revise_異常系_Claude_API失敗
- **目的**: Claude API呼び出しが失敗した場合のエラーハンドリングを検証
- **前提条件**:
  - design.mdが存在する
  - Claude Agent SDKのモックがエラーを返す
- **入力**: `review_feedback="有効なフィードバック"`
- **期待結果**:
  - 返り値: `{"success": False, "output": None, "error": "..."}`
  - エラーメッセージにAPI失敗の詳細が含まれる
- **テストデータ**: モックされたClaude APIエラーレスポンス

---

### 2.5 DesignPhase._parse_review_result()

#### テストケース15: parse_review_result_正常系_PASS
- **目的**: PASS判定のパースが正しく行われることを検証
- **前提条件**: なし
- **入力**:
```python
messages = [
    {
        "type": "message",
        "content": [
            {
                "type": "text",
                "text": "**判定: PASS**\n\n設計書は要件を満たしています。"
            }
        ]
    }
]
```
- **期待結果**:
```python
{
    "result": "PASS",
    "feedback": "**判定: PASS**\n\n設計書は要件を満たしています。",
    "suggestions": []
}
```
- **テストデータ**: 上記messages

#### テストケース16: parse_review_result_正常系_FAIL
- **目的**: FAIL判定のパースが正しく行われることを検証
- **前提条件**: なし
- **入力**:
```python
messages = [
    {
        "type": "message",
        "content": [
            {
                "type": "text",
                "text": "**判定: FAIL**\n\n## 修正が必要な点\n- 実装戦略の根拠が不足\n- テスト戦略の説明が不明確"
            }
        ]
    }
]
```
- **期待結果**:
```python
{
    "result": "FAIL",
    "feedback": "**判定: FAIL**\n\n## 修正が必要な点\n- 実装戦略の根拠が不足\n- テスト戦略の説明が不明確",
    "suggestions": ["実装戦略の根拠が不足", "テスト戦略の説明が不明確"]
}
```
- **テストデータ**: 上記messages

#### テストケース17: parse_review_result_境界値_判定なし
- **目的**: 判定キーワードが見つからない場合の動作を検証
- **前提条件**: なし
- **入力**:
```python
messages = [
    {
        "type": "message",
        "content": [
            {
                "type": "text",
                "text": "これは設計書のレビューです。"
            }
        ]
    }
]
```
- **期待結果**:
```python
{
    "result": "UNKNOWN",
    "feedback": "これは設計書のレビューです。",
    "suggestions": []
}
```
- **テストデータ**: 上記messages

#### テストケース18: parse_review_result_異常系_空のメッセージ
- **目的**: 空のメッセージリストの場合の動作を検証
- **前提条件**: なし
- **入力**: `messages = []`
- **期待結果**:
```python
{
    "result": "UNKNOWN",
    "feedback": "",
    "suggestions": []
}
```
- **テストデータ**: 空のリスト

---

### 2.6 DesignPhase._parse_design_decisions()

#### テストケース19: parse_design_decisions_正常系_すべて抽出
- **目的**: 3つの戦略判断がすべて正しく抽出されることを検証
- **前提条件**: なし
- **入力**:
```markdown
## 2. 実装戦略判断

### 実装戦略: EXTEND

**判断根拠**:
- 既存コードを拡張

---

## 3. テスト戦略判断

### テスト戦略: UNIT_BDD

**判断根拠**:
- UnitテストとBDDテスト

---

## 4. テストコード戦略判断

### テストコード戦略: EXTEND_TEST

**判断根拠**:
- 既存テストを拡張
```
- **期待結果**:
```python
{
    "implementation_strategy": "EXTEND",
    "test_strategy": "UNIT_BDD",
    "test_code_strategy": "EXTEND_TEST"
}
```
- **テストデータ**: 上記Markdown文字列

#### テストケース20: parse_design_decisions_正常系_CREATE戦略
- **目的**: CREATE戦略が正しく抽出されることを検証
- **前提条件**: なし
- **入力**:
```markdown
### 実装戦略: CREATE
### テスト戦略: UNIT_ONLY
### テストコード戦略: CREATE_TEST
```
- **期待結果**:
```python
{
    "implementation_strategy": "CREATE",
    "test_strategy": "UNIT_ONLY",
    "test_code_strategy": "CREATE_TEST"
}
```
- **テストデータ**: 上記Markdown文字列

#### テストケース21: parse_design_decisions_境界値_一部欠損
- **目的**: 一部の戦略判断が欠損している場合の動作を検証
- **前提条件**: なし
- **入力**:
```markdown
### 実装戦略: EXTEND
### テスト戦略: UNIT_BDD
```
- **期待結果**:
```python
{
    "implementation_strategy": "EXTEND",
    "test_strategy": "UNIT_BDD",
    "test_code_strategy": None
}
```
- **テストデータ**: 上記Markdown文字列

#### テストケース22: parse_design_decisions_異常系_すべて欠損
- **目的**: すべての戦略判断が欠損している場合の動作を検証
- **前提条件**: なし
- **入力**: `design_md_content = "# 設計書\n\n何もありません"`
- **期待結果**:
```python
{
    "implementation_strategy": None,
    "test_strategy": None,
    "test_code_strategy": None
}
```
- **テストデータ**: 上記Markdown文字列

#### テストケース23: parse_design_decisions_異常系_不正なフォーマット
- **目的**: 不正なフォーマットの場合の動作を検証
- **前提条件**: なし
- **入力**:
```markdown
実装戦略: EXTEND（見出しなし）
テスト戦略 UNIT_BDD（コロンなし）
### テストコード戦略: （値なし）
```
- **期待結果**:
```python
{
    "implementation_strategy": None,
    "test_strategy": None,
    "test_code_strategy": None
}
```
- **テストデータ**: 上記Markdown文字列

---

### 2.7 統合動作確認（Unitテストレベル）

#### テストケース24: DesignPhase_フルフロー_正常系
- **目的**: execute → review（PASS） の一連の流れが正しく動作することを検証
- **前提条件**:
  - requirements.mdが存在する
  - Claude Agent SDKのモックが正常なレスポンスを返す
- **入力**: なし
- **期待結果**:
  1. `execute()`が成功し、design.mdが作成される
  2. `review()`が成功し、PASS判定が返される
  3. metadata.jsonに設計判断とレビュー結果が記録される
- **テストデータ**:
  - モックされたClaude APIレスポンス（設計書＋PASSレビュー）
  - requirements.mdファイル

#### テストケース25: DesignPhase_フルフロー_リトライ成功
- **目的**: execute → review（FAIL） → revise → review（PASS） のリトライフローが正しく動作することを検証
- **前提条件**:
  - requirements.mdが存在する
  - Claude Agent SDKのモックが1回目はFAIL、2回目はPASSを返す
- **入力**: なし
- **期待結果**:
  1. `execute()`が成功し、design.mdが作成される
  2. `review()`がFAIL判定を返す
  3. `revise()`が成功し、design.mdが修正される
  4. 2回目の`review()`がPASS判定を返す
  5. metadata.jsonのretry_countが1になる
- **テストデータ**:
  - モックされたClaude APIレスポンス（設計書＋FAILレビュー＋修正版設計書＋PASSレビュー）
  - requirements.mdファイル

#### テストケース26: DesignPhase_フルフロー_リトライ上限
- **目的**: リトライが上限（3回）に達した場合の動作を検証
- **前提条件**:
  - requirements.mdが存在する
  - Claude Agent SDKのモックがすべてFAIL判定を返す
- **入力**: なし
- **期待結果**:
  1. `execute()`が成功し、design.mdが作成される
  2. `review()`がFAIL判定を返す
  3. `revise()`→`review()`を3回繰り返す
  4. 3回目のFAIL後、リトライを停止する
  5. metadata.jsonのretry_countが3になる
  6. フェーズステータスが"failed"になる
- **テストデータ**:
  - モックされたClaude APIレスポンス（すべてFAIL判定）
  - requirements.mdファイル

---

### 2.8 既存コンポーネントとの統合確認

#### テストケース27: MetadataManager_design_decisions記録
- **目的**: MetadataManagerの設計判断記録機能が正しく動作することを検証
- **前提条件**: metadata.jsonが存在する
- **入力**:
```python
decisions = {
    "implementation_strategy": "EXTEND",
    "test_strategy": "UNIT_BDD",
    "test_code_strategy": "EXTEND_TEST"
}
```
- **期待結果**:
  - metadata.jsonの`design_decisions`フィールドに上記データが記録される
  - `updated_at`タイムスタンプが更新される
- **テストデータ**: 上記decisionsディクショナリ

#### テストケース28: ClaudeAgentClient_execute_task_sync呼び出し
- **目的**: ClaudeAgentClientの同期実行が正しく呼び出されることを検証
- **前提条件**: Claude Agent SDKのモックが設定されている
- **入力**:
```python
task_description="Phase 2: 詳細設計"
prompt="設計書を作成してください"
```
- **期待結果**:
  - `execute_task_sync()`が呼び出される
  - プロンプトがClaude Agent SDKに渡される
  - レスポンスが正しく返される
- **テストデータ**: モックされたClaude APIレスポンス

#### テストケース29: BasePhase_run統合
- **目的**: BasePhaseの`run()`メソッドとDesignPhaseの統合が正しく動作することを検証
- **前提条件**:
  - DesignPhaseがBasePhaseを継承している
  - requirements.mdが存在する
- **入力**: なし
- **期待結果**:
  - `run()`メソッドが`execute()` → `review()` → （必要に応じて`revise()`）のフローを実行する
  - フェーズステータスが適切に更新される
- **テストデータ**:
  - モックされたClaude APIレスポンス
  - requirements.mdファイル

---

## 3. テストデータ

### 3.1 モックデータ

#### 3.1.1 Claude APIレスポンス（設計書生成）

```python
MOCK_DESIGN_RESPONSE = {
    "type": "message",
    "content": [
        {
            "type": "text",
            "text": """# 詳細設計書: AI駆動開発自動化ワークフローMVP v1.0.0

## ドキュメント情報
- Issue番号: #304
- バージョン: v1.0.0

---

## 2. 実装戦略判断

### 実装戦略: EXTEND

**判断根拠**:
- 既存コードを拡張

---

## 3. テスト戦略判断

### テスト戦略: UNIT_BDD

**判断根拠**:
- UnitテストとBDDテスト

---

## 4. テストコード戦略判断

### テストコード戦略: EXTEND_TEST

**判断根拠**:
- 既存テストを拡張
"""
        }
    ]
}
```

#### 3.1.2 Claude APIレスポンス（レビュー - PASS）

```python
MOCK_REVIEW_PASS = {
    "type": "message",
    "content": [
        {
            "type": "text",
            "text": """**判定: PASS**

## レビュー結果

設計書は要件定義書の内容を正しく反映しています。

- 実装戦略の判断根拠が明確です
- テスト戦略の選択が適切です
- 既存コードへの影響分析が十分です
"""
        }
    ]
}
```

#### 3.1.3 Claude APIレスポンス（レビュー - FAIL）

```python
MOCK_REVIEW_FAIL = {
    "type": "message",
    "content": [
        {
            "type": "text",
            "text": """**判定: FAIL**

## 修正が必要な点

- 実装戦略の判断根拠が不足しています
- セキュリティ考慮事項の記載が不十分です
- 非機能要件への対応が欠けています
"""
        }
    ]
}
```

#### 3.1.4 Claude APIレスポンス（修正版設計書）

```python
MOCK_REVISED_DESIGN = {
    "type": "message",
    "content": [
        {
            "type": "text",
            "text": """# 詳細設計書: AI駆動開発自動化ワークフローMVP v1.0.0（修正版）

## ドキュメント情報
- Issue番号: #304
- バージョン: v1.0.1（修正版）

---

## 2. 実装戦略判断

### 実装戦略: EXTEND

**判断根拠**:
1. 既存コードベースの存在（詳細に記載）
2. 既存パターンの踏襲（具体例を追加）
3. 影響範囲の限定性（分析結果を追加）

---

## 8. セキュリティ考慮事項（追加）

### 8.1 認証・認可
- GitHub API認証: Personal Access Token
- Claude API認証: API Key

---

## 9. 非機能要件への対応（追加）

### 9.1 パフォーマンス
- NFR-001: ワークフロー初期化は5秒以内
"""
        }
    ]
}
```

### 3.2 テストフィクスチャ

#### 3.2.1 requirements.md（テスト用）

```markdown
# 要件定義書: AI駆動開発自動化ワークフローMVP v1.0.0

## 1. 概要
テスト用の要件定義書です。

## 2. 機能要件
- FR-001: ワークフロー初期化機能
- FR-002: 状態管理機能

## 6. 受け入れ基準
- ワークフローが正常に初期化される
- metadata.jsonが正しく更新される
```

#### 3.2.2 metadata.json（テスト用）

```json
{
  "issue_number": "304",
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/304",
  "issue_title": "Test Issue",
  "workflow_version": "1.0.0",
  "current_phase": "design",
  "design_decisions": null,
  "phases": {
    "requirements": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-09T00:00:00.000000Z",
      "completed_at": "2025-10-09T00:05:00.000000Z",
      "review_result": "PASS"
    },
    "design": {
      "status": "in_progress",
      "retry_count": 0,
      "started_at": "2025-10-09T00:10:00.000000Z",
      "completed_at": null,
      "review_result": null
    }
  },
  "created_at": "2025-10-09T00:00:00.000000Z",
  "updated_at": "2025-10-09T00:10:00.000000Z"
}
```

---

## 4. テスト環境要件

### 4.1 ローカル開発環境
- **Python**: 3.8以上
- **必須パッケージ**:
  - pytest
  - pytest-mock
  - pytest-cov
  - click
  - behave（BDDテスト用、ただし今回はUNIT_ONLYなので参考）

### 4.2 モック/スタブの必要性

#### 4.2.1 ClaudeAgentClient（モック必須）
- **理由**: 実際のClaude APIを呼び出すとコストがかかり、テスト実行時間も長くなる
- **モック対象**: `execute_task_sync()`メソッド
- **モック方法**: `pytest-mock`を使用して、事前定義されたレスポンスを返す

#### 4.2.2 GitHubClient（モック推奨）
- **理由**: 実際のGitHub APIを呼び出すとレート制限に引っかかる可能性がある
- **モック対象**: `post_comment()`メソッド
- **モック方法**: `pytest-mock`を使用

#### 4.2.3 ファイルシステム（実ファイル使用）
- **理由**: ファイルI/Oのテストは実ファイルで行う方が信頼性が高い
- **対策**: テスト用の一時ディレクトリ（`tmpdir`フィクスチャ）を使用
- **クリーンアップ**: テスト終了後に自動削除

### 4.3 CI/CD環境
- **Jenkins**: テスト実行パイプラインで使用
- **Docker**: テスト実行環境の統一（将来対応）
- **GitHub Actions**: PR時の自動テスト実行（将来対応）

---

## 5. テストカバレッジ目標

### 5.1 カバレッジ目標
- **全体カバレッジ**: 80%以上
- **DesignPhaseクラス**: 90%以上
- **クリティカルパス**: 100%

### 5.2 カバレッジ除外
以下のコードはカバレッジ計測から除外：
- `if __name__ == "__main__":` ブロック
- デバッグ用のprint文
- 例外ハンドリング内の詳細ログ出力（実行は困難）

---

## 6. テスト実行方法

### 6.1 全Unitテスト実行
```bash
cd /workspace/scripts/ai-workflow
pytest tests/unit/phases/test_design_phase.py -v
```

### 6.2 カバレッジ測定
```bash
pytest tests/unit/phases/test_design_phase.py --cov=phases.design --cov-report=html
```

### 6.3 特定テストケースのみ実行
```bash
pytest tests/unit/phases/test_design_phase.py::test_DesignPhase_execute_正常系 -v
```

---

## 7. 品質ゲートチェック

### ✅ Phase 2の戦略に沿ったテストシナリオである
- **確認**: UNIT_ONLY戦略に基づき、Unitテストのみを作成
- **根拠**: BDD/Integrationテストシナリオは含めていない

### ✅ 主要な正常系がカバーされている
- **確認**: 以下の正常系シナリオをカバー
  - DesignPhase初期化（テストケース1）
  - 設計書生成（テストケース3）
  - レビューPASS（テストケース7）
  - レビューFAIL（テストケース9）
  - 設計書修正（テストケース12）
  - フルフロー（テストケース24-26）

### ✅ 主要な異常系がカバーされている
- **確認**: 以下の異常系シナリオをカバー
  - metadata.json不在（テストケース2）
  - requirements.md不在（テストケース4）
  - Claude API失敗（テストケース5, 14）
  - 空のフィードバック（テストケース13）
  - パース失敗（テストケース11, 18, 22, 23）

### ✅ 期待結果が明確である
- **確認**: すべてのテストケースに以下を記載
  - 具体的な入力値
  - 期待される出力形式（Pythonディクショナリ形式）
  - ファイルシステムへの影響（作成/更新されるファイル）
  - metadata.jsonへの影響

---

## 8. 補足情報

### 8.1 テスト実装時の注意事項

1. **モックの適切な使用**
   - Claude APIは必ずモック化する（実APIを呼ばない）
   - ファイルシステムは実ファイルを使用（`tmpdir`フィクスチャ）
   - 環境変数のモックも必要に応じて実施

2. **テストの独立性**
   - 各テストケースは独立して実行可能にする
   - テスト間で共有状態を持たない
   - `setUp`/`tearDown`で環境を初期化/クリーンアップ

3. **エラーメッセージの検証**
   - 異常系テストでは、エラーメッセージの内容も検証する
   - ユーザーフレンドリーなエラーメッセージであることを確認

4. **タイムスタンプの扱い**
   - タイムスタンプの検証は相対的に行う（現在時刻との差分が許容範囲内か）
   - 固定値での比較は避ける

### 8.2 Phase 4（実装フェーズ）への引き継ぎ事項

1. **テストファーストで実装**
   - 本テストシナリオに基づいてテストコードを先に作成
   - その後、テストがパスするようにDesignPhaseを実装

2. **リファクタリング時もテスト維持**
   - 実装中にリファクタリングを行う場合も、テストがパスし続けることを確認
   - テストが失敗する場合は、実装ではなくテストを見直す

3. **カバレッジの継続的な確認**
   - 実装完了後、カバレッジ80%以上を達成していることを確認
   - 未カバー箇所は意図的なものか確認

### 8.3 参考ドキュメント
- [要件定義書](/workspace/.ai-workflow/issue-304/01_requirements/output/requirements.md)
- [詳細設計書](/workspace/.ai-workflow/issue-304/02_design/output/design.md)
- [pytest公式ドキュメント](https://docs.pytest.org/)
- [pytest-mock公式ドキュメント](https://pytest-mock.readthedocs.io/)

---

**End of Document**
