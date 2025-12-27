# Codex Agent 実行ログ

開始日時: 2025/12/27 15:10:01

---

## Turn 1: スレッド開始

**Thread ID**: `[REDACTED_TOKEN]`

## Turn 2: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 3: ツール実行

**種別**: コマンド実行
**コマンド**: `/bin/bash -lc ls`
**ステータス**: completed (exit_code=0)

```text
ARCHITECTURE.md
CLAUDE.md
CONTRIBUTION.md
LICENSE
README.md
ansible
bootstrap
docker
docs
jenkins
pulumi
run_tests_issue_322.sh
scripts
tests
```

## Turn 4: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 5: ツール実行

**種別**: コマンド実行
**コマンド**: `/bin/bash -lc 'cat .ai-workflow/issue-542/00_planning/output/planning.md'`
**ステータス**: completed (exit_code=0)

```text
# プロジェクト計画書: Issue #542

## SpotFleetエージェントのCPUクレジットUnlimited設定適用

---

## 1. Issue分析

### 概要
SpotFleetエージェントのt3/t4g系LaunchTemplateに`creditSpecification.cpuCredits="unlimited"`設定を追加し、CI負荷時のCPUスロットリングを防止する。

### 複雑度: **簡単**

**判断根拠**:
- 変更対象は単一ファイル（`pulumi/jenkins-agent/index.ts`）のみ
- 2つのLaunchTemplate定義（x86_64用とARM64用）に`creditSpecification`プロパティを追加するだけ
- 既存のPulumiスタック構造への影響が限定的
- AWSの標準的なEC2設定オプションの追加であり、技術的な不確実性が低い

### 見積もり工数: **2~3時間**

| フェーズ | 見積もり時間 |
|---------|-------------|
| Phase 1: 要件定義 | 0.25h |
| Phase 2: 設計 | 0.25h |
| Phase 3: テストシナリオ | 0.25h |
| Phase 4: 実装 | 0.5h |
| Phase 5: テストコード実装 | 0h (手動検証) |
| Phase 6: テスト実行 | 0.5h |
| Phase 7: ドキュメント | 0.5h |
| Phase 8: レポート | 0.25h |
| **合計** | **2.5h** |

### リスク評価: **低**

- 既存のインフラへの影響は限定的
- ロールバックが容易（Pulumiの変更を元に戻すだけ）
- Unlimited設定は追加コストが発生するが、CI性能向上のトレードオフとして許容済み

---

## 2. 実装戦略判断

### 実装戦略: **EXTEND**

**判断根拠**:
- 既存の`pulumi/jenkins-agent/index.ts`の2つのLaunchTemplate定義に新しいプロパティを追加する
- 新規ファイルやクラスの作成は不要
- 既存コードの構造変更（リファクタリング）も不要
- 純粋な機能拡張（既存リソース定義へのプロパティ追加）

### テスト戦略: **INTEGRATION_ONLY**

**判断根拠**:
- Pulumiインフラコードであり、ユニットテストの対象ではない
- `pulumi preview`による差分確認が主要な検証手段
- 実際のAWSリソースへの反映後、CloudWatchでCPUクレジット動作を確認
- BDDテストは不要（インフラ設定変更であり、ユーザーストーリー中心ではない）

### テストコード戦略: **該当なし（手動検証）**

**判断根拠**:
- Pulumiインフラコードには専用のテストファイルが存在しない
- 検証は`pulumi preview`コマンドと実環境でのCloudWatch確認で実施
- 自動テストコードの作成は不要

---

## 3. 影響範囲分析

### 既存コードへの影響

| ファイル | 変更内容 | 影響度 |
|----------|----------|--------|
| `pulumi/jenkins-agent/index.ts` | 2つのLaunchTemplateに`creditSpecification`追加 | 低 |

### 変更対象の詳細

#### agentLaunchTemplate（x86_64用、293行目付近）
```typescript
const agentLaunchTemplate = new aws.ec2.LaunchTemplate(`agent-lt`, {
    // 既存のプロパティ...
    creditSpecification: {
        cpuCredits: "unlimited",
    },
    // ...
});
```

#### [REDACTED_TOKEN]（ARM64用、393行目付近）
```typescript
const [REDACTED_TOKEN] = new aws.ec2.LaunchTemplate(`agent-lt-arm`, {
    // 既存のプロパティ...
    creditSpecification: {
        cpuCredits: "unlimited",
    },
    // ...
});
```

### 依存関係の変更
- **新規依存の追加**: なし
- **既存依存の変更**: なし
- **npm パッケージ変更**: なし

### マイグレーション要否
- **データベーススキーマ変更**: なし
- **設定ファイル変更**: なし
- **SSMパラメータ変更**: なし

### インフラ更新の影響

SpotFleetは以下の動作で更新される:
1. Pulumiがスタックを更新すると、LaunchTemplateの新しいバージョンが作成される
2. SpotFleetは`latestVersion`を参照しているため、新しいインスタンスから自動的に新設定が適用される
3. 既存インスタンスは終了時に新設定のインスタンスに置き換わる（ローリング更新）

---

## 4. タスク分割

### Phase 1: 要件定義 (見積もり: 0.25h)

- [x] Task 1-1: 対象インスタンスタイプの確認 (0.15h)
  - t3/t3a系（x86_64）の確認: t3a.medium, t3.medium, t3a.small, t3.small, t3a.micro, t3.micro
  - t4g系（ARM64）の確認: t4g.medium, t4g.small, t4g.micro
  - すべてがT系バースタブルインスタンスであることを確認
- [x] Task 1-2: 受け入れ基準の明確化 (0.1h)
  - `creditSpecification.cpuCredits="unlimited"`が両LaunchTemplateに設定されていること
  - `pulumi preview`で差分が期待通りであること
  - 高負荷ジョブ実行時にスロットリングが発生しないこと

### Phase 2: 設計 (見積もり: 0.25h)

- [x] Task 2-1: 変更箇所の特定と設計 (0.15h)
  - `agentLaunchTemplate`（293行目付近）への追加位置決定
  - `[REDACTED_TOKEN]`（393行目付近）への追加位置決定
  - プロパティ追加の構文確認（Pulumi AWS provider）
- [x] Task 2-2: コスト影響の確認 (0.1h)
  - Unlimited設定によるCPUクレジット追加料金の理解
  - ドキュメントへの注意事項記載内容の検討

### Phase 3: テストシナリオ (見積もり: 0.25h)

- [x] Task 3-1: Pulumi preview検証シナリオ作成 (0.15h)
  - 期待される差分内容の定義
  - 差分確認手順の文書化
- [x] Task 3-2: 動作確認シナリオ作成 (0.1h)
  - CloudWatch CPUCreditBalanceメトリクス監視手順
  - 高負荷ジョブの実行手順

### Phase 4: 実装 (見積もり: 0.5h)

- [ ] Task 4-1: x86_64用LaunchTemplateの修正 (0.2h)
  - `agentLaunchTemplate`に`creditSpecification`プロパティを追加
  - `cpuCredits: "unlimited"`を設定
- [ ] Task 4-2: ARM64用LaunchTemplateの修正 (0.2h)
  - `[REDACTED_TOKEN]`に`creditSpecification`プロパティを追加
  - `cpuCredits: "unlimited"`を設定
- [ ] Task 4-3: コード品質確認 (0.1h)
  - TypeScriptの型エラーがないことを確認
  - 既存のコードスタイルとの整合性確認

### Phase 5: テストコード実装 (見積もり: 0h)

- [ ] Task 5-1: 該当なし
  - Pulumiインフラコードのため、専用テストコードは作成しない
  - 検証はPhase 6の手動テストで実施

### Phase 6: テスト実行 (見積もり: 0.5h)

- [ ] Task 6-1: Pulumi previewによる差分確認 (0.2h)
  - `pulumi preview`コマンドの実行
  - LaunchTemplateの`creditSpecification`変更が表示されることを確認
  - 予期しない変更がないことを確認
- [ ] Task 6-2
... (truncated)
```

## Turn 6: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 7: ツール実行

**種別**: コマンド実行
**コマンド**: `/bin/bash -lc 'cat .ai-workflow/issue-542/02_design/output/design.md'`
**ステータス**: completed (exit_code=0)

```text
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
│  │  │  agentLaunchTemplate │    │  [REDACTED_TOKEN]     │    │  │
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
│  └── [REDACTED_TOKEN] (393行目)                           │
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
│ 参照
... (truncated)
```

## Turn 8: ツール実行

**種別**: コマンド実行
**コマンド**: `/bin/bash -lc 'cat .ai-workflow/issue-542/03_test_scenario/output/test-scenario.md'`
**ステータス**: completed (exit_code=0)

```text
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
| `pulumi/jenkins-agent/index.ts` | `agentLaunchTemplate`と`[REDACTED_TOKEN]`への`creditSpecification`プロパティ追加 |
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

**シナリオ名**: [REDACTED_TOKEN]差分確認

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

**シナリオ名**: [REDACTED_TOKEN]差分確認

| 項目 | 内容 |
|------|------|
| **目的** | ARM64用LaunchTemplate（`agent-lt-arm`）に`creditSpecification`の変更が正しく検出されることを検証 |
| **前提条件** | - `[REDACTED_TOKEN]`に`creditSpecification: { cpuCredits: "unlimited" }`が追加されている<br>- Pulumiスタックが設定済み<br>- AWS認証が設定済み |
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
| **確認項目** | - [ ] 変更リソース数が2件（`agent-lt`と`agent-lt-arm`）のみ<br>- [ ] SpotFleet設定に変更がない<br>- [ ] セキュリティグループに変更がない<br>- [ ] IAMロール/インスタンスプロファイルに変更がない<br>- [ ] EBS設定（暗号化含む）に変更がない<br>- [ ] ネットワーク設定に変更がない<br>- [ ]
... (truncated)
```

## Turn 9: ツール実行

**種別**: コマンド実行
**コマンド**: `/bin/bash -lc 'cat .ai-workflow/issue-542/01_requirements/output/requirements.md'`
**ステータス**: completed (exit_code=0)

```text
# 要件定義書: Issue #542

## SpotFleetエージェントのCPUクレジットUnlimited設定適用

---

## 0. Planning Document確認サマリー

### 開発計画の概要
- **複雑度**: 簡単（単一ファイルへの限定的な変更）
- **見積もり工数**: 2.5時間
- **リスク評価**: 低（ロールバックが容易）
- **実装戦略**: EXTEND（既存コードへのプロパティ追加）
- **テスト戦略**: INTEGRATION_ONLY（`pulumi preview`と手動検証）

### 策定済みの方針
- 変更対象は`pulumi/jenkins-agent/index.ts`の2つのLaunchTemplate定義のみ
- 自動テストコードは不要（Pulumiインフラコードのため）
- SpotFleetはローリング更新で新設定を適用

---

## 1. 概要

### 1.1 背景
現在、JenkinsエージェントのSpotFleetで使用しているt3/t3a/t4g系インスタンスは、デフォルトの`standard`モードでCPUクレジットを運用している。CI/CDパイプラインで継続的なビルドやテストを実行する際、CPUクレジットが枯渇し、ベースラインCPU性能（t3系で5-20%程度）まで性能が急激に低下する「スロットリング」が発生している。

### 1.2 問題点
- **ジョブ完了時間の大幅延長**: CPUクレジット枯渇時にビルド/テスト時間が数倍に増加
- **ジョブの失敗・タイムアウト**: 性能低下によるタイムアウト発生でCI信頼性が低下
- **リトライ増加**: 失敗したジョブの再実行によるリソース浪費
- **開発者の待ち時間増加**: CI結果を待つ時間が長期化

### 1.3 目的
SpotFleetエージェントのLaunchTemplateに`creditSpecification.cpuCredits="unlimited"`設定を追加し、CPUクレジット枯渇時もスロットリングを回避して安定したビルド/テスト性能を維持する。

### 1.4 ビジネス価値
| 項目 | 効果 |
|------|------|
| 開発者生産性向上 | CI待ち時間の短縮による開発効率向上 |
| CI信頼性向上 | タイムアウト・失敗率の低減 |
| 運用コスト最適化 | リトライ減少によるリソース効率化 |

### 1.5 技術的価値
| 項目 | 効果 |
|------|------|
| インフラ安定性 | 負荷変動時も一定のCPU性能を維持 |
| 予測可能性 | ジョブ実行時間の安定化・予測精度向上 |
| 運用簡素化 | CPUクレジット監視・対応作業の削減 |

---

## 2. 機能要件

### 2.1 FR-001: x86_64用LaunchTemplateへのCPUクレジットUnlimited設定追加
| 項目 | 内容 |
|------|------|
| **要件ID** | FR-001 |
| **優先度** | 高 |
| **説明** | `agentLaunchTemplate`（x86_64用）に`creditSpecification`プロパティを追加し、`cpuCredits: "unlimited"`を設定する |
| **対象ファイル** | `pulumi/jenkins-agent/index.ts` |
| **対象行** | 293行目付近（`agentLaunchTemplate`定義） |
| **対象インスタンスタイプ** | t3a.medium, t3.medium, t3a.small, t3.small, t3a.micro, t3.micro |

### 2.2 FR-002: ARM64用LaunchTemplateへのCPUクレジットUnlimited設定追加
| 項目 | 内容 |
|------|------|
| **要件ID** | FR-002 |
| **優先度** | 高 |
| **説明** | `[REDACTED_TOKEN]`（ARM64用）に`creditSpecification`プロパティを追加し、`cpuCredits: "unlimited"`を設定する |
| **対象ファイル** | `pulumi/jenkins-agent/index.ts` |
| **対象行** | 393行目付近（`[REDACTED_TOKEN]`定義） |
| **対象インスタンスタイプ** | t4g.medium, t4g.small, t4g.micro |

### 2.3 FR-003: Pulumiスタック更新によるLaunchTemplate反映
| 項目 | 内容 |
|------|------|
| **要件ID** | FR-003 |
| **優先度** | 高 |
| **説明** | `pulumi up`コマンドでスタックを更新し、LaunchTemplateの新バージョンを作成する |
| **期待動作** | SpotFleetが`latestVersion`を参照しているため、新規インスタンス起動時から自動的に新設定が適用される |

### 2.4 FR-004: ドキュメント更新
| 項目 | 内容 |
|------|------|
| **要件ID** | FR-004 |
| **優先度** | 中 |
| **説明** | `docs/architecture/infrastructure.md`にCPUクレジットUnlimited設定の説明とコスト影響に関する注意事項を追記する |
| **追記内容** | 設定の目的、適用範囲、コスト影響、監視方法 |

---

## 3. 非機能要件

### 3.1 パフォーマンス要件
| 要件ID | 項目 | 基準 |
|--------|------|------|
| NFR-P01 | CPU性能維持 | CPUクレジット枯渇時もベースラインを超える性能を維持 |
| NFR-P02 | ジョブ実行時間 | 高負荷時のジョブ実行時間がスロットリングにより大幅に増加しないこと |

### 3.2 セキュリティ要件
| 要件ID | 項目 | 基準 |
|--------|------|------|
| NFR-S01 | 既存設定の維持 | セキュリティグループ、IAMロール等の既存セキュリティ設定に影響を与えないこと |
| NFR-S02 | 暗号化設定の維持 | EBS暗号化（`encrypted: "true"`）設定が変更されないこと |

### 3.3 可用性・信頼性要件
| 要件ID | 項目 | 基準 |
|--------|------|------|
| NFR-A01 | ローリング更新 | 既存インスタンスへの影響なく、新規インスタンスから段階的に適用されること |
| NFR-A02 | ロールバック可能性 | 問題発生時にPulumi変更を元に戻すことで即座にロールバック可能であること |
| NFR-A03 | サービス継続性 | 設定変更中もJenkinsジョブの実行に影響を与えないこと |

### 3.4 保守性・拡張性要件
| 要件ID | 項目 | 基準 |
|--------|------|------|
| NFR-M01 | コードスタイル | 既存のPulumiコードスタイル・構造に準拠すること |
| NFR-M02 | ドキュメント整合性 | 変更内容がドキュメントに正確に反映されていること |
| NFR-M03 | 将来の拡張性 | 必要に応じてSSMパラメータで`unlimited`/`standard`を切り替え可能な設計を検討できる余地を残すこと |

### 3.5 コスト要件
| 要件ID | 項目 | 基準 |
|--------|------|------|
| NFR-C01 | コスト認識 | Unlimited設定による追加コストが発生することを認識し、ドキュメントに明記すること |
| NFR-C02 | コスト監視 | CloudWatch BillingアラートでCPUクレジット追加料金の監視が可能であること |

---

## 4. 制約事項

### 4.1 技術的制約
| 制約ID | 項目 | 内容 |
|--------|------|------|
| TC-001 | 変更対象限定 | 変更は`pulumi/jenkins-agent/index.ts`ファイルのみに限定 |
| TC-002 | Pulumiバージョン | `@pulumi/aws` v6.0以降が必要（`creditSpecification`プロパティのサポート要件） |
| TC-003 | TypeScript構文 | 既存のPulumiリソース定義構文に準拠した実装 |
| TC-004 | リソース名固定 | Pulumiリソース名（第1引数）は既存のまま変更しない |

### 4.2 リソース制約
| 制約ID | 項目 | 内容 |
|--------|------|------|
| RC-001 | 作業時間 | 見積もり工数2.5時間以内
... (truncated)
```

## Turn 10: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 11: ツール実行

**種別**: コマンド実行
**コマンド**: `/bin/bash -lc 'cat CLAUDE.md'`
**ステータス**: completed (exit_code=0)

```text
# CLAUDE.md

このファイルは、このリポジトリでコードを扱う際のClaude Code (claude.ai/code) へのガイダンスを提供します。

## プロジェクト概要

包括的なJenkins CI/CDインフラ自動化プロジェクトで、ブートストラップにCloudFormation、インフラプロビジョニングにPulumi (TypeScript)、オーケストレーションにAnsibleを使用しています。ブルーグリーンデプロイメント機能、自動スケーリングエージェント、高可用性機能を備えた本番環境対応のJenkins環境をAWS上にデプロイします。

詳細なセットアップ・運用手順は`docs/`配下に分割されたドキュメント（READMEのクイックナビゲーション参照）を確認してください。

## アーキテクチャ設計思想

**Platform Engineeringの設計思想とアーキテクチャの詳細は [ARCHITECTURE.md](ARCHITECTURE.md) を参照してください。**

このプロジェクトは以下の原則に基づいて設計されています：
- **Jenkins**: 統括司令塔（WHO & WHEN）
- **Ansible**: オーケストレーター（HOW）
- **Pulumi**: インフラ構築者（WHAT）
- **SSM Parameter Store**: Single Source of Truth

## コーディングガイドライン

### 基本原則
- **思考**: 技術的な内容は英語、プロジェクト固有の内容は日本語で柔軟に思考
- **対話**: 日本語で対話 (Dialogue in Japanese with users)
- **ドキュメント**: 日本語で記述 (Documentation in Japanese)
- **コメント**: ソースコード内のコメントは日本語
- **README/ドキュメント**: すべて日本語で記述

### 重要な注意事項
- **Bootstrap修正時**: `bootstrap/` ディレクトリ内のファイルを修正した場合、必ずREADME.mdの更新が必要かチェックすること
- **依存関係の順序**: コンポーネント間の依存関係を常に意識し、デプロイ/削除順序を守ること
- **環境分離**: dev/staging/production環境を明確に分離すること

## Pulumiベストプラクティス

**Pulumiスタックの使用方法については [pulumi/README.md](pulumi/README.md) を参照してください。**
**開発者向けの詳細な実装方法は [pulumi/CONTRIBUTION.md](pulumi/CONTRIBUTION.md) を参照してください。**

### 重要な注意事項

- **Pulumi開発時**: Pulumiスタックを修正・追加した場合、必ず `pulumi/README.md` の更新が必要かチェックすること
- **ドキュメント更新対象**:
  - 新しいスタックの追加
  - スタック間の依存関係変更
  - 設定パラメータの変更
  - コーディング規約の追加
  - トラブルシューティング情報の追加

## Jenkinsベストプラクティス

**Jenkinsの設定、Job DSL、パイプライン、共有ライブラリについては [jenkins/README.md](jenkins/README.md) を参照してください。**
**開発者向けの詳細な実装方法は [jenkins/CONTRIBUTION.md](jenkins/CONTRIBUTION.md) を参照してください。**

### 重要な注意事項

- **Jenkins開発時**: Jenkins設定、ジョブ定義、パイプラインを修正・追加した場合、必ず `jenkins/README.md` の更新が必要かチェックすること
- **ドキュメント更新対象**:
  - 新しいジョブの追加
  - パイプラインの変更
  - 共有ライブラリの追加・変更
  - プラグインの変更
  - セキュリティ設定の変更
  - トラブルシューティング情報の追加
- **⚠️ ECS Fargate設定の重要な注意**:
  - `jenkins.yaml.template`のECS設定は`amazon-ecs`プラグインの仕様に厳密に従うこと
  - **サポートされていない設定項目**: `[REDACTED_TOKEN]`, `maxInstances`（これらを含めるとJenkins起動失敗）
  - **必須のIAM権限**: ControllerのIAM Roleに`ecs:RunTask`, `ecs:StopTask`, `ecs:DescribeTasks`等のECS操作権限が必要
  - Pulumi `jenkins-controller`スタックにECS Fargateポリシーが定義されていること

### ⚠️ Jenkinsパラメータ定義ルール

**重要**: Jenkinsfileでのパラメータ定義は禁止です。パラメータは必ずJob DSLファイルで定義してください。

```groovy
// ✅ 正しい: DSLファイルでパラメータ定義
pipelineJob(jobName) {
    parameters {
        stringParam('VERSION', '1.0.0', 'バージョン')
        choiceParam('ENV', ['dev', 'staging', 'prod'], '環境')
    }
}

// ❌ 間違い: Jenkinsfileでパラメータ定義
pipeline {
    parameters {  // 禁止！初回実行時に問題が発生
        string(name: 'VERSION', defaultValue: '1.0.0')
    }
}
```

詳細は [jenkins/CONTRIBUTION.md#重要-パラメータ定義のルール](jenkins/CONTRIBUTION.md#重要-パラメータ定義のルール) を参照。

## Ansibleベストプラクティス

**Ansibleプレイブックの開発・使用方法については [ansible/README.md](ansible/README.md) を参照してください。**
**開発者向けの詳細な実装方法は [ansible/CONTRIBUTION.md](ansible/CONTRIBUTION.md) を参照してください。**

### 重要な注意事項

- **Ansible開発時**: Ansibleプレイブックやロールを修正・追加した場合、必ず `ansible/README.md` の更新が必要かチェックすること
- **ドキュメント更新対象**:
  - 新しいプレイブックの追加
  - 新しいロールの追加
  - パラメータ変更
  - 依存関係の変更
  - 実行手順の変更
  - トラブルシューティング情報の追加
- **ヘルパーロールの活用**: `pulumi_helper`、`ssm_parameter_store`、`aws_cli_helper`、`aws_setup`を積極的に使用すること
- **meta/main.yml必須**: ヘルパーロールを使用する場合は、必ず`meta/main.yml`に依存関係を定義すること

## デプロイメントアーキテクチャ

**各システムのコンポーネント依存関係やデプロイ順序については [ansible/README.md#デプロイメントアーキテクチャ](ansible/README.md#デプロイメントアーキテクチャ) を参照してください。**

### 一般的なデプロイ原則

1. **初期化**: SSMパラメータの準備
2. **基盤**: ネットワーク → セキュリティ
3. **インフラ**: ストレージ、ロードバランサー等
4. **コンピュート**: EC2、Lambda等
5. **アプリケーション**: 設定、デプロイ

### 削除原則

削除は常にデプロイの逆順で実行すること。

## 開発ワークフロー

### ⚠️ 開発開始前の必須確認事項

**重要**: 開発を開始する前に、必ず対応するCONTRIBUTION.mdを確認してください。
- **Ansible開発**: `ansible/CONTRIBUTION.md` を必ず確認
- **Pulumi開発**: `pulumi/CONTRIBUTION.md` を必ず確認
- **Jenkins開発**: `jenkins/CONTRIBUTION.md` を必ず確認
- **スクリプト開発**: `scripts/CONTRIBUTION.md` を必ず確認

これらのドキュメントには、実装方法、コーディング規約、ベストプラクティスが記載されています。

### 0. Issue作成とブランチ作成（新規タスクの場合）

```bash
# 1. Issueテンプレートを確認
ls .github/ISSUE_TEMPLATE/
# - bug_report.md: バグ報告用
... (truncated)
```

## Turn 12: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 13: ツール実行

**種別**: コマンド実行
**コマンド**: `/bin/bash -lc 'cat pulumi/CONTRIBUTION.md'`
**ステータス**: completed (exit_code=0)

```text
# Pulumi開発規約

このドキュメントは、Pulumiスタック開発における詳細な規約とベストプラクティスを定めたものです。

## 📋 目次

- [プロジェクト構造](#プロジェクト構造)
- [コーディング規約](#コーディング規約)
- [命名規則](#命名規則)
- [設定管理](#設定管理)
- [スタック間の依存関係](#スタック間の依存関係)
- [エラーハンドリング](#エラーハンドリング)
- [テストとバリデーション](#テストとバリデーション)
- [パフォーマンス最適化](#パフォーマンス最適化)
- [セキュリティベストプラクティス](#セキュリティベストプラクティス)

## プロジェクト構造

### 必須ファイル構成

```
{stack-name}/
├── Pulumi.yaml             # プロジェクト定義（必須）
├── Pulumi.{env}.yaml       # 環境別設定（オプション）
├── index.ts                # メインエントリーポイント（必須）
├── package.json            # Node.js依存関係（必須）
├── tsconfig.json           # TypeScript設定（必須）
├── bin/                    # コンパイル出力ディレクトリ
└── README.md              # スタック説明（推奨）
```

### package.json テンプレート

```json
{
  "name": "@project/{stack-name}",
  "version": "1.0.0",
  "main": "bin/index.js",
  "scripts": {
    "build": "tsc",
    "preview": "pulumi preview",
    "deploy": "pulumi up -y",
    "destroy": "pulumi destroy -y",
    "refresh": "pulumi refresh -y",
    "export": "pulumi stack export > stack-state.json",
    "import": "pulumi stack import --file=stack-state.json"
  },
  "devDependencies": {
    "@types/node": "^18.0.0",
    "typescript": "^4.0.0"
  },
  "dependencies": {
    "@pulumi/pulumi": "^3.0.0",
    "@pulumi/aws": "^6.0.0"
  }
}
```

### tsconfig.json テンプレート

```json
{
  "compilerOptions": {
    "strict": true,
    "outDir": "bin",
    "target": "es2016",
    "module": "commonjs",
    "moduleResolution": "node",
    "sourceMap": true,
    "[REDACTED_TOKEN]": true,
    "pretty": true,
    "[REDACTED_TOKEN]": true,
    "noImplicitReturns": true,
    "[REDACTED_TOKEN]": true,
    "esModuleInterop": true
  },
  "files": ["index.ts"],
  "exclude": ["node_modules", "bin"]
}
```

### index.ts 標準構造

```typescript
/**
 * pulumi/{stack-name}/index.ts
 * {stack}のインフラストラクチャ定義
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// ========================================
// 環境変数取得
// ========================================
const environment = pulumi.getStack();

// ========================================
// SSMパラメータ参照（Single Source of Truth）
// ========================================
// 重要: Pulumi ConfigやStackReferenceは使用せず、
// SSMパラメータストアから全ての設定を取得する

// プロジェクト名を取得
const projectNameParam = aws.ssm.getParameter({
    name: `/{system-name}/${environment}/common/project-name`,
});
const projectName = pulumi.output(projectNameParam).apply(p => p.value);

// 他の設定値も同様にSSMから取得
const vpcIdParam = aws.ssm.getParameter({
    name: `/${projectName}/${environment}/network/vpc-id`,
});
const vpcId = pulumi.output(vpcIdParam).apply(p => p.value);

// ========================================
// リソース定義
// ========================================
// リソース名は固定文字列を使用（Output<T>エラー回避）
const resource = new aws.ec2.Instance("fixed-resource-name", {
    // プロパティにはpulumi.interpolateを使用
    tags: {
        Name: pulumi.interpolate`${projectName}-instance-${environment}`,
        Environment: environment,
    },
});

// ========================================
// SSMパラメータへの保存
// ========================================
// 他のスタックが参照する値はSSMに保存
const outputParam = new aws.ssm.Parameter("output-param", {
    name: pulumi.interpolate`/${projectName}/${environment}/component/output-value`,
    type: "String",
    value: resource.id,
    description: "Component output value",
    tags: {
        Environment: environment,
    },
});

// ========================================
// エクスポート（表示用のみ）
// ========================================
// エクスポートは表示・確認用のみ
// 他のスタックはSSMパラメータから値を取得すること
export const outputs = {
    resourceId: resource.id,
    ssmParameterName: outputParam.name,
};
```

## コーディング規約

### Output<T>エラーの回避

```typescript
// ❌ 間違い: リソース名にOutput<T>を使用
const bucket = new aws.s3.Bucket(`${projectName}-bucket`, {});

// ✅ 正しい: リソース名は固定文字列
const bucket = new aws.s3.Bucket("my-bucket", {
    bucket: pulumi.interpolate`${projectName}-bucket-${environment}`,
});

// ❌ 間違い: JSON.stringify内でOutput<T>を使用
const co
... (truncated)
```

## Turn 14: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 15: ツール実行

**種別**: コマンド実行
**コマンド**: `/bin/bash -lc 'rg -n "Jenkins|CPU" docs/architecture/infrastructure.md'`
**ステータス**: failed (exit_code=127)

```text
/bin/bash: line 1: rg: command not found
```

## Turn 16: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 17: ツール実行

**種別**: コマンド実行
**コマンド**: `/bin/bash -lc 'grep -n "Jenkins" docs/architecture/infrastructure.md'`
**ステータス**: completed (exit_code=0)

```text
7:Jenkins基盤で利用するAWSリソース、リポジトリのディレクトリ構造、主要機能と管理ポイントをまとめています。
12:- Jenkinsコントローラー用のEC2インスタンス（ブルー/グリーン環境）
13:- Jenkinsエージェント用のEC2 SpotFleet（自動スケーリング対応）
14:- Jenkinsエージェント用のECS Fargateクラスタ、ECRリポジトリ、Task Definition、CloudWatch Logs
15:- Jenkinsエージェント用のカスタムAMI（EC2 Image Builder）
16:- Jenkinsデータ永続化のためのEFSファイルシステム
18:- Jenkins関連リソースのIAMロールとポリシー
28:│  │  ├─ jenkins/             # Jenkins関連プレイブック
38:│      ├─ jenkins_*/          # Jenkins関連（network, controller, agent等）
45:├─ jenkins/                    # Jenkins設定とジョブ定義
46:│  └─ jobs/                    # Jenkinsジョブ定義
48:│      ├─ pipeline/            # パイプラインジョブ（Jenkinsfile）
52:│  ├─ jenkins-*/               # Jenkinsインフラスタック
53:│  │  ├─ jenkins-agent/        # Jenkins Agent SpotFleet
54:│  │  └─ jenkins-agent-ami/    # Jenkins Agent AMI Builder
59:│  └─ jenkins/                 # Jenkins設定スクリプト
65:├─ docker/                      # Jenkinsエージェントコンテナ定義
67:│      ├─ Dockerfile           # ECS専用Jenkinsエージェントイメージ
77:- **jenkins/**: Jenkinsジョブ定義とパイプライン。Job DSLとJenkinsfileによるジョブ管理
79:- **scripts/**: 各種ユーティリティスクリプト。AWS操作、Jenkins設定、初期化処理など
87:- **ブルー/グリーンデプロイメント**: Jenkinsの更新を無停止で行えるデュアル環境
88:- **自動スケーリングエージェント**: EC2 SpotFleetによるコスト効率の高いJenkinsエージェント
90:- **データ永続性**: EFSによるJenkinsデータの永続化と高可用性の確保
91:- **アプリケーション設定管理**: Jenkinsバージョン更新、プラグイン管理、再起動処理の自動化
92:- **Jenkins CLIユーザー管理**: APIトークンを使用したCLIアクセスの自動設定
95:## Jenkinsエージェント構成
97:本番環境では、Jenkins コントローラーから接続するエージェントを SpotFleet（EC2）と ECS Fargate の双方で運用しています。SpotFleet は既存のバッチ/長時間ジョブに対して安定したキャパシティを提供し、ECS Fargate は短時間かつ高い並列性が求められるジョブを高速に処理します。どちらの構成も `pulumi/jenkins-agent/index.ts` 内で定義されたリソース群と SSM パラメータを通じて Jenkins に公開されます。
114:- Jenkins からは両方のエージェントを amazon-ecs プラグインと SpotFleet プラグインで個別に管理し、SSM パラメータ経由で接続情報を取得
118:`pulumi/jenkins-agent/index.ts` の 739 行以降では、ECS Fargate エージェント用の Cluster、ECR、Task Definition、IAM Role、CloudWatch Logs が定義され、各リソースは SSM パラメータとして Jenkins に提供されます。
126:`docker/jenkins-agent-ecs` でビルドした Jenkins エージェントイメージは専用の ECR リポジトリに格納され、Fargate タスクはこのリポジトリからイメージを取得します。リポジトリ URL も SSM パラメータとして公開し、タスク定義の `image` フィールドへ埋め込みます。
130:タスク定義では利用するコンテナの CPU/Mem、実行ロール（`ecs-task-role`）、実行時ロール（`ecs-execution-role`）、ログドライバ（CloudWatch Logs）、必要な環境変数・ボリュームなどを包括的に定義しています。定義の ARN は SSM パラメータ `/jenkins-infra/{environment}/agent/ecs-task-definition-arn` で管理され、Jenkins から amazon-ecs プラグイン経由で参照します。
134:Fargate タスクには Execution Role（ECR へのプル、CloudWatch へのログ送信）と Task Role（Jenkins 内での操作権限）の 2 つの IAM Role を割り当てています。Task Role は AdministratorAccess ポリシーを継承し、SpotFleet とは異なる最小権限の境界を維持しつつも必要なリソースへアクセスできるようにしています。
142:`docker/jenkins-agent-ecs` 以下には、ECS Fargate で動作する Jenkins エージェントコンテナの定義が集約されています。主なファイルは次の通りです：
144:- `Dockerfile`: Multi-stage build を採用し、OpenJDK、AWS CLI、Pulumi、Ansible、Jenkins Remoting など必要なツールを含む軽量イメージを構築します。ビルド後は不要ファイルを削ぎ落とし、最終ステージでは実行に必要なファイルのみを残します。
149:ECS エージェントに必要な接続情報は全て SSM Parameter Store で管理され、`/jenkins-infra/{environment}/agent/` プレフィックスに集約されています。SpotFleet で利用しているパラメータと同様に Pulumi の `pulumi/jenkins-agent/index.ts` から出力され、Jenkins の amazon-ecs プラグインや運用手順でそのまま参照されます。
155:| `/jenkins-infra/{environment}/agent/ecs-task-definition-arn` | Task Definition ARN | Task Definition のリビジョンを Jenkins から指定 |
158:| `/jenkins-infra/{environment}/agent/ecs-task-role-arn` | ECS Task Role ARN | Jenkins 内処理用ロール（AdministratorAccess） |
161:## Jenkins環境構築後の管理機能
165:1. **Jenkinsバージョン更新**
175:   - APIトークンの生成とJenkinsクレデンシャルストアへの保存
184:   - Jenkinsの安全な再起動
189:- [Jenkinsインフラデプロイ](../operations/jenkins-deploy.md)
190:- [Jenkins環境運用管理](../operations/jenkins-management.md)
```

## Turn 18: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 19: ツール実行

**種別**: コマンド実行
**コマンド**: `/bin/bash -lc "sed -n '90,180p' docs/architecture/infrastructure.md"`
**ステータス**: completed (exit_code=0)

```text
- **データ永続性**: EFSによるJenkinsデータの永続化と高可用性の確保
- **アプリケーション設定管理**: Jenkinsバージョン更新、プラグイン管理、再起動処理の自動化
- **Jenkins CLIユーザー管理**: APIトークンを使用したCLIアクセスの自動設定
- **シードジョブによるジョブ管理**: Infrastructure as Codeによるジョブの自動作成・更新・削除

## Jenkinsエージェント構成

本番環境では、Jenkins コントローラーから接続するエージェントを SpotFleet（EC2）と ECS Fargate の双方で運用しています。SpotFleet は既存のバッチ/長時間ジョブに対して安定したキャパシティを提供し、ECS Fargate は短時間かつ高い並列性が求められるジョブを高速に処理します。どちらの構成も `pulumi/jenkins-agent/index.ts` 内で定義されたリソース群と SSM パラメータを通じて Jenkins に公開されます。

### SpotFleet vs ECS Fargate 比較

| 観点 | SpotFleet | ECS Fargate |
|------|-----------|-------------|
| コスト | スポットインスタンスによる低コスト | オンデマンド課金のためやや高価だが必要な分だけ課金 |
| 起動速度 | EC2 の起動を伴うため中程度 | コンテナ起動のため高速 |
| スケーラビリティ | 数百台まで拡張可能 | 数千タスクの並行実行が可能 |
| 管理負荷 | AMI と Launch Template の管理が必要 | コンテナ定義のみで運用 |
| リソース効率 | 固定サイズのインスタンス | 必要なリソースに応じたスケール |
| 適用場面 | 長時間バッチ処理やツールチェーン依存 | 短時間・並列処理、CI ファーストパーティタスク |

#### 使い分けの指針

- 長時間実行を前提にした大容量やレガシーツールチェーンは SpotFleet を維持
- 短時間かつスケールが必要なタスク、たとえば並列ビルド/テストは ECS Fargate エージェントへ切り替え
- Jenkins からは両方のエージェントを amazon-ecs プラグインと SpotFleet プラグインで個別に管理し、SSM パラメータ経由で接続情報を取得

## ECS Fargateエージェント詳細

`pulumi/jenkins-agent/index.ts` の 739 行以降では、ECS Fargate エージェント用の Cluster、ECR、Task Definition、IAM Role、CloudWatch Logs が定義され、各リソースは SSM パラメータとして Jenkins に提供されます。

### ECS Cluster

専用の ECS Cluster を作成し、Fargate タスクの実行環境を分離しています。クラスタ名・ARN は SSM パラメータ `/jenkins-infra/{environment}/agent/ecs-cluster-*` で公開され、amazon-ecs プラグインのクラスタ設定にそのまま流し込めるようにしています。

### ECR Repository

`docker/jenkins-agent-ecs` でビルドした Jenkins エージェントイメージは専用の ECR リポジトリに格納され、Fargate タスクはこのリポジトリからイメージを取得します。リポジトリ URL も SSM パラメータとして公開し、タスク定義の `image` フィールドへ埋め込みます。

### Task Definition

タスク定義では利用するコンテナの CPU/Mem、実行ロール（`ecs-task-role`）、実行時ロール（`ecs-execution-role`）、ログドライバ（CloudWatch Logs）、必要な環境変数・ボリュームなどを包括的に定義しています。定義の ARN は SSM パラメータ `/jenkins-infra/{environment}/agent/ecs-task-definition-arn` で管理され、Jenkins から amazon-ecs プラグイン経由で参照します。

### IAM Roles

Fargate タスクには Execution Role（ECR へのプル、CloudWatch へのログ送信）と Task Role（Jenkins 内での操作権限）の 2 つの IAM Role を割り当てています。Task Role は AdministratorAccess ポリシーを継承し、SpotFleet とは異なる最小権限の境界を維持しつつも必要なリソースへアクセスできるようにしています。

### CloudWatch Logs

タスクのコンテナログは CloudWatch Logs に送信し、Log Group 名も SSM パラメータ `/jenkins-infra/{environment}/agent/ecs-log-group-name` で管理しています。S3 やログフィルタは必要に応じて追加できますが、基本は Pulumi 定義内でリテンションとストリームポリシーを維持しています。

## docker/jenkins-agent-ecs

`docker/jenkins-agent-ecs` 以下には、ECS Fargate で動作する Jenkins エージェントコンテナの定義が集約されています。主なファイルは次の通りです：

- `Dockerfile`: Multi-stage build を採用し、OpenJDK、AWS CLI、Pulumi、Ansible、Jenkins Remoting など必要なツールを含む軽量イメージを構築します。ビルド後は不要ファイルを削ぎ落とし、最終ステージでは実行に必要なファイルのみを残します。
- `entrypoint.sh`: amazon-ecs プラグイン互換のエントリーポイントで、引数の変換や環境変数の整備、動作ログの出力を行います。古い形式の引数をサポートしつつ新しい ECS タスクからの実行も可能なように調整されています。

## ECSエージェント用SSMパラメータ

ECS エージェントに必要な接続情報は全て SSM Parameter Store で管理され、`/jenkins-infra/{environment}/agent/` プレフィックスに集約されています。SpotFleet で利用しているパラメータと同様に Pulumi の `pulumi/jenkins-agent/index.ts` から出力され、Jenkins の amazon-ecs プラグインや運用手順でそのまま参照されます。

| パラメータ名 | 説明 | 用途 |
|-------------|------|------|
| `/jenkins-infra/{environment}/agent/ecs-cluster-arn` | ECS Cluster ARN | amazon-ecs プラグインのクラスタ指定 |
| `/jenkins-infra/{environment}/agent/ecs-cluster-name` | ECS Cluster 名 | 管理者がクラスタを識別するため |
| `/jenkins-infra/{environment}/agent/ecs-task-definition-arn` | Task Definition ARN | Task Definition のリビジョンを Jenkins から指定 |
| `/jenkins-infra/{environment}/agent/ecr-repository-url` | ECR リポジトリ URL | ECS タスクの `image` フィールドに設定 |
| `/jenkins-infra/{environment}/agent/ecs-execution-role-arn` | ECS Execution Role ARN | ECR へのアクセスやログ送信権限 |
| `/jenkins-infra/{environment}/agent/ecs-task-role-arn` | ECS Task Role ARN | Jenkins 内処理用ロール（AdministratorAccess） |
| `/jenkins-infra/{environment}/agent/ecs-log-group-name` | CloudWatch Logs Group 名 | タスクログの送信先 |

## Jenkins環境構築後の管理機能

`[REDACTED_TOKEN].yml` プレイブックを使用して、以下の管理タスクを実行できます：

1. **Jenkinsバージョン更新**
   - 最新バージョンまたは特定バージョンへの安全なアップグレード
   - 自動バックアップとロールバック機能

2. **プラグイン管理**
   - `install-plugins.groovy`スクリプト
... (truncated)
```

## Turn 20: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 21: ツール実行

**種別**: コマンド実行
**コマンド**: `/bin/bash -lc "sed -n '260,450p' pulumi/jenkins-agent/index.ts"`
**ステータス**: completed (exit_code=0)

```text
const jenkinsAgentProfile = new aws.iam.InstanceProfile(
    `agent-profile`, 
    {
        role: jenkinsAgentRole.name,
        tags: {
            Environment: environment,
        },
    }
);

// SpotFleet用IAMロール
const spotFleetRole = new aws.iam.Role(`spotfleet-role`, {
    name: pulumi.interpolate`${projectName}-spotfleet-role-${environment}`,
    assumeRolePolicy: JSON.stringify({
        Version: "2012-10-17",
        Statement: [{
            Effect: "Allow",
            Principal: {
                Service: "spotfleet.amazonaws.com",
            },
            Action: "sts:AssumeRole",
        }],
    }),
    managedPolicyArns: [
        "arn:aws:iam::aws:policy/service-role/[REDACTED_TOKEN]",
    ],
    tags: {
        Name: `[REDACTED_TOKEN]-${environment}`,
        Environment: environment,
    },
});

// エージェント起動テンプレート（x86_64用、IPv6対応）
const agentLaunchTemplate = new aws.ec2.LaunchTemplate(`agent-lt`, {
    namePrefix: `[REDACTED_TOKEN]-`,
    imageId: amiX86Id,
    instanceType: "t3a.medium", // デフォルトをt3a.mediumに変更（AMDプロセッサで10%安価）
    keyName: agentKeyPair.keyName,  // 作成したキーペアを使用
    ebsOptimized: "true",  // EBS最適化を有効化
    // vpcSecurityGroupIds は networkInterfaces と競合するため削除
    iamInstanceProfile: {
        name: jenkinsAgentProfile.name,
    },
    blockDeviceMappings: [{
        deviceName: "/dev/xvda",
        ebs: {
            volumeSize: 30, // expect size>= 30GB
            volumeType: "gp3",
            deleteOnTermination: "true", // 文字列に変更
            encrypted: "true", // 文字列に変更
        },
    }],
    metadataOptions: {
        httpEndpoint: "enabled",
        httpTokens: "required",
        [REDACTED_TOKEN]: 2,
    },
    networkInterfaces: [{
        [REDACTED_TOKEN]: "false",
        deleteOnTermination: "true",
        deviceIndex: 0,
        ipv6AddressCount: 1,  // IPv6アドレスを1つ割り当て
        securityGroups: [[REDACTED_TOKEN]],
    }],
    tagSpecifications: [{
        resourceType: "instance",
        tags: {
            Name: `jenkins-infra-agent-${environment}`,
            Environment: environment,
            Role: "jenkins-agent",
            IPv6Enabled: "true",  // IPv6有効化タグを追加
        },
    }],
    // ユーザーデータをBase64エンコード（カスタムAMI使用時は最小限の設定）
    userData: pulumi.all([amiX86Id, customAmiX86Promise]).apply(([id, customId]) => {
        const isCustomAmi = customId && !customId.startsWith("ami-placeholder");
        
        // 外部スクリプトファイルのパスを決定
        const scriptName = isCustomAmi ? '[REDACTED_TOKEN].sh' : 'jenkins-agent-setup.sh';
        const scriptPath = path.resolve(__dirname, '..', '..', 'scripts', 'aws', 'userdata', scriptName);
        
        let userDataTemplate: string;
        
        try {
            if (!fs.existsSync(scriptPath)) {
                // フォールバックパス（Pulumi実行時のカレントディレクトリから）
                const alternativePath = path.resolve(process.cwd(), 'scripts', 'aws', 'userdata', scriptName);
                if (fs.existsSync(alternativePath)) {
                    userDataTemplate = fs.readFileSync(alternativePath, 'utf8');
                } else {
                    throw new Error(`Userdata script not found at ${scriptPath} or ${alternativePath}`);
                }
            } else {
                userDataTemplate = fs.readFileSync(scriptPath, 'utf8');
            }
        } catch (error) {
            pulumi.log.error(`Failed to read userdata script: ${error}`);
            throw error;
        }
        
        // テンプレート変数の置換
        const ipv6Config = isCustomAmi ? `# IPv6設定の有効化
echo "Configuring IPv6..."
cat >> /etc/sysconfig/network << EOF
NETWORKING_IPV6=yes
IPV6_DEFAULTDEV=eth0
EOF

# IPv6 の確認と記録
IPV6_ADDR=$(ip -6 addr show eth0 | grep "inet6" | grep -v "fe80" | awk '{print $2}' | cut -d'/' -f1 | head -n1)
if [ -n "$IPV6_ADDR" ]; then
    echo "IPv6 Address: $IPV6_ADDR"
    echo "$IPV6_ADDR" > /home/jenkins/ipv6_address
fi

` : '';
        
        const userData = userDataTemplate
... (truncated)
```

## Turn 22: ツール実行

**種別**: コマンド実行
**コマンド**: `/bin/bash -lc "sed -n '450,780p' pulumi/jenkins-agent/index.ts"`
**ステータス**: completed (exit_code=0)

```text
} else {
                    throw new Error(`Userdata script not found at ${scriptPath} or ${alternativePath}`);
                }
            } else {
                userDataTemplate = fs.readFileSync(scriptPath, 'utf8');
            }
        } catch (error) {
            pulumi.log.error(`Failed to read userdata script: ${error}`);
            throw error;
        }
        
        // テンプレート変数の置換
        const userData = userDataTemplate
            .replace(/\${PROJECT_NAME}/g, 'jenkins-infra')
            .replace(/\${ENVIRONMENT}/g, environment)
            .replace(/\${IPV6_CONFIG}/g, '')
            .replace(/\${IPV6_ENV}/g, '')
            .replace(/\${ARCHITECTURE_ENV}/g, 'echo "ARCHITECTURE=arm64" >> /etc/jenkins-agent-env\n');
        
        return Buffer.from(userData).toString("base64");
    }),
    tags: {
        Name: `[REDACTED_TOKEN]-${environment}`,
        Environment: environment,
    },
});

// Medium インスタンス専用のSpotFleetリクエスト設定（複数の起動テンプレートを使用、AZ別に最適化）
const spotFleetRequest = new aws.ec2.SpotFleetRequest(`agent-spot-fleet`, {
    iamFleetRole: spotFleetRole.arn,
    spotPrice: spotPriceMedium,
    targetCapacity: [REDACTED_TOKEN],
    [REDACTED_TOKEN]: true,
    [REDACTED_TOKEN]: "terminate",
    allocationStrategy: "lowestPrice", // 最も安価なインスタンスを優先
    [REDACTED_TOKEN]: true,
    [REDACTED_TOKEN]: pulumi.all([privateSubnetIds]).apply(([subnetIds]) => {
        const configs: any[] = [];

        // 各サブネットのAZ情報を取得して適切なインスタンスタイプを設定
        subnetIds.forEach((subnetId: string) => {
            // ARM64インスタンス用の設定（t4g.medium）- 全AZで利用可能
            configs.push({
                [REDACTED_TOKEN]: {
                    id: [REDACTED_TOKEN].id,
                    version: [REDACTED_TOKEN].latestVersion.apply(v => v.toString()),
                },
                overrides: [{
                    subnetId: subnetId,
                    instanceType: "t4g.medium",
                    spotPrice: spotPriceMedium,
                    priority: 1, // 最優先
                }],
            });

            // x86_64インスタンス用の設定
            // サブネットAZ取得のため、AWSリソースから情報を取得
            const subnet = aws.ec2.getSubnetOutput({ id: subnetId });
            const azSuffix = subnet.availabilityZone.apply(az => az.slice(-1)); // 'a' or 'c'

            // ap-northeast-1a: t3a.mediumが利用可能
            // ap-northeast-1c: t3a.mediumは利用不可
            const x86Overrides = azSuffix.apply(suffix => {
                if (suffix === 'a') {
                    // ap-northeast-1a: t3a.medium, t3.medium の順
                    return [
                        {
                            subnetId: subnetId,
                            instanceType: "t3a.medium",
                            spotPrice: spotPriceMedium,
                            priority: 2,
                        },
                        {
                            subnetId: subnetId,
                            instanceType: "t3.medium",
                            spotPrice: spotPriceMedium,
                            priority: 3,
                        }
                    ];
                } else {
                    // ap-northeast-1c: t3.medium のみ（t3a.mediumは除外）
                    return [
                        {
                            subnetId: subnetId,
                            instanceType: "t3.medium",
                            spotPrice: spotPriceMedium,
                            priority: 2,
                        }
                    ];
                }
            });

            configs.push({
                [REDACTED_TOKEN]: {
                    id: agentLaunchTemplate.id,
                    version: agentLaunchTemplate.latestVersion.apply(v => v.toString()),
                },
                overrides: x86Overrides,
            });
        });

        return configs;
    }),
    tags: {
        Name: `[REDACTED_TOKEN]
... (truncated)
```

## Turn 23: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 24: ツール実行

**種別**: コマンド実行
**コマンド**: `/bin/bash -lc 'ls .ai-workflow/issue-542'`
**ステータス**: completed (exit_code=0)

```text
00_planning
01_requirements
02_design
03_test_scenario
04_implementation
metadata.json
```

## Turn 25: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 26: ツール実行

**種別**: コマンド実行
**コマンド**: `/bin/bash -lc 'ls .ai-workflow/issue-542/04_implementation'`
**ステータス**: completed (exit_code=0)

```text
execute
output
review
revise
```

## Turn 27: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 28: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 29: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 30: ツール実行

**種別**: file_change
**ステータス**: completed

## Turn 31: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 32: ツール実行

**種別**: file_change
**ステータス**: completed

## Turn 33: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 34: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 35: ツール実行

**種別**: コマンド実行
**コマンド**: `/bin/bash -lc 'ls .ai-workflow/issue-542/04_implementation/output'`
**ステータス**: completed (exit_code=0)

## Turn 36: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 37: ツール実行

**種別**: file_change
**ステータス**: completed

## Turn 38: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 39: ツール実行

**種別**: reasoning
**ステータス**: completed

## Turn 40: ツール実行

**種別**: agent_message
**ステータス**: completed

## Turn 41: ツール実行

**種別**: todo_list
**ステータス**: completed

## Turn 42: 実行完了

**ステータス**: completed
**所要時間**: 115018ms
**ターン数**: N/A

---

**経過時間**: 115018ms
**開始**: 2025-12-27T15:10:01.447Z
**終了**: 2025-12-27T15:11:56.465Z