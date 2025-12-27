# 詳細設計書: Issue #542

## SpotFleetエージェントのCPUクレジットUnlimited設定適用

---

## 1. アーキテクチャ設計

### 1.1 システム全体図

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Jenkins Agent Infrastructure                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                    Launch Templates                              │  │
│  │  ┌─────────────────────┐    ┌─────────────────────────────┐    │  │
│  │  │  agentLaunchTemplate │    │  agentLaunchTemplateArm     │    │  │
│  │  │  (x86_64)            │    │  (ARM64)                    │    │  │
│  │  │                      │    │                             │    │  │
│  │  │  + creditSpecification│   │  + creditSpecification     │    │  │
│  │  │    cpuCredits:       │    │    cpuCredits:             │    │  │
│  │  │    "unlimited"       │    │    "unlimited"             │    │  │
│  │  │                      │    │                             │    │  │
│  │  │  Instance Types:     │    │  Instance Types:           │    │  │
│  │  │  - t3a.medium/small/ │    │  - t4g.medium/small/       │    │  │
│  │  │    micro             │    │    micro                   │    │  │
│  │  │  - t3.medium/small/  │    │                             │    │  │
│  │  │    micro             │    │                             │    │  │
│  │  └──────────┬──────────┘    └───────────┬─────────────────┘    │  │
│  └─────────────┼───────────────────────────┼────────────────────────┘  │
│                │                           │                           │
│                ▼                           ▼                           │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                     Spot Fleet Requests                         │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │  │
│  │  │ spotFleet    │  │ spotFleet    │  │ spotFleet    │         │  │
│  │  │ (medium)     │  │ (small)      │  │ (micro)      │         │  │
│  │  │              │  │              │  │              │         │  │
│  │  │ latestVersion│  │ latestVersion│  │ latestVersion│         │  │
│  │  │ 参照         │  │ 参照         │  │ 参照         │         │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘         │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 コンポーネント間の関係

```
┌─────────────────────────────────────────────────────────────────┐
│                    Pulumi Stack: jenkins-agent                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  pulumi/jenkins-agent/index.ts                                   │
│  ├── agentLaunchTemplate (293行目)                               │
│  │   └── [追加] creditSpecification: { cpuCredits: "unlimited" }│
│  │                                                               │
│  └── agentLaunchTemplateArm (393行目)                           │
│      └── [追加] creditSpecification: { cpuCredits: "unlimited" }│
│                                                                   │
│  ※ SpotFleetはlatestVersionを参照するため、                     │
│    LaunchTemplate更新で自動的に新設定が適用される                │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 データフロー

```
┌──────────────────┐
│  pulumi up       │
│  コマンド実行     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ LaunchTemplate   │
│ 新バージョン作成 │
│ (creditSpec追加) │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ SpotFleet        │
│ latestVersion    │
│ 参照更新         │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐        ┌──────────────────┐
│ 既存インスタンス │        │ 新規インスタンス │
│ (旧設定のまま)   │        │ (Unlimited適用)  │
│ ↓終了時に置換    │ ───→   │ ローリング更新   │
└──────────────────┘        └──────────────────┘
```

---

## 2. 実装戦略判断

### 実装戦略: EXTEND

**判断根拠**:
- 既存の`pulumi/jenkins-agent/index.ts`ファイル内の2つのLaunchTemplate定義に新しいプロパティを追加するのみ
- 新規ファイルやクラスの作成は不要
- 既存コードの構造変更（リファクタリング）も不要
- 純粋な機能拡張（既存リソース定義へのプロパティ追加）に該当

---

## 3. テスト戦略判断

### テスト戦略: INTEGRATION_ONLY

**判断根拠**:
- Pulumiインフラコードであり、従来のユニットテストの対象ではない
- `pulumi preview`による差分確認が主要な検証手段
- 実際のAWSリソースへの反映後、AWSコンソールまたはCloudWatchでCPUクレジット設定を確認する必要がある
- BDDテストは不要（インフラ設定変更であり、ユーザーストーリー中心のテストではない）
- このリポジトリにはPulumiスタック用の自動テストフレームワークが存在しない

---

## 4. テストコード戦略判断

### テストコード戦略: 該当なし（手動検証）

**判断根拠**:
- `pulumi/jenkins-agent/`ディレクトリには専用のテストファイルが存在しない
- 検証は以下の手動確認で実施:
  1. `pulumi preview`コマンドによる差分確認
  2. `pulumi up`実行後のAWSコンソールでのLaunchTemplate設定確認
  3. （オプション）CloudWatchでCPUSurplusCreditBalanceメトリクス確認
- 既存プロジェクトのテストパターンに準拠（インフラコードは手動検証）

---

## 5. 影響範囲分析

### 5.1 既存コードへの影響

| ファイル | 変更内容 | 影響度 |
|----------|----------|--------|
| `pulumi/jenkins-agent/index.ts` | 2つのLaunchTemplateに`creditSpecification`プロパティを追加 | **低** |
| `docs/architecture/infrastructure.md` | CPUクレジットUnlimited設定の説明とコスト注意事項を追記 | **低** |

### 5.2 依存関係の変更

- **新規依存の追加**: なし
- **既存依存の変更**: なし
- **npm パッケージ変更**: なし
- **SSMパラメータ変更**: なし

### 5.3 マイグレーション要否

- **データベーススキーマ変更**: なし
- **設定ファイル変更**: なし
- **既存インスタンスへの影響**:
  - 既存インスタンスは終了まで旧設定で動作
  - SpotFleetのローリング更新により段階的に新設定が適用される
  - 即時反映が必要な場合は手動でインスタンスを入れ替え可能

### 5.4 インフラ更新の動作

```
[更新プロセス]
1. Pulumi up実行
   └→ LaunchTemplateの新バージョンが作成される

2. SpotFleet設定
   └→ latestVersionを参照しているため自動的に新バージョンを認識

3. 新規インスタンス起動時
   └→ 新しいLaunchTemplateバージョンが使用される
   └→ creditSpecification: unlimited が適用される

4. 既存インスタンス
   └→ 終了するまで旧設定で動作
   └→ Spot中断やスケールイン時に置き換わる
```

---

## 6. 変更・追加ファイルリスト

### 6.1 修正が必要な既存ファイル

| ファイル（相対パス） | 変更内容 |
|---------------------|----------|
| `pulumi/jenkins-agent/index.ts` | `agentLaunchTemplate`と`agentLaunchTemplateArm`に`creditSpecification`プロパティを追加 |
| `docs/architecture/infrastructure.md` | CPUクレジットUnlimited設定の説明セクションを追加 |

### 6.2 新規作成ファイル

なし

### 6.3 削除が必要なファイル

なし

---

## 7. 詳細設計

### 7.1 LaunchTemplate変更設計

#### 7.1.1 x86_64用LaunchTemplate (agentLaunchTemplate)

**変更箇所**: `pulumi/jenkins-agent/index.ts` 293行目付近

```typescript
// 現在の定義（簡略化）
const agentLaunchTemplate = new aws.ec2.LaunchTemplate(`agent-lt`, {
    namePrefix: `jenkins-infra-agent-lt-`,
    imageId: amiX86Id,
    instanceType: "t3a.medium",
    keyName: agentKeyPair.keyName,
    ebsOptimized: "true",
    iamInstanceProfile: {
        name: jenkinsAgentProfile.name,
    },
    blockDeviceMappings: [{
        deviceName: "/dev/xvda",
        ebs: {
            volumeSize: 30,
            volumeType: "gp3",
            deleteOnTermination: "true",
            encrypted: "true",
        },
    }],
    metadataOptions: {
        httpEndpoint: "enabled",
        httpTokens: "required",
        httpPutResponseHopLimit: 2,
    },
    networkInterfaces: [{
        associatePublicIpAddress: "false",
        deleteOnTermination: "true",
        deviceIndex: 0,
        ipv6AddressCount: 1,
        securityGroups: [jenkinsAgentSecurityGroupId],
    }],
    // ↓ 追加するプロパティ
    creditSpecification: {
        cpuCredits: "unlimited",
    },
    tagSpecifications: [{
        resourceType: "instance",
        tags: {
            Name: `jenkins-infra-agent-${environment}`,
            Environment: environment,
            Role: "jenkins-agent",
            IPv6Enabled: "true",
        },
    }],
    userData: /* 既存のuserData設定 */,
    tags: {
        Name: `jenkins-infra-agent-lt-${environment}`,
        Environment: environment,
    },
});
```

**追加するプロパティ**:
```typescript
creditSpecification: {
    cpuCredits: "unlimited",
},
```

**挿入位置**: `networkInterfaces`プロパティの後、`tagSpecifications`の前

#### 7.1.2 ARM64用LaunchTemplate (agentLaunchTemplateArm)

**変更箇所**: `pulumi/jenkins-agent/index.ts` 393行目付近

```typescript
// 現在の定義（簡略化）
const agentLaunchTemplateArm = new aws.ec2.LaunchTemplate(`agent-lt-arm`, {
    namePrefix: `jenkins-infra-agent-lt-arm-`,
    imageId: amiArmId,
    instanceType: "t4g.medium",
    keyName: agentKeyPair.keyName,
    ebsOptimized: "true",
    iamInstanceProfile: {
        name: jenkinsAgentProfile.name,
    },
    blockDeviceMappings: [{
        deviceName: "/dev/xvda",
        ebs: {
            volumeSize: 30,
            volumeType: "gp3",
            deleteOnTermination: "true",
            encrypted: "true",
        },
    }],
    metadataOptions: {
        httpEndpoint: "enabled",
        httpTokens: "required",
        httpPutResponseHopLimit: 2,
    },
    networkInterfaces: [{
        associatePublicIpAddress: "false",
        deleteOnTermination: "true",
        deviceIndex: 0,
        ipv6AddressCount: 1,
        securityGroups: [jenkinsAgentSecurityGroupId],
    }],
    // ↓ 追加するプロパティ
    creditSpecification: {
        cpuCredits: "unlimited",
    },
    tagSpecifications: [{
        resourceType: "instance",
        tags: {
            Name: `jenkins-infra-agent-${environment}`,
            Environment: environment,
            Role: "jenkins-agent",
            Architecture: "arm64",
            IPv6Enabled: "true",
        },
    }],
    userData: /* 既存のuserData設定 */,
    tags: {
        Name: `jenkins-infra-agent-lt-arm-${environment}`,
        Environment: environment,
    },
});
```

**追加するプロパティ**:
```typescript
creditSpecification: {
    cpuCredits: "unlimited",
},
```

**挿入位置**: `networkInterfaces`プロパティの後、`tagSpecifications`の前

### 7.2 ドキュメント更新設計

#### 7.2.1 追加セクション内容

**変更箇所**: `docs/architecture/infrastructure.md`

**追加位置**: 「Jenkinsエージェント構成」セクション内、または「SpotFleet vs ECS Fargate 比較」の後

```markdown
## CPUクレジット設定

### Unlimited モードの適用

SpotFleetエージェントのt3/t3a/t4g系インスタンスには、CPUクレジットのUnlimitedモードが適用されています。

#### 設定内容

| 設定項目 | 値 |
|---------|-----|
| creditSpecification.cpuCredits | "unlimited" |
| 対象LaunchTemplate | agent-lt (x86_64), agent-lt-arm (ARM64) |
| 対象インスタンスタイプ | t3a.medium/small/micro, t3.medium/small/micro, t4g.medium/small/micro |

#### CPUクレジットモードの比較

| モード | 動作 | コスト |
|--------|------|--------|
| standard（デフォルト） | クレジット枯渇時にベースラインCPUに制限（スロットリング） | 追加コストなし |
| unlimited | クレジット枯渇後も高いCPU使用率を維持可能 | 超過分は追加課金 |

#### 適用理由

- CI/CDパイプラインで継続的なビルドやテスト実行時に、CPUクレジット枯渇によるスロットリングを防止
- ジョブ完了時間の大幅延長、タイムアウト、リトライ増加を回避
- 開発者の待ち時間短縮とCI信頼性向上

#### コスト影響

Unlimitedモードでは、CPUクレジットが枯渇した後も高いCPU使用率を維持できますが、**ベースラインを超えた使用分は追加課金**されます。

- **課金単位**: vCPU時間あたりのCPUクレジット超過分
- **監視方法**: CloudWatchの`CPUSurplusCreditBalance`メトリクスで超過クレジットを確認可能
- **コスト管理**: CloudWatch Billingアラートで監視を推奨

#### 更新の適用

LaunchTemplateの更新はローリング方式で適用されます：
1. Pulumiスタック更新でLaunchTemplateの新バージョンが作成される
2. SpotFleetは`latestVersion`を参照しているため、新規インスタンスから自動的に新設定が適用される
3. 既存インスタンスは終了時に新設定のインスタンスに置き換わる
```

### 7.3 Pulumi AWS LaunchTemplate creditSpecification構文

**Pulumi AWS Provider v6.0+での構文**:

```typescript
const launchTemplate = new aws.ec2.LaunchTemplate("example", {
    // 他のプロパティ...
    creditSpecification: {
        cpuCredits: "unlimited", // または "standard"
    },
});
```

**型定義** (`@pulumi/aws`):

```typescript
interface LaunchTemplateCreditSpecification {
    cpuCredits?: pulumi.Input<string>;  // "standard" | "unlimited"
}
```

---

## 8. セキュリティ考慮事項

### 8.1 認証・認可

- **変更なし**: 今回の変更はCPUクレジット設定のみであり、IAMロール、セキュリティグループ、認証設定への影響なし

### 8.2 データ保護

- **変更なし**: EBS暗号化設定（`encrypted: "true"`）は維持される
- **変更なし**: メタデータオプション（IMDSv2必須）は維持される

### 8.3 セキュリティリスクと対策

| リスク | 対策 |
|--------|------|
| 追加コストによる予算超過 | CloudWatch Billingアラートで監視、ドキュメントに注意事項記載 |
| 設定変更による意図しない影響 | `pulumi preview`で事前確認、既存設定に影響がないことを検証 |

---

## 9. 非機能要件への対応

### 9.1 パフォーマンス

| 要件 | 対応 |
|------|------|
| CPU性能維持（NFR-P01） | Unlimitedモードにより、クレジット枯渇時もベースラインを超える性能を維持 |
| ジョブ実行時間安定化（NFR-P02） | スロットリング回避により、高負荷時のジョブ実行時間の大幅増加を防止 |

### 9.2 スケーラビリティ

- **影響なし**: SpotFleetのスケーリング設定には変更なし
- **改善**: CPUスロットリングがなくなることで、各インスタンスの処理能力が安定し、効率的なジョブ実行が可能

### 9.3 保守性

| 要件 | 対応 |
|------|------|
| コードスタイル準拠（NFR-M01） | 既存のPulumiコードスタイルに準拠したプロパティ追加 |
| ドキュメント整合性（NFR-M02） | `docs/architecture/infrastructure.md`に設定内容とコスト影響を追記 |
| 将来の拡張性（NFR-M03） | SSMパラメータによる動的切り替えは将来の拡張候補として検討可能 |

---

## 10. 実装の順序

### 推奨実装順序

```
Step 1: pulumi/jenkins-agent/index.ts の修正
├── 1.1 agentLaunchTemplate に creditSpecification を追加
└── 1.2 agentLaunchTemplateArm に creditSpecification を追加

Step 2: TypeScriptコンパイル確認
└── 2.1 型エラーがないことを確認

Step 3: Pulumi preview による差分確認
└── 3.1 期待される変更のみが表示されることを確認

Step 4: Pulumi up によるデプロイ
└── 4.1 スタック更新の実行

Step 5: AWSコンソールでの設定確認
└── 5.1 LaunchTemplateの新バージョンにcreditSpecificationが含まれることを確認

Step 6: ドキュメント更新
└── 6.1 docs/architecture/infrastructure.md に説明を追加
```

### 依存関係の考慮

```
┌────────────────────────────────────────────────────────────────┐
│ 依存関係なし: 全タスクは順次実行                                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ Step 1 (コード修正) → Step 2 (コンパイル確認)                  │
│                              ↓                                 │
│                       Step 3 (preview)                         │
│                              ↓                                 │
│                       Step 4 (deploy)                          │
│                              ↓                                 │
│                       Step 5 (確認)                            │
│                              ↓                                 │
│                       Step 6 (ドキュメント)                    │
│                                                                │
│ ※ Step 1-5が完了してからStep 6を実施することを推奨             │
│   (実装内容が確定してからドキュメントを更新するため)             │
└────────────────────────────────────────────────────────────────┘
```

---

## 11. 検証計画

### 11.1 Pulumi Preview検証

**目的**: 期待される差分のみが表示されることを確認

**手順**:
```bash
cd pulumi/jenkins-agent
npm run preview
```

**期待される出力**:
```
Previewing update (dev):
     Type                          Name                     Plan       Info
     pulumi:pulumi:Stack          jenkins-agent-dev
 ~   └─ aws:ec2:LaunchTemplate   agent-lt                 update     [diff: +creditSpecification]
 ~   └─ aws:ec2:LaunchTemplate   agent-lt-arm             update     [diff: +creditSpecification]

Resources:
    ~ 2 to update
```

### 11.2 AWSコンソール確認

**目的**: LaunchTemplateにcreditSpecificationが正しく設定されていることを確認

**手順**:
1. AWSコンソール → EC2 → Launch Templates を開く
2. `jenkins-infra-agent-lt-*` を選択
3. 最新バージョンの詳細を確認
4. 「Advanced details」セクションで `Credit specification: Unlimited` を確認

### 11.3 CloudWatch確認（オプション）

**目的**: CPUクレジットメトリクスの動作確認

**監視メトリクス**:
- `CPUCreditBalance`: 現在のクレジット残高
- `CPUSurplusCreditBalance`: Unlimitedモードで使用した超過クレジット

---

## 12. 品質ゲート確認

| 品質ゲート項目 | 状態 | 説明 |
|----------------|------|------|
| 実装戦略の判断根拠が明記されている | ✅ | EXTEND戦略、既存リソースへのプロパティ追加 |
| テスト戦略の判断根拠が明記されている | ✅ | INTEGRATION_ONLY、Pulumiインフラコードのため手動検証 |
| 既存コードへの影響範囲が分析されている | ✅ | 2ファイルのみ、影響度は低 |
| 変更が必要なファイルがリストアップされている | ✅ | セクション6に詳細を記載 |
| 設計が実装可能である | ✅ | 具体的なコード変更箇所と構文を明示 |

---

## 13. 参考資料

### AWS公式ドキュメント
- [Unlimited Mode for Burstable Performance Instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-credits-baseline-concepts.html)
- [CPU Credits and Baseline Utilization](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances.html)

### Pulumi公式ドキュメント
- [aws.ec2.LaunchTemplate](https://www.pulumi.com/registry/packages/aws/api-docs/ec2/launchtemplate/)
- [creditSpecification property](https://www.pulumi.com/registry/packages/aws/api-docs/ec2/launchtemplate/#creditspecification)

### プロジェクト内ドキュメント
- [CLAUDE.md](../../CLAUDE.md) - プロジェクトガイダンス
- [pulumi/CONTRIBUTION.md](../../pulumi/CONTRIBUTION.md) - Pulumi開発規約
- [docs/architecture/infrastructure.md](../../docs/architecture/infrastructure.md) - インフラ構成説明

---

## 14. 変更履歴

| バージョン | 日付 | 変更者 | 変更内容 |
|------------|------|--------|----------|
| 1.0 | 2025-01-20 | AI Workflow | 初版作成 |
