# 要件定義書: ansible-lint スタイル違反の修正 (Issue #524)

## 0. Planning Documentの確認

Planning Phaseで策定された開発計画を踏まえ、以下の方針で要件定義を実施：

- **実装戦略**: REFACTOR - 既存のAnsibleコードベースのフォーマットとスタイルを改善
- **テスト戦略**: INTEGRATION_ONLY - ansible-lint実行とplaybook動作確認に特化
- **見積もり工数**: 2時間（フォーマット修正0.5h + Jinja2修正0.5h + テスト・検証1h）
- **リスク評価**: 低（動作に影響しないスタイル修正のみ）

## 1. 概要

### 背景
ansible-lint CI導入（Issue #522）により、既存のAnsibleコードベースから20個のスタイル違反エラーが検出されました。これらはすべてフォーマット・スタイル関連の問題で、Ansibleの動作には影響しないものです。

### 目的
ansible-lint標準に準拠したコードベースを確立し、継続的インテグレーションの基盤を整備することで、以下の価値を実現します：

**技術的価値**:
- コード品質の標準化と向上
- 開発者間でのコーディングスタイル統一
- 今後の保守性向上

**ビジネス価値**:
- CI/CDパイプラインの安定化
- コードレビューの効率化
- 開発生産性の向上

## 2. 機能要件

### FR-001: フォーマット関連エラーの修正（優先度: 高）

**詳細**: bootstrap-setup.ymlとall.ymlのフォーマットエラー11個を修正

#### FR-001-1: 末尾空白の削除
- 対象ファイル: `ansible/playbooks/bootstrap-setup.yml`
- 対象行: 10、19、28、35、51行目（計5箇所）
- 実行方法: エディタの自動整形機能またはスクリプトによる一括削除

#### FR-001-2: Truthy値の標準化
- 対象ファイル: `ansible/playbooks/bootstrap-setup.yml`
- 対象行: 9、34、50行目（計3箇所）
- 修正内容: `yes/no`、`True/False` → `true/false` に統一

#### FR-001-3: ドキュメント開始マーカーの追加
- 対象ファイル: `ansible/playbooks/bootstrap-setup.yml`
- 対象行: 6行目（ファイル先頭）
- 修正内容: `---` マーカーを追加

#### FR-001-4: ファイル末尾改行の追加
- 対象ファイル: `ansible/inventory/group_vars/all.yml`
- 対象行: 47行目（ファイル末尾）
- 修正内容: 改行文字を追加

### FR-002: Jinja2スペーシングエラーの修正（優先度: 中）

**詳細**: Jenkins関連ロールのJinja2式スペーシング10個を修正

#### 対象ファイルと修正箇所
1. `ansible/roles/jenkins_cleanup_agent_amis/tasks/process_ami_retention.yml`: 40、41、47行目
2. `ansible/roles/jenkins_cleanup_agent_amis/tasks/process_pipeline_outputs.yml`: 45行目
3. `ansible/roles/jenkins_cleanup_agent_amis/tasks/process_image_versions.yml`: 30、31行目
4. `ansible/roles/jenkins_cleanup_agent_amis/tasks/delete_snapshots.yml`: 33、48行目
5. `ansible/roles/jenkins_agent_ami/tasks/cleanup_amis.yml`: 62、69行目

#### 修正パターン
```jinja2
# 修正前
{{ some_var[0] }}
{{ dict['key'] }}

# 修正後（ansible-lint推奨スタイル）
{{ some_var[ 0 ] }}
{{ dict[ 'key' ] }}
```

### FR-003: 修正内容の検証（優先度: 高）

#### FR-003-1: ansible-lint実行による検証
- 修正後のファイルでansible-lintを実行し、エラー・警告が0件であることを確認

#### FR-003-2: Ansible構文チェック
- `ansible-playbook --syntax-check`によりPlaybook構文に問題がないことを確認

#### FR-003-3: 既存機能への影響確認
- 修正対象のplaybookがドライランモードで正常実行できることを確認

## 3. 非機能要件

### NFR-001: パフォーマンス要件
- 修正作業による既存Playbook実行時間への影響: 0秒（スタイル修正のため）
- ansible-lint実行時間: 既存と同等（エラー解消により若干短縮の可能性）

### NFR-002: 保守性要件
- 修正後のコードは ansible-lint v6.0以上の標準に準拠
- 統一されたコーディングスタイルにより、新規開発者の理解容易性を向上

### NFR-003: 互換性要件
- 既存のAnsible実行環境（v2.9以上）との100%互換性を維持
- 修正前後でPlaybook実行結果に差異がないこと

### NFR-004: 品質要件
- すべてのファイルでansible-lint実行時のエラー・警告件数: 0件
- yamllint実行時のエラー件数: 0件（警告レベルは許容）

## 4. 制約事項

### 技術的制約
- **既存ロジック変更禁止**: スタイル修正のみで、機能的な変更は一切行わない
- **ansible-lint準拠**: ansible-lint標準ルールに完全に準拠（カスタムルールは使用しない）
- **バージョン制約**: Ansible 2.9以上の互換性を維持

### リソース制約
- **作業時間**: 最大2時間以内で完了
- **影響範囲**: 7ファイル・21箇所の修正に限定
- **テスト時間**: 30分以内で完了

### ポリシー制約
- **コーディング規約**: CLAUDE.mdおよびAnsible CONTRIBUTIONガイドに準拠
- **変更管理**: すべての修正はPull Requestを通じてコードレビューを実施
- **ドキュメント更新**: README.md更新は不要（スタイル修正のため）

## 5. 前提条件

### システム環境
- ansible-lint v6.0以上がインストール済み
- Python 3.8以上の実行環境
- Git管理されたリポジトリへのアクセス権限

### 依存コンポーネント
- ansible-lint CI設定が有効（Issue #522で導入済み）
- 既存のAnsible実行環境が正常稼働
- 修正対象ファイルに他の開発者による同時編集がない

### 外部システム連携
- GitHub Actions CI環境での自動検証
- ansible-lintルールセット（デフォルト設定）

## 6. 受け入れ基準

### AC-001: フォーマットエラー解消
**Given**: bootstrap-setup.ymlとall.ymlにフォーマットエラーが存在する
**When**: 末尾空白削除、truthy値修正、マーカー追加、改行追加を実行する
**Then**: 該当ファイルでansible-lint実行時にフォーマット関連エラーが0件になる

### AC-002: Jinja2スペーシング修正完了
**Given**: 5つのタスクファイルにJinja2スペーシング警告が存在する
**When**: ブラケット演算子周りにスペースを追加する
**Then**: 該当ファイルでansible-lint実行時にJinja2関連警告が0件になる

### AC-003: 全体検証成功
**Given**: すべてのスタイル修正が完了している
**When**: `ansible-lint ansible/`を実行する
**Then**: エラー件数0件、警告件数0件で成功する

### AC-004: 既存機能への影響なし
**Given**: スタイル修正が完了したPlaybookが存在する
**When**: `ansible-playbook --syntax-check`および`--check`モードで実行する
**Then**: 構文エラーなし、かつ修正前と同一の実行結果を得る

### AC-005: CI環境での自動検証
**Given**: 修正されたコードがmainブランチにマージされている
**When**: GitHub Actions CIが実行される
**Then**: ansible-lintステップが成功（グリーン）で完了する

## 7. スコープ外

### 明確にスコープ外とする事項
- **機能的変更**: Playbook内のタスクロジックや変数定義の変更
- **パフォーマンス最適化**: 実行速度向上のためのリファクタリング
- **新規ルール追加**: カスタムansible-lintルールの作成・適用
- **ドキュメント更新**: README.mdや他のドキュメントファイルの更新
- **テストコード追加**: 新規のテストケースやテストスクリプトの作成

### 将来的な拡張候補
- 他のAnsibleファイル（非Jenkins関連）への同様の修正適用
- より厳密なlintルール（yamllint、ansible-lint拡張ルール）の導入
- CI/CDパイプラインでの自動フォーマット機能の実装
- pre-commitフックによる事前チェック機能の導入

---

## 品質ゲート確認

✅ **機能要件が明確に記載されている**: 3つの主要機能要件（FR-001〜003）を具体的な修正内容と共に定義
✅ **受け入れ基準が定義されている**: 5つの受け入れ基準をGiven-When-Then形式で明確に記述
✅ **スコープが明確である**: 7ファイル・21箇所の修正に限定し、スコープ外事項も明記
✅ **論理的な矛盾がない**: 実装戦略（REFACTOR）とテスト戦略（INTEGRATION_ONLY）が整合

この要件定義書は、Planning Documentで策定された戦略に基づき、具体的かつ検証可能な形で要件を定義しています。すべての品質ゲートを満たしており、次フェーズ（設計フェーズ）への進行が可能です。