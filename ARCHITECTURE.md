# Platform Engineering アーキテクチャ設計思想

このドキュメントは、本プロジェクトが目指すPlatform Engineeringの理想的な設計思想と実装アプローチを記載します。

> **📌 重要**: このドキュメントは「目指すべき姿」を示しています。現在、段階的に実装を進めており、すべての機能が完全に実現されているわけではありません。しかし、この設計思想に基づいて継続的に改善を行っています。

## 📋 目次

- [Platform Engineering とは](#platform-engineering-とは)
- [アーキテクチャ全体像](#アーキテクチャ全体像)
- [各コンポーネントの責務](#各コンポーネントの責務)
- [ツール選定の理由](#ツール選定の理由)
- [設計原則](#設計原則)
- [実装のベストプラクティス](#実装のベストプラクティス)

## Platform Engineering とは

### 一言での定義
**「開発者が開発に専念できるように、インフラや運用を自動化・セルフサービス化する取り組み」**

### 従来の問題と解決
```
【従来】
開発者「サーバー欲しい」→ 運用チーム「3日後に用意します」→ 待機...
開発者「デプロイして」→ 運用チーム「手順書に従って...」→ ミス発生

【Platform Engineering】
開発者「サーバー欲しい」→ セルフサービスポータルでクリック → 5分で自動構築
開発者「デプロイして」→ git push → 自動デプロイ完了
```

### 3つの本質
1. **セルフサービス化**: 開発者が自分で必要なものを即座に用意できる
2. **自動化の徹底**: 手作業ゼロ、ミスが起きない仕組み
3. **標準化**: 誰でも同じ方法で同じ結果、属人性の排除

## アーキテクチャ全体像

### 階層構造と責務分担

```
┌─────────────────────────────────────────┐
│         Jenkins (統括司令塔)              │
│  ・WHO & WHEN (誰が・いつ)               │
│  ・実行トリガー                           │
│  ・ログ集約・可視化                       │
│  ・権限管理・承認フロー                   │
└──────────────┬──────────────────────────┘
               ↓ キック
┌─────────────────────────────────────────┐
│      Ansible (オーケストレーター)         │
│  ・HOW (どうやって)                      │
│  ・処理順序制御                           │
│  ・エラーハンドリング                     │
│  ・条件分岐・リトライ                     │
└──────────────┬──────────────────────────┘
               ↓ 実行指示
┌─────────────────────────────────────────┐
│       Pulumi (インフラ構築者)             │
│  ・WHAT (何を)                          │
│  ・リソースプロビジョニング               │
│  ・状態管理                               │
│  ・型安全な定義                           │
└─────────────────────────────────────────┘

    ↑↓ パラメータ参照 (全層から参照)
    
┌─────────────────────────────────────────┐
│   SSM Parameter Store (設定の中央管理)    │
│  ・Single Source of Truth               │
│  ・環境別パラメータ管理                   │
│  ・暗号化・監査ログ                       │
└─────────────────────────────────────────┘
```

## 各コンポーネントの責務

### Jenkins - 統括司令塔
**役割**: WHO & WHEN (誰が・いつ実行するか)

```groovy
// 実行権限の制御
pipeline {
    parameters {
        choice(name: 'ENVIRONMENT', choices: ['dev', 'staging', 'prod'])
    }
    stages {
        stage('Deploy') {
            steps {
                // Ansibleをキック
                ansiblePlaybook playbook: 'deploy.yml'
            }
        }
    }
}
```

**主要機能**:
- セルフサービスポータル（開発者向けUI）
- 実行ログの永続化と可視化
- 承認フロー・権限管理
- スケジュール実行・イベントトリガー

### Ansible - オーケストレーター
**役割**: HOW (どうやって実行するか)

```yaml
# 処理フローの制御
- name: デプロイメントフロー
  block:
    - include_role: pulumi_helper    # Pulumi実行
    - include_role: health_check     # ヘルスチェック
  rescue:
    - include_role: rollback         # エラー時ロールバック
  always:
    - include_role: notification     # 結果通知
```

**主要機能**:
- 複雑な処理フローの制御
- エラーハンドリング・リトライ
- 条件分岐・並列実行
- 冪等性の保証

### Pulumi - インフラ構築者
**役割**: WHAT (何を構築するか)

```typescript
// TypeScriptで型安全にインフラを定義
const instance = new aws.ec2.Instance("web-server", {
    instanceType: config.require("instanceType"),
    ami: aws.ec2.getAmi({
        mostRecent: true,
        filters: [{ name: "name", values: ["ubuntu/images/*"] }]
    }).then(ami => ami.id),
    tags: {
        Name: `${projectName}-${stack}`,
        Environment: stack
    }
});
```

**主要機能**:
- クラウドリソースのプロビジョニング
- インフラ状態の管理（State管理）
- 型安全な設定（TypeScript）
- マルチクラウド対応

### SSM Parameter Store - パラメータ中央管理
**役割**: Single Source of Truth

```
/jenkins-infra/
  ├── common/           # 共通設定
  │   ├── github/
  │   └── slack/
  ├── dev/             # 開発環境
  │   ├── jenkins/
  │   └── database/
  ├── staging/         # ステージング環境
  └── prod/            # 本番環境
```

**主要機能**:
- パラメータの一元管理（2重管理の排除）
- 環境別設定の管理
- SecureStringによる暗号化
- 変更履歴・監査ログ

## ツール選定の理由

### なぜ Jenkins？
- **既存資産の活用**: 多くの企業で既に導入済み
- **究極の柔軟性**: 2000以上のプラグイン、何でも連携可能
- **エンタープライズ対応**: オンプレミス、複雑な承認フロー、レガシーシステム連携
- **成熟度**: 10年以上の実績、膨大なナレッジベース

### なぜ Pulumi？
- **真のプログラミング言語**: TypeScript/Python/Go等で記述可能
- **型安全**: コンパイル時にエラー検出、IDE補完
- **テスト可能**: 通常のユニットテストが書ける
- **抽象化が自然**: クラスやモジュールで再利用可能なコンポーネント化

### なぜ Ansible？
- **デファクトスタンダード**: チーム全員が読み書き可能
- **エージェントレス**: 追加ソフトウェア不要
- **豊富なモジュール**: AWS、Azure、GCP等あらゆるサービスに対応
- **オーケストレーション特化**: 複雑な処理フローを簡潔に記述

### なぜ SSM Parameter Store？
- **AWSネイティブ**: 追加インフラ不要
- **統合が容易**: IAMロールで権限管理
- **コスト効率**: 無料枠で十分（スタンダード）
- **暗号化標準対応**: KMS統合でセキュア

## 設計原則

### 1. Single Source of Truth
```
パラメータ → SSM Parameter Store
インフラ定義 → Pulumi (Git管理)
ジョブ定義 → Job DSL (Git管理)
```

### 2. Infrastructure as Code / Everything as Code
```groovy
// ジョブもコード
pipelineJob('deploy-app') { ... }
```
```typescript
// インフラもコード
new aws.ec2.Instance("app", { ... });
```
```yaml
# 設定もコード
jenkins:
  systemMessage: "Managed by JCasC"
```

### 3. Self-Healing / GitOps
- コードから削除 = リソースも自動削除
- Git = 真実の源
- 差分検出と自動修正

### 4. 疎結合アーキテクチャ
```bash
Jenkins → Ansible : ansible-playbook コマンド
Ansible → Pulumi : pulumi up コマンド
各層 → SSM : aws ssm get-parameter
```

### 5. 段階的自動化
```
レベル1: 手動実行（Jenkinsボタンクリック）
レベル2: パラメータ化（選択式実行）
レベル3: イベント駆動（git push連動）
レベル4: 完全自動化（自己修復）
```

## 実装のベストプラクティス

### Platform Engineering の5原則

#### 1. ✅ Internal Developer Platform (IDP)
Jenkinsがセルフサービスポータルとして機能し、開発者は必要なリソースを自分で作成・管理できる。

#### 2. ✅ Everything as Code
インフラ（Pulumi）、設定（JCasC）、ジョブ（Job DSL）、全てをコードとして管理。

#### 3. ✅ GitOps
Gitが唯一の真実の源。全ての変更はPRレビューを経て反映。

#### 4. ✅ Self-Healing
Job DSLによる自動削除、Pulumiによるdrift修正、JCasCによる設定復元。

#### 5. ✅ Multi-Environment
common/dev/staging/prodを明確に分離し、環境間のプロモーションを自動化。

### 運用フロー例

```
1. 開発者がインフラ変更をPR作成
   ↓
2. コードレビュー・承認
   ↓
3. マージ → Jenkins Webhook起動
   ↓
4. Jenkins: 権限確認、ログ開始
   ↓
5. Ansible: 処理フロー制御
   ↓
6. Pulumi: インフラ更新
   ↓
7. SSM: パラメータ参照・更新
   ↓
8. Jenkins: 結果通知、ログ保存
```

### セキュリティ考慮事項

1. **最小権限の原則**: 各コンポーネントは必要最小限の権限のみ
2. **暗号化**: SSM SecureString、転送時暗号化
3. **監査ログ**: 全操作をCloudTrail、Jenkins Audit Logで記録
4. **承認フロー**: 本番環境は承認必須
5. **シークレット管理**: ハードコーディング禁止、SSM/Secrets Manager使用

## まとめ

このアーキテクチャが目指すもの:

- **開発者の生産性向上**: セルフサービスで待ち時間ゼロ
- **運用の安定性**: 自動化によるヒューマンエラー排除
- **ガバナンス強化**: 全変更の追跡可能性
- **コスト最適化**: リソースの効率的な利用
- **スケーラビリティ**: 組織の成長に応じた拡張が容易

「開発者のための自動販売機」を作ることで、本来のビジネス価値創出に集中できる環境を目指します。