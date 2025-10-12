# 詳細設計書 - Issue #363

**作成日**: 2025-10-12
**対象Issue**: [AI-WORKFLOW] 全フェーズ完了後のPull Request内容の自動更新
**Issue URL**: https://github.com/tielec/infrastructure-as-code/issues/363

---

## 目次

1. [実装戦略判断](#1-実装戦略判断)
2. [テスト戦略判断](#2-テスト戦略判断)
3. [テストコード戦略判断](#3-テストコード戦略判断)
4. [アーキテクチャ設計](#4-アーキテクチャ設計)
5. [影響範囲分析](#5-影響範囲分析)
6. [変更・追加ファイルリスト](#6-変更追加ファイルリスト)
7. [詳細設計](#7-詳細設計)
8. [セキュリティ考慮事項](#8-セキュリティ考慮事項)
9. [非機能要件への対応](#9-非機能要件への対応)
10. [実装の順序](#10-実装の順序)

---

## 1. 実装戦略判断

### 実装戦略: **EXTEND（拡張）**

#### 判断根拠

1. **既存クラスへの機能追加**
   - `GitHubClient` クラス（`scripts/ai-workflow/core/github_client.py`）に新規メソッドを追加
   - 既存のPR作成機能（`create_pull_request()`, lines 336-416）と同様のパターンで実装可能
   - 既存の GitHub API wrapper（PyGithub）を活用できる

2. **既存フェーズへの統合**
   - `ReportPhase` クラス（`scripts/ai-workflow/phases/report.py`）の `execute()` メソッドに処理を追加
   - 既存の成果物取得ロジック（`_get_phase_outputs()`, lines 331-351）を再利用可能
   - Phase 8完了時の処理フローに自然に組み込める

3. **既存テンプレート管理の拡張**
   - 既存の `pr_body_template.md`（簡易版）と同じディレクトリに詳細版テンプレートを追加
   - 既存のテンプレート読み込みロジック（`_generate_pr_body_template()`, lines 478-512）を参考に実装

4. **新規クラス作成は不要**
   - 既存コンポーネントの拡張で要件を満たせる
   - アーキテクチャの大幅な変更は必要なし

#### 実装範囲

- **拡張対象**:
  - `GitHubClient` クラス: 3つの新規メソッド追加
  - `ReportPhase` クラス: `execute()` メソッドの後処理に統合
  - テンプレート: 詳細版PR本文テンプレートの新規作成

- **新規作成は不要**:
  - 新規クラス・モジュールの作成なし
  - 既存インターフェースの変更なし

---

## 2. テスト戦略判断

### テスト戦略: **UNIT_INTEGRATION（ユニットテスト + インテグレーションテスト）**

#### 判断根拠

1. **ユニットテストが必要な理由**
   - **`GitHubClient.update_pull_request()`**: GitHub APIとの通信をモック化して単体テスト
     - 正常系: PR更新成功
     - 異常系: PR未存在（404 Not Found）、権限エラー（401/403）、API制限（429 Rate Limit）
   - **`GitHubClient._generate_pr_body_detailed()`**: テンプレート置換ロジックの検証
     - プレースホルダー置換の正確性
     - 成果物情報の適切な埋め込み
   - **`GitHubClient._extract_phase_outputs()`**: 成果物パース処理の検証
     - 各フェーズのMarkdownファイルから情報抽出
     - 欠落データへのフォールバック動作

2. **インテグレーションテストが必要な理由**
   - **Phase 8完了 → PR更新のE2Eフロー**: 実際の処理フロー全体を検証
     - `ReportPhase.execute()` 完了後にPR更新が実行されること
     - メタデータから `pr_number` が正しく取得されること
     - 成果物パスが正しく収集されること
   - **GitHub API連携**: モックを使用した統合テスト
     - PR取得 → 本文生成 → PR更新の一連の流れ
     - エラーハンドリングの動作確認

3. **BDDテストが不要な理由**
   - **エンドユーザー向けUIではない**: 内部処理の拡張であり、Given-When-Then形式のBDDシナリオは不要
   - **ビジネスロジックよりも技術的処理**: ユーザーストーリーではなく、技術的な統合処理

#### テスト対象

| テストレベル | 対象 | テスト項目 |
|------------|------|-----------|
| **ユニットテスト** | `GitHubClient.update_pull_request()` | PR更新成功、PR未存在エラー、権限エラー、API制限エラー |
| **ユニットテスト** | `GitHubClient._generate_pr_body_detailed()` | テンプレート置換、プレースホルダー埋め込み |
| **ユニットテスト** | `GitHubClient._extract_phase_outputs()` | 成果物パース、フィールド抽出、欠落時のフォールバック |
| **インテグレーションテスト** | `ReportPhase.execute()` → PR更新 | Phase 8完了時のPR更新フロー |
| **インテグレーションテスト** | GitHub API連携 | モックを使用したPR取得・更新の統合動作 |

---

## 3. テストコード戦略判断

### テストコード戦略: **BOTH_TEST（既存テスト拡張 + 新規テスト作成）**

#### 判断根拠

1. **既存テストファイルへの追加が必要（EXTEND_TEST）**
   - **既存テストファイル**: 現在 `tests/` ディレクトリにはテストファイルが存在しない（Glob検索結果: 0件）
   - しかし、`GitHubClient` のユニットテストは `tests/unit/core/test_github_client.py` に配置すべき
   - 将来的に既存テストが追加された場合、統一性を保つため

2. **新規テストファイルの作成が必要（CREATE_TEST）**
   - **新規ユニットテストファイル**: `tests/unit/core/test_github_client.py`
     - `GitHubClient` の新規メソッドをテスト
     - 既存メソッド（`create_pull_request()`, `check_existing_pr()`）のテストも今後追加可能
   - **新規インテグレーションテストファイル**: `tests/integration/test_pr_update_integration.py`
     - Phase 8完了 → PR更新のE2Eフローをテスト
     - GitHub API連携のモックテスト

3. **テストディレクトリ構造の整備**
   - 現在テストファイルが存在しないため、推奨ディレクトリ構造を構築
   ```
   tests/
   ├── unit/
   │   ├── core/
   │   │   ├── __init__.py
   │   │   └── test_github_client.py  # 新規作成
   │   └── phases/
   │       ├── __init__.py
   │       └── test_report.py  # 将来的に追加（オプション）
   └── integration/
       ├── __init__.py
       └── test_pr_update_integration.py  # 新規作成
   ```

#### テストファイル配置

| ファイルパス | テストタイプ | 対象 |
|------------|------------|------|
| `tests/unit/core/test_github_client.py` | ユニットテスト | `GitHubClient` 新規メソッド |
| `tests/integration/test_pr_update_integration.py` | インテグレーションテスト | Phase 8 → PR更新フロー |

---

## 4. アーキテクチャ設計

### 4.1 システム全体図

```
┌─────────────────────────────────────────────────────────────────┐
│                       AI Workflow System                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │   Phase 0: Planning │
                    │   (PR作成)          │
                    └─────────────────────┘
                                │
                                │ 簡易版PR本文
                                │ (pr_body_template.md)
                                ▼
                    ┌─────────────────────┐
                    │  GitHub Repository  │
                    │  Pull Request #XXX  │
                    │  (Draft状態)        │
                    └─────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
    ┌─────────────────────┐       ┌─────────────────────┐
    │ Phase 1-7: 実行中    │       │ PR本文: 簡易版      │
    │ (各フェーズ成果物)   │       │ (チェックリスト更新) │
    └─────────────────────┘       └─────────────────────┘
                │
                ▼
    ┌─────────────────────┐
    │ Phase 8: Report     │
    │ (最終レポート作成)   │
    └─────────────────────┘
                │
                │ Phase 8完了
                ▼
    ┌─────────────────────────────────────┐
    │   ReportPhase.execute()             │
    │   1. report.md 生成                 │
    │   2. PR更新処理を呼び出し ← NEW!    │
    └─────────────────────────────────────┘
                │
                ▼
    ┌─────────────────────────────────────┐
    │   GitHubClient.update_pull_request()│
    │   1. 成果物情報を抽出               │
    │   2. 詳細版PR本文を生成             │
    │   3. GitHub APIでPR更新             │
    └─────────────────────────────────────┘
                │
                ▼
    ┌─────────────────────┐
    │  GitHub Repository  │
    │  Pull Request #XXX  │
    │  (詳細版本文に更新) │
    └─────────────────────┘
```

### 4.2 コンポーネント間の関係

```
┌────────────────────────────────────────────────────────────────┐
│                      GitHubClient                              │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  既存メソッド                                             │ │
│  │  - create_pull_request()  (PR作成)                       │ │
│  │  - check_existing_pr()    (既存PR確認)                   │ │
│  │  - _generate_pr_body_template()  (簡易版本文生成)        │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  新規メソッド ← NEW!                                      │ │
│  │  - update_pull_request()         (PR更新)                │ │
│  │  - _generate_pr_body_detailed()  (詳細版本文生成)        │ │
│  │  - _extract_phase_outputs()      (成果物情報抽出)        │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                              ▲
                              │ 呼び出し
                              │
┌────────────────────────────────────────────────────────────────┐
│                       ReportPhase                              │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  execute()                                                │ │
│  │  1. 各フェーズ成果物を収集                                 │ │
│  │  2. report.md 生成                                        │ │
│  │  3. PR更新処理を実行 ← NEW!                               │ │
│  │     - メタデータから pr_number 取得                        │ │
│  │     - update_pull_request() 呼び出し                      │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  _get_phase_outputs()                                     │ │
│  │  - 各フェーズの成果物パスを返却（既存メソッド、再利用）    │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                  テンプレートファイル                           │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  scripts/ai-workflow/templates/                           │ │
│  │  - pr_body_template.md         (簡易版、既存)             │ │
│  │  - pr_body_detailed_template.md (詳細版、新規作成)        │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

### 4.3 データフロー

```
┌──────────────────────────────────────────────────────────────────┐
│  1. Phase 8 完了トリガー                                          │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  2. ReportPhase.execute() 実行                                    │
│     - report.md 生成成功                                          │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  3. メタデータから PR番号を取得                                   │
│     metadata.data['pr_number']                                    │
│     ├─ 存在する → PR番号を使用                                    │
│     └─ 存在しない → check_existing_pr() で検索                    │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  4. 各フェーズの成果物パスを取得                                  │
│     _get_phase_outputs(issue_number)                              │
│     {                                                             │
│       'requirements': '.../requirements.md',                      │
│       'design': '.../design.md',                                  │
│       'test_scenario': '.../test-scenario.md',                    │
│       'implementation': '.../implementation.md',                  │
│       'test_implementation': '.../test-implementation.md',        │
│       'test_result': '.../test-result.md',                        │
│       'documentation': '.../documentation-update-log.md'          │
│     }                                                             │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  5. _extract_phase_outputs(phase_outputs) 実行                    │
│     各成果物から情報抽出:                                          │
│     - Issue本文 → summary                                         │
│     - Phase 4 → implementation_details                            │
│     - Phase 6 → test_results                                      │
│     - Phase 7 → documentation_updates                             │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  6. _generate_pr_body_detailed() 実行                             │
│     - pr_body_detailed_template.md 読み込み                       │
│     - プレースホルダー置換                                         │
│       {issue_number}, {branch_name}, {summary},                   │
│       {implementation_details}, {test_results},                   │
│       {documentation_updates}, {review_points}                    │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  7. update_pull_request(pr_number, body) 実行                     │
│     - repository.get_pull(pr_number)                              │
│     - pr.edit(body=new_body)                                      │
│     - GitHub APIでPR本文を更新                                    │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  8. 結果ログ出力                                                  │
│     - 成功: "[INFO] PR更新成功: <PR_URL>"                         │
│     - 失敗: "[WARNING] PR更新失敗: <エラーメッセージ>"            │
│     ※ Phase 8全体は成功として継続                                 │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. 影響範囲分析

### 5.1 既存コードへの影響

#### 修正が必要な既存ファイル

| ファイルパス | 修正箇所 | 修正内容 | 影響レベル |
|------------|---------|---------|-----------|
| `scripts/ai-workflow/core/github_client.py` | 新規メソッド追加 | `update_pull_request()`, `_generate_pr_body_detailed()`, `_extract_phase_outputs()` を追加 | 低（新規メソッド追加のみ） |
| `scripts/ai-workflow/phases/report.py` | `execute()` メソッド末尾 | Phase 8完了後、PR更新処理を追加（lines 107-116の後） | 低（後処理追加） |

#### 既存メソッドへの影響

- **`GitHubClient` の既存メソッド**: 影響なし
  - `create_pull_request()`: 変更不要
  - `check_existing_pr()`: 既存のまま利用（PR番号検索用）
  - `_generate_pr_body_template()`: 変更不要（Phase 0での簡易版生成に継続使用）

- **`ReportPhase` の既存メソッド**: 影響なし
  - `_get_phase_outputs()`: 変更不要（既存のまま再利用）
  - `review()`, `revise()`: 変更不要

### 5.2 依存関係の変更

#### 新規依存の追加

- **なし**（既存の `PyGithub` ライブラリを活用）

#### 既存依存の変更

- **なし**

### 5.3 マイグレーション要否

#### データベーススキーマ変更

- **なし**

#### 設定ファイル変更

- **なし**（テンプレートの追加のみ）

#### 環境変数追加

- **なし**（既存の `GITHUB_TOKEN` を使用）

#### メタデータ構造の変更

- **なし**（既存の `pr_number` を使用）

---

## 6. 変更・追加ファイルリスト

### 6.1 新規作成ファイル

| ファイルパス | 説明 | 理由 |
|------------|------|------|
| `scripts/ai-workflow/templates/pr_body_detailed_template.md` | 詳細版PR本文テンプレート | 成果物情報を含む詳細版PR本文を生成するため |
| `tests/unit/core/__init__.py` | テストパッケージ初期化 | Pythonパッケージとして認識させるため |
| `tests/unit/core/test_github_client.py` | `GitHubClient` ユニットテスト | 新規メソッドのユニットテストを実装 |
| `tests/integration/__init__.py` | テストパッケージ初期化 | Pythonパッケージとして認識させるため |
| `tests/integration/test_pr_update_integration.py` | PR更新統合テスト | Phase 8 → PR更新のE2Eフローをテスト |

### 6.2 修正が必要な既存ファイル

| ファイルパス | 修正箇所 | 修正内容 |
|------------|---------|---------|
| `scripts/ai-workflow/core/github_client.py` | クラス末尾（line 844付近） | 3つの新規メソッドを追加 |
| `scripts/ai-workflow/phases/report.py` | `execute()` メソッド末尾（lines 107-125付近） | PR更新処理を追加（try-except内） |

### 6.3 削除が必要なファイル

- **なし**

---

## 7. 詳細設計

### 7.1 クラス設計

#### 7.1.1 `GitHubClient` クラス拡張

**場所**: `scripts/ai-workflow/core/github_client.py`

##### 新規メソッド1: `update_pull_request()`

**シグネチャ**:
```python
def update_pull_request(
    self,
    pr_number: int,
    body: str
) -> Dict[str, Any]:
```

**引数**:
- `pr_number` (int): PR番号
- `body` (str): 新しいPR本文（Markdown形式）

**戻り値**:
```python
Dict[str, Any]: {
    'success': bool,    # 成功/失敗
    'error': Optional[str]  # エラーメッセージ（成功時はNone）
}
```

**処理フロー**:
1. `repository.get_pull(pr_number)` でPRを取得
2. `pr.edit(body=body)` でPR本文を更新
3. 成功時は `{'success': True, 'error': None}` を返却
4. 失敗時はエラーメッセージを返却

**エラーハンドリング**:
```python
try:
    pr = self.repository.get_pull(pr_number)
    pr.edit(body=body)
    return {'success': True, 'error': None}
except GithubException as e:
    if e.status == 404:
        return {'success': False, 'error': f'PR #{pr_number} not found'}
    elif e.status == 401 or e.status == 403:
        return {'success': False, 'error': 'GitHub Token lacks PR edit permissions'}
    elif e.status == 429:
        return {'success': False, 'error': 'GitHub API rate limit exceeded'}
    else:
        return {'success': False, 'error': f'GitHub API error: {e.status} - {e.data.get("message", "Unknown")}'}
except Exception as e:
    return {'success': False, 'error': f'Unexpected error: {e}'}
```

---

##### 新規メソッド2: `_generate_pr_body_detailed()`

**シグネチャ**:
```python
def _generate_pr_body_detailed(
    self,
    issue_number: int,
    branch_name: str,
    extracted_info: Dict[str, Any]
) -> str:
```

**引数**:
- `issue_number` (int): Issue番号
- `branch_name` (str): ブランチ名
- `extracted_info` (Dict[str, Any]): 抽出された成果物情報
  ```python
  {
      'summary': str,                     # 変更サマリー
      'implementation_details': str,      # 実装詳細
      'test_results': str,                # テスト結果
      'documentation_updates': str,       # ドキュメント更新リスト
      'review_points': str                # レビューポイント
  }
  ```

**戻り値**:
- `str`: 詳細版PR本文（Markdown形式）

**処理フロー**:
1. テンプレートファイル `pr_body_detailed_template.md` を読み込み
2. プレースホルダーを置換
   ```python
   template.format(
       issue_number=issue_number,
       branch_name=branch_name,
       summary=extracted_info['summary'],
       implementation_details=extracted_info['implementation_details'],
       test_results=extracted_info['test_results'],
       documentation_updates=extracted_info['documentation_updates'],
       review_points=extracted_info['review_points']
   )
   ```
3. 生成されたPR本文を返却

**エラーハンドリング**:
```python
from pathlib import Path

try:
    template_path = Path(__file__).parent.parent / 'templates' / 'pr_body_detailed_template.md'
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    return template.format(**extracted_info, issue_number=issue_number, branch_name=branch_name)
except FileNotFoundError:
    raise FileNotFoundError(f"Template file not found: {template_path}")
except KeyError as e:
    raise KeyError(f"Missing placeholder in template: {e}")
```

---

##### 新規メソッド3: `_extract_phase_outputs()`

**シグネチャ**:
```python
def _extract_phase_outputs(
    self,
    issue_number: int,
    phase_outputs: Dict[str, Path]
) -> Dict[str, Any]:
```

**引数**:
- `issue_number` (int): Issue番号
- `phase_outputs` (Dict[str, Path]): フェーズ名 → 成果物パス
  ```python
  {
      'requirements': Path('.ai-workflow/issue-XXX/01_requirements/output/requirements.md'),
      'design': Path('.ai-workflow/issue-XXX/02_design/output/design.md'),
      'test_scenario': Path('.ai-workflow/issue-XXX/03_test_scenario/output/test-scenario.md'),
      'implementation': Path('.ai-workflow/issue-XXX/04_implementation/output/implementation.md'),
      'test_implementation': Path('.ai-workflow/issue-XXX/05_test_implementation/output/test-implementation.md'),
      'test_result': Path('.ai-workflow/issue-XXX/06_testing/output/test-result.md'),
      'documentation': Path('.ai-workflow/issue-XXX/07_documentation/output/documentation-update-log.md')
  }
  ```

**戻り値**:
```python
Dict[str, Any]: {
    'summary': str,                     # 変更サマリー（Issueから抽出）
    'implementation_details': str,      # 実装詳細（Phase 4から抽出）
    'test_results': str,                # テスト結果（Phase 6から抽出）
    'documentation_updates': str,       # ドキュメント更新リスト（Phase 7から抽出）
    'review_points': str                # レビューポイント（設計書から抽出）
}
```

**処理フロー**:

1. **Issue本文から概要（summary）を抽出**
   ```python
   issue = self.get_issue(issue_number)
   summary = self._extract_summary_from_issue(issue.body)
   ```

2. **Phase 4（implementation.md）から実装詳細を抽出**
   ```python
   impl_path = phase_outputs['implementation']
   if impl_path.exists():
       content = impl_path.read_text(encoding='utf-8')
       implementation_details = self._extract_section(content, '## 実装内容')
   else:
       implementation_details = '（実装詳細の記載なし）'
   ```

3. **Phase 6（test-result.md）からテスト結果を抽出**
   ```python
   test_path = phase_outputs['test_result']
   if test_path.exists():
       content = test_path.read_text(encoding='utf-8')
       test_results = self._extract_section(content, '## テスト結果サマリー')
   else:
       test_results = '（テスト結果の記載なし）'
   ```

4. **Phase 7（documentation-update-log.md）からドキュメント更新リストを抽出**
   ```python
   doc_path = phase_outputs['documentation']
   if doc_path.exists():
       content = doc_path.read_text(encoding='utf-8')
       documentation_updates = self._extract_section(content, '## 更新されたドキュメント')
   else:
       documentation_updates = '（ドキュメント更新の記載なし）'
   ```

5. **設計書からレビューポイントを抽出**
   ```python
   design_path = phase_outputs['design']
   if design_path.exists():
       content = design_path.read_text(encoding='utf-8')
       review_points = self._extract_section(content, '## レビューポイント')
   else:
       review_points = '（レビューポイントの記載なし）'
   ```

**ヘルパーメソッド**: `_extract_section()`

```python
def _extract_section(self, content: str, section_header: str) -> str:
    """
    Markdown文書から特定セクションを抽出

    Args:
        content: Markdown文書全体
        section_header: 抽出したいセクションのヘッダー（例: "## 実装内容"）

    Returns:
        str: 抽出されたセクションの内容（ヘッダー以降、次のヘッダーまで）
    """
    lines = content.split('\n')
    section_lines = []
    in_section = False

    for line in lines:
        if line.strip().startswith(section_header):
            in_section = True
            continue
        elif line.strip().startswith('##') and in_section:
            # 次のセクションに到達したら終了
            break
        elif in_section:
            section_lines.append(line)

    return '\n'.join(section_lines).strip()
```

**エラーハンドリング**:
```python
try:
    # 各フェーズから情報抽出
    extracted = {
        'summary': summary,
        'implementation_details': implementation_details,
        'test_results': test_results,
        'documentation_updates': documentation_updates,
        'review_points': review_points
    }
    return extracted
except Exception as e:
    print(f"[WARNING] 成果物抽出中にエラー: {e}")
    # デフォルト値を返却
    return {
        'summary': '（情報抽出エラー）',
        'implementation_details': '（情報抽出エラー）',
        'test_results': '（情報抽出エラー）',
        'documentation_updates': '（情報抽出エラー）',
        'review_points': '（情報抽出エラー）'
    }
```

---

#### 7.1.2 `ReportPhase` クラス拡張

**場所**: `scripts/ai-workflow/phases/report.py`

##### 修正箇所: `execute()` メソッド

**修正位置**: line 107（GitHub成果物投稿後）の後に追加

**追加コード**:
```python
# PR本文を更新（Phase 8完了時）
try:
    print("[INFO] PR本文を詳細版に更新します")

    # メタデータからPR番号を取得
    pr_number = self.metadata.data.get('pr_number')

    if not pr_number:
        print("[WARNING] メタデータにpr_numberが保存されていません。既存PRを検索します。")
        branch_name = self.metadata.data.get('branch_name', f'ai-workflow/issue-{issue_number}')
        existing_pr = self.github_client.check_existing_pr(head=branch_name)
        if existing_pr:
            pr_number = existing_pr['pr_number']
            print(f"[INFO] 既存PRが見つかりました: #{pr_number}")
        else:
            print("[WARNING] PRが見つかりませんでした。PR更新をスキップします。")
            pr_number = None

    if pr_number:
        # 成果物情報を抽出
        extracted_info = self.github_client._extract_phase_outputs(
            issue_number=issue_number,
            phase_outputs=phase_outputs
        )

        # 詳細版PR本文を生成
        branch_name = self.metadata.data.get('branch_name', f'ai-workflow/issue-{issue_number}')
        pr_body_detailed = self.github_client._generate_pr_body_detailed(
            issue_number=issue_number,
            branch_name=branch_name,
            extracted_info=extracted_info
        )

        # PR本文を更新
        result = self.github_client.update_pull_request(
            pr_number=pr_number,
            body=pr_body_detailed
        )

        if result['success']:
            print(f"[INFO] PR本文の更新に成功しました: PR #{pr_number}")
        else:
            print(f"[WARNING] PR本文の更新に失敗しました: {result['error']}")

except Exception as e:
    print(f"[WARNING] PR更新処理でエラーが発生しました: {e}")
    print("[INFO] Phase 8は成功として継続します")
```

**エラーハンドリングの方針**:
- **PR更新失敗時でもPhase 8全体は成功として継続**
  - PR更新は「ベストエフォート」処理
  - 失敗しても最終レポート（report.md）は生成されている
  - 警告ログを出力して手動でPR更新を促す

---

### 7.2 データ構造設計

#### 7.2.1 テンプレート構造

**ファイル**: `scripts/ai-workflow/templates/pr_body_detailed_template.md`

**プレースホルダー**:
```markdown
## AI Workflow自動生成PR

### 📋 関連Issue
Closes #{issue_number}

### 📝 変更サマリー
{summary}

### 🔄 ワークフロー進捗

- [x] Phase 0: Planning
- [x] Phase 1: Requirements
- [x] Phase 2: Design
- [x] Phase 3: Test Scenario
- [x] Phase 4: Implementation
- [x] Phase 5: Test Implementation
- [x] Phase 6: Testing
- [x] Phase 7: Documentation
- [x] Phase 8: Report

### 🔧 実装詳細

{implementation_details}

### ✅ テスト結果

{test_results}

### 📚 ドキュメント更新

{documentation_updates}

### 👀 レビューポイント

{review_points}

### 📁 成果物

`.ai-workflow/issue-{issue_number}/` ディレクトリに各フェーズの成果物が格納されています。

### ⚙️ 実行環境

- **モデル**: Claude Code Pro Max (Sonnet 4.5)
- **ContentParser**: OpenAI GPT-4o mini
- **ブランチ**: {branch_name}
```

---

### 7.3 インターフェース設計

#### 7.3.1 既存インターフェースとの互換性

**変更なし**:
- `GitHubClient.__init__()`: 変更不要
- `GitHubClient.create_pull_request()`: 変更不要
- `ReportPhase.__init__()`: 変更不要
- `ReportPhase.review()`: 変更不要
- `ReportPhase.revise()`: 変更不要

**新規追加**:
- `GitHubClient.update_pull_request()`: 新規publicメソッド
- `GitHubClient._generate_pr_body_detailed()`: 新規privateメソッド
- `GitHubClient._extract_phase_outputs()`: 新規privateメソッド

---

## 8. セキュリティ考慮事項

### 8.1 認証・認可

**GitHub Token の権限**:
- **必要スコープ**: `repo`（リポジトリへの完全アクセス）
- **PR編集権限**: `repository.get_pull(number).edit()` にはrepoスコープが必要
- **エラーハンドリング**: 権限不足時は `401 Unauthorized` または `403 Forbidden` を返却

**環境変数**:
```python
self.token = token or os.getenv('GITHUB_TOKEN')
```
- 環境変数 `GITHUB_TOKEN` から取得
- ハードコーディング禁止

### 8.2 データ保護

**SecureString使用**:
- GitHub Tokenは環境変数またはSSMパラメータストア（SecureString）で管理
- ログ出力時にトークンを含めない

**PR本文のサニタイゼーション**:
- 成果物から抽出した情報はMarkdown形式であることを前提
- 特殊文字のエスケープは不要（GitHub APIが自動処理）

### 8.3 セキュリティリスクと対策

| リスク | 対策 |
|--------|------|
| **GitHub Token漏洩** | 環境変数で管理、ログ出力時にマスク |
| **API Rate Limit到達** | エラーハンドリングで `429 Rate Limit Exceeded` を検知、警告ログ出力 |
| **PR本文への機密情報混入** | 成果物生成時に機密情報を含めないよう注意（別タスクで対応） |
| **権限エラー** | `401/403` エラーを検知、エラーメッセージで権限不足を通知 |

---

## 9. 非機能要件への対応

### 9.1 パフォーマンス

**PR更新処理時間**: 5秒以内（NFR-1）

| 処理 | 想定時間 |
|------|---------|
| `repository.get_pull(pr_number)` | 1-2秒 |
| `_extract_phase_outputs()` | 2-3秒 |
| `_generate_pr_body_detailed()` | < 1秒 |
| `pr.edit(body=body)` | 1-2秒 |
| **合計** | **5秒以内** |

**成果物パース処理**: 10秒以内（NFR-1）

| 処理 | 想定時間 |
|------|---------|
| 7ファイルの読み込み | 2-3秒 |
| Markdownパース | 3-5秒 |
| セクション抽出 | 2-3秒 |
| **合計** | **10秒以内** |

**GitHub API呼び出し回数**: Phase 8実行時に追加で2回以内（NFR-1）
- `repository.get_pull(pr_number)`: 1回
- `pr.edit(body=body)`: 1回

### 9.2 スケーラビリティ

**成果物ファイル数の増加**:
- 現在7フェーズ（Phase 1-7）の成果物を処理
- 将来的にフェーズ追加時も `_get_phase_outputs()` に追加すれば対応可能

**PR本文の最大長**:
- GitHub APIの制限: 理論上1MB（実用上10KB程度に抑える）
- テンプレート設計時に簡潔な記載を心がける

### 9.3 保守性

**コードの可読性**:
- 各メソッドにdocstringを記載
- 処理フローをコメントで明記

**テンプレートの拡張性**:
- 新しいプレースホルダーを追加しやすい設計
- `_extract_phase_outputs()` でフィールドを追加すれば対応可能

**成果物パース処理の拡張性**:
- `_extract_section()` ヘルパーメソッドで共通化
- 新しいフェーズの成果物を追加しやすい

### 9.4 信頼性

**PR更新失敗時の挙動**:
- Phase 8全体は失敗させず、警告ログを出力して継続
- エラーメッセージで原因を明示

**成果物欠落時の挙動**:
- 必須フィールドが欠落している場合もエラーとせず、デフォルト値を使用
- 例: `'（情報抽出エラー）'`

**冪等性**:
- 同じPRに対して複数回実行しても、最新の成果物に基づいて正しく更新される
- PR本文は完全に上書きされる

---

## 10. 実装の順序

### 10.1 推奨実装順序

実装は以下の順序で進めることを推奨します：

#### ステップ1: テンプレート作成（優先度: 高）
1. `scripts/ai-workflow/templates/pr_body_detailed_template.md` を作成
   - プレースホルダーを定義
   - 既存の `pr_body_template.md` を参考にする

#### ステップ2: GitHubClient拡張（優先度: 高）
2. `GitHubClient._extract_section()` ヘルパーメソッドを実装
   - Markdownセクション抽出ロジック
3. `GitHubClient._extract_phase_outputs()` を実装
   - 各フェーズの成果物から情報抽出
4. `GitHubClient._generate_pr_body_detailed()` を実装
   - テンプレート読み込みと置換
5. `GitHubClient.update_pull_request()` を実装
   - GitHub APIでPR更新

#### ステップ3: ReportPhase統合（優先度: 高）
6. `ReportPhase.execute()` メソッドにPR更新処理を追加
   - Phase 8完了後にPR更新を実行
   - エラーハンドリングを実装

#### ステップ4: ユニットテスト実装（優先度: 中）
7. `tests/unit/core/test_github_client.py` を作成
   - `test_update_pull_request_success()`
   - `test_update_pull_request_not_found()`
   - `test_update_pull_request_api_error()`
   - `test_generate_pr_body_detailed()`
   - `test_extract_phase_outputs()`
   - `test_extract_section()`

#### ステップ5: インテグレーションテスト実装（優先度: 中）
8. `tests/integration/test_pr_update_integration.py` を作成
   - Phase 8完了 → PR更新のE2Eフロー
   - GitHub API連携テスト（モック使用）

#### ステップ6: ドキュメント整備（優先度: 低）
9. APIドキュメント（docstring）の整備
10. トラブルシューティングガイドの作成

### 10.2 依存関係の考慮

**実装順序の依存関係**:
```
ステップ1（テンプレート）
    │
    ▼
ステップ2-2（_extract_section）
    │
    ▼
ステップ2-3（_extract_phase_outputs）
    │
    ▼
ステップ2-4（_generate_pr_body_detailed）
    │
    ▼
ステップ2-5（update_pull_request）
    │
    ▼
ステップ3（ReportPhase統合）
    │
    ├───────────────────────┐
    ▼                       ▼
ステップ4              ステップ5
（ユニットテスト）      （統合テスト）
    │                       │
    └───────────────────────┘
              │
              ▼
          ステップ6
       （ドキュメント）
```

**並行実装可能な箇所**:
- ステップ4（ユニットテスト）とステップ5（統合テスト）は並行して実装可能
- ステップ6（ドキュメント）は他のステップと並行して実装可能

---

## まとめ

本設計書は、AI Workflow の Phase 8（Report）完了時に Pull Request の本文を詳細版に更新する機能の詳細設計を記載しました。

### 設計のポイント

1. **実装戦略: EXTEND（拡張）**
   - 既存の`GitHubClient`と`ReportPhase`を拡張
   - 新規クラス作成は不要
   - アーキテクチャの大幅な変更なし

2. **テスト戦略: UNIT_INTEGRATION**
   - ユニットテスト: `GitHubClient` 新規メソッドの単体テスト
   - インテグレーションテスト: Phase 8 → PR更新のE2Eフロー

3. **テストコード戦略: BOTH_TEST**
   - 既存テスト拡張: `tests/unit/core/test_github_client.py`
   - 新規テスト作成: `tests/integration/test_pr_update_integration.py`

4. **品質ゲート達成**
   - ✅ 実装戦略の判断根拠が明記されている
   - ✅ テスト戦略の判断根拠が明記されている
   - ✅ 既存コードへの影響範囲が分析されている
   - ✅ 変更が必要なファイルがリストアップされている
   - ✅ 設計が実装可能である

この設計書に基づいて、Phase 4（Implementation）で実装を進めることができます。
