# 要件定義書: Issue #547

## Jenkins Agent AMI ビルド失敗: CloudWatch Agent Translator が見つからない

---

## 0. Planning Documentの確認結果

### 開発計画の全体像
- **複雑度**: 簡単（単一コンポーネント内の2つのYAMLファイル修正）
- **見積もり工数**: 約4時間
- **実装戦略**: EXTEND（既存コードの修正・拡張）
- **テスト戦略**: INTEGRATION_ONLY（YAMLファイル修正のため、インテグレーションテストで確認）

### 策定された方針
- **採用する対応方法**: 方法2（JSONシンタックスチェック）を基本とし、方法3の一部（基本構造チェック）を組み合わせ
- **理由**:
  1. `jq`コマンドはInstallBasicPackagesステップで既にインストール済み
  2. translatorバイナリへの依存を完全に排除できる
  3. 設定ファイルの構文エラーは検出可能
  4. 実装リスクが最小で、確実に問題を解決できる

---

## 1. 概要

### 1.1 背景

Jenkins Agent AMIのイメージビルダーにおいて、CloudWatch Agentの設定検証ステップ（`ValidateCloudWatchAgentConfig`）がビルド時に失敗しています。Amazon Linux 2023（AL2023）環境では、CloudWatch Agentのtranslatorバイナリ（`amazon-cloudwatch-agent-config-translator`）が期待されるパス（`/opt/aws/amazon-cloudwatch-agent/bin/`）に存在しないことが原因です。

### 1.2 目的

CloudWatch Agent設定の検証方法を、AL2023環境で確実に動作する方法に変更し、Jenkins Agent AMIのビルドを成功させることを目的とします。

### 1.3 ビジネス価値・技術的価値

| カテゴリ | 価値 |
|---------|------|
| **ビジネス価値** | Jenkins Agentのデプロイ再開によるCI/CDパイプラインの稼働継続 |
| **技術的価値** | AL2023環境でのCloudWatch Agent検証の標準化、translator依存の排除による保守性向上 |
| **運用価値** | AMIビルドプロセスの安定化、将来のOS更新への耐性向上 |

### 1.4 影響範囲

- Jenkins Agent AMI (x86) のビルドプロセス
- Jenkins Agent AMI (ARM) のビルドプロセス
- CloudWatch Agent設定の検証方法

---

## 2. 機能要件

### 2.1 必須機能要件

| ID | 要件 | 優先度 | 対応ファイル |
|----|------|--------|-------------|
| FR-001 | `component-x86.yml`の`ValidateCloudWatchAgentConfig`ステップを修正し、translatorバイナリへの依存を排除する | 高 | `pulumi/jenkins-agent-ami/component-x86.yml:156-172` |
| FR-002 | `component-arm.yml`の`ValidateCloudWatchAgentConfig`ステップを修正し、translatorバイナリへの依存を排除する | 高 | `pulumi/jenkins-agent-ami/component-arm.yml:156-172` |
| FR-003 | 修正後の検証ステップは、CloudWatch Agent設定ファイル（JSON）の構文チェックを行う | 高 | 両YAMLファイル |
| FR-004 | 修正後の検証ステップは、設定ファイルの存在確認を行う | 高 | 両YAMLファイル |

### 2.2 推奨機能要件

| ID | 要件 | 優先度 | 備考 |
|----|------|--------|------|
| FR-005 | 設定ファイルの基本構造チェック（`metrics`セクションの存在確認等）を警告レベルで実施する | 中 | 将来的な設定ミス検出のため |
| FR-006 | 検証成功時に設定ファイルの内容を表示する（デバッグ用） | 低 | 既存動作の維持 |

---

## 3. 非機能要件

### 3.1 パフォーマンス要件

| ID | 要件 | 測定基準 |
|----|------|---------|
| NFR-001 | 検証ステップの実行時間は5秒以内に完了すること | ステップ実行時間 < 5秒 |
| NFR-002 | AMIビルド全体の実行時間に有意な増加がないこと | 既存ビルド時間との差分 < 1分 |

### 3.2 セキュリティ要件

| ID | 要件 |
|----|------|
| NFR-003 | 検証ステップで使用するコマンド（`jq`等）は、InstallBasicPackagesで既にインストールされている標準ツールのみを使用すること |
| NFR-004 | 外部への通信を必要としないこと（オフライン検証） |

### 3.3 可用性・信頼性要件

| ID | 要件 |
|----|------|
| NFR-005 | x86およびARM両アーキテクチャで同一の検証方法が動作すること |
| NFR-006 | 検証失敗時は明確なエラーメッセージを出力し、ビルドを適切に中断すること |

### 3.4 保守性・拡張性要件

| ID | 要件 |
|----|------|
| NFR-007 | 将来のCloudWatch Agentパッケージ更新に影響されない検証方法であること |
| NFR-008 | x86版とARM版で同一の検証コードを使用し、保守性を確保すること |
| NFR-009 | コード内のコメントは日本語で記述すること（CLAUDE.mdのコーディングガイドラインに準拠） |

---

## 4. 制約事項

### 4.1 技術的制約

| 制約ID | 内容 | 理由 |
|--------|------|------|
| TC-001 | EC2 Image Builderのコンポーネント定義（YAML形式）で記述すること | 既存アーキテクチャの維持 |
| TC-002 | `jq`コマンドを使用したJSON構文チェックを採用すること | 既にInstallBasicPackagesでインストール済み、追加依存なし |
| TC-003 | CloudWatch Agent CLIの`fetch-config`は使用しないこと | 設定適用を伴うため、ビルド時の検証には不適切 |
| TC-004 | translatorバイナリへの依存を完全に排除すること | AL2023での動作保証のため |

### 4.2 リソース制約

| 制約ID | 内容 |
|--------|------|
| RC-001 | 実装工数: 約1時間（2つのYAMLファイル修正） |
| RC-002 | テスト: AMIビルドパイプライン実行による検証（20-40分/回） |

### 4.3 ポリシー制約

| 制約ID | 内容 | 参照 |
|--------|------|------|
| PC-001 | ソースコード内のコメントは日本語で記述 | CLAUDE.md |
| PC-002 | 変更はPulumi管轄のファイルのみに限定 | プロジェクト構造 |

---

## 5. 前提条件

### 5.1 システム環境

| 前提ID | 内容 |
|--------|------|
| PA-001 | ベースAMI: Amazon Linux 2023（AL2023） |
| PA-002 | アーキテクチャ: x86_64およびarm64 |
| PA-003 | EC2 Image Builderによるビルド実行 |

### 5.2 依存コンポーネント

| 前提ID | 内容 | 備考 |
|--------|------|------|
| PA-004 | `jq`コマンドがInstallBasicPackagesステップでインストール済み | component-x86.yml:55, component-arm.yml:55 |
| PA-005 | CloudWatch Agentがインストール済み | InstallCloudWatchAgentステップ（136-142行目） |
| PA-006 | CloudWatch Agent設定ファイルが配置済み | ConfigureCloudWatchAgentステップ（144-154行目） |

### 5.3 前処理ステップの完了

修正対象の`ValidateCloudWatchAgentConfig`ステップ実行前に、以下のステップが正常完了していることを前提とする：

1. **InstallBasicPackages** (51-56行目): `jq`コマンドを含む基本パッケージのインストール
2. **InstallCloudWatchAgent** (136-142行目): CloudWatch Agentのインストール
3. **ConfigureCloudWatchAgent** (144-154行目): 設定ファイルの配置

---

## 6. 受け入れ基準

### 6.1 FR-001, FR-002: ValidateCloudWatchAgentConfigステップの修正

**Given-When-Then形式:**

```gherkin
Scenario: CloudWatch Agent設定ファイルの検証成功
  Given CloudWatch Agentがインストールされている
    And 設定ファイル(/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json)が存在する
    And 設定ファイルの内容が有効なJSON形式である
  When ValidateCloudWatchAgentConfigステップが実行される
  Then ステップが正常終了する（ExitCode 0）
    And "CloudWatch Agent configuration validation passed." がログに出力される
    And 設定ファイルの内容がログに表示される

Scenario: 設定ファイルが存在しない場合
  Given CloudWatch Agentがインストールされている
    And 設定ファイルが存在しない
  When ValidateCloudWatchAgentConfigステップが実行される
  Then ステップが失敗する（ExitCode 1）
    And "ERROR: Configuration file not found" がログに出力される

Scenario: 設定ファイルのJSON構文が無効な場合
  Given CloudWatch Agentがインストールされている
    And 設定ファイルが存在する
    And 設定ファイルの内容がJSON構文エラーを含む
  When ValidateCloudWatchAgentConfigステップが実行される
  Then ステップが失敗する（ExitCode 1）
    And "ERROR: Invalid JSON syntax" がログに出力される
```

### 6.2 FR-003, FR-004: JSON構文チェックと存在確認

```gherkin
Scenario: jqによるJSON構文チェック
  Given 設定ファイルが存在する
  When jq empty コマンドで構文チェックが実行される
  Then 有効なJSONの場合、コマンドが成功する
    And 無効なJSONの場合、コマンドが失敗しエラー詳細が出力される
```

### 6.3 NFR-005: 両アーキテクチャでの動作

```gherkin
Scenario: x86アーキテクチャでのAMIビルド成功
  Given component-x86.ymlが修正されている
  When EC2 Image BuilderでAMIビルドが実行される
  Then ビルドが正常完了する
    And 作成されたAMIでCloudWatch Agent設定が正しく動作する

Scenario: ARMアーキテクチャでのAMIビルド成功
  Given component-arm.ymlが修正されている
  When EC2 Image BuilderでAMIビルドが実行される
  Then ビルドが正常完了する
    And 作成されたAMIでCloudWatch Agent設定が正しく動作する
```

---

## 7. スコープ外

### 7.1 明確にスコープ外とする事項

| ID | 内容 | 理由 |
|----|------|------|
| OS-001 | CloudWatch Agent CLIによる設定適用検証の実装 | `fetch-config`は設定適用を伴い、ビルド時には不適切 |
| OS-002 | translatorバイナリのパス探索ロジックの実装 | AL2023での安定性を確保するため、translator依存を完全に排除 |
| OS-003 | CloudWatch Agentの設定内容の妥当性検証（スキーマ検証） | 本対応は構文チェックに留め、妥当性検証は将来対応 |
| OS-004 | index.ts（Pulumiスタック定義）の変更 | YAMLファイルの修正のみで対応可能 |
| OS-005 | 他のステップ（InstallCloudWatchAgent, ConfigureCloudWatchAgent, EnableCloudWatchAgent）の修正 | 問題はValidateCloudWatchAgentConfigステップのみに限定 |

### 7.2 将来的な拡張候補

| ID | 内容 | 優先度 |
|----|------|--------|
| FE-001 | CloudWatch Agentの設定スキーマ検証の実装 | 低 |
| FE-002 | AL2023でのCloudWatch Agent公式検証方法の調査と採用 | 中 |
| FE-003 | pulumi/README.mdへの注意事項追記 | 低 |

---

## 8. 技術仕様

### 8.1 修正後の ValidateCloudWatchAgentConfig ステップ

Planning Documentで策定された推奨実装を採用：

```yaml
- name: ValidateCloudWatchAgentConfig
  action: ExecuteBash
  inputs:
    commands:
      - echo "Validating CloudWatch Agent configuration..."
      - |
        set -e
        CONFIG_PATH="/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"

        # 設定ファイルの存在確認
        if [ ! -f "$CONFIG_PATH" ]; then
          echo "ERROR: Configuration file not found at $CONFIG_PATH"
          exit 1
        fi

        # JSONシンタックスチェック（jqを使用）
        echo "Checking JSON syntax..."
        if ! jq empty "$CONFIG_PATH" 2>/dev/null; then
          echo "ERROR: Invalid JSON syntax in $CONFIG_PATH"
          jq . "$CONFIG_PATH" 2>&1 || true
          exit 1
        fi

        # 基本的な構造チェック（metricsセクションの存在確認）
        if ! jq -e '.metrics' "$CONFIG_PATH" >/dev/null 2>&1; then
          echo "WARNING: 'metrics' section not found in configuration"
        fi

        echo "CloudWatch Agent configuration validation passed."
      - cat /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
```

### 8.2 変更対象ファイル

| ファイル | 修正箇所 | 変更内容 |
|---------|---------|---------|
| `pulumi/jenkins-agent-ami/component-x86.yml` | 156-172行目 | ValidateCloudWatchAgentConfigステップの書き換え |
| `pulumi/jenkins-agent-ami/component-arm.yml` | 156-172行目 | ValidateCloudWatchAgentConfigステップの書き換え（x86と同一内容） |

---

## 9. 品質ゲートチェックリスト

### Phase 1: 要件定義

- [x] **機能要件が明確に記載されている**: FR-001〜FR-006として具体的な要件を定義
- [x] **受け入れ基準が定義されている**: Given-When-Then形式で検証可能な基準を記載
- [x] **スコープが明確である**: スコープ外事項と将来拡張候補を明示
- [x] **論理的な矛盾がない**: 各セクション間の整合性を確認済み

---

## 10. 参考情報

### 10.1 関連ファイル

- `pulumi/jenkins-agent-ami/component-x86.yml` - x86版コンポーネント定義
- `pulumi/jenkins-agent-ami/component-arm.yml` - ARM版コンポーネント定義
- `pulumi/jenkins-agent-ami/index.ts` - Pulumiスタック定義（変更なし）
- `pulumi/jenkins-agent-ami/templates/cloudwatch-agent-config.json` - CloudWatch Agent設定テンプレート

### 10.2 CloudWatch Agentインストールフロー

1. **InstallCloudWatchAgent** (136-142行目): `dnf install -y amazon-cloudwatch-agent`
2. **ConfigureCloudWatchAgent** (144-154行目): 設定ファイルの配置
3. **ValidateCloudWatchAgentConfig** (156-172行目): **問題箇所 → 本修正対象**
4. **EnableCloudWatchAgent** (173-179行目): サービス有効化

### 10.3 関連ドキュメント

- [AWS CloudWatch Agent ドキュメント](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent.html)
- [EC2 Image Builder コンポーネントドキュメント](https://docs.aws.amazon.com/imagebuilder/latest/userguide/component-manager.html)
- プロジェクト内: `pulumi/CONTRIBUTION.md`, `CLAUDE.md`

---

## 改訂履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| 1.0 | 作成日 | 初版作成 |
