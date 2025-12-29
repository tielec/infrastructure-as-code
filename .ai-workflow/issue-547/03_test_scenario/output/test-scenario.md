# テストシナリオ: Issue #547

## Jenkins Agent AMI ビルド失敗: CloudWatch Agent Translator が見つからない

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略

**テスト戦略: INTEGRATION_ONLY**

Phase 2（設計フェーズ）で決定された通り、本修正はEC2 Image BuilderのコンポーネントYAMLファイルの修正であり、プログラムコードではないため、インテグレーションテストのみを実施します。

### 1.2 戦略選択の根拠

| 根拠 | 説明 |
|------|------|
| 対象がインフラ定義コード | 修正対象はEC2 Image BuilderのコンポーネントYAMLファイルであり、TypeScript/プログラムコードではない |
| ユニットテスト不可 | YAMLファイル内のシェルスクリプトは、EC2 Image Builder実行環境でのみ動作検証可能 |
| BDDテスト非該当 | ユーザーストーリーベースの機能ではなく、インフラビルドプロセスの修正 |
| インテグレーションテストが適切 | AMIビルドパイプラインの実行によって、修正内容が正しく動作するかを検証 |
| 静的解析で補完 | YAMLシンタックスチェック（yamllint等）による事前検証が可能 |

### 1.3 テスト対象の範囲

| 対象 | ファイルパス | 修正箇所 |
|------|-------------|---------|
| x86版コンポーネント | `pulumi/jenkins-agent-ami/component-x86.yml` | 156-172行目（ValidateCloudWatchAgentConfigステップ） |
| ARM版コンポーネント | `pulumi/jenkins-agent-ami/component-arm.yml` | 156-172行目（ValidateCloudWatchAgentConfigステップ） |

### 1.4 テストの目的

1. **主目的**: 修正後のValidateCloudWatchAgentConfigステップがAL2023環境で正常に動作することを確認
2. **副目的**: CloudWatch Agent設定ファイルの検証が適切に機能することを確認
3. **品質確認**: AMIビルドプロセス全体が正常に完了することを確認

---

## 2. 静的解析テストシナリオ

インテグレーションテストの前提として、YAMLファイルの静的解析を実施します。

### 2.1 YAMLシンタックスチェック

**シナリオ名**: YAML構文の妥当性検証

| 項目 | 内容 |
|------|------|
| **目的** | 修正後のYAMLファイルが構文的に正しいことを確認 |
| **前提条件** | yamllintまたは同等のYAML構文チェックツールがインストールされている |
| **対象ファイル** | `component-x86.yml`, `component-arm.yml` |
| **実行コマンド** | `yamllint component-x86.yml component-arm.yml` |
| **合格基準** | エラーなし（警告は許容） |

**テスト手順**:

```bash
# 1. yamllintのインストール（必要に応じて）
pip install yamllint

# 2. x86版の構文チェック
yamllint pulumi/jenkins-agent-ami/component-x86.yml

# 3. ARM版の構文チェック
yamllint pulumi/jenkins-agent-ami/component-arm.yml
```

**期待結果**:
- 両ファイルともYAML構文エラーなし
- EC2 Image Builderのスキーマに準拠した構造であること

### 2.2 差分確認

**シナリオ名**: 修正箇所の意図確認

| 項目 | 内容 |
|------|------|
| **目的** | 修正が意図した箇所のみに限定されていることを確認 |
| **前提条件** | gitリポジトリでの変更追跡が有効 |
| **実行コマンド** | `git diff pulumi/jenkins-agent-ami/component-*.yml` |
| **合格基準** | ValidateCloudWatchAgentConfigステップのみに変更が限定されている |

**確認項目チェックリスト**:
- [ ] `component-x86.yml`の156-172行目のみが変更されている
- [ ] `component-arm.yml`の156-172行目のみが変更されている
- [ ] 他のステップ（InstallCloudWatchAgent, ConfigureCloudWatchAgent, EnableCloudWatchAgent）に変更がない
- [ ] x86版とARM版の修正内容が同一である

---

## 3. インテグレーションテストシナリオ

### 3.1 シナリオ1: 正常系 - CloudWatch Agent設定検証成功

**シナリオ名**: ValidateCloudWatchAgentConfig_正常系_設定ファイル存在_JSON構文正常

| 項目 | 内容 |
|------|------|
| **目的** | 有効な設定ファイルが存在する場合、検証ステップが正常終了することを確認 |
| **テスト種別** | インテグレーションテスト |
| **アーキテクチャ** | x86_64, arm64（両方で実施） |
| **優先度** | 高（必須） |

**前提条件**:
- CloudWatch Agentがインストール済み（InstallCloudWatchAgentステップ完了）
- 設定ファイル（`/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json`）が配置済み（ConfigureCloudWatchAgentステップ完了）
- 設定ファイルの内容が有効なJSON形式である
- `jq`コマンドがインストール済み（InstallBasicPackagesステップ完了）

**テスト手順**:

1. EC2 Image BuilderでAMIビルドパイプラインを実行
2. ValidateCloudWatchAgentConfigステップの実行を監視
3. ステップの完了ステータスとログ出力を確認

**期待結果**:

| 確認項目 | 期待値 |
|---------|--------|
| ステップ終了コード | 0（成功） |
| ログ出力: 開始メッセージ | "Validating CloudWatch Agent configuration..." |
| ログ出力: JSON構文チェック | "Checking JSON syntax..." |
| ログ出力: 成功メッセージ | "CloudWatch Agent configuration validation passed." |
| ログ出力: 設定ファイル内容 | JSON形式の設定内容が表示される |
| 後続ステップ | EnableCloudWatchAgentステップが開始される |

**検証コマンド（ログ確認）**:

```bash
# EC2 Image Builderのビルドログで以下を確認
grep -E "Validating CloudWatch Agent|Checking JSON syntax|validation passed" <build_log>
```

---

### 3.2 シナリオ2: 異常系 - 設定ファイル不存在

**シナリオ名**: ValidateCloudWatchAgentConfig_異常系_設定ファイル不存在

| 項目 | 内容 |
|------|------|
| **目的** | 設定ファイルが存在しない場合、検証ステップが適切にエラー終了することを確認 |
| **テスト種別** | インテグレーションテスト（手動シミュレーション） |
| **アーキテクチャ** | x86_64（代表として実施） |
| **優先度** | 中（ConfigureCloudWatchAgentステップの失敗をシミュレート） |

**前提条件**:
- ConfigureCloudWatchAgentステップを意図的にスキップまたは失敗させた状態
- または、設定ファイルを手動で削除した状態

**テスト手順**:

1. テスト用に修正したコンポーネントYAMLを用意（ConfigureCloudWatchAgentステップを無効化）
2. AMIビルドを実行
3. ValidateCloudWatchAgentConfigステップの実行を監視

**期待結果**:

| 確認項目 | 期待値 |
|---------|--------|
| ステップ終了コード | 1（失敗） |
| ログ出力: エラーメッセージ | "ERROR: Configuration file not found at /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json" |
| ビルドステータス | ビルドが適切に中断される |

**注記**: 本シナリオは通常のビルドフローでは発生しないため、手動でのシミュレーションテストとして位置付けます。

---

### 3.3 シナリオ3: 異常系 - JSON構文エラー

**シナリオ名**: ValidateCloudWatchAgentConfig_異常系_JSON構文エラー

| 項目 | 内容 |
|------|------|
| **目的** | 設定ファイルにJSON構文エラーがある場合、検証ステップが適切にエラー終了することを確認 |
| **テスト種別** | インテグレーションテスト（手動シミュレーション） |
| **アーキテクチャ** | x86_64（代表として実施） |
| **優先度** | 中（設定ミスの検出能力を確認） |

**前提条件**:
- 意図的に無効なJSONを含む設定ファイルを配置した状態

**テスト手順**:

1. テスト用にtemplates/cloudwatch-agent-config.jsonを無効なJSONに変更
   ```json
   {
     "metrics": {
       "invalid_json":
     }
   }
   ```
2. AMIビルドを実行
3. ValidateCloudWatchAgentConfigステップの実行を監視

**期待結果**:

| 確認項目 | 期待値 |
|---------|--------|
| ステップ終了コード | 1（失敗） |
| ログ出力: エラーメッセージ | "ERROR: Invalid JSON syntax in /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json" |
| ログ出力: エラー詳細 | jqによるパースエラーの詳細が表示される |
| ビルドステータス | ビルドが適切に中断される |

**注記**: 本シナリオは通常のビルドフローでは発生しないため、手動でのシミュレーションテストとして位置付けます。

---

### 3.4 シナリオ4: 警告系 - metricsセクション不存在

**シナリオ名**: ValidateCloudWatchAgentConfig_警告系_metricsセクション不存在

| 項目 | 内容 |
|------|------|
| **目的** | 設定ファイルにmetricsセクションがない場合、警告を出力しつつビルドが継続することを確認 |
| **テスト種別** | インテグレーションテスト（手動シミュレーション） |
| **アーキテクチャ** | x86_64（代表として実施） |
| **優先度** | 低（基本構造チェックの動作確認） |

**前提条件**:
- metricsセクションを含まない有効なJSONを設定ファイルとして配置した状態

**テスト手順**:

1. テスト用にtemplates/cloudwatch-agent-config.jsonを以下に変更
   ```json
   {
     "logs": {
       "logs_collected": {}
     }
   }
   ```
2. AMIビルドを実行
3. ValidateCloudWatchAgentConfigステップの実行を監視

**期待結果**:

| 確認項目 | 期待値 |
|---------|--------|
| ステップ終了コード | 0（成功） |
| ログ出力: 警告メッセージ | "WARNING: 'metrics' section not found in configuration" |
| ログ出力: 成功メッセージ | "CloudWatch Agent configuration validation passed." |
| 後続ステップ | EnableCloudWatchAgentステップが開始される（ビルド継続） |

---

### 3.5 シナリオ5: x86アーキテクチャAMIビルド成功

**シナリオ名**: AMIビルド_x86_64_正常系_全ステップ成功

| 項目 | 内容 |
|------|------|
| **目的** | x86アーキテクチャでAMIビルド全体が正常に完了することを確認 |
| **テスト種別** | インテグレーションテスト（End-to-End） |
| **アーキテクチャ** | x86_64 |
| **優先度** | 高（必須） |

**前提条件**:
- component-x86.ymlが修正済み
- EC2 Image Builderパイプラインが設定済み
- 必要なIAMロール、セキュリティグループが設定済み

**テスト手順**:

1. Pulumiでx86用のImage Builderパイプラインをデプロイ
2. AMIビルドパイプラインを手動またはスケジュールトリガーで実行
3. ビルドの完了を待機（約20-40分）
4. ビルドステータスを確認

**期待結果**:

| 確認項目 | 期待値 |
|---------|--------|
| ビルドステータス | AVAILABLE（成功） |
| 全ステップステータス | 全ステップがSUCCESS |
| ValidateCloudWatchAgentConfigステップ | SUCCESS（旧実装では FAILED だった） |
| 作成されたAMI | AMI IDが取得できる |

**確認コマンド（AWS CLI）**:

```bash
# ビルドステータスの確認
aws imagebuilder get-image-pipeline --image-pipeline-arn <pipeline-arn>

# 最新ビルドの確認
aws imagebuilder list-image-build-versions --image-version-arn <image-arn>
```

---

### 3.6 シナリオ6: ARMアーキテクチャAMIビルド成功

**シナリオ名**: AMIビルド_arm64_正常系_全ステップ成功

| 項目 | 内容 |
|------|------|
| **目的** | ARMアーキテクチャでAMIビルド全体が正常に完了することを確認 |
| **テスト種別** | インテグレーションテスト（End-to-End） |
| **アーキテクチャ** | arm64 |
| **優先度** | 高（必須） |

**前提条件**:
- component-arm.ymlが修正済み
- EC2 Image Builderパイプラインが設定済み
- 必要なIAMロール、セキュリティグループが設定済み

**テスト手順**:

1. Pulumiでarm64用のImage Builderパイプラインをデプロイ
2. AMIビルドパイプラインを手動またはスケジュールトリガーで実行
3. ビルドの完了を待機（約20-40分）
4. ビルドステータスを確認

**期待結果**:

| 確認項目 | 期待値 |
|---------|--------|
| ビルドステータス | AVAILABLE（成功） |
| 全ステップステータス | 全ステップがSUCCESS |
| ValidateCloudWatchAgentConfigステップ | SUCCESS |
| 作成されたAMI | AMI IDが取得できる |

---

### 3.7 シナリオ7: CloudWatch Agent動作確認

**シナリオ名**: CloudWatchAgent_動作確認_作成AMIでのメトリクス収集

| 項目 | 内容 |
|------|------|
| **目的** | 作成されたAMIでCloudWatch Agentが正常に動作することを確認 |
| **テスト種別** | インテグレーションテスト（機能検証） |
| **アーキテクチャ** | x86_64, arm64（両方で実施） |
| **優先度** | 高（必須） |

**前提条件**:
- シナリオ5, 6で作成されたAMIが利用可能
- EC2インスタンスを起動するためのVPC、サブネット、IAMロールが設定済み

**テスト手順**:

1. 作成されたAMIからEC2インスタンスを起動
2. インスタンスの起動完了を待機
3. CloudWatch Agentサービスの状態を確認
4. CloudWatchメトリクスを確認

**期待結果**:

| 確認項目 | 期待値 |
|---------|--------|
| インスタンス起動 | 正常に起動 |
| CloudWatch Agentサービス状態 | active (running) |
| 設定ファイルの存在 | `/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json` が存在 |
| CloudWatchメトリクス | CWAgent名前空間にcpu_*, mem_*メトリクスが送信されている |

**確認コマンド（EC2インスタンス内）**:

```bash
# CloudWatch Agentサービスの状態確認
systemctl status amazon-cloudwatch-agent

# 設定ファイルの確認
cat /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# CloudWatch Agentのログ確認
tail -f /opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log
```

**確認コマンド（AWS CLI）**:

```bash
# CloudWatchメトリクスの確認
aws cloudwatch list-metrics --namespace CWAgent

# 特定のメトリクスデータの取得
aws cloudwatch get-metric-statistics \
  --namespace CWAgent \
  --metric-name cpu_usage_active \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Average
```

---

## 4. テストデータ

### 4.1 正常系テストデータ

**CloudWatch Agent設定ファイル（有効なJSON）**:

```json
{
  "metrics": {
    "namespace": "CWAgent",
    "metrics_collected": {
      "cpu": {
        "resources": ["*"],
        "measurement": [
          {"name": "cpu_usage_active"},
          {"name": "cpu_usage_user"},
          {"name": "cpu_usage_system"},
          {"name": "cpu_usage_iowait"}
        ],
        "metrics_collection_interval": 60
      },
      "mem": {
        "measurement": [
          {"name": "mem_used_percent"},
          {"name": "mem_used"},
          {"name": "mem_available"}
        ],
        "metrics_collection_interval": 60
      }
    },
    "append_dimensions": {
      "AutoScalingGroupName": "${aws:AutoScalingGroupName}"
    },
    "aggregation_dimensions": [
      ["AutoScalingGroupName"]
    ]
  }
}
```

### 4.2 異常系テストデータ

**JSON構文エラーを含む設定ファイル（シナリオ3用）**:

```json
{
  "metrics": {
    "namespace": "CWAgent",
    "metrics_collected": {
      "cpu": {
        "resources": ["*"],
        "measurement": [
          {"name": "cpu_usage_active"
        ]
      }
    }
  }
}
```
※ 閉じ括弧が不足している無効なJSON

**metricsセクションがない設定ファイル（シナリオ4用）**:

```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/messages",
            "log_group_name": "system-logs"
          }
        ]
      }
    }
  }
}
```

---

## 5. テスト環境要件

### 5.1 静的解析環境

| 項目 | 要件 |
|------|------|
| ツール | yamllint（pip install yamllint） |
| 実行環境 | ローカル開発環境またはCI/CD |
| 所要時間 | 数秒 |

### 5.2 インテグレーションテスト環境

| 項目 | 要件 |
|------|------|
| AWSアカウント | EC2 Image Builder実行権限を持つアカウント |
| IAMロール | imagebuilderRole（EC2 Image Builder用） |
| VPC/サブネット | Image Builder用のサブネット |
| ベースAMI | Amazon Linux 2023（AL2023） |
| インスタンスタイプ | x86: m5.large以上, ARM: m6g.large以上 |
| ディスク容量 | 30GB以上 |
| 所要時間 | 20-40分/ビルド |

### 5.3 CloudWatch Agent動作確認環境

| 項目 | 要件 |
|------|------|
| EC2インスタンス | 作成されたAMIから起動 |
| IAMロール | CloudWatchAgentServerPolicy を含むロール |
| セキュリティグループ | アウトバウンド443許可（CloudWatchエンドポイント） |
| 所要時間 | 5-10分 |

---

## 6. テスト実行計画

### 6.1 テスト実行順序

```
1. 静的解析（前提テスト）
   │
   ├── 1-1. YAMLシンタックスチェック（x86）
   ├── 1-2. YAMLシンタックスチェック（ARM）
   └── 1-3. 差分確認

2. インテグレーションテスト（本テスト）
   │
   ├── 2-1. x86 AMIビルド（シナリオ5）
   │   └── 2-1-1. ValidateCloudWatchAgentConfig成功確認（シナリオ1）
   │
   ├── 2-2. ARM AMIビルド（シナリオ6）
   │   └── 2-2-1. ValidateCloudWatchAgentConfig成功確認（シナリオ1）
   │
   └── 2-3. CloudWatch Agent動作確認（シナリオ7）
       ├── 2-3-1. x86インスタンスでの確認
       └── 2-3-2. ARMインスタンスでの確認

3. 異常系テスト（オプション・手動シミュレーション）
   │
   ├── 3-1. 設定ファイル不存在テスト（シナリオ2）
   ├── 3-2. JSON構文エラーテスト（シナリオ3）
   └── 3-3. metricsセクション不存在テスト（シナリオ4）
```

### 6.2 実行タイムライン（見積もり）

| フェーズ | テスト内容 | 所要時間 | 並行可否 |
|---------|-----------|---------|---------|
| Phase 1 | 静的解析 | 5分 | N/A |
| Phase 2a | x86 AMIビルド | 20-40分 | ✓ |
| Phase 2b | ARM AMIビルド | 20-40分 | ✓（2aと並行可能） |
| Phase 3a | x86 CloudWatch Agent確認 | 10分 | ✓ |
| Phase 3b | ARM CloudWatch Agent確認 | 10分 | ✓（3aと並行可能） |
| Phase 4 | 異常系テスト（オプション） | 60-120分 | - |

**合計見積もり**: 約1時間（異常系テスト除く）

---

## 7. 合格基準と判定

### 7.1 必須合格基準

| ID | 基準 | 判定方法 |
|----|------|---------|
| AC-001 | YAMLシンタックスチェックがエラーなしで完了 | yamllintの終了コード = 0 |
| AC-002 | x86 AMIビルドが成功 | Image Builderステータス = AVAILABLE |
| AC-003 | ARM AMIビルドが成功 | Image Builderステータス = AVAILABLE |
| AC-004 | ValidateCloudWatchAgentConfigステップが成功 | ステップステータス = SUCCESS |
| AC-005 | 作成AMIでCloudWatch Agentが動作 | systemctl status = active (running) |

### 7.2 推奨合格基準

| ID | 基準 | 判定方法 |
|----|------|---------|
| RC-001 | CloudWatchメトリクスが送信されている | aws cloudwatch list-metricsでメトリクス存在確認 |
| RC-002 | 異常系テストで適切なエラーハンドリング | エラーメッセージとビルド中断の確認 |

### 7.3 総合判定

| 判定 | 条件 |
|------|------|
| **PASS** | AC-001〜AC-005がすべて合格 |
| **CONDITIONAL PASS** | AC-001〜AC-004が合格、AC-005が未確認 |
| **FAIL** | AC-001〜AC-004のいずれかが不合格 |

---

## 8. 品質ゲートチェックリスト

### Phase 3: テストシナリオ

- [x] **Phase 2の戦略に沿ったテストシナリオである**: INTEGRATION_ONLY戦略に基づき、インテグレーションテストシナリオのみを作成
- [x] **主要な正常系がカバーされている**: シナリオ1, 5, 6, 7で正常系をカバー
- [x] **主要な異常系がカバーされている**: シナリオ2, 3, 4で異常系をカバー
- [x] **期待結果が明確である**: 各シナリオに具体的な期待結果を記載

---

## 9. 参考情報

### 9.1 関連ドキュメント

- Planning Document: `.ai-workflow/issue-547/00_planning/output/planning.md`
- Requirements Document: `.ai-workflow/issue-547/01_requirements/output/requirements.md`
- Design Document: `.ai-workflow/issue-547/02_design/output/design.md`

### 9.2 関連ファイル

| ファイル | 説明 |
|---------|------|
| `pulumi/jenkins-agent-ami/component-x86.yml` | x86版コンポーネント定義（修正対象） |
| `pulumi/jenkins-agent-ami/component-arm.yml` | ARM版コンポーネント定義（修正対象） |
| `pulumi/jenkins-agent-ami/templates/cloudwatch-agent-config.json` | CloudWatch Agent設定テンプレート |
| `pulumi/jenkins-agent-ami/index.ts` | Pulumiスタック定義 |

### 9.3 CloudWatch Agentインストールフロー

| ステップ | 行番号 | 内容 | テストでの確認 |
|---------|-------|------|---------------|
| InstallBasicPackages | 51-56 | jqを含む基本パッケージのインストール | jqコマンドの前提確認 |
| InstallCloudWatchAgent | 136-142 | CloudWatch Agentのインストール | ステップ成功確認 |
| ConfigureCloudWatchAgent | 144-154 | 設定ファイルの配置 | ステップ成功確認 |
| ValidateCloudWatchAgentConfig | 156-172 | 設定検証 | **本テストの主対象** |
| EnableCloudWatchAgent | 173-179 | サービス有効化 | ステップ成功確認 |

---

## 改訂履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| 1.0 | 作成日 | 初版作成 |
