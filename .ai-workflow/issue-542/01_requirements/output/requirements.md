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
| **説明** | `agentLaunchTemplateArm`（ARM64用）に`creditSpecification`プロパティを追加し、`cpuCredits: "unlimited"`を設定する |
| **対象ファイル** | `pulumi/jenkins-agent/index.ts` |
| **対象行** | 393行目付近（`agentLaunchTemplateArm`定義） |
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
| RC-001 | 作業時間 | 見積もり工数2.5時間以内での完了 |
| RC-002 | レビュー | コードレビュー1名以上による承認が必要 |

### 4.3 ポリシー制約
| 制約ID | 項目 | 内容 |
|--------|------|------|
| PC-001 | コーディング規約 | `CLAUDE.md`および`pulumi/CONTRIBUTION.md`のガイドラインに準拠 |
| PC-002 | コミットメッセージ | `[pulumi] update: 詳細説明`形式のコミットメッセージ |
| PC-003 | ドキュメント言語 | ドキュメントは日本語で記述 |

---

## 5. 前提条件

### 5.1 システム環境
| 項目 | 前提条件 |
|------|----------|
| AWSリージョン | ap-northeast-1 |
| Pulumiバックエンド | S3バックエンド設定済み |
| AWS認証 | 適切なIAM権限でAWS CLIが設定済み |

### 5.2 依存コンポーネント
| コンポーネント | 依存関係 |
|----------------|----------|
| jenkins-network | VPC、サブネット情報をSSMパラメータから参照 |
| jenkins-security | セキュリティグループIDをSSMパラメータから参照 |
| SSM Parameter Store | 各種設定値（プロジェクト名、キャパシティ設定等）を参照 |

### 5.3 外部システム連携
| システム | 連携内容 |
|----------|----------|
| AWS EC2 SpotFleet | LaunchTemplateの新バージョンを自動参照 |
| AWS CloudWatch | CPUクレジット関連メトリクス（CPUCreditBalance, CPUSurplusCreditBalance）の監視 |

### 5.4 既存リソース状態
| リソース | 現状 |
|----------|------|
| `agentLaunchTemplate` | 293行目付近に定義済み、`creditSpecification`未設定 |
| `agentLaunchTemplateArm` | 393行目付近に定義済み、`creditSpecification`未設定 |
| SpotFleet（medium/small/micro） | 3種類のフリートが定義済み、`latestVersion`を参照 |

---

## 6. 受け入れ基準

### 6.1 AC-001: x86_64用LaunchTemplateの設定確認
```gherkin
Given pulumi/jenkins-agent/index.tsのagentLaunchTemplateが定義されている
When creditSpecificationプロパティを追加し、cpuCredits: "unlimited"を設定する
Then pulumi previewで該当LaunchTemplateにcreditSpecificationの変更が表示される
And TypeScriptのコンパイルエラーが発生しない
```

### 6.2 AC-002: ARM64用LaunchTemplateの設定確認
```gherkin
Given pulumi/jenkins-agent/index.tsのagentLaunchTemplateArmが定義されている
When creditSpecificationプロパティを追加し、cpuCredits: "unlimited"を設定する
Then pulumi previewで該当LaunchTemplateにcreditSpecificationの変更が表示される
And TypeScriptのコンパイルエラーが発生しない
```

### 6.3 AC-003: Pulumiデプロイの成功確認
```gherkin
Given 両LaunchTemplateにcreditSpecificationが追加されている
When pulumi upコマンドを実行する
Then デプロイが正常に完了する
And LaunchTemplateの新バージョンが作成される
And 予期しないリソース変更が発生しない
```

### 6.4 AC-004: AWSコンソールでの設定確認
```gherkin
Given Pulumiデプロイが完了している
When AWSコンソールでLaunchTemplateの設定を確認する
Then agent-lt（x86_64用）にcreditSpecification.cpuCredits="unlimited"が設定されている
And agent-lt-arm（ARM64用）にcreditSpecification.cpuCredits="unlimited"が設定されている
```

### 6.5 AC-005: SpotFleetインスタンスへの適用確認（オプション）
```gherkin
Given 新しいLaunchTemplateバージョンが作成されている
When SpotFleetから新しいインスタンスが起動される
Then 新インスタンスにUnlimited設定が適用されている
And CloudWatchでCPUSurplusCreditBalanceメトリクスが確認できる
```

### 6.6 AC-006: ドキュメント更新確認
```gherkin
Given 実装が完了している
When docs/architecture/infrastructure.mdを確認する
Then CPUクレジットUnlimited設定の説明が追記されている
And コスト影響に関する注意事項が記載されている
```

### 6.7 AC-007: 既存機能への影響なし確認
```gherkin
Given creditSpecification設定が追加されている
When pulumi previewで変更内容を確認する
Then creditSpecification以外の設定変更がない
And セキュリティグループ、IAMロール、EBS設定に変更がない
```

---

## 7. スコープ外

### 7.1 今回のスコープ外とする事項
| 項目 | 理由 |
|------|------|
| SSMパラメータによる動的切り替え | 初期実装では固定値で十分。将来的な拡張候補として検討 |
| 既存インスタンスの即時更新 | ローリング更新で段階的に適用するため不要 |
| CloudWatch Billingアラートの新規設定 | 既存の監視体制を利用。追加設定は別Issue |
| ECS Fargateエージェントへの影響 | ECS FargateはCPUクレジットの概念がないため対象外 |
| t3/t4g以外のインスタンスタイプ対応 | 現在使用していないため対象外 |

### 7.2 将来的な拡張候補
| 項目 | 概要 |
|------|------|
| SSMパラメータ化 | `unlimited`/`standard`をSSMパラメータで切り替え可能にする |
| コスト最適化ダッシュボード | CPUクレジット追加料金の可視化ダッシュボード |
| 自動切り替え機能 | コストしきい値に基づく自動的なモード切り替え |

---

## 8. 用語定義

| 用語 | 定義 |
|------|------|
| CPUクレジット | バースタブルインスタンス（T系）でCPU使用率がベースラインを超える際に消費されるリソース単位 |
| Standard モード | CPUクレジット枯渇時にベースラインCPU性能に制限されるモード（デフォルト） |
| Unlimited モード | CPUクレジット枯渇後も高いCPU使用率を維持できるモード。超過分は追加課金 |
| スロットリング | CPUクレジット枯渇によりCPU性能がベースラインに制限される現象 |
| LaunchTemplate | EC2インスタンス起動時の設定テンプレート |
| SpotFleet | Spot Instanceを管理するAWSサービス |
| ローリング更新 | 既存インスタンスを段階的に新設定のインスタンスに置き換える更新方式 |

---

## 9. 参考資料

### 9.1 AWS公式ドキュメント
- [Unlimited Mode for Burstable Performance Instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-credits-baseline-concepts.html)
- [CPU Credits and Baseline Utilization](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances.html)

### 9.2 Pulumi公式ドキュメント
- [aws.ec2.LaunchTemplate](https://www.pulumi.com/registry/packages/aws/api-docs/ec2/launchtemplate/)
- [creditSpecification property](https://www.pulumi.com/registry/packages/aws/api-docs/ec2/launchtemplate/#creditspecification)

### 9.3 プロジェクト内ドキュメント
- [CLAUDE.md](../../CLAUDE.md) - プロジェクトガイダンス
- [pulumi/CONTRIBUTION.md](../../../pulumi/CONTRIBUTION.md) - Pulumi開発規約
- [docs/architecture/infrastructure.md](../../../docs/architecture/infrastructure.md) - インフラ構成説明

---

## 10. 変更履歴

| バージョン | 日付 | 変更者 | 変更内容 |
|------------|------|--------|----------|
| 1.0 | 2025-01-20 | AI Workflow | 初版作成 |
