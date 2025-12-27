# テストシナリオ: Issue #542

## SpotFleetエージェントのCPUクレジットUnlimited設定適用

---

## 1. テスト戦略サマリー

### 選択されたテスト戦略

**INTEGRATION_ONLY（手動検証）**

### 戦略選択の根拠（Phase 2より引用）

- Pulumiインフラコードであり、従来のユニットテストの対象ではない
- `pulumi preview`による差分確認が主要な検証手段
- 実際のAWSリソースへの反映後、AWSコンソールまたはCloudWatchで設定を確認する必要がある
- このリポジトリにはPulumiスタック用の自動テストフレームワークが存在しない
- BDDテストは不要（インフラ設定変更であり、ユーザーストーリー中心のテストではない）

### テスト対象の範囲

| 対象 | 説明 |
|------|------|
| `pulumi/jenkins-agent/index.ts` | `agentLaunchTemplate`と`agentLaunchTemplateArm`への`creditSpecification`プロパティ追加 |
| AWS LaunchTemplate | AWSリソースとして正しく設定が反映されていること |
| SpotFleet連携 | 新規インスタンスにUnlimited設定が適用されること |

### テストの目的

1. **コード品質の確認**: TypeScriptコンパイルエラーがないこと
2. **差分確認**: `pulumi preview`で期待される変更のみが表示されること
3. **デプロイ成功**: `pulumi up`が正常に完了すること
4. **設定反映**: AWSリソースに正しく設定が反映されていること
5. **既存機能への影響なし**: 他の設定に意図しない変更がないこと

---

## 2. Integrationテストシナリオ

### 2.1 IT-001: TypeScriptコンパイル検証

**シナリオ名**: Pulumiコード_TypeScriptコンパイル確認

| 項目 | 内容 |
|------|------|
| **目的** | creditSpecificationプロパティ追加後、TypeScriptの型エラーが発生しないことを検証 |
| **前提条件** | `pulumi/jenkins-agent/index.ts`に`creditSpecification`プロパティが追加されている |
| **テスト手順** | 1. `pulumi/jenkins-agent`ディレクトリに移動<br>2. `npm install`で依存関係をインストール（未実施の場合）<br>3. `npx tsc --noEmit`または`npm run build`を実行 |
| **期待結果** | コンパイルが正常に完了し、エラーが0件であること |
| **確認項目** | - [ ] TypeScriptコンパイルエラーなし<br>- [ ] 型定義の警告なし |

---

### 2.2 IT-002: Pulumi Preview差分検証（x86_64用LaunchTemplate）

**シナリオ名**: agentLaunchTemplate_creditSpecification差分確認

| 項目 | 内容 |
|------|------|
| **目的** | x86_64用LaunchTemplate（`agent-lt`）に`creditSpecification`の変更が正しく検出されることを検証 |
| **前提条件** | - `agentLaunchTemplate`に`creditSpecification: { cpuCredits: "unlimited" }`が追加されている<br>- Pulumiスタックが設定済み<br>- AWS認証が設定済み |
| **テスト手順** | 1. `pulumi/jenkins-agent`ディレクトリに移動<br>2. `pulumi preview`または`npm run preview`を実行<br>3. 出力結果を確認 |
| **期待結果** | - `agent-lt` LaunchTemplateに対して`update`が表示される<br>- 差分に`creditSpecification`の追加が含まれる |
| **確認項目** | - [ ] `aws:ec2:LaunchTemplate agent-lt`が`update`として表示される<br>- [ ] 差分情報に`+creditSpecification`が含まれる<br>- [ ] `cpuCredits: "unlimited"`が設定値として表示される |

**期待される出力例**:
```
Previewing update (dev):
     Type                          Name                Plan       Info
     pulumi:pulumi:Stack          jenkins-agent-dev
 ~   └─ aws:ec2:LaunchTemplate   agent-lt            update     [diff: +creditSpecification]
```

---

### 2.3 IT-003: Pulumi Preview差分検証（ARM64用LaunchTemplate）

**シナリオ名**: agentLaunchTemplateArm_creditSpecification差分確認

| 項目 | 内容 |
|------|------|
| **目的** | ARM64用LaunchTemplate（`agent-lt-arm`）に`creditSpecification`の変更が正しく検出されることを検証 |
| **前提条件** | - `agentLaunchTemplateArm`に`creditSpecification: { cpuCredits: "unlimited" }`が追加されている<br>- Pulumiスタックが設定済み<br>- AWS認証が設定済み |
| **テスト手順** | 1. `pulumi/jenkins-agent`ディレクトリに移動<br>2. `pulumi preview`または`npm run preview`を実行<br>3. 出力結果を確認 |
| **期待結果** | - `agent-lt-arm` LaunchTemplateに対して`update`が表示される<br>- 差分に`creditSpecification`の追加が含まれる |
| **確認項目** | - [ ] `aws:ec2:LaunchTemplate agent-lt-arm`が`update`として表示される<br>- [ ] 差分情報に`+creditSpecification`が含まれる<br>- [ ] `cpuCredits: "unlimited"`が設定値として表示される |

**期待される出力例**:
```
Previewing update (dev):
     Type                          Name                Plan       Info
     pulumi:pulumi:Stack          jenkins-agent-dev
 ~   └─ aws:ec2:LaunchTemplate   agent-lt-arm        update     [diff: +creditSpecification]
```

---

### 2.4 IT-004: 予期しない変更がないことの検証

**シナリオ名**: Pulumi_予期しない変更なし確認

| 項目 | 内容 |
|------|------|
| **目的** | creditSpecification以外の設定変更が発生していないことを検証 |
| **前提条件** | `pulumi preview`が実行可能な状態 |
| **テスト手順** | 1. `pulumi preview`の出力結果を詳細に確認<br>2. 変更されるリソース数を確認<br>3. 各リソースの変更内容を確認 |
| **期待結果** | - 変更されるリソースは2つのLaunchTemplateのみ<br>- 各LaunchTemplateの変更は`creditSpecification`のみ<br>- セキュリティグループ、IAMロール、EBS設定に変更がない |
| **確認項目** | - [ ] 変更リソース数が2件（`agent-lt`と`agent-lt-arm`）のみ<br>- [ ] SpotFleet設定に変更がない<br>- [ ] セキュリティグループに変更がない<br>- [ ] IAMロール/インスタンスプロファイルに変更がない<br>- [ ] EBS設定（暗号化含む）に変更がない<br>- [ ] ネットワーク設定に変更がない<br>- [ ] メタデータオプションに変更がない |

---

### 2.5 IT-005: Pulumiデプロイ成功検証

**シナリオ名**: Pulumi_スタック更新成功確認

| 項目 | 内容 |
|------|------|
| **目的** | `pulumi up`コマンドが正常に完了し、LaunchTemplateが更新されることを検証 |
| **前提条件** | - IT-001〜IT-004が完了している<br>- preview結果に問題がない<br>- デプロイ権限がある |
| **テスト手順** | 1. `pulumi/jenkins-agent`ディレクトリに移動<br>2. `pulumi up`または`npm run update`を実行<br>3. 確認プロンプトで`yes`を入力<br>4. 完了メッセージを確認 |
| **期待結果** | - デプロイが正常に完了する<br>- LaunchTemplateの新バージョンが作成される<br>- エラーが発生しない |
| **確認項目** | - [ ] `pulumi up`が正常終了する（exit code 0）<br>- [ ] 「2 updated」のようなサマリーが表示される<br>- [ ] エラーメッセージが表示されない<br>- [ ] 警告メッセージが重大でない |

**期待される出力例**:
```
Updating (dev):
     Type                          Name                Status      Info
     pulumi:pulumi:Stack          jenkins-agent-dev
 ~   └─ aws:ec2:LaunchTemplate   agent-lt            updated     [diff: +creditSpecification]
 ~   └─ aws:ec2:LaunchTemplate   agent-lt-arm        updated     [diff: +creditSpecification]

Resources:
    ~ 2 updated
```

---

### 2.6 IT-006: AWSコンソールでのLaunchTemplate設定確認（x86_64）

**シナリオ名**: AWS_x86_64_LaunchTemplate設定確認

| 項目 | 内容 |
|------|------|
| **目的** | AWSコンソールでx86_64用LaunchTemplateに`creditSpecification`が正しく設定されていることを検証 |
| **前提条件** | IT-005（Pulumiデプロイ）が完了している |
| **テスト手順** | 1. AWSコンソールにログイン<br>2. EC2サービス → Launch Templates を開く<br>3. `jenkins-infra-agent-lt-*`（x86_64用）を選択<br>4. 最新バージョンを選択<br>5. 「Advanced details」セクションを確認 |
| **期待結果** | - 「Credit specification」に「Unlimited」が設定されている |
| **確認項目** | - [ ] LaunchTemplateの新バージョンが作成されている<br>- [ ] 「Credit specification」が「Unlimited」と表示される<br>- [ ] 他の設定（セキュリティグループ、IAMロール等）が維持されている |

---

### 2.7 IT-007: AWSコンソールでのLaunchTemplate設定確認（ARM64）

**シナリオ名**: AWS_ARM64_LaunchTemplate設定確認

| 項目 | 内容 |
|------|------|
| **目的** | AWSコンソールでARM64用LaunchTemplateに`creditSpecification`が正しく設定されていることを検証 |
| **前提条件** | IT-005（Pulumiデプロイ）が完了している |
| **テスト手順** | 1. AWSコンソールにログイン<br>2. EC2サービス → Launch Templates を開く<br>3. `jenkins-infra-agent-lt-arm-*`（ARM64用）を選択<br>4. 最新バージョンを選択<br>5. 「Advanced details」セクションを確認 |
| **期待結果** | - 「Credit specification」に「Unlimited」が設定されている |
| **確認項目** | - [ ] LaunchTemplateの新バージョンが作成されている<br>- [ ] 「Credit specification」が「Unlimited」と表示される<br>- [ ] 他の設定（セキュリティグループ、IAMロール等）が維持されている |

---

### 2.8 IT-008: SpotFleetからの新規インスタンス起動確認（オプション）

**シナリオ名**: SpotFleet_新規インスタンス_Unlimited適用確認

| 項目 | 内容 |
|------|------|
| **目的** | SpotFleetから新規に起動されるインスタンスにUnlimited設定が適用されていることを検証 |
| **前提条件** | - IT-005〜IT-007が完了している<br>- SpotFleetが稼働中<br>- 新規インスタンスが起動される状況（またはテスト用に手動起動） |
| **テスト手順** | 1. 新規インスタンスが起動されるのを待つ（または既存インスタンスを終了して置換を待つ）<br>2. AWSコンソール → EC2 → Instances を開く<br>3. 新規起動されたJenkinsエージェントインスタンスを選択<br>4. 「Details」タブで「Credit specification」を確認 |
| **期待結果** | - 新規インスタンスの「Credit specification」が「Unlimited」と表示される |
| **確認項目** | - [ ] 新規インスタンスが起動されている<br>- [ ] インスタンスの「Credit specification」が「Unlimited」<br>- [ ] インスタンスがSpotFleetの一部として正常に動作している |

---

### 2.9 IT-009: CloudWatch CPUクレジットメトリクス確認（オプション）

**シナリオ名**: CloudWatch_CPUクレジットメトリクス確認

| 項目 | 内容 |
|------|------|
| **目的** | CloudWatchでCPUクレジット関連メトリクスが正常に取得されていることを検証 |
| **前提条件** | - IT-008が完了している<br>- Unlimited設定の新規インスタンスが稼働中 |
| **テスト手順** | 1. AWSコンソール → CloudWatch → Metrics を開く<br>2. EC2 → Per-Instance Metrics を選択<br>3. 対象インスタンスのメトリクスを表示<br>4. `CPUCreditBalance`と`CPUSurplusCreditBalance`を確認 |
| **期待結果** | - `CPUCreditBalance`メトリクスが表示される<br>- `CPUSurplusCreditBalance`メトリクスが表示される（Unlimited設定の証拠） |
| **確認項目** | - [ ] `CPUCreditBalance`が取得されている<br>- [ ] `CPUSurplusCreditBalance`が取得可能（Unlimited固有のメトリクス）<br>- [ ] メトリクスの値が正常範囲内 |

---

### 2.10 IT-010: 高負荷時のスロットリング非発生確認（オプション）

**シナリオ名**: 高負荷ジョブ_スロットリング非発生確認

| 項目 | 内容 |
|------|------|
| **目的** | 高負荷なJenkinsジョブ実行時にCPUスロットリングが発生しないことを検証 |
| **前提条件** | - IT-008が完了している<br>- Unlimited設定の新規インスタンスが稼働中<br>- テスト用の高負荷ジョブが用意されている |
| **テスト手順** | 1. Jenkinsで高負荷なビルド/テストジョブを実行<br>2. ジョブ実行中にCloudWatchでCPU使用率を監視<br>3. `CPUCreditBalance`の推移を確認<br>4. ジョブの完了時間を記録 |
| **期待結果** | - CPUクレジットが枯渇してもCPU使用率が維持される<br>- ジョブがタイムアウトなく完了する<br>- `CPUSurplusCreditBalance`が増加する（クレジット超過使用の証拠） |
| **確認項目** | - [ ] ジョブが正常に完了する<br>- [ ] CPU使用率がベースライン以上を維持<br>- [ ] タイムアウトが発生しない<br>- [ ] ジョブ実行時間が大幅に延長されない |

---

## 3. テスト実行順序

```
[必須テスト - Phase 6で実行]

IT-001: TypeScriptコンパイル検証
    ↓
IT-002: Pulumi Preview差分検証（x86_64）
IT-003: Pulumi Preview差分検証（ARM64）
IT-004: 予期しない変更がないことの検証
    ↓ (すべて並行実行可能)
IT-005: Pulumiデプロイ成功検証
    ↓
IT-006: AWSコンソール設定確認（x86_64）
IT-007: AWSコンソール設定確認（ARM64）
    ↓ (並行実行可能)

[オプションテスト - 時間と環境が許す場合]

IT-008: SpotFleet新規インスタンス確認
    ↓
IT-009: CloudWatchメトリクス確認
IT-010: 高負荷時スロットリング非発生確認
```

---

## 4. テストデータ

### 4.1 期待される設定値

| 項目 | 値 |
|------|-----|
| creditSpecification.cpuCredits | `"unlimited"` |
| 対象LaunchTemplate（x86_64） | `agent-lt` |
| 対象LaunchTemplate（ARM64） | `agent-lt-arm` |

### 4.2 対象インスタンスタイプ

| アーキテクチャ | インスタンスタイプ |
|----------------|-------------------|
| x86_64 | t3a.medium, t3.medium, t3a.small, t3.small, t3a.micro, t3.micro |
| ARM64 | t4g.medium, t4g.small, t4g.micro |

### 4.3 変更されてはいけない設定（回帰確認用）

| 設定項目 | 維持されるべき値 |
|----------|------------------|
| EBS暗号化 | `encrypted: "true"` |
| メタデータオプション | `httpTokens: "required"`（IMDSv2必須） |
| ネットワーク | `associatePublicIpAddress: "false"` |
| IPv6 | `ipv6AddressCount: 1` |

---

## 5. テスト環境要件

### 5.1 必須環境

| 項目 | 要件 |
|------|------|
| Node.js | v18以上（Pulumiプロジェクトの要件に準拠） |
| npm | v9以上 |
| Pulumi CLI | v3.x |
| AWS CLI | v2.x、認証設定済み |
| AWS認証 | 適切なIAM権限（EC2 LaunchTemplate更新権限） |

### 5.2 AWS権限要件

| サービス | 必要な権限 |
|----------|-----------|
| EC2 | `ec2:DescribeLaunchTemplates`, `ec2:ModifyLaunchTemplate`, `ec2:CreateLaunchTemplateVersion` |
| IAM | `iam:PassRole`（既存のインスタンスプロファイル用） |
| CloudWatch | `cloudwatch:GetMetricData`（オプションテスト用） |

### 5.3 Pulumiスタック設定

| 項目 | 要件 |
|------|------|
| スタック名 | `jenkins-agent-dev`（または適切な環境） |
| バックエンド | S3バックエンド設定済み |
| 状態 | 最新のスタック状態が同期されている |

---

## 6. テスト結果記録テンプレート

### 6.1 必須テスト結果

| テストID | テスト名 | 結果 | 実行日時 | 実行者 | 備考 |
|----------|----------|------|----------|--------|------|
| IT-001 | TypeScriptコンパイル検証 | □ Pass / □ Fail | | | |
| IT-002 | Pulumi Preview（x86_64） | □ Pass / □ Fail | | | |
| IT-003 | Pulumi Preview（ARM64） | □ Pass / □ Fail | | | |
| IT-004 | 予期しない変更なし確認 | □ Pass / □ Fail | | | |
| IT-005 | Pulumiデプロイ成功 | □ Pass / □ Fail | | | |
| IT-006 | AWS設定確認（x86_64） | □ Pass / □ Fail | | | |
| IT-007 | AWS設定確認（ARM64） | □ Pass / □ Fail | | | |

### 6.2 オプションテスト結果

| テストID | テスト名 | 結果 | 実行日時 | 実行者 | 備考 |
|----------|----------|------|----------|--------|------|
| IT-008 | 新規インスタンス確認 | □ Pass / □ Fail / □ Skip | | | |
| IT-009 | CloudWatchメトリクス確認 | □ Pass / □ Fail / □ Skip | | | |
| IT-010 | スロットリング非発生確認 | □ Pass / □ Fail / □ Skip | | | |

---

## 7. 受け入れ基準との対応

| 受け入れ基準 | 対応するテストシナリオ |
|--------------|----------------------|
| AC-001: x86_64用LaunchTemplateの設定確認 | IT-002, IT-006 |
| AC-002: ARM64用LaunchTemplateの設定確認 | IT-003, IT-007 |
| AC-003: Pulumiデプロイの成功確認 | IT-005 |
| AC-004: AWSコンソールでの設定確認 | IT-006, IT-007 |
| AC-005: SpotFleetインスタンスへの適用確認 | IT-008 |
| AC-006: ドキュメント更新確認 | Phase 7で検証 |
| AC-007: 既存機能への影響なし確認 | IT-004 |

---

## 8. 機能要件との対応

| 機能要件 | 対応するテストシナリオ |
|----------|----------------------|
| FR-001: x86_64用LaunchTemplateへの設定追加 | IT-001, IT-002, IT-006 |
| FR-002: ARM64用LaunchTemplateへの設定追加 | IT-001, IT-003, IT-007 |
| FR-003: Pulumiスタック更新によるLaunchTemplate反映 | IT-005, IT-008 |
| FR-004: ドキュメント更新 | Phase 7で検証 |

---

## 9. 非機能要件との対応

| 非機能要件 | 対応するテストシナリオ |
|------------|----------------------|
| NFR-P01: CPU性能維持 | IT-010 |
| NFR-S01: 既存設定の維持 | IT-004 |
| NFR-S02: 暗号化設定の維持 | IT-004 |
| NFR-A01: ローリング更新 | IT-008 |
| NFR-A02: ロールバック可能性 | 検証不要（Pulumi標準機能） |
| NFR-M01: コードスタイル | IT-001 |

---

## 10. 品質ゲート確認

| 品質ゲート項目 | 状態 | 説明 |
|----------------|------|------|
| Phase 2の戦略に沿ったテストシナリオである | ✅ | INTEGRATION_ONLY戦略に基づき、手動検証シナリオを作成 |
| 主要な正常系がカバーされている | ✅ | IT-001〜IT-007で正常系を網羅 |
| 主要な異常系がカバーされている | ✅ | IT-004で予期しない変更の検出をカバー |
| 期待結果が明確である | ✅ | 各シナリオに具体的な期待結果と確認項目を記載 |

---

## 11. 変更履歴

| バージョン | 日付 | 変更者 | 変更内容 |
|------------|------|--------|----------|
| 1.0 | 2025-01-20 | AI Workflow | 初版作成 |
