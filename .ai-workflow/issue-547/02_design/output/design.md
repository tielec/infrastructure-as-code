# 詳細設計書: Issue #547

## Jenkins Agent AMI ビルド失敗: CloudWatch Agent Translator が見つからない

---

## 1. 概要

### 1.1 設計目的

本設計書は、Jenkins Agent AMIのEC2 Image Builderビルドにおいて、CloudWatch Agent設定検証ステップ（`ValidateCloudWatchAgentConfig`）がtranslatorバイナリの不在により失敗する問題を解決するための詳細設計を記述します。

### 1.2 対象コンポーネント

- `pulumi/jenkins-agent-ami/component-x86.yml`
- `pulumi/jenkins-agent-ami/component-arm.yml`

### 1.3 設計方針

Planning DocumentおよびRequirements Documentで策定された方針に従い、**方法2（JSONシンタックスチェック）** を採用します。`jq`コマンドを使用してJSON構文を検証し、translatorバイナリへの依存を完全に排除します。

---

## 2. アーキテクチャ設計

### 2.1 システム全体図

```
┌─────────────────────────────────────────────────────────────────────┐
│                     EC2 Image Builder                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    Build Phase                                   │ │
│  ├─────────────────────────────────────────────────────────────────┤ │
│  │                                                                   │ │
│  │  [1] InstallBasicPackages ───────────────────────────────────┐  │ │
│  │      └── dnf install -y git jq wget ...                       │  │ │
│  │                                                                │  │ │
│  │  [2] InstallCloudWatchAgent ─────────────────────────────────┤  │ │
│  │      └── dnf install -y amazon-cloudwatch-agent              │  │ │
│  │                                                                │  │ │
│  │  [3] ConfigureCloudWatchAgent ───────────────────────────────┤  │ │
│  │      └── 設定ファイルの配置                                   │  │ │
│  │          /opt/aws/amazon-cloudwatch-agent/etc/                │  │ │
│  │          amazon-cloudwatch-agent.json                         │  │ │
│  │                                                                │  │ │
│  │  [4] ValidateCloudWatchAgentConfig ──────────────────────────┤  │ │
│  │      └── 【本修正対象】                                       │  │ │
│  │          ❌ 旧: translatorバイナリによる検証 (失敗)          │  │ │
│  │          ✅ 新: jqによるJSONシンタックスチェック             │  │ │
│  │                                                                │  │ │
│  │  [5] EnableCloudWatchAgent ──────────────────────────────────┘  │ │
│  │      └── systemctl enable amazon-cloudwatch-agent               │ │
│  │                                                                   │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 コンポーネント間の関係

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Pulumi Stack                                     │
│                  pulumi/jenkins-agent-ami/                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  index.ts ────────────────────────────────────────────────────────┐  │
│      │                                                             │  │
│      ├── component-x86.yml を読み込み ──────────────────────────┐ │  │
│      │                                                           │ │  │
│      ├── component-arm.yml を読み込み ──────────────────────────┼─┘  │
│      │                                                           │    │
│      └── templates/cloudwatch-agent-config.json を注入 ─────────┘    │
│                                                                       │
│  injectCloudWatchConfig() 関数                                       │
│      └── __CWAGENT_CONFIG__ プレースホルダを置換                     │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.3 データフロー

```
[AMI Build Time]

1. component-x86.yml / component-arm.yml
   │
   ├── InstallBasicPackages
   │   └── jq コマンドがインストールされる
   │
   ├── ConfigureCloudWatchAgent
   │   └── 設定ファイル配置: /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
   │
   └── ValidateCloudWatchAgentConfig (修正対象)
       │
       ├── [Step 1] 設定ファイルの存在確認
       │   └── [ -f "$CONFIG_PATH" ]
       │
       ├── [Step 2] JSONシンタックスチェック
       │   └── jq empty "$CONFIG_PATH"
       │
       ├── [Step 3] 基本構造チェック (警告レベル)
       │   └── jq -e '.metrics' "$CONFIG_PATH"
       │
       └── [Step 4] 検証結果の出力
           └── 成功/失敗メッセージ + 設定ファイル内容表示
```

---

## 3. 実装戦略判断

### 実装戦略: EXTEND

**判断根拠**:

1. **既存ファイルの修正のみ**: 新規ファイルの作成は不要。既存の`component-x86.yml`と`component-arm.yml`の`ValidateCloudWatchAgentConfig`ステップを修正する
2. **既存の処理フローを維持**: CloudWatch Agentのインストール→設定→検証→有効化という既存のフローは変更なし
3. **修正箇所の局所性**: 変更箇所は両ファイルの156-172行目の`ValidateCloudWatchAgentConfig`ステップのみに限定
4. **既存依存関係の活用**: `jq`コマンドは既にInstallBasicPackagesステップ（55行目）でインストール済み
5. **アーキテクチャ変更なし**: EC2 Image Builderのコンポーネント構造、Pulumiスタック構成に変更なし

---

## 4. テスト戦略判断

### テスト戦略: INTEGRATION_ONLY

**判断根拠**:

1. **対象がインフラ定義コード**: 修正対象はEC2 Image BuilderのコンポーネントYAMLファイルであり、TypeScript/プログラムコードではない
2. **ユニットテスト不可**: YAMLファイル内のシェルスクリプトは、EC2 Image Builder実行環境でのみ動作検証可能
3. **BDDテスト非該当**: ユーザーストーリーベースの機能ではなく、インフラビルドプロセスの修正
4. **インテグレーションテストが適切**: AMIビルドパイプラインの実行によって、修正内容が正しく動作するかを検証
5. **静的解析で補完**: YAMLシンタックスチェック（yamllint等）による事前検証が可能

**テスト方法**:
- YAMLシンタックスチェック（静的解析）
- AMIビルドパイプラインの実行（インテグレーションテスト）
- 作成されたAMIでのCloudWatch Agent動作確認

---

## 5. テストコード戦略判断

### テストコード戦略: NO_CHANGE

**判断根拠**:

1. **修正対象がYAMLファイル**: EC2 Image Builderのコンポーネント定義であり、プログラムコードではない
2. **既存テストコードなし**: jenkins-agent-amiスタックにはTypeScript/プログラムコードのテストは存在しない
3. **テストはビルド実行で代替**: AMIビルドパイプラインの実行自体がインテグレーションテストとして機能
4. **静的解析のみ実施**: YAMLシンタックスチェックは既存のCI/CD環境またはローカルで実施可能

---

## 6. 影響範囲分析

### 6.1 既存コードへの影響

| ファイル | 変更内容 | 影響度 | 詳細 |
|---------|---------|--------|------|
| `pulumi/jenkins-agent-ami/component-x86.yml` | ValidateCloudWatchAgentConfigステップの書き換え | 中 | 156-172行目を新しい検証ロジックに置換 |
| `pulumi/jenkins-agent-ami/component-arm.yml` | ValidateCloudWatchAgentConfigステップの書き換え | 中 | 156-172行目を新しい検証ロジックに置換（x86と同一内容） |
| `pulumi/jenkins-agent-ami/index.ts` | なし | なし | YAMLファイルの読み込みロジックに変更なし |
| `pulumi/jenkins-agent-ami/templates/cloudwatch-agent-config.json` | なし | なし | 設定テンプレートに変更なし |

### 6.2 依存関係の変更

| 項目 | 変更有無 | 詳細 |
|------|---------|------|
| 新規依存の追加 | なし | `jq`は既にInstallBasicPackagesでインストール済み |
| 既存依存の変更 | あり | translatorバイナリへの依存を削除 |
| パッケージ依存 | なし | package.json、tsconfig.jsonに変更なし |
| SSMパラメータ | なし | 参照・保存するパラメータに変更なし |

### 6.3 マイグレーション要否

| 項目 | 要否 | 詳細 |
|------|------|------|
| データベーススキーマ変更 | 不要 | データベース非使用 |
| 設定ファイル変更 | YAMLファイル修正のみ | ビルド時に自動適用 |
| SSMパラメータ変更 | 不要 | 既存パラメータの変更なし |
| 既存AMIへの影響 | なし | 新規ビルドから適用 |
| ロールバック | 容易 | Git revertで対応可能 |

---

## 7. 変更・追加ファイルリスト

### 7.1 修正が必要な既存ファイル

| ファイルパス | 修正箇所 | 変更内容 |
|-------------|---------|---------|
| `pulumi/jenkins-agent-ami/component-x86.yml` | 156-172行目 | ValidateCloudWatchAgentConfigステップを新しい検証ロジックに置換 |
| `pulumi/jenkins-agent-ami/component-arm.yml` | 156-172行目 | ValidateCloudWatchAgentConfigステップを新しい検証ロジックに置換（x86と同一内容） |

### 7.2 新規作成ファイル

なし

### 7.3 削除が必要なファイル

なし

---

## 8. 詳細設計

### 8.1 修正後の ValidateCloudWatchAgentConfig ステップ

#### 設計仕様

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

#### 設計根拠

| 設計項目 | 根拠 |
|---------|------|
| `set -e` | エラー時に即座に終了し、ビルドを適切に中断する |
| 設定ファイル存在確認 | ConfigureCloudWatchAgentステップの正常完了を確認 |
| `jq empty` | JSON構文の妥当性のみを検証（パースエラーを検出） |
| `jq -e '.metrics'` | 基本構造の存在確認（警告レベル、ビルドは中断しない） |
| 設定ファイル内容表示 | デバッグ用に既存動作を維持 |

### 8.2 処理フロー

```
┌─────────────────────────────────────────────────────────────────────┐
│                  ValidateCloudWatchAgentConfig                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  [Start]                                                              │
│     │                                                                 │
│     ▼                                                                 │
│  ┌─────────────────────────────────────────┐                         │
│  │ Step 1: 設定ファイル存在確認             │                         │
│  │ [ -f "$CONFIG_PATH" ]                   │                         │
│  └─────────────────────────────────────────┘                         │
│     │                                                                 │
│     ├── 存在しない ───────────────────────────────────┐              │
│     │                                                   ▼              │
│     │                                        ┌──────────────────────┐ │
│     │                                        │ ERROR: File not found │ │
│     │                                        │ exit 1               │ │
│     │                                        └──────────────────────┘ │
│     │                                                                 │
│     ├── 存在する                                                      │
│     ▼                                                                 │
│  ┌─────────────────────────────────────────┐                         │
│  │ Step 2: JSONシンタックスチェック          │                         │
│  │ jq empty "$CONFIG_PATH"                 │                         │
│  └─────────────────────────────────────────┘                         │
│     │                                                                 │
│     ├── 失敗 ─────────────────────────────────────────┐              │
│     │                                                   ▼              │
│     │                                        ┌──────────────────────┐ │
│     │                                        │ ERROR: Invalid JSON   │ │
│     │                                        │ jq . (詳細表示)       │ │
│     │                                        │ exit 1               │ │
│     │                                        └──────────────────────┘ │
│     │                                                                 │
│     ├── 成功                                                          │
│     ▼                                                                 │
│  ┌─────────────────────────────────────────┐                         │
│  │ Step 3: 基本構造チェック (警告レベル)     │                         │
│  │ jq -e '.metrics' "$CONFIG_PATH"         │                         │
│  └─────────────────────────────────────────┘                         │
│     │                                                                 │
│     ├── 失敗 ─────────────────────────────────────────┐              │
│     │                                                   ▼              │
│     │                                        ┌──────────────────────┐ │
│     │                                        │ WARNING: metrics     │ │
│     │                                        │ section not found    │ │
│     │                                        │ (ビルド継続)          │ │
│     │                                        └──────────────────────┘ │
│     │                                                   │              │
│     ├── 成功                                            │              │
│     │                                                   │              │
│     ▼                                                   ▼              │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Step 4: 検証成功メッセージ出力                                   │ │
│  │ "CloudWatch Agent configuration validation passed."             │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│     │                                                                 │
│     ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Step 5: 設定ファイル内容表示 (デバッグ用)                         │ │
│  │ cat /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json │
│  └─────────────────────────────────────────────────────────────────┘ │
│     │                                                                 │
│     ▼                                                                 │
│  [End - Success]                                                      │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 8.3 エラーハンドリング

| エラー条件 | 対応 | 終了コード |
|-----------|------|-----------|
| 設定ファイルが存在しない | エラーメッセージを出力してビルドを中断 | 1 |
| JSON構文エラー | エラーメッセージとjqの詳細出力を表示してビルドを中断 | 1 |
| metricsセクションが存在しない | 警告メッセージを出力してビルドを継続 | 0 |
| 検証成功 | 成功メッセージを出力 | 0 |

### 8.4 コマンド仕様

| コマンド | 目的 | オプション説明 |
|---------|------|---------------|
| `jq empty "$CONFIG_PATH"` | JSON構文の妥当性検証 | `empty`フィルターは出力なしでパースのみ実行 |
| `jq . "$CONFIG_PATH"` | JSON整形出力（エラー詳細表示用） | `.`フィルターはそのまま出力 |
| `jq -e '.metrics' "$CONFIG_PATH"` | metricsセクションの存在確認 | `-e`は結果がnull/falseの場合に終了コード1を返す |

---

## 9. セキュリティ考慮事項

### 9.1 認証・認可

| 項目 | 対応 |
|------|------|
| 認証 | 変更なし（EC2 Image Builderの既存認証機構を使用） |
| 認可 | 変更なし（imageBuilderRoleの権限に変更なし） |
| IAMロール | 変更なし |

### 9.2 データ保護

| 項目 | 対応 |
|------|------|
| 設定ファイルの内容 | ログに出力されるが、機密情報は含まれない |
| クレデンシャル | 設定ファイルにクレデンシャルは含まれない |
| 暗号化 | 変更なし |

### 9.3 セキュリティリスクと対策

| リスク | 影響度 | 対策 |
|-------|-------|------|
| jqコマンドの脆弱性 | 低 | AL2023の公式パッケージを使用、定期的なOS更新で対応 |
| 検証バイパス | 低 | JSON構文エラーはビルドを中断、基本構造チェックで警告 |

---

## 10. 非機能要件への対応

### 10.1 パフォーマンス

| 要件ID | 要件 | 対応方法 | 測定基準 |
|--------|------|---------|---------|
| NFR-001 | 検証ステップの実行時間は5秒以内 | jqコマンドは高速に動作 | ステップ実行時間 < 5秒 |
| NFR-002 | AMIビルド全体の実行時間に有意な増加なし | 検証ロジックの簡略化 | 既存ビルド時間との差分 < 1分 |

### 10.2 スケーラビリティ

| 項目 | 対応 |
|------|------|
| 複数アーキテクチャ対応 | x86/ARM両方で同一の検証コードを使用 |
| 設定ファイルサイズ | jqは大きなJSONファイルも高速に処理可能 |

### 10.3 保守性

| 要件ID | 要件 | 対応方法 |
|--------|------|---------|
| NFR-007 | CloudWatch Agentパッケージ更新に影響されない | translator依存を排除、標準ツール(jq)のみ使用 |
| NFR-008 | x86/ARM版で同一の検証コード | 両ファイルに同一の検証ステップを適用 |
| NFR-009 | 日本語コメント | CLAUDE.mdのコーディングガイドラインに準拠 |

---

## 11. 実装の順序

### 11.1 推奨実装順序

```
1. component-x86.yml の修正
   │
   ├── ValidateCloudWatchAgentConfig ステップの書き換え (156-172行目)
   │
   └── YAMLシンタックスチェック

2. component-arm.yml の修正
   │
   ├── ValidateCloudWatchAgentConfig ステップの書き換え (156-172行目)
   │   └── x86版と同一の内容を適用
   │
   └── YAMLシンタックスチェック

3. 静的解析・検証
   │
   ├── yamllint による構文チェック
   │
   └── 修正前後の差分確認
```

### 11.2 依存関係の考慮

| 順序 | タスク | 依存関係 |
|------|-------|---------|
| 1 | component-x86.yml 修正 | なし（独立） |
| 2 | component-arm.yml 修正 | なし（独立、x86と並行可能） |
| 3 | 静的解析 | 1, 2の完了後 |

**注記**: x86版とARM版の修正は独立しており、並行して実施可能です。ただし、同一の修正内容を適用するため、x86版を先に修正し、その内容をARM版にコピーすることを推奨します。

---

## 12. テスト計画

### 12.1 静的解析

| テスト項目 | 方法 | 合格基準 |
|-----------|------|---------|
| YAMLシンタックス | `yamllint component-x86.yml component-arm.yml` | エラーなし |
| 差分確認 | `git diff` | 意図した変更のみ |

### 12.2 インテグレーションテスト

| テスト項目 | 方法 | 合格基準 |
|-----------|------|---------|
| x86 AMIビルド | EC2 Image Builder パイプライン実行 | ビルド成功 |
| ARM AMIビルド | EC2 Image Builder パイプライン実行 | ビルド成功 |
| CloudWatch Agent動作 | 作成されたAMIでインスタンス起動、ログ確認 | メトリクス収集成功 |

### 12.3 テストシナリオ

#### シナリオ1: 正常系（設定ファイル存在、JSON構文正常）

```gherkin
Given CloudWatch Agentがインストールされている
  And 設定ファイル(/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json)が存在する
  And 設定ファイルの内容が有効なJSON形式である
When ValidateCloudWatchAgentConfigステップが実行される
Then ステップが正常終了する（ExitCode 0）
  And "CloudWatch Agent configuration validation passed." がログに出力される
  And 設定ファイルの内容がログに表示される
```

#### シナリオ2: 異常系（設定ファイル不存在）

```gherkin
Given CloudWatch Agentがインストールされている
  And 設定ファイルが存在しない
When ValidateCloudWatchAgentConfigステップが実行される
Then ステップが失敗する（ExitCode 1）
  And "ERROR: Configuration file not found" がログに出力される
```

#### シナリオ3: 異常系（JSON構文エラー）

```gherkin
Given CloudWatch Agentがインストールされている
  And 設定ファイルが存在する
  And 設定ファイルの内容がJSON構文エラーを含む
When ValidateCloudWatchAgentConfigステップが実行される
Then ステップが失敗する（ExitCode 1）
  And "ERROR: Invalid JSON syntax" がログに出力される
```

---

## 13. 品質ゲートチェックリスト

### Phase 2: 設計

- [x] **実装戦略の判断根拠が明記されている**: EXTEND戦略を選択し、5つの判断根拠を記載
- [x] **テスト戦略の判断根拠が明記されている**: INTEGRATION_ONLY戦略を選択し、5つの判断根拠を記載
- [x] **既存コードへの影響範囲が分析されている**: 6.1節で影響度を含む詳細な分析を記載
- [x] **変更が必要なファイルがリストアップされている**: 7節で修正対象ファイルとその箇所を明記
- [x] **設計が実装可能である**: 8節で具体的なYAMLコード、処理フロー、エラーハンドリングを記載

---

## 14. 参考情報

### 14.1 関連ファイル

| ファイル | 説明 | 修正有無 |
|---------|------|---------|
| `pulumi/jenkins-agent-ami/component-x86.yml` | x86版コンポーネント定義 | **修正対象** |
| `pulumi/jenkins-agent-ami/component-arm.yml` | ARM版コンポーネント定義 | **修正対象** |
| `pulumi/jenkins-agent-ami/index.ts` | Pulumiスタック定義 | 変更なし |
| `pulumi/jenkins-agent-ami/templates/cloudwatch-agent-config.json` | CloudWatch Agent設定テンプレート | 変更なし |

### 14.2 CloudWatch Agentインストールフロー

| ステップ | 行番号 | 内容 | 本修正との関係 |
|---------|-------|------|---------------|
| InstallBasicPackages | 51-56 | jqを含む基本パッケージのインストール | jqコマンドの前提 |
| InstallCloudWatchAgent | 136-142 | CloudWatch Agentのインストール | 前提ステップ |
| ConfigureCloudWatchAgent | 144-154 | 設定ファイルの配置 | 前提ステップ |
| ValidateCloudWatchAgentConfig | 156-172 | 設定検証 | **本修正対象** |
| EnableCloudWatchAgent | 173-179 | サービス有効化 | 後続ステップ |

### 14.3 関連ドキュメント

- [AWS CloudWatch Agent ドキュメント](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent.html)
- [EC2 Image Builder コンポーネントドキュメント](https://docs.aws.amazon.com/imagebuilder/latest/userguide/component-manager.html)
- プロジェクト内: `pulumi/CONTRIBUTION.md`, `CLAUDE.md`

---

## 改訂履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| 1.0 | 作成日 | 初版作成 |
