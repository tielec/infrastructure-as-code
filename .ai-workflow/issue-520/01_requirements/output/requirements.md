# 要件定義書: Issue #520

## IaC CI/CD パイプライン - Ansible lint / Pulumi preview / pytest 並列実行

---

## 0. Planning Documentの確認

本要件定義書は、Planning Phase（`.ai-workflow/issue-520/00_planning/output/planning.md`）で策定された以下の開発計画に基づいて作成されています。

### 開発計画の概要

- **複雑度**: 中程度
- **見積もり工数**: 12〜16時間
- **実装戦略**: CREATE（新規ワークフローファイルの作成）
- **テスト戦略**: INTEGRATION_ONLY（実際のPR作成によるインテグレーションテスト）
- **リスク評価**: 中（S3バックエンド、パスフレーズ設定、23個のPulumiプロジェクト管理）

---

## 1. 概要

### 1.1 目的

本機能は、GitHub Actionsを使用してInfrastructure as Code（IaC）の品質ゲートを自動化し、PRステージでの早期問題検出を実現するものです。

### 1.2 背景

現状の課題：
- **Ansible**: lintチェックがCI/CDパイプラインに組み込まれておらず、手動検証に依存
- **Pulumi**: S3バックエンドとパスフレーズ設定が必要なため、ローカル以外での再現性が低い
- **pytest**: 統合テストが手動・分断されており、PRマージ後に問題が発覚するリスクが高い
- **レビュー**: 上記の状況により、レビュアーが自信を持って承認判断を行いづらい

### 1.3 ビジネス価値

| 価値領域 | 具体的効果 |
|---------|-----------|
| **品質向上** | 構文エラー、依存関係の欠如、リソース差分を自動検出 |
| **リスク低減** | デプロイ前に問題を発見し、本番障害を未然に防止 |
| **開発効率** | レビュアーの判断精度向上、開発速度の向上 |
| **標準化** | CI/CD品質ゲートの確立による開発プロセス標準化 |

### 1.4 技術的価値

- GitHub Actionsによる自動化基盤の確立
- 並列実行（matrix）によるCI実行時間の最適化
- 依存関係キャッシュによるビルド高速化
- アーティファクト保存によるデバッグ効率向上

---

## 2. 機能要件

### 2.1 GitHub Actionsワークフロー作成

| ID | 要件 | 優先度 | 説明 |
|----|------|--------|------|
| FR-001 | ワークフローファイルの作成 | **高** | `.github/workflows/iac-ci.yml`を新規作成する |
| FR-002 | PRトリガー設定 | **高** | `pull_request`イベント（opened, synchronize）で自動実行 |
| FR-003 | ブランチフィルタ | **高** | `main`および`develop`ブランチへのPR時にトリガー |
| FR-004 | パスフィルタ | **中** | `ansible/**`, `pulumi/**`, `tests/**`, `jenkins/**`の変更時のみ実行 |

### 2.2 Ansible lint/yamllint ジョブ

| ID | 要件 | 優先度 | 説明 |
|----|------|--------|------|
| FR-010 | ansible-lint実行 | **高** | `ansible/`ディレクトリに対してansible-lintを実行 |
| FR-011 | yamllint実行 | **高** | `ansible/`ディレクトリに対してyamllintを実行 |
| FR-012 | `.ansible-lint`設定ファイル作成 | **高** | ansible-lint用の設定ファイルを新規作成 |
| FR-013 | `.yamllint`設定ファイル作成 | **高** | yamllint用の設定ファイルを新規作成 |
| FR-014 | Python環境キャッシュ | **中** | pip依存関係をキャッシュして実行時間を短縮 |

### 2.3 Pulumi preview ジョブ

| ID | 要件 | 優先度 | 説明 |
|----|------|--------|------|
| FR-020 | Pulumi previewの実行 | **高** | 指定されたスタックに対して`pulumi preview --non-interactive`を実行 |
| FR-021 | S3バックエンドログイン | **高** | `pulumi login s3://...`でS3バックエンドにログイン |
| FR-022 | AWSシークレット設定 | **高** | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`をシークレットから注入 |
| FR-023 | Pulumiパスフレーズ設定 | **高** | `PULUMI_CONFIG_PASSPHRASE`をシークレットから注入 |
| FR-024 | Node.js環境キャッシュ | **中** | npm依存関係をキャッシュして実行時間を短縮 |
| FR-025 | 初期対象スタック選定 | **中** | `jenkins-controller`, `jenkins-network`, `jenkins-security`を初期対象とする |

### 2.4 pytest ジョブ

| ID | 要件 | 優先度 | 説明 |
|----|------|--------|------|
| FR-030 | pytest実行 | **高** | `tests/integration/`ディレクトリに対してpytestを実行 |
| FR-031 | 環境変数設定 | **高** | `AWS_REGION`などの必要な環境変数を設定 |
| FR-032 | テストレポート出力 | **中** | pytest実行結果をレポート形式で出力 |

### 2.5 並列実行・アーティファクト管理

| ID | 要件 | 優先度 | 説明 |
|----|------|--------|------|
| FR-040 | 3ジョブ並列実行 | **高** | ansible-lint, pulumi-preview, pytestを並列実行 |
| FR-041 | アーティファクトアップロード | **中** | 失敗時にログファイルをアーティファクトとして保存 |
| FR-042 | テストレポートアーティファクト | **中** | pytestのテストレポートをアーティファクトとして保存 |

### 2.6 ドキュメント更新

| ID | 要件 | 優先度 | 説明 |
|----|------|--------|------|
| FR-050 | CI/CDドキュメント作成 | **中** | ワークフローの説明、トリガー条件、シークレット設定手順を文書化 |
| FR-051 | README.mdへのバッジ追加 | **低** | CIステータスバッジをREADME.mdに追加（任意） |
| FR-052 | トラブルシューティングガイド | **低** | よくあるエラーと対処法を文書化 |

---

## 3. 非機能要件

### 3.1 パフォーマンス要件

| ID | 要件 | 目標値 | 説明 |
|----|------|--------|------|
| NFR-001 | 全体実行時間 | 15分以内 | 3ジョブ並列実行の合計時間 |
| NFR-002 | キャッシュ効果 | 30%以上短縮 | 2回目以降のキャッシュヒット時の実行時間短縮率 |
| NFR-003 | 個別ジョブ時間 | 各10分以内 | 各ジョブの個別実行時間の上限 |

### 3.2 セキュリティ要件

| ID | 要件 | 説明 |
|----|------|------|
| NFR-010 | シークレット管理 | AWS認証情報、Pulumiパスフレーズは必ずGitHub Secretsで管理 |
| NFR-011 | 最小権限の原則 | CI用AWSユーザーは必要最小限の権限のみ付与 |
| NFR-012 | シークレット露出防止 | ログ出力時にシークレット値がマスクされることを確認 |
| NFR-013 | パブリックPR対応 | フォークからのPRではシークレットを利用できない仕様の考慮 |

### 3.3 可用性・信頼性要件

| ID | 要件 | 説明 |
|----|------|------|
| NFR-020 | ジョブ独立性 | 各ジョブは独立して実行でき、他ジョブの失敗に影響されない |
| NFR-021 | 失敗時のログ保存 | 失敗時は詳細ログがアーティファクトとして保存される |
| NFR-022 | リトライ対応 | 一時的なネットワークエラー等でのリトライが可能 |

### 3.4 保守性・拡張性要件

| ID | 要件 | 説明 |
|----|------|------|
| NFR-030 | モジュラー設計 | 新しいlintツールやテストの追加が容易な構造 |
| NFR-031 | Pulumiスタック拡張性 | 対象Pulumiスタックを容易に追加可能な設計 |
| NFR-032 | Jenkins移植性 | 将来的にJenkinsパイプラインへの移植が可能な設計 |

---

## 4. 制約事項

### 4.1 技術的制約

| ID | 制約 | 説明 |
|----|------|------|
| TC-001 | GitHub Actions使用 | CI/CDプラットフォームとしてGitHub Actionsを使用 |
| TC-002 | ubuntu-latest使用 | ランナーはubuntu-latestを使用 |
| TC-003 | Python 3.11 | Python環境はバージョン3.11を使用 |
| TC-004 | Node.js 20 | Node.js環境はバージョン20を使用 |
| TC-005 | S3バックエンド | Pulumiの状態管理はS3バックエンドを使用 |

### 4.2 リソース制約

| ID | 制約 | 説明 |
|----|------|------|
| RC-001 | GitHub Actions制限 | ワークフロー実行時間は6時間以内（GitHub制限） |
| RC-002 | 同時実行数制限 | GitHub Actionsの同時実行数制限を考慮 |
| RC-003 | ストレージ制限 | アーティファクト保存容量の制限を考慮 |

### 4.3 ポリシー制約

| ID | 制約 | 説明 |
|----|------|------|
| PC-001 | コーディング規約 | CLAUDE.mdに記載のコーディングガイドラインに従う |
| PC-002 | コミットメッセージ | `[Component] Action: 詳細な説明`形式に従う |
| PC-003 | ドキュメント言語 | ドキュメントは日本語で記述 |
| PC-004 | Co-Author禁止 | コミットメッセージにCo-Authorを含めない |

---

## 5. 前提条件

### 5.1 システム環境

| ID | 前提条件 | 説明 |
|----|---------|------|
| PRE-001 | GitHubリポジトリ | tielec/infrastructure-as-codeリポジトリが存在 |
| PRE-002 | GitHub Actions有効 | リポジトリでGitHub Actionsが有効化されている |
| PRE-003 | AWSアカウント | CI実行用のAWSアカウントが存在 |

### 5.2 依存コンポーネント

| ID | 依存 | 説明 |
|----|------|------|
| DEP-001 | actions/checkout@v4 | ソースコードチェックアウト |
| DEP-002 | actions/setup-python@v5 | Python環境セットアップ |
| DEP-003 | actions/setup-node@v4 | Node.js環境セットアップ |
| DEP-004 | actions/upload-artifact@v4 | アーティファクトアップロード |

### 5.3 GitHub Actionsシークレット（要事前設定）

| シークレット名 | 説明 | 必須 |
|---------------|------|------|
| `AWS_ACCESS_KEY_ID` | AWSアクセスキーID | **必須** |
| `AWS_SECRET_ACCESS_KEY` | AWSシークレットアクセスキー | **必須** |
| `PULUMI_CONFIG_PASSPHRASE` | Pulumi暗号化パスフレーズ | **必須** |
| `PULUMI_STATE_BUCKET` | S3バケット名 | **必須** |

---

## 6. 受け入れ基準

### 6.1 ワークフロー全体

#### AC-001: ワークフローがPRで自動実行される

```gherkin
Given GitHubリポジトリに`.github/workflows/iac-ci.yml`が存在する
When main/developブランチへのPRが作成または更新される
And 対象パス（ansible/**, pulumi/**, tests/**, jenkins/**）に変更がある
Then IaC CIワークフローが自動的に実行される
```

#### AC-002: 3ジョブが並列実行される

```gherkin
Given IaC CIワークフローが実行される
When ワークフローが開始される
Then ansible-lint, pulumi-preview, pytestの3ジョブが並列で実行される
And 各ジョブは他のジョブの結果に依存しない
```

### 6.2 Ansible lintジョブ

#### AC-010: ansible-lintが正常実行される

```gherkin
Given ansible-lintジョブが実行される
And `.ansible-lint`設定ファイルが存在する
When ansible/ディレクトリに対してansible-lintが実行される
Then lint結果が出力される
And lintエラーがある場合はジョブが失敗する
```

#### AC-011: yamllintが正常実行される

```gherkin
Given ansible-lintジョブが実行される
And `.yamllint`設定ファイルが存在する
When ansible/ディレクトリに対してyamllintが実行される
Then lint結果が出力される
And lintエラーがある場合はジョブが失敗する
```

### 6.3 Pulumi previewジョブ

#### AC-020: Pulumi previewが正常実行される

```gherkin
Given pulumi-previewジョブが実行される
And AWSシークレットとPulumiパスフレーズが設定されている
When pulumi login s3://... でS3バックエンドにログインする
And pulumi preview --stack dev --non-interactive を実行する
Then preview結果が出力される
And エラーがある場合はジョブが失敗する
```

#### AC-021: S3バックエンド認証が成功する

```gherkin
Given pulumi-previewジョブが実行される
And AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, PULUMI_CONFIG_PASSPHRASEが設定されている
When pulumi login s3://${{ secrets.PULUMI_STATE_BUCKET }} を実行する
Then S3バックエンドへのログインが成功する
And "Logged in to..." メッセージが出力される
```

### 6.4 pytestジョブ

#### AC-030: pytestが正常実行される

```gherkin
Given pytestジョブが実行される
And tests/integration/ディレクトリにテストファイルが存在する
When pytest tests/integration -v を実行する
Then テスト結果が出力される
And テスト失敗がある場合はジョブが失敗する
```

### 6.5 アーティファクト

#### AC-040: 失敗時にログがアーティファクトとして保存される

```gherkin
Given いずれかのジョブが失敗する
When ジョブの後処理が実行される
Then ログファイルがアーティファクトとしてアップロードされる
And アーティファクトはGitHub Actions UIからダウンロード可能
```

### 6.6 パフォーマンス

#### AC-050: 全体実行時間が15分以内

```gherkin
Given IaC CIワークフローが実行される
When 全ジョブが完了する
Then 全体実行時間が15分以内である
```

#### AC-051: キャッシュにより実行時間が短縮される

```gherkin
Given 同一ブランチで2回目のワークフロー実行が行われる
When pip/npmキャッシュがヒットする
Then 1回目と比較して実行時間が30%以上短縮される
```

---

## 7. スコープ外

### 7.1 本Issue対象外の事項

| ID | 項目 | 理由 |
|----|------|------|
| OUT-001 | 全22 Pulumiプロジェクトのpreview | 初期実装では3プロジェクト（jenkins-controller, jenkins-network, jenkins-security）のみ対象。段階的に拡大予定 |
| OUT-002 | Jenkinsパイプラインへの移植 | GitHub Actionsでの実装・検証後に別Issueとして対応 |
| OUT-003 | 変更ファイルに基づく動的スタック選択 | 初期実装後の改善として検討 |
| OUT-004 | Slack/Teams通知連携 | 別途Enhancement Issueとして検討 |
| OUT-005 | PRコメントへの結果投稿 | 別途Enhancement Issueとして検討 |
| OUT-006 | セキュリティスキャン（Trivy等） | 別途Security Issueとして検討 |

### 7.2 将来的な拡張候補

| 項目 | 説明 |
|------|------|
| 全Pulumiプロジェクト対応 | 23プロジェクト全てのpreview実行 |
| 変更検知による対象絞り込み | PRで変更されたファイルに基づいてPulumiスタックを動的選択 |
| Jenkinsパイプライン移植 | GitHub Actions実装をJenkinsfileに移植 |
| Terraform/CloudFormation対応 | 他のIaCツールへの対応 |
| カスタムレポート生成 | PR詳細レポートの自動生成 |

---

## 8. 用語集

| 用語 | 説明 |
|------|------|
| **IaC** | Infrastructure as Code - インフラをコードで管理する手法 |
| **CI** | Continuous Integration - 継続的インテグレーション |
| **Pulumi** | TypeScriptでインフラを定義するIaCツール |
| **ansible-lint** | Ansibleプレイブック/ロールの静的解析ツール |
| **yamllint** | YAMLファイルの構文チェックツール |
| **matrix** | GitHub Actionsの並列実行機能 |
| **S3バックエンド** | Pulumiの状態をS3に保存する構成 |
| **シークレット** | GitHub Actionsで安全に管理される機密情報 |

---

## 9. 参考資料

### 9.1 内部ドキュメント

- [CLAUDE.md](../../CLAUDE.md) - プロジェクトのコーディングガイドライン
- [ARCHITECTURE.md](../../ARCHITECTURE.md) - アーキテクチャ設計思想
- [CONTRIBUTION.md](../../CONTRIBUTION.md) - 開発ガイドライン
- [README.md](../../README.md) - プロジェクト概要

### 9.2 外部リソース

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [ansible-lint Documentation](https://ansible.readthedocs.io/projects/lint/)
- [Pulumi Documentation](https://www.pulumi.com/docs/)
- [pytest Documentation](https://docs.pytest.org/)

---

## 10. 改訂履歴

| バージョン | 日付 | 変更内容 | 作成者 |
|-----------|------|---------|--------|
| 1.0 | 2025-01-XX | 初版作成 | AI Workflow |

---

## 品質ゲートチェックリスト

- [x] **機能要件が明確に記載されている**: FR-001〜FR-052で全機能要件を定義
- [x] **受け入れ基準が定義されている**: AC-001〜AC-051でGiven-When-Then形式で定義
- [x] **スコープが明確である**: セクション7で対象外事項を明示
- [x] **論理的な矛盾がない**: 機能要件と受け入れ基準が1:1で対応
