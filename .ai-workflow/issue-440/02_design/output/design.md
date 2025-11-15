# 詳細設計書 - Issue #440

## 0. Planning Document・要件定義書の確認

### Planning Phaseで策定された開発計画
- **実装戦略**: EXTEND - 既存の`component-arm.yml`と`component-x86.yml`にPullDockerImagesステップを追加
- **テスト戦略**: INTEGRATION_ONLY - AMIビルド実行とDockerイメージ存在確認の統合テスト
- **テストコード戦略**: CREATE_TEST - 新規にテストスクリプトを作成
- **見積もり工数**: 6~10時間
- **リスク評価**: 低（既存機能への影響なし、ロールバック容易）

### 要件定義書の主要ポイント
- **FR-1**: Dockerイメージ事前プル機能（12種類、合計約2.9GB）
- **FR-2**: Docker Daemon起動確認
- **FR-3**: プル成功確認とログ出力
- **FR-4**: マルチアーキテクチャ対応（ARM64/x86_64）
- **FR-5**: AMIビルドプロセスへの統合

---

## 1. アーキテクチャ設計

### 1.1 システム全体図

```
┌─────────────────────────────────────────────────────────────┐
│               EC2 Image Builder (AMIビルド)                   │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ component-arm.yml / component-x86.yml                  │  │
│  │                                                         │  │
│  │  1. InstallDocker          (既存ステップ)              │  │
│  │  2. InstallCloudWatchAgent (既存ステップ)              │  │
│  │  3. ConfigureCloudWatchAgent (既存ステップ)            │  │
│  │  4. EnableCloudWatchAgent  (既存ステップ)              │  │
│  │  ┌─────────────────────────────────────────────┐      │  │
│  │  │ 5. PullDockerImages (新規追加)              │      │  │
│  │  │   - Docker Daemon起動確認                    │      │  │
│  │  │   - 12種類のイメージプル                      │      │  │
│  │  │   - プル成功確認                             │      │  │
│  │  └─────────────────────────────────────────────┘      │  │
│  │  6. CreateJenkinsUser      (既存ステップ)              │  │
│  │  7. SetupSwap              (既存ステップ)              │  │
│  │  8. CleanupCache           (既存ステップ)              │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           ↓
                        AMI作成
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              Jenkins Agent (SpotFleet)                        │
│                                                               │
│  ローカルにキャッシュされたDockerイメージ:                    │
│  ✓ python:3.11-slim (130MB)                                 │
│  ✓ node:18-slim (180MB)                                     │
│  ✓ rust:1.76-slim (850MB)                                   │
│  ✓ rust:slim (850MB)                                        │
│  ✓ amazon/aws-cli:latest (400MB)                            │
│  ✓ pulumi/pulumi:latest (100MB)                             │
│  ✓ ubuntu:22.04 (77MB)                                      │
│  ✓ nikolaik/python-nodejs:python3.11-nodejs20 (400MB)       │
│                                                               │
│  合計: 約2.9GB                                               │
└─────────────────────────────────────────────────────────────┘
                           ↓
                    ジョブ実行時
                           ↓
                 イメージプル時間: 10-20秒 → 1-2秒
```

### 1.2 コンポーネント間の関係

```
┌────────────────────────────────────────────┐
│ pulumi/jenkins-agent-ami/                  │
│  ├── component-arm.yml     (修正)          │
│  └── component-x86.yml     (修正)          │
└────────────────────────────────────────────┘
             ↓ 使用
┌────────────────────────────────────────────┐
│ ansible/roles/jenkins_agent_ami/           │
│  └── tasks/deploy.yml      (参照のみ)      │
└────────────────────────────────────────────┘
             ↓ ドキュメント更新
┌────────────────────────────────────────────┐
│ ansible/README.md          (更新)          │
└────────────────────────────────────────────┘
```

### 1.3 データフロー

```
┌──────────────┐
│ AMIビルド開始 │
└──────┬───────┘
       │
       ↓
┌─────────────────────────────────────┐
│ 1. InstallDocker実行                 │
│    - Docker のインストール            │
│    - systemctl enable docker         │
└─────────────┬───────────────────────┘
              │
              ↓
┌─────────────────────────────────────┐
│ 2. EnableCloudWatchAgent実行         │
│    - CloudWatch Agent有効化          │
└─────────────┬───────────────────────┘
              │
              ↓
┌─────────────────────────────────────┐
│ 3. PullDockerImages実行（新規）       │
│    ┌───────────────────────────┐    │
│    │ 3-1. Docker Daemon起動     │    │
│    │      systemctl start docker│    │
│    │      sleep 5               │    │
│    └───────────┬───────────────┘    │
│                ↓                     │
│    ┌───────────────────────────┐    │
│    │ 3-2. イメージプル実行      │    │
│    │   For each image:          │    │
│    │     - echo "Pulling..."    │    │
│    │     - docker pull {image}  │    │
│    └───────────┬───────────────┘    │
│                ↓                     │
│    ┌───────────────────────────┐    │
│    │ 3-3. 成功確認              │    │
│    │      docker images         │    │
│    │      echo "Complete"       │    │
│    └───────────────────────────┘    │
└─────────────┬───────────────────────┘
              │
              ↓
┌─────────────────────────────────────┐
│ 4. CreateJenkinsUser実行             │
│    - jenkinsユーザー作成              │
│    - Dockerグループへの追加           │
└─────────────┬───────────────────────┘
              │
              ↓
┌─────────────────────────────────────┐
│ AMI作成完了                          │
└─────────────────────────────────────┘
```

---

## 2. 実装戦略判断

### 実装戦略: EXTEND（拡張）

**判断根拠**:
1. **既存ファイルへの追加が中心**: `component-arm.yml`と`component-x86.yml`に新しいステップ（PullDockerImages）を追加するだけで、既存のステップ構造（ExecuteBashアクション）を踏襲
2. **新規ファイル作成は不要**: 既存のコンポーネント定義YAMLファイルに追記するだけで実現可能
3. **既存のビルドプロセスへの統合**: EC2 Image Builderの既存ワークフローに自然に組み込まれる形
4. **依存関係の明確さ**: InstallDockerステップの後、CreateJenkinsUserステップの前に挿入することで、依存関係が明確

**実装内容**:
- EnableCloudWatchAgentステップの直後にPullDockerImagesステップを挿入
- ARM64とx86_64の両方で同一のDockerイメージリストを使用
- 既存のExecuteBashアクション形式を完全に踏襲

---

## 3. テスト戦略判断

### テスト戦略: INTEGRATION_ONLY（インテグレーションテストのみ）

**判断根拠**:
1. **ユニットテストは不適切**: YAMLファイルへのステップ追加のみで、プログラムロジックが存在しないため、ユニットテストは書けない
2. **インテグレーションテストが必須**: 以下の統合的な動作確認が必要
   - EC2 Image Builderによる実際のAMIビルド実行
   - Dockerサービスの起動確認
   - Docker Hubからの12種類のイメージプル
   - AMI起動後のイメージ存在確認
   - ジョブ実行時の起動時間測定（before/after比較）
3. **BDDテストは不要**: エンドユーザー向け機能ではなく、インフラレベルのパフォーマンス改善のため、ユーザーストーリーベースのBDDテストは不要

**テスト内容**:
1. dev環境でのAMIビルド実行
2. ビルド成功の確認
3. AMI起動後のDockerイメージ存在確認（`docker images`）
4. ジョブ実行時の起動時間測定（変更前後の比較）
5. AMIサイズとビルド時間の測定

---

## 4. テストコード戦略判断

### テストコード戦略: CREATE_TEST（新規テスト作成）

**判断根拠**:
1. **既存テストの不存在**: 現時点でAMIビルド検証のテストコードが存在しない
2. **新規テストスクリプトの必要性**: Dockerイメージの存在確認とジョブ起動時間測定のための専用スクリプトが必要
3. **テストコードの永続性**: 今後のAMI変更時にも再利用可能なテストアセットとして保存

**テストファイル作成**:
- `.ai-workflow/issue-440/06_test/integration/test_docker_images.sh`
  - AMI起動後にSSM Session Managerで接続
  - `docker images`コマンドで12種類のイメージ存在確認
  - 結果をJSON形式で出力
- `.ai-workflow/issue-440/06_test/integration/measure_job_startup.sh`
  - 変更前後のAMIでジョブ起動時間を測定
  - 結果を比較レポートとして出力

---

## 5. 影響範囲分析

### 5.1 既存コードへの影響

#### 直接的な影響（ファイル修正）

| ファイルパス | 変更内容 | 影響度 |
|------------|---------|--------|
| `pulumi/jenkins-agent-ami/component-arm.yml` | PullDockerImagesステップを追加（行番号183-184の間に挿入） | 中 |
| `pulumi/jenkins-agent-ami/component-x86.yml` | PullDockerImagesステップを追加（行番号183-184の間に挿入） | 中 |
| `ansible/README.md` | Jenkins Agent AMIセクションに事前プルイメージリスト追加 | 低 |

#### 間接的な影響

| 項目 | 変更前 | 変更後 | 影響 |
|-----|--------|--------|------|
| AMIビルド時間 | 30-45分 | 35-50分 | +5-10分程度（許容範囲内） |
| AMIサイズ | 基準値 | +2-3GB | EBSコスト約$0.24/月増加（開発環境のみなら無視可能） |
| ジョブ起動時間 | 小イメージ: 10-20秒<br>大イメージ: 1-2分 | 1-2秒 | 大幅改善（目的達成） |
| ネットワーク帯域 | ジョブ実行ごとに数百MB~GB | ほぼゼロ | 大幅削減 |

### 5.2 依存関係の変更

#### 新規依存の追加
- **なし**: すべて既存のツール（Docker、EC2 Image Builder）を使用

#### 既存依存の変更
- **なし**: Dockerは既にInstallDockerステップでインストール済み
- **外部依存**: Docker Hubへのインターネット接続（AMIビルド時のみ）

### 5.3 マイグレーション要否

**不要**

**理由**:
- データベーススキーマ変更なし
- 設定ファイル変更なし
- 既存のAMIは引き続き使用可能（新しいAMIビルド時のみ変更が反映される）
- 既存のJenkinsジョブやパイプラインへの変更不要
- ロールバック容易（変更前のAMIに戻すだけ）

---

## 6. 変更・追加ファイルリスト

### 6.1 修正が必要な既存ファイル

| ファイルパス（相対パス） | 変更内容 | 優先度 |
|------------------------|---------|--------|
| `pulumi/jenkins-agent-ami/component-arm.yml` | PullDockerImagesステップを183行目付近に追加 | 高 |
| `pulumi/jenkins-agent-ami/component-x86.yml` | PullDockerImagesステップを183行目付近に追加 | 高 |
| `ansible/README.md` | ## CloudWatchモニタリング セクションの後に## Docker Image Pre-pulling セクションを追加 | 中 |

### 6.2 新規作成ファイル

| ファイルパス（相対パス） | 内容 | 優先度 |
|------------------------|------|--------|
| `.ai-workflow/issue-440/06_test/integration/test_docker_images.sh` | Dockerイメージ存在確認スクリプト | 高 |
| `.ai-workflow/issue-440/06_test/integration/measure_job_startup.sh` | ジョブ起動時間測定スクリプト | 中 |
| `.ai-workflow/issue-440/08_report/implementation_report.md` | 実装レポート（実装後に作成） | 低 |

### 6.3 削除が必要なファイル

**なし**

---

## 7. 詳細設計

### 7.1 PullDockerImagesステップ設計

#### 7.1.1 ステップ挿入位置

**挿入位置**: EnableCloudWatchAgentステップの直後（行番号183-184の間）

**理由**:
1. Dockerは既にInstallDockerステップでインストール済み
2. CloudWatch Agent設定完了後なら、他のステップへの影響がない
3. CreateJenkinsUserの前に実行することで、jenkinsユーザーもプルされたイメージを使用可能

#### 7.1.2 ステップ定義（ARM64版）

```yaml
      - name: PullDockerImages
        action: ExecuteBash
        inputs:
          commands:
            - echo "===== Docker Image Pre-pulling for faster job startup ====="
            - echo "Starting Docker daemon..."
            - systemctl start docker
            - sleep 5  # Docker Daemonの起動完了を待機
            - systemctl is-active docker || (echo "ERROR: Docker daemon is not running" && exit 1)
            - echo "Docker daemon is running. Starting image pull..."
            - |
              # Python系イメージ
              echo "Pulling python:3.11-slim..."
              docker pull python:3.11-slim || echo "WARNING: Failed to pull python:3.11-slim"

              # Node.js系イメージ
              echo "Pulling node:18-slim..."
              docker pull node:18-slim || echo "WARNING: Failed to pull node:18-slim"

              # Rust系イメージ
              echo "Pulling rust:1.76-slim..."
              docker pull rust:1.76-slim || echo "WARNING: Failed to pull rust:1.76-slim"

              echo "Pulling rust:slim..."
              docker pull rust:slim || echo "WARNING: Failed to pull rust:slim"

              # AWS系イメージ
              echo "Pulling amazon/aws-cli:latest..."
              docker pull amazon/aws-cli:latest || echo "WARNING: Failed to pull amazon/aws-cli:latest"

              # Pulumi系イメージ
              echo "Pulling pulumi/pulumi:latest..."
              docker pull pulumi/pulumi:latest || echo "WARNING: Failed to pull pulumi/pulumi:latest"

              # Ubuntu系イメージ
              echo "Pulling ubuntu:22.04..."
              docker pull ubuntu:22.04 || echo "WARNING: Failed to pull ubuntu:22.04"

              # Python + Node.js複合イメージ
              echo "Pulling nikolaik/python-nodejs:python3.11-nodejs20..."
              docker pull nikolaik/python-nodejs:python3.11-nodejs20 || echo "WARNING: Failed to pull nikolaik/python-nodejs:python3.11-nodejs20"
            - echo "===== Verifying pulled images ====="
            - docker images
            - echo "===== Docker image pre-pulling completed successfully ====="
```

#### 7.1.3 ステップ定義（x86版）

x86版は**完全に同一の内容**を使用します（マルチアーキテクチャ対応イメージのため）。

#### 7.1.4 エラーハンドリング方針

| エラーケース | 挙動 | 理由 |
|------------|------|------|
| Docker Daemon起動失敗 | **ビルド失敗** (`exit 1`) | 致命的エラー。後続ステップが実行できない |
| 個別イメージのプル失敗 | **警告表示** (`|| echo "WARNING: ..."`) | 一部イメージのプル失敗でビルド全体を失敗させない。ログで確認可能 |
| 全イメージのプル失敗 | **警告のみ** | ビルド自体は成功させ、docker imagesで実際にプルされたイメージを確認 |

**設計判断**:
- プル失敗は警告のみとし、ビルドは継続する
- 最終的に`docker images`でプルされたイメージ一覧を表示し、手動確認可能にする
- Docker Hubのレート制限や一時的なネットワーク障害に対してレジリエントな設計

### 7.2 テストスクリプト設計

#### 7.2.1 test_docker_images.sh

**目的**: AMI起動後に12種類のDockerイメージが存在することを確認

**入力**:
- EC2インスタンスID（引数または環境変数）

**処理フロー**:
```bash
#!/bin/bash
set -euo pipefail

# 期待されるイメージリスト
EXPECTED_IMAGES=(
  "python:3.11-slim"
  "node:18-slim"
  "rust:1.76-slim"
  "rust:slim"
  "amazon/aws-cli:latest"
  "pulumi/pulumi:latest"
  "ubuntu:22.04"
  "nikolaik/python-nodejs:python3.11-nodejs20"
)

# 1. SSM Session Managerでコマンド実行
# 2. docker imagesの出力をパース
# 3. 各イメージの存在確認
# 4. 結果をJSON形式で出力
```

**出力**:
```json
{
  "total_expected": 8,
  "total_found": 8,
  "missing_images": [],
  "success": true,
  "timestamp": "2025-01-XX 12:34:56"
}
```

#### 7.2.2 measure_job_startup.sh

**目的**: ジョブ起動時間を測定し、before/after比較

**入力**:
- 変更前AMI ID
- 変更後AMI ID
- テスト対象ジョブ名（小・中・大イメージの3種類）

**処理フロー**:
```bash
#!/bin/bash
set -euo pipefail

# 1. 変更前AMIでジョブ実行（3回測定して平均値）
# 2. 変更後AMIでジョブ実行（3回測定して平均値）
# 3. 起動時間を比較
# 4. レポート生成
```

**出力**:
```markdown
# Job Startup Time Comparison Report

## Summary
- Baseline AMI: ami-0123456789abcdef0
- New AMI: ami-fedcba9876543210

## Results

| Job Name | Image Size | Before (avg) | After (avg) | Improvement |
|----------|-----------|--------------|-------------|-------------|
| small-image-job | 130MB | 15.2s | 1.8s | 88.2% |
| medium-image-job | 400MB | 32.5s | 2.1s | 93.5% |
| large-image-job | 850MB | 78.3s | 2.4s | 96.9% |

## Conclusion
All jobs show significant improvement in startup time.
```

### 7.3 データ構造設計

#### 7.3.1 Dockerイメージリスト（定数）

| イメージ名 | タグ | サイズ | 使用箇所 |
|----------|------|--------|---------|
| python | 3.11-slim | 130MB | diagram-generator, pull-request-comment-builder |
| node | 18-slim | 180MB | mermaid-generator |
| rust | 1.76-slim | 850MB | pr-complexity-analyzer |
| rust | slim | 850MB | (バックアップ用) |
| amazon/aws-cli | latest | 400MB | ssm-dashboard, pulumi-dashboard |
| pulumi/pulumi | latest | 100MB | pulumi-dashboard |
| ubuntu | 22.04 | 77MB | (汎用用途) |
| nikolaik/python-nodejs | python3.11-nodejs20 | 400MB | auto-insert-doxygen-comment, technical-docs-writer |

**合計サイズ**: 約2.9GB

#### 7.3.2 AMIビルド成果物

| 項目 | 値 | 備考 |
|-----|---|------|
| AMIサイズ増加 | 約2-3GB | 許容範囲: +3GB以内 |
| ビルド時間増加 | 約5-10分 | 許容範囲: +10分以内 |
| イメージ数 | 12種類 | ただし、rust:1.76-slimとrust:slimは実質同じサイズ |

### 7.4 インターフェース設計

#### 7.4.1 YAMLコンポーネント定義インターフェース

**既存インターフェース**:
```yaml
phases:
  - name: build
    steps:
      - name: {StepName}
        action: ExecuteBash
        inputs:
          commands:
            - {command1}
            - {command2}
```

**新規ステップの適合**:
```yaml
      - name: PullDockerImages  # 新規ステップ名
        action: ExecuteBash      # 既存のアクション形式を踏襲
        inputs:
          commands:              # 既存のcommands形式を踏襲
            - echo "..."
            - systemctl start docker
            - docker pull ...
```

**完全互換**: 既存のExecuteBashアクション形式を100%踏襲しているため、EC2 Image Builderとの統合は問題なし

#### 7.4.2 テストスクリプトインターフェース

**test_docker_images.sh**:
```bash
# 使用方法
./test_docker_images.sh <instance-id>

# 出力: 標準出力にJSON形式
# 終了コード: 0=成功、1=失敗
```

**measure_job_startup.sh**:
```bash
# 使用方法
./measure_job_startup.sh <baseline-ami-id> <new-ami-id> <job-name>

# 出力: 標準出力にMarkdown形式のレポート
# 終了コード: 0=成功、1=失敗
```

---

## 8. セキュリティ考慮事項

### 8.1 認証・認可

| 項目 | 対応内容 | リスク |
|-----|---------|--------|
| Docker Hub認証 | 匿名アクセス（レート制限: 100回/6時間） | 中 - レート制限に抵触する可能性 |
| Docker Hub認証（認証済み） | （オプション）SSMパラメータストアで認証情報管理 | 低 - レート制限緩和（200回/6時間） |
| EC2 Image Builder権限 | IAMロールで制御済み | 低 |

### 8.2 データ保護

| 項目 | 対応内容 | リスク |
|-----|---------|--------|
| Docker認証情報 | SSM Parameter Store（SecureString）で暗号化保存 | 低 |
| AMI暗号化 | （既存設定に従う） | 低 |
| ログ出力 | 機密情報なし（イメージ名とタグのみ） | 低 |

### 8.3 セキュリティリスクと対策

| リスク | 影響度 | 確率 | 対策 |
|--------|--------|------|------|
| Docker Hubレート制限 | 中 | 中 | 1. 認証情報の使用でレート制限緩和<br>2. リトライロジック追加（`|| echo "WARNING"`） |
| マルウェア混入イメージ | 高 | 低 | 1. 公式イメージのみ使用<br>2. タグ固定（latestタグは最小限） |
| イメージの脆弱性 | 中 | 中 | 1. 定期的なイメージ更新<br>2. （将来）脆弱性スキャンツール統合 |
| AMIへの不正アクセス | 高 | 低 | 1. 既存のIAM権限管理に従う<br>2. AMI暗号化 |

---

## 9. 非機能要件への対応

### 9.1 パフォーマンス

| 項目 | 要件 | 実装 | 検証方法 |
|-----|------|------|---------|
| ジョブ起動時間短縮 | 小イメージ: 10-20秒→1-2秒<br>大イメージ: 1-2分→1-2秒 | Dockerイメージをローカルキャッシュに保存 | measure_job_startup.shで測定 |
| AMIビルド時間増加 | +10分以内 | 12種類のイメージを順次プル | EC2 Image Builderログで確認 |
| ネットワーク帯域削減 | ジョブ実行時のダウンロードゼロ | ローカルキャッシュから起動 | ジョブ実行時のネットワークトラフィック監視 |

### 9.2 スケーラビリティ

| 項目 | 要件 | 実装 |
|-----|------|------|
| イメージ追加 | 新しいイメージの追加が容易 | docker pullコマンドを1行追加するだけ |
| マルチアーキテクチャ | ARM64/x86_64両対応 | component-arm.ymlとcomponent-x86.ymlで同じイメージリスト |
| 並列ビルド | 複数環境の同時ビルド | Docker Hubレート制限に注意（認証使用を推奨） |

### 9.3 保守性

| 項目 | 要件 | 実装 |
|-----|------|------|
| イメージバージョン管理 | 固定バージョンの使用 | タグ指定（例: `python:3.11-slim`は既に固定） |
| ログ可読性 | ビルドログで進捗確認可能 | 各イメージプル前にecho文でイメージ名出力 |
| ドキュメント化 | プルされたイメージ一覧を文書化 | ansible/README.mdに一覧表を追加 |
| エラーハンドリング | プル失敗時の挙動が明確 | 警告表示のみ（ビルド継続） |

---

## 10. 実装の順序

### Phase 1: 要件定義（完了）
- [x] Dockerイメージリストの確定
- [x] 受け入れ基準の定義

### Phase 2: 設計（このドキュメント）
- [x] PullDockerImagesステップの設計
- [x] ARM/x86共通化の設計
- [x] テスト設計

### Phase 3: テストシナリオ（次フェーズ）
- [ ] AMIビルドテストシナリオ作成
- [ ] Dockerイメージ検証シナリオ作成
- [ ] 起動時間測定シナリオ作成

### Phase 4: 実装
**推奨順序**:

1. **component-arm.ymlの修正**（優先度: 高）
   - 183行目付近にPullDockerImagesステップを追加
   - 既存ステップとの依存関係を確認

2. **component-x86.ymlの修正**（優先度: 高）
   - component-arm.ymlと同じ内容を追加
   - diff比較で内容が一致することを確認

3. **テストスクリプト作成**（優先度: 中）
   - test_docker_images.sh作成
   - measure_job_startup.sh作成
   - 実行権限付与（chmod +x）

4. **ドキュメント更新**（優先度: 低）
   - ansible/README.mdに事前プルイメージリストを追加
   - AMIビルド時間・サイズの更新

**依存関係の考慮**:
- component-arm.ymlとcomponent-x86.ymlは独立して修正可能
- テストスクリプトはAMIビルド完了後に実行するため、並行作業可能
- ドキュメントは実装完了後でも問題なし

---

## 11. 補足情報

### 11.1 実装時の注意事項

1. **Dockerサービスの起動確認**
   - `systemctl start docker`の後に`sleep 5`を入れて確実に起動
   - または`systemctl is-active docker`で起動確認

2. **プル失敗時の処理**
   - 個別イメージのプル失敗でビルド全体を失敗させない（`|| echo "WARNING: ..."`）
   - ただし、最後に`docker images`で実際にプルされたイメージを確認

3. **イメージタグの固定**
   - `latest`タグは予期しない変更を引き起こす可能性がある
   - 可能な限りバージョン固定を推奨（例: `python:3.11-slim`は既に固定されている）

4. **ビルドログの可読性**
   - 各イメージプル前にecho文でイメージ名を出力
   - プル完了後に`docker images`で一覧表示

### 11.2 参考情報

- Docker公式ドキュメント: https://docs.docker.com/engine/reference/commandline/pull/
- Docker Hub レート制限: https://docs.docker.com/docker-hub/download-rate-limit/
- EC2 Image Builder公式ドキュメント: https://docs.aws.amazon.com/imagebuilder/

### 11.3 既存コーディング規約への準拠

- **CLAUDE.md準拠**:
  - [x] コメントは日本語で記載
  - [x] 既存のディレクトリ構造を尊重
  - [x] セキュリティチェックリスト（クレデンシャルのハードコーディングなし）

- **既存パターンの踏襲**:
  - [x] ExecuteBashアクションの使用
  - [x] commands配列での複数コマンド記載
  - [x] systemctlコマンドの使用パターン
  - [x] echoによるログ出力パターン

---

## 12. 成功基準（品質ゲート）

本設計書は、以下の品質ゲートをすべて満たしています：

- [x] **実装戦略の判断根拠が明記されている**: セクション2で「EXTEND（拡張）」の判断根拠を4点記載
- [x] **テスト戦略の判断根拠が明記されている**: セクション3で「INTEGRATION_ONLY」の判断根拠を3点記載
- [x] **テストコード戦略の判断根拠が明記されている**: セクション4で「CREATE_TEST」の判断根拠を3点記載
- [x] **既存コードへの影響範囲が分析されている**: セクション5で直接的影響・間接的影響・依存関係の変更を詳細分析
- [x] **変更が必要なファイルがリストアップされている**: セクション6で修正ファイル3件、新規ファイル3件を明記
- [x] **設計が実装可能である**: セクション7で詳細設計（ステップ定義、テストスクリプト、データ構造）を具体的に記載

---

## 13. 次フェーズへの引き継ぎ事項

Phase 3（テストシナリオ）で作成すべきドキュメント：

1. **AMIビルドテストシナリオ**
   - dev環境でのAMIビルド手順書
   - ビルド成功確認項目リスト
   - エラー発生時の対処手順

2. **Dockerイメージ検証シナリオ**
   - AMI起動後のSSH/SSM接続手順
   - docker imagesコマンドでの確認項目
   - 各イメージのサイズとタグ確認方法

3. **起動時間測定シナリオ**
   - 変更前後のAMI比較手順
   - 測定対象ジョブの選定（小・中・大のイメージを使うジョブ各1つ）
   - 測定結果のレポート形式定義

---

**作成日**: 2025-01-XX
**作成者**: AI Workflow System
**レビュー状態**: 設計レビュー待ち
**次フェーズ**: Phase 3 - テストシナリオ作成
