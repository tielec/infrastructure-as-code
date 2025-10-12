# 要件定義書 - Issue #319

## 0. Planning Documentの確認

Planning Phaseは実行されていないため、このセクションはスキップします。

---

## 1. 概要

### 背景

現在のAIワークフローシステムは、全フェーズ（Phase 1: 要件定義 〜 Phase 8: レポート）が固定的な順次実行を前提として設計されています。各フェーズは前フェーズの成果物に強く依存しており、以下のような課題が存在します：

- **Phase 1-7の強制的な依存関係**: 各フェーズは前フェーズの成果物を必須入力として扱っているため、途中のフェーズから実行することが困難
- **小規模タスクでのオーバーヘッド**: 簡単な不具合修正や小規模な変更でも全フェーズを実行する必要があり、時間とコストが無駄になる
- **柔軟性の欠如**: 要件定義だけレビューしたい、既存の設計書に基づいて実装だけ行いたい、などの部分的な実行ニーズに対応できない

### 目的

AIワークフローの各フェーズ間の依存関係を明示化し、選択的フェーズ実行を可能にすることで、開発規模やタスクの種類に応じた柔軟なワークフロー実行を実現します。

### ビジネス価値

- **開発効率の向上**: 不要なフェーズをスキップすることで、小規模タスクの実行時間を大幅に短縮（最大80%削減）
- **コスト削減**: 不要なAI API呼び出しを削減し、運用コストを最適化
- **段階的レビューの実現**: 要件定義や設計段階でのレビューを可能にし、早期フィードバックサイクルを確立
- **既存資産の活用**: 手動作成された要件定義書や設計書を活用して、実装フェーズから開始可能

### 技術的価値

- **依存関係の明示化**: フェーズ間の依存関係をメタデータとして管理し、保守性を向上
- **拡張性の向上**: 新規フェーズの追加や依存関係の変更が容易
- **エラーハンドリングの強化**: 依存関係違反を事前検出し、明確なエラーメッセージを提供

---

## 2. 機能要件

### FR-1: フェーズ依存関係の明示化（優先度: 高）

**要件ID**: FR-1
**タイトル**: フェーズ依存関係のメタデータ定義

**説明**:
各フェーズが必要とする前提フェーズを辞書形式で定義し、システムで管理する。

**詳細要件**:
- `PHASE_DEPENDENCIES` 定数を新規追加（`Dict[str, List[str]]`）
- 各フェーズ名をキー、依存フェーズのリストを値として定義
- `requirements` フェーズは依存なし（空リスト）
- 以下の依存関係を定義:
  - `requirements`: `[]` （依存なし）
  - `design`: `['requirements']`
  - `test_scenario`: `['requirements', 'design']`
  - `implementation`: `['requirements', 'design', 'test_scenario']`
  - `test_implementation`: `['implementation']`
  - `testing`: `['implementation', 'test_implementation']`
  - `documentation`: `['implementation']`
  - `report`: `['requirements', 'design', 'implementation', 'testing', 'documentation']`

**受け入れ基準**:
- Given: AIワークフローシステムが起動している
- When: `PHASE_DEPENDENCIES`定数を参照する
- Then: 全8フェーズの依存関係が正しく定義されている

---

### FR-2: 依存関係チェック機能（優先度: 高）

**要件ID**: FR-2
**タイトル**: フェーズ実行前の依存関係検証

**説明**:
フェーズ実行前に、依存する前提フェーズがすべて完了しているかを検証する関数を実装する。

**詳細要件**:
- `validate_phase_dependencies(phase_name: str, metadata: MetadataManager) -> bool` 関数を実装
- 依存フェーズのステータスを `metadata.get_phase_status()` で確認
- 依存フェーズのステータスが `completed` 以外の場合、`DependencyError` 例外を発生
- エラーメッセージには未完了のフェーズ名を明記
- 依存関係がすべて満たされている場合は `True` を返却

**受け入れ基準**:
- Given: `requirements` フェーズが完了している
- When: `design` フェーズを実行しようとする
- Then: 依存関係チェックが成功し、実行が許可される

- Given: `requirements` フェーズが未完了
- When: `design` フェーズを実行しようとする
- Then: `DependencyError` 例外が発生し、エラーメッセージに「Phase 'requirements' must be completed before 'design'」が含まれる

---

### FR-3: CLIオプション - 依存関係チェックのスキップ（優先度: 中）

**要件ID**: FR-3
**タイトル**: `--skip-dependency-check` フラグの追加

**説明**:
依存関係チェックを完全にスキップして、強制的にフェーズを実行できるオプションを提供する。

**詳細要件**:
- `main.py` の `execute` コマンドに `--skip-dependency-check` フラグを追加
- フラグが指定された場合、`validate_phase_dependencies()` 呼び出しをスキップ
- 警告メッセージを表示:
  `[WARNING] Dependency check skipped. Proceeding without validation.`
- デフォルトは `False`（依存関係チェックを実施）

**受け入れ基準**:
- Given: `requirements` フェーズが未完了
- When: `python main.py execute --phase implementation --issue 319 --skip-dependency-check` を実行
- Then: 依存関係チェックをスキップして実装フェーズが実行される

---

### FR-4: CLIオプション - 依存関係警告モード（優先度: 中）

**要件ID**: FR-4
**タイトル**: `--ignore-dependencies` フラグの追加

**説明**:
依存関係チェックを実施するが、違反時もエラーではなく警告を表示して実行を継続するモードを提供する。

**詳細要件**:
- `main.py` の `execute` コマンドに `--ignore-dependencies` フラグを追加
- フラグが指定された場合、`validate_phase_dependencies()` を実行
- 依存関係違反時、例外を発生させずに警告メッセージを表示して実行継続
- 警告メッセージ例:
  `[WARNING] Dependency violation: Phase 'requirements' is not completed. Continuing anyway.`
- デフォルトは `False`（依存関係違反時はエラー終了）

**受け入れ基準**:
- Given: `requirements` フェーズが未完了
- When: `python main.py execute --phase design --issue 319 --ignore-dependencies` を実行
- Then: 警告メッセージが表示され、設計フェーズが実行される

---

### FR-5: CLIオプション - 外部ドキュメント指定（優先度: 低）

**要件ID**: FR-5
**タイトル**: `--{phase}-doc` オプションによる成果物の外部指定

**説明**:
既存の要件定義書や設計書を外部ファイルとして指定し、該当フェーズをスキップして次フェーズから実行できるようにする。

**詳細要件**:
- 以下のオプションを追加:
  - `--requirements-doc <path>`: 要件定義書のパス
  - `--design-doc <path>`: 設計書のパス
  - `--test-scenario-doc <path>`: テストシナリオのパス
- 指定されたパスのファイルを該当フェーズの成果物ディレクトリにコピー
- メタデータの該当フェーズステータスを `completed` に更新
- ファイル存在チェックとバリデーションを実施

**受け入れ基準**:
- Given: `/path/to/custom_requirements.md` が存在する
- When: `python main.py execute --phase design --issue 319 --requirements-doc /path/to/custom_requirements.md` を実行
- Then:
  - `/path/to/custom_requirements.md` が `.ai-workflow/issue-319/01_requirements/output/requirements.md` にコピーされる
  - `requirements` フェーズのステータスが `completed` に更新される
  - `design` フェーズが実行される

---

### FR-6: プリセット実行モード（優先度: 中）

**要件ID**: FR-6
**タイトル**: よくあるパターンのプリセット提供

**説明**:
頻繁に使用される実行パターンをプリセットとして定義し、簡易に実行できるようにする。

**詳細要件**:
- `main.py` の `execute` コマンドに `--preset` オプションを追加
- 以下のプリセットを実装:
  - `requirements-only`: Phase 1のみ実行
  - `design-phase`: Phase 1-2を実行
  - `implementation-phase`: Phase 1-4を実行
  - `full-workflow`: Phase 1-8をすべて実行（デフォルト）
- `--preset` と `--phase` の同時指定はエラー
- プリセット実行時、依存関係チェックは自動的に有効化

**受け入れ基準**:
- Given: ワークフローが初期化されている
- When: `python main.py execute --preset requirements-only --issue 319` を実行
- Then: `requirements` フェーズのみが実行され、他フェーズはスキップされる

- Given: `--preset design-phase` と `--phase implementation` を同時指定
- When: コマンドを実行
- Then: エラーメッセージ「`--preset` and `--phase` cannot be used together」が表示される

---

### FR-7: BasePhaseクラスへの依存関係チェック統合（優先度: 高）

**要件ID**: FR-7
**タイトル**: `BasePhase.run()` への依存関係チェック組み込み

**説明**:
各フェーズの実行メソッド（`BasePhase.run()`）に依存関係チェックロジックを統合し、自動的に検証を実施する。

**詳細要件**:
- `BasePhase.run()` メソッドの開始時に `validate_phase_dependencies()` を呼び出し
- 依存関係チェック失敗時、フェーズステータスを `failed` に更新
- GitHub Issueにエラーメッセージを投稿
- `--skip-dependency-check` フラグが指定されている場合は検証をスキップ
- `--ignore-dependencies` フラグが指定されている場合は警告のみ表示

**受け入れ基準**:
- Given: `requirements` フェーズが未完了
- When: `design` フェーズの `run()` メソッドが呼び出される
- Then:
  - `DependencyError` が発生
  - フェーズステータスが `failed` に更新される
  - GitHub Issueにエラーメッセージが投稿される

---

## 3. 非機能要件

### NFR-1: パフォーマンス要件

- **NFR-1.1**: 依存関係チェックの実行時間は100ms以内であること
- **NFR-1.2**: メタデータの読み取り回数を最小化し、キャッシュを活用すること

### NFR-2: 保守性要件

- **NFR-2.1**: フェーズ依存関係は一箇所（`PHASE_DEPENDENCIES`定数）で管理され、変更が容易であること
- **NFR-2.2**: 新規フェーズの追加時、既存コードの変更を最小限に抑えること
- **NFR-2.3**: ドキュメント（README.md）に依存関係図とプリセット一覧を記載すること

### NFR-3: 可用性・信頼性要件

- **NFR-3.1**: 依存関係チェック失敗時、メタデータが破損しないこと
- **NFR-3.2**: 外部ドキュメント指定時、ファイルコピーが失敗してもロールバックされること

### NFR-4: ユーザビリティ要件

- **NFR-4.1**: エラーメッセージは具体的で、ユーザーが解決方法を理解できること
- **NFR-4.2**: CLIヘルプ（`--help`）にすべてのオプションとプリセットが表示されること
- **NFR-4.3**: 警告メッセージは `[WARNING]` プレフィックスで統一されること

---

## 4. 制約事項

### 技術的制約

- **TC-1**: 既存のメタデータスキーマ（`metadata.json`）との互換性を維持すること
- **TC-2**: 既存のフェーズクラス（`RequirementsPhase`, `DesignPhase` など）のインターフェースを変更しないこと
- **TC-3**: Python 3.8以上で動作すること
- **TC-4**: 既存のテストケース（E2Eテスト、統合テスト）が破損しないこと

### リソース制約

- **RC-1**: 実装期間は2週間以内とすること
- **RC-2**: 追加のライブラリ依存を最小限に抑えること

### ポリシー制約

- **PC-1**: CLAUDE.mdのコーディング規約に従うこと（日本語コメント、命名規則）
- **PC-2**: すべての変更にユニットテストを追加すること
- **PC-3**: セキュリティリスク（パストラバーサル等）に対処すること

---

## 5. 前提条件

### システム環境

- **ENV-1**: Python 3.8以上がインストールされていること
- **ENV-2**: Claude Agent SDKが利用可能であること
- **ENV-3**: GitHub APIトークン（`GITHUB_TOKEN`）が設定されていること

### 依存コンポーネント

- **DEP-1**: `core.metadata_manager.MetadataManager` クラスが正常に動作すること
- **DEP-2**: `phases.base_phase.BasePhase` クラスが実装済みであること
- **DEP-3**: `main.py` のCLI実装（Click）が利用可能であること

### 外部システム連携

- **EXT-1**: GitHub APIが正常に応答すること（進捗投稿・コメント投稿）
- **EXT-2**: Gitリポジトリが初期化されていること

---

## 6. 受け入れ基準

### AC-1: 依存関係の明示化

- Given: AIワークフローシステムが起動している
- When: `PHASE_DEPENDENCIES` 定数を参照する
- Then: 全8フェーズの依存関係が正しく定義されている

### AC-2: 依存関係チェック成功

- Given: `requirements` フェーズが完了している
- When: `design` フェーズを実行する
- Then: 依存関係チェックが成功し、設計フェーズが実行される

### AC-3: 依存関係チェック失敗

- Given: `requirements` フェーズが未完了
- When: `design` フェーズを実行する
- Then: `DependencyError` が発生し、エラーメッセージ「Phase 'requirements' must be completed before 'design'」が表示される

### AC-4: 依存関係スキップ機能

- Given: `requirements` フェーズが未完了
- When: `python main.py execute --phase design --issue 319 --skip-dependency-check` を実行
- Then: 依存関係チェックをスキップして設計フェーズが実行される

### AC-5: 依存関係警告モード

- Given: `requirements` フェーズが未完了
- When: `python main.py execute --phase design --issue 319 --ignore-dependencies` を実行
- Then: 警告メッセージが表示され、設計フェーズが実行される

### AC-6: 外部ドキュメント指定

- Given: `/path/to/requirements.md` が存在する
- When: `python main.py execute --phase design --issue 319 --requirements-doc /path/to/requirements.md` を実行
- Then:
  - ファイルがコピーされる
  - `requirements` フェーズのステータスが `completed` に更新される
  - `design` フェーズが実行される

### AC-7: プリセット実行（requirements-only）

- Given: ワークフローが初期化されている
- When: `python main.py execute --preset requirements-only --issue 319` を実行
- Then: `requirements` フェーズのみが実行され、他フェーズはスキップされる

### AC-8: プリセット実行（design-phase）

- Given: ワークフローが初期化されている
- When: `python main.py execute --preset design-phase --issue 319` を実行
- Then: `requirements` と `design` フェーズが順次実行される

### AC-9: プリセット実行（implementation-phase）

- Given: ワークフローが初期化されている
- When: `python main.py execute --preset implementation-phase --issue 319` を実行
- Then: `requirements`, `design`, `test_scenario`, `implementation` フェーズが順次実行される

### AC-10: プリセットとphaseの同時指定エラー

- Given: `--preset design-phase` と `--phase implementation` を同時指定
- When: コマンドを実行
- Then: エラーメッセージ「`--preset` and `--phase` cannot be used together」が表示される

---

## 7. スコープ外

### 明確にスコープ外とする事項

- **OUT-1**: フェーズの動的な依存関係変更（実行時に依存関係を変更する機能）
- **OUT-2**: フェーズの並列実行（複数フェーズの同時実行）
- **OUT-3**: フェーズ間の循環依存チェック（現時点では非循環依存を前提）
- **OUT-4**: GUI/Web UIでの依存関係可視化
- **OUT-5**: 依存関係グラフの自動生成機能
- **OUT-6**: フェーズの条件分岐実行（if文による実行フロー制御）

### 将来的な拡張候補

- **FUT-1**: フェーズ依存関係のYAML/TOML設定ファイル化
- **FUT-2**: 依存関係の可視化ツール（Graphviz等）
- **FUT-3**: フェーズ実行計画のドライラン機能（`--dry-run`）
- **FUT-4**: フェーズ間の部分的な依存関係（オプショナル依存）
- **FUT-5**: カスタムフェーズの動的登録機能
- **FUT-6**: 依存関係違反時の自動修復機能（依存フェーズの自動実行）

---

## 付録A: フェーズ依存関係図

```
requirements (Phase 1)
  ├── design (Phase 2)
  │   ├── test_scenario (Phase 3)
  │   │   └── implementation (Phase 4)
  │   │       ├── test_implementation (Phase 5)
  │   │       │   └── testing (Phase 6)
  │   │       ├── documentation (Phase 7)
  │   └── implementation (Phase 4) ← 重複表示は省略
  └── report (Phase 8) ← requirements, design, implementation, testing, documentation に依存
```

### 依存関係の説明

| フェーズ | 依存フェーズ | 理由 |
|---------|-------------|------|
| requirements | なし | 最初のフェーズ |
| design | requirements | 要件定義がないと設計できない |
| test_scenario | requirements, design | 要件と設計に基づいてテストシナリオを作成 |
| implementation | requirements, design, test_scenario | 要件・設計・テストシナリオに基づいて実装 |
| test_implementation | implementation | 実装コードが必要 |
| testing | implementation, test_implementation | 実装コードとテストコードが必要 |
| documentation | implementation | 実装コードのドキュメント化 |
| report | requirements, design, implementation, testing, documentation | 全工程の成果物をまとめる |

---

## 付録B: プリセット一覧

| プリセット名 | 実行フェーズ | 用途 |
|------------|------------|------|
| `requirements-only` | Phase 1 | 要件定義のみ作成してレビュー |
| `design-phase` | Phase 1-2 | 設計まで完了して設計レビュー |
| `implementation-phase` | Phase 1-4 | 実装まで完了（テストは未実施） |
| `full-workflow` | Phase 1-8 | 全フェーズを実行（デフォルト） |

---

## 変更履歴

| バージョン | 日付 | 変更内容 | 作成者 |
|----------|------|---------|--------|
| 1.0 | 2025-10-12 | 初版作成 | Claude (AI Workflow) |

