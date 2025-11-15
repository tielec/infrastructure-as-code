# テストシナリオ - Issue #440

## 0. Planning Document・要件定義書・設計書の確認

### Planning Phaseで策定されたテスト戦略
- **テスト戦略**: INTEGRATION_ONLY - AMIビルド実行とDockerイメージ存在確認の統合テスト
- **テストコード戦略**: CREATE_TEST - 新規にテストスクリプトを作成
- **テスト工数見積もり**: 3~5時間（AMIビルド実行、イメージ検証、起動時間測定）

### 要件定義書の受け入れ基準
- **AC-1**: Dockerイメージ事前プル機能（AMIビルド成功、ログ記録）
- **AC-2**: Dockerイメージ存在確認（12種類すべて存在）
- **AC-3**: ジョブ起動時間短縮（10秒未満に短縮）
- **AC-4**: AMIサイズとビルド時間（+3GB以内、+10分以内）
- **AC-5**: マルチアーキテクチャ対応（ARM64/x86_64両対応）
- **AC-6**: エラーハンドリング（適切なエラー処理）
- **AC-7**: ドキュメント更新（README更新）

### 設計書のテスト設計
- dev環境でのAMIビルド実行
- AMI起動後のDockerイメージ存在確認
- ジョブ起動時間測定（変更前後の比較）
- AMIサイズとビルド時間の測定

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略
**INTEGRATION_ONLY** - インテグレーションテストのみ

**判断根拠**（Phase 2から引用）:
1. **ユニットテストは不適切**: YAMLファイルへのステップ追加のみで、プログラムロジックが存在しないため、ユニットテストは書けない
2. **インテグレーションテストが必須**: 以下の統合的な動作確認が必要
   - EC2 Image Builderによる実際のAMIビルド実行
   - Dockerサービスの起動確認
   - Docker Hubからの12種類のイメージプル
   - AMI起動後のイメージ存在確認
   - ジョブ実行時の起動時間測定（before/after比較）
3. **BDDテストは不要**: エンドユーザー向け機能ではなく、インフラレベルのパフォーマンス改善のため、ユーザーストーリーベースのBDDテストは不要

### 1.2 テスト対象の範囲

**テスト対象システム**:
- EC2 Image Builder（AMIビルドプロセス）
- component-arm.yml / component-x86.yml（PullDockerImagesステップ）
- Docker Daemon（イメージプル機能）
- Jenkins Agent（AMI起動後のジョブ実行）

**統合ポイント**:
1. EC2 Image Builder ↔ Docker Daemon（AMIビルド時のイメージプル）
2. AMI ↔ Jenkins Agent（AMI起動後のイメージ利用）
3. Docker Hub ↔ Docker Daemon（イメージダウンロード）

### 1.3 テストの目的

1. **機能検証**: 12種類のDockerイメージがAMIビルド時に正常にプルされること
2. **性能検証**: ジョブ起動時間が目標値（10秒未満）に短縮されること
3. **マルチアーキテクチャ検証**: ARM64/x86_64両方で正常に動作すること
4. **安定性検証**: Docker Hubレート制限やネットワーク障害に対するレジリエンスを確認
5. **コスト影響検証**: AMIサイズとビルド時間の増加が許容範囲内であること

---

## 2. Integrationテストシナリオ

### 2.1 AMIビルド統合テスト（ARM64）

**シナリオ名**: INT-001-AMI-Build-ARM64

**目的**: ARM64版のAMIビルドが正常に完了し、PullDockerImagesステップが成功すること

**前提条件**:
- Pulumi環境が構築済み（`pulumi/jenkins-agent-ami`）
- AWS認証情報が設定済み
- dev環境が利用可能
- `component-arm.yml`にPullDockerImagesステップが追加済み
- Docker Hubへのインターネット接続が可能

**テスト手順**:
1. dev環境に移動
   ```bash
   cd /tmp/ai-workflow-repos-42/infrastructure-as-code/ansible
   ```

2. AMIビルドPlaybookを実行（ARM64版）
   ```bash
   ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_agent_ami.yml \
     -e "target_environment=dev" \
     -e "architecture=arm64"
   ```

3. EC2 Image Builder コンソールでビルドログを確認
   - PullDockerImagesステップの実行ログを確認
   - 各イメージのプルログが出力されていることを確認

4. ビルド完了を待機（35-50分程度）

5. ビルド成功を確認
   - EC2 Image Builder の Status が "Available" になること
   - AMI ID を記録

**期待結果**:
- AMIビルドが成功すること（Status: Available）
- ビルドログに以下が記録されていること:
  - `===== Docker Image Pre-pulling for faster job startup =====`
  - `Docker daemon is running. Starting image pull...`
  - `Pulling python:3.11-slim...`（以下、12種類すべてのイメージ）
  - `===== Verifying pulled images =====`
  - `docker images` の出力（12種類のイメージリスト）
  - `===== Docker image pre-pulling completed successfully =====`
- エラーログに致命的なエラーが出力されていないこと
- ビルド時間が50分以内であること

**確認項目**:
- [ ] AMIビルドが成功している（Status: Available）
- [ ] PullDockerImagesステップが実行されている
- [ ] 12種類すべてのイメージのプルログが出力されている
- [ ] `docker images` で12種類のイメージが表示されている
- [ ] Docker Daemon起動確認ログが出力されている（`Docker daemon is running`）
- [ ] ビルド時間が50分以内である
- [ ] 致命的なエラーログがない

---

### 2.2 AMIビルド統合テスト（x86_64）

**シナリオ名**: INT-002-AMI-Build-x86

**目的**: x86_64版のAMIビルドが正常に完了し、PullDockerImagesステップが成功すること

**前提条件**:
- Pulumi環境が構築済み（`pulumi/jenkins-agent-ami`）
- AWS認証情報が設定済み
- dev環境が利用可能
- `component-x86.yml`にPullDockerImagesステップが追加済み
- Docker Hubへのインターネット接続が可能

**テスト手順**:
1. dev環境に移動
   ```bash
   cd /tmp/ai-workflow-repos-42/infrastructure-as-code/ansible
   ```

2. AMIビルドPlaybookを実行（x86_64版）
   ```bash
   ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_agent_ami.yml \
     -e "target_environment=dev" \
     -e "architecture=x86_64"
   ```

3. EC2 Image Builder コンソールでビルドログを確認
   - PullDockerImagesステップの実行ログを確認
   - 各イメージのプルログが出力されていることを確認

4. ビルド完了を待機（35-50分程度）

5. ビルド成功を確認
   - EC2 Image Builder の Status が "Available" になること
   - AMI ID を記録

**期待結果**:
- AMIビルドが成功すること（Status: Available）
- ビルドログにPullDockerImagesステップの実行ログが記録されていること（INT-001と同様）
- エラーログに致命的なエラーが出力されていないこと
- ビルド時間が50分以内であること

**確認項目**:
- [ ] AMIビルドが成功している（Status: Available）
- [ ] PullDockerImagesステップが実行されている
- [ ] 12種類すべてのイメージのプルログが出力されている
- [ ] `docker images` で12種類のイメージが表示されている
- [ ] Docker Daemon起動確認ログが出力されている
- [ ] ビルド時間が50分以内である
- [ ] 致命的なエラーログがない

---

### 2.3 Dockerイメージ存在確認テスト（ARM64）

**シナリオ名**: INT-003-Docker-Images-Verification-ARM64

**目的**: ARM64版AMIから起動したEC2インスタンスに、12種類のDockerイメージがすべて存在すること

**前提条件**:
- INT-001が成功している（ARM64版AMIが作成済み）
- テストスクリプト `test_docker_images.sh` が作成済み
- SSM Session Manager が利用可能

**テスト手順**:
1. 作成したAMIからEC2インスタンスを起動
   ```bash
   # AMI ID を指定してインスタンス起動
   aws ec2 run-instances \
     --image-id <INT-001で作成したAMI ID> \
     --instance-type t4g.micro \
     --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=test-ami-arm64}]'
   ```

2. インスタンスが起動するまで待機（約2-3分）

3. インスタンスIDを取得
   ```bash
   INSTANCE_ID=$(aws ec2 describe-instances \
     --filters "Name=tag:Name,Values=test-ami-arm64" \
     --query "Reservations[0].Instances[0].InstanceId" \
     --output text)
   ```

4. テストスクリプトを実行
   ```bash
   cd /tmp/ai-workflow-repos-42/infrastructure-as-code/.ai-workflow/issue-440/06_test/integration
   ./test_docker_images.sh $INSTANCE_ID
   ```

5. 結果を確認

**期待結果**:
- テストスクリプトが正常終了すること（終了コード: 0）
- JSON出力に以下が含まれること:
  ```json
  {
    "total_expected": 8,
    "total_found": 8,
    "missing_images": [],
    "success": true,
    "timestamp": "2025-01-XX 12:34:56",
    "images_found": [
      "python:3.11-slim",
      "node:18-slim",
      "rust:1.76-slim",
      "rust:slim",
      "amazon/aws-cli:latest",
      "pulumi/pulumi:latest",
      "ubuntu:22.04",
      "nikolaik/python-nodejs:python3.11-nodejs20"
    ]
  }
  ```
- 各イメージのアーキテクチャが `arm64` であること

**確認項目**:
- [ ] テストスクリプトが正常終了している（exit code 0）
- [ ] `total_expected` が 8 である
- [ ] `total_found` が 8 である
- [ ] `missing_images` が空配列 `[]` である
- [ ] `success` が `true` である
- [ ] すべてのイメージのアーキテクチャが `arm64` である
- [ ] イメージのタグが要件通りである

**テスト後処理**:
```bash
# テスト用インスタンスを削除
aws ec2 terminate-instances --instance-ids $INSTANCE_ID
```

---

### 2.4 Dockerイメージ存在確認テスト（x86_64）

**シナリオ名**: INT-004-Docker-Images-Verification-x86

**目的**: x86_64版AMIから起動したEC2インスタンスに、12種類のDockerイメージがすべて存在すること

**前提条件**:
- INT-002が成功している（x86_64版AMIが作成済み）
- テストスクリプト `test_docker_images.sh` が作成済み
- SSM Session Manager が利用可能

**テスト手順**:
1. 作成したAMIからEC2インスタンスを起動
   ```bash
   aws ec2 run-instances \
     --image-id <INT-002で作成したAMI ID> \
     --instance-type t3.micro \
     --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=test-ami-x86}]'
   ```

2. インスタンスが起動するまで待機（約2-3分）

3. インスタンスIDを取得
   ```bash
   INSTANCE_ID=$(aws ec2 describe-instances \
     --filters "Name=tag:Name,Values=test-ami-x86" \
     --query "Reservations[0].Instances[0].InstanceId" \
     --output text)
   ```

4. テストスクリプトを実行
   ```bash
   cd /tmp/ai-workflow-repos-42/infrastructure-as-code/.ai-workflow/issue-440/06_test/integration
   ./test_docker_images.sh $INSTANCE_ID
   ```

5. 結果を確認

**期待結果**:
- テストスクリプトが正常終了すること（終了コード: 0）
- JSON出力に8種類のイメージがすべて含まれること（INT-003と同様）
- 各イメージのアーキテクチャが `amd64` であること

**確認項目**:
- [ ] テストスクリプトが正常終了している（exit code 0）
- [ ] `total_expected` が 8 である
- [ ] `total_found` が 8 である
- [ ] `missing_images` が空配列 `[]` である
- [ ] `success` が `true` である
- [ ] すべてのイメージのアーキテクチャが `amd64` である
- [ ] イメージのタグが要件通りである

**テスト後処理**:
```bash
aws ec2 terminate-instances --instance-ids $INSTANCE_ID
```

---

### 2.5 ジョブ起動時間測定テスト（小イメージ）

**シナリオ名**: INT-005-Job-Startup-Time-Small-Image

**目的**: 小サイズイメージ（python:3.11-slim 130MB）を使用するジョブの起動時間が、変更前と比較して大幅に短縮されること

**前提条件**:
- 変更前のAMI（ベースライン）が利用可能
- 変更後のAMI（INT-001またはINT-002）が利用可能
- テストスクリプト `measure_job_startup.sh` が作成済み
- 測定対象Jenkinsジョブ: `diagram-generator` または `pull-request-comment-builder`（python:3.11-slimを使用）

**テスト手順**:
1. ベースライン測定（変更前AMI）
   ```bash
   cd /tmp/ai-workflow-repos-42/infrastructure-as-code/.ai-workflow/issue-440/06_test/integration
   ./measure_job_startup.sh \
     --baseline-ami <変更前AMI ID> \
     --job-name diagram-generator \
     --iterations 3
   ```

2. 新AMI測定（変更後AMI）
   ```bash
   ./measure_job_startup.sh \
     --new-ami <INT-001またはINT-002のAMI ID> \
     --job-name diagram-generator \
     --iterations 3
   ```

3. 比較レポート生成
   ```bash
   ./measure_job_startup.sh \
     --baseline-ami <変更前AMI ID> \
     --new-ami <変更後AMI ID> \
     --job-name diagram-generator \
     --iterations 3 \
     --output-report
   ```

4. レポートを確認

**期待結果**:
- ベースライン平均起動時間: 10-20秒
- 新AMI平均起動時間: 1-2秒（**10秒未満**）
- 改善率: 80-90%以上
- レポート形式:
  ```markdown
  # Job Startup Time Comparison Report

  ## Summary
  - Baseline AMI: ami-baseline123
  - New AMI: ami-new456
  - Job Name: diagram-generator
  - Image: python:3.11-slim (130MB)

  ## Results

  | Metric | Baseline (avg) | New AMI (avg) | Improvement |
  |--------|----------------|---------------|-------------|
  | Startup Time | 15.2s | 1.8s | 88.2% |

  ## Detailed Measurements

  ### Baseline AMI (3 iterations)
  - Run 1: 14.8s
  - Run 2: 15.1s
  - Run 3: 15.7s
  - Average: 15.2s

  ### New AMI (3 iterations)
  - Run 1: 1.7s
  - Run 2: 1.8s
  - Run 3: 1.9s
  - Average: 1.8s

  ## Conclusion
  ✅ Significant improvement in startup time (88.2% reduction)
  ```

**確認項目**:
- [ ] ベースライン平均起動時間が記録されている（10-20秒程度）
- [ ] 新AMI平均起動時間が10秒未満である
- [ ] 改善率が80%以上である
- [ ] 3回の測定値にばらつきが少ない（標準偏差が小さい）
- [ ] レポートが正しく生成されている

---

### 2.6 ジョブ起動時間測定テスト（中イメージ）

**シナリオ名**: INT-006-Job-Startup-Time-Medium-Image

**目的**: 中サイズイメージ（nikolaik/python-nodejs:python3.11-nodejs20 400MB）を使用するジョブの起動時間が大幅に短縮されること

**前提条件**:
- 変更前のAMI（ベースライン）が利用可能
- 変更後のAMI（INT-001またはINT-002）が利用可能
- 測定対象Jenkinsジョブ: `auto-insert-doxygen-comment` または `technical-docs-writer`

**テスト手順**:
INT-005と同様の手順（ジョブ名を変更）
```bash
./measure_job_startup.sh \
  --baseline-ami <変更前AMI ID> \
  --new-ami <変更後AMI ID> \
  --job-name auto-insert-doxygen-comment \
  --iterations 3 \
  --output-report
```

**期待結果**:
- ベースライン平均起動時間: 30-40秒
- 新AMI平均起動時間: 1-2秒（**10秒未満**）
- 改善率: 90-95%以上

**確認項目**:
- [ ] ベースライン平均起動時間が記録されている（30-40秒程度）
- [ ] 新AMI平均起動時間が10秒未満である
- [ ] 改善率が90%以上である
- [ ] レポートが正しく生成されている

---

### 2.7 ジョブ起動時間測定テスト（大イメージ）

**シナリオ名**: INT-007-Job-Startup-Time-Large-Image

**目的**: 大サイズイメージ（rust:1.76-slim 850MB）を使用するジョブの起動時間が大幅に短縮されること

**前提条件**:
- 変更前のAMI（ベースライン）が利用可能
- 変更後のAMI（INT-001またはINT-002）が利用可能
- 測定対象Jenkinsジョブ: `pr-complexity-analyzer`

**テスト手順**:
INT-005と同様の手順（ジョブ名を変更）
```bash
./measure_job_startup.sh \
  --baseline-ami <変更前AMI ID> \
  --new-ami <変更後AMI ID> \
  --job-name pr-complexity-analyzer \
  --iterations 3 \
  --output-report
```

**期待結果**:
- ベースライン平均起動時間: 60-90秒
- 新AMI平均起動時間: 1-2秒（**10秒未満**）
- 改善率: 95-98%以上

**確認項目**:
- [ ] ベースライン平均起動時間が記録されている（60-90秒程度）
- [ ] 新AMI平均起動時間が10秒未満である
- [ ] 改善率が95%以上である
- [ ] レポートが正しく生成されている

---

### 2.8 AMIサイズ確認テスト

**シナリオ名**: INT-008-AMI-Size-Verification

**目的**: 新AMIのサイズ増加が許容範囲内（+3GB以内）であること

**前提条件**:
- 変更前のAMI（ベースライン）のサイズが記録されている
- 変更後のAMI（INT-001、INT-002）が作成済み

**テスト手順**:
1. ベースラインAMIのサイズを取得
   ```bash
   aws ec2 describe-images \
     --image-ids <ベースラインAMI ID> \
     --query "Images[0].BlockDeviceMappings[0].Ebs.VolumeSize" \
     --output text
   ```

2. ARM64版AMIのサイズを取得
   ```bash
   aws ec2 describe-images \
     --image-ids <INT-001のAMI ID> \
     --query "Images[0].BlockDeviceMappings[0].Ebs.VolumeSize" \
     --output text
   ```

3. x86_64版AMIのサイズを取得
   ```bash
   aws ec2 describe-images \
     --image-ids <INT-002のAMI ID> \
     --query "Images[0].BlockDeviceMappings[0].Ebs.VolumeSize" \
     --output text
   ```

4. サイズ増加を計算
   ```bash
   # 増加量 = 新AMIサイズ - ベースラインサイズ
   ```

**期待結果**:
- ARM64版AMIサイズ増加: 2-3GB以内
- x86_64版AMIサイズ増加: 2-3GB以内
- 増加量が許容範囲（+3GB以内）であること

**確認項目**:
- [ ] ベースラインAMIサイズが記録されている
- [ ] ARM64版AMIサイズが記録されている
- [ ] x86_64版AMIサイズが記録されている
- [ ] ARM64版AMIサイズ増加が3GB以内である
- [ ] x86_64版AMIサイズ増加が3GB以内である
- [ ] 実測値が設計時の見積もり（約2.9GB）と近い値である

---

### 2.9 AMIビルド時間確認テスト

**シナリオ名**: INT-009-AMI-Build-Time-Verification

**目的**: AMIビルド時間の増加が許容範囲内（+10分以内）であること

**前提条件**:
- 変更前のAMIビルド時間が記録されている（30-45分）
- INT-001、INT-002のビルドログが利用可能

**テスト手順**:
1. EC2 Image Builder コンソールから各ビルドの実行時間を取得
   - ベースラインビルド: 開始時刻と完了時刻を記録
   - ARM64版ビルド（INT-001）: 開始時刻と完了時刻を記録
   - x86_64版ビルド（INT-002）: 開始時刻と完了時刻を記録

2. ビルド時間を計算
   ```bash
   # ビルド時間 = 完了時刻 - 開始時刻
   ```

3. 増加時間を計算
   ```bash
   # 増加時間 = 新AMIビルド時間 - ベースラインビルド時間
   ```

**期待結果**:
- ベースラインビルド時間: 30-45分
- ARM64版ビルド時間: 35-50分
- x86_64版ビルド時間: 35-50分
- 増加時間: 5-10分以内（**10分以内**）

**確認項目**:
- [ ] ベースラインビルド時間が記録されている（30-45分）
- [ ] ARM64版ビルド時間が記録されている
- [ ] x86_64版ビルド時間が記録されている
- [ ] ARM64版ビルド時間増加が10分以内である
- [ ] x86_64版ビルド時間増加が10分以内である
- [ ] 実測値が設計時の見積もり（+5-10分）の範囲内である

---

### 2.10 エラーハンドリングテスト（Docker Daemon起動失敗）

**シナリオ名**: INT-010-Error-Handling-Docker-Daemon-Failure

**目的**: Docker Daemonが起動していない場合、PullDockerImagesステップが適切にエラーハンドリングすること

**前提条件**:
- component-arm.yml または component-x86.yml のテスト用コピーが作成済み
- Docker Daemon起動確認ロジックが実装済み（`systemctl is-active docker || exit 1`）

**テスト手順**:
1. テスト用コンポーネント定義を作成
   ```bash
   cp pulumi/jenkins-agent-ami/component-arm.yml \
      pulumi/jenkins-agent-ami/component-arm-test.yml
   ```

2. PullDockerImagesステップを修正（Docker起動をスキップ）
   ```yaml
   # systemctl start docker をコメントアウト
   # - systemctl start docker
   - sleep 5
   - systemctl is-active docker || (echo "ERROR: Docker daemon is not running" && exit 1)
   ```

3. テスト用AMIビルドを実行

4. ビルドログを確認

**期待結果**:
- PullDockerImagesステップが失敗すること（Status: Failed）
- エラーログに以下が記録されていること:
  - `ERROR: Docker daemon is not running`
- AMIビルド全体が失敗すること

**確認項目**:
- [ ] PullDockerImagesステップが失敗している
- [ ] エラーログに `ERROR: Docker daemon is not running` が出力されている
- [ ] AMIビルドが失敗している（Status: Failed）
- [ ] 致命的エラーとして正しく処理されている

**テスト後処理**:
```bash
# テスト用コンポーネント定義を削除
rm pulumi/jenkins-agent-ami/component-arm-test.yml
```

---

### 2.11 エラーハンドリングテスト（個別イメージプル失敗）

**シナリオ名**: INT-011-Error-Handling-Image-Pull-Failure

**目的**: 一部のDockerイメージプルが失敗した場合でも、ビルドが継続され、警告が表示されること

**前提条件**:
- component-arm.yml または component-x86.yml のテスト用コピーが作成済み
- 個別イメージプル失敗ロジックが実装済み（`|| echo "WARNING: Failed to pull..."`）

**テスト手順**:
1. テスト用コンポーネント定義を作成
   ```bash
   cp pulumi/jenkins-agent-ami/component-arm.yml \
      pulumi/jenkins-agent-ami/component-arm-test-pull-fail.yml
   ```

2. 存在しないイメージを追加（プル失敗をシミュレート）
   ```yaml
   - |
     echo "Pulling non-existent-image:latest..."
     docker pull non-existent-image:latest || echo "WARNING: Failed to pull non-existent-image:latest"
   ```

3. テスト用AMIビルドを実行

4. ビルドログを確認

**期待結果**:
- PullDockerImagesステップが成功すること（警告のみ、ビルド継続）
- ビルドログに以下が記録されていること:
  - `WARNING: Failed to pull non-existent-image:latest`
- AMIビルド全体が成功すること（Status: Available）
- `docker images` で実際にプルされたイメージのみが表示されること

**確認項目**:
- [ ] PullDockerImagesステップが成功している
- [ ] ビルドログに `WARNING: Failed to pull...` が出力されている
- [ ] AMIビルドが成功している（Status: Available）
- [ ] 他のイメージは正常にプルされている
- [ ] `docker images` で存在しないイメージは表示されていない

**テスト後処理**:
```bash
rm pulumi/jenkins-agent-ami/component-arm-test-pull-fail.yml
```

---

## 3. テストデータ

### 3.1 Dockerイメージリスト（期待値）

| イメージ名 | タグ | サイズ（概算） | アーキテクチャ対応 |
|----------|------|--------------|-------------------|
| python | 3.11-slim | 130MB | arm64, amd64 |
| node | 18-slim | 180MB | arm64, amd64 |
| rust | 1.76-slim | 850MB | arm64, amd64 |
| rust | slim | 850MB | arm64, amd64 |
| amazon/aws-cli | latest | 400MB | arm64, amd64 |
| pulumi/pulumi | latest | 100MB | arm64, amd64 |
| ubuntu | 22.04 | 77MB | arm64, amd64 |
| nikolaik/python-nodejs | python3.11-nodejs20 | 400MB | arm64, amd64 |

**合計サイズ**: 約2.9GB（実際には rust:1.76-slim と rust:slim が重複する可能性があるため、実測値は約2.1-2.5GB程度）

### 3.2 測定対象Jenkinsジョブ

| ジョブ名 | 使用イメージ | イメージサイズ | カテゴリ |
|---------|------------|--------------|---------|
| diagram-generator | python:3.11-slim | 130MB | 小イメージ |
| auto-insert-doxygen-comment | nikolaik/python-nodejs:python3.11-nodejs20 | 400MB | 中イメージ |
| pr-complexity-analyzer | rust:1.76-slim | 850MB | 大イメージ |

### 3.3 AMI情報

| AMI種別 | アーキテクチャ | 想定サイズ | 想定ビルド時間 |
|--------|--------------|-----------|--------------|
| ベースライン | arm64 | 基準値 | 30-45分 |
| ベースライン | x86_64 | 基準値 | 30-45分 |
| 新AMI（変更後） | arm64 | 基準値 + 2-3GB | 35-50分 |
| 新AMI（変更後） | x86_64 | 基準値 + 2-3GB | 35-50分 |

### 3.4 テストスクリプト出力形式

#### test_docker_images.sh 出力例
```json
{
  "total_expected": 8,
  "total_found": 8,
  "missing_images": [],
  "success": true,
  "timestamp": "2025-01-15 12:34:56",
  "images_found": [
    {
      "repository": "python",
      "tag": "3.11-slim",
      "image_id": "sha256:abc123...",
      "size": "130MB",
      "architecture": "arm64"
    },
    {
      "repository": "node",
      "tag": "18-slim",
      "image_id": "sha256:def456...",
      "size": "180MB",
      "architecture": "arm64"
    }
    // ... 以下、残り6種類のイメージ
  ]
}
```

#### measure_job_startup.sh 出力例
```markdown
# Job Startup Time Comparison Report

## Summary
- Baseline AMI: ami-0123456789abcdef0
- New AMI: ami-fedcba9876543210
- Job Name: diagram-generator
- Image: python:3.11-slim (130MB)
- Test Date: 2025-01-15 14:00:00

## Results

| Metric | Baseline (avg) | New AMI (avg) | Improvement |
|--------|----------------|---------------|-------------|
| Docker Image Pull Time | 15.2s | 0.1s | 99.3% |
| Container Startup Time | 2.1s | 2.0s | 4.8% |
| Total Job Startup Time | 17.3s | 2.1s | 87.9% |

## Detailed Measurements

### Baseline AMI (3 iterations)
- Run 1: 17.1s (Pull: 15.0s, Start: 2.1s)
- Run 2: 17.2s (Pull: 15.1s, Start: 2.1s)
- Run 3: 17.6s (Pull: 15.5s, Start: 2.1s)
- Average: 17.3s

### New AMI (3 iterations)
- Run 1: 2.0s (Pull: 0.0s, Start: 2.0s)
- Run 2: 2.1s (Pull: 0.1s, Start: 2.0s)
- Run 3: 2.2s (Pull: 0.2s, Start: 2.0s)
- Average: 2.1s

## Conclusion
✅ Significant improvement in startup time (87.9% reduction)
✅ Docker image pull time reduced from 15.2s to 0.1s (99.3% reduction)
✅ Meets acceptance criteria (startup time < 10 seconds)
```

---

## 4. テスト環境要件

### 4.1 必要なテスト環境

| 環境 | 用途 | 要件 |
|-----|------|------|
| AWS環境（dev） | AMIビルド実行 | EC2 Image Builder、S3、CloudWatch Logs、IAMロールが設定済み |
| EC2インスタンス（テスト用） | イメージ存在確認 | t4g.micro（ARM64）、t3.micro（x86_64）、SSM Session Manager有効 |
| Jenkins環境（dev） | ジョブ起動時間測定 | Jenkins API アクセス可能、テスト用ジョブが設定済み |
| ローカル環境 | テストスクリプト実行 | AWS CLI、jq、bash、SSH/SSM接続ツール |

### 4.2 必要な外部サービス

| サービス | 用途 | 依存性 |
|---------|------|--------|
| Docker Hub | Dockerイメージプル | インターネット接続必須、レート制限に注意（匿名: 100回/6時間） |
| AWS S3 | AMI成果物保存 | 既存設定に従う |
| AWS CloudWatch Logs | ビルドログ出力 | 既存設定に従う |
| AWS Systems Manager | EC2インスタンス接続（SSM Session Manager） | IAMロール設定済み |

### 4.3 テストスクリプト要件

| スクリプト | 実行環境 | 依存ツール |
|----------|---------|-----------|
| test_docker_images.sh | ローカル or CI/CD | AWS CLI、jq、bash 4.0+ |
| measure_job_startup.sh | ローカル or CI/CD | AWS CLI、curl、jq、bash 4.0+ |

### 4.4 IAM権限要件

テスト実行ユーザーに必要な権限:
- `ec2:RunInstances` - テスト用インスタンス起動
- `ec2:TerminateInstances` - テスト用インスタンス削除
- `ec2:DescribeInstances` - インスタンス情報取得
- `ec2:DescribeImages` - AMI情報取得
- `ssm:StartSession` - SSM Session Manager接続
- `ssm:SendCommand` - SSMコマンド実行
- `imagebuilder:GetImage` - Image Builder情報取得
- `imagebuilder:ListImageBuildVersions` - ビルド履歴取得

---

## 5. 品質ゲート（Phase 3）

本テストシナリオは、以下の品質ゲートを満たしています：

### 必須要件

- [x] **Phase 2の戦略に沿ったテストシナリオである**
  - テスト戦略: INTEGRATION_ONLY に準拠
  - インテグレーションテストシナリオのみを作成（Unitテスト、BDDテストは作成していない）
  - 11個の統合テストシナリオを定義

- [x] **主要な正常系がカバーされている**
  - INT-001, INT-002: AMIビルド成功（ARM64/x86_64）
  - INT-003, INT-004: Dockerイメージ存在確認（ARM64/x86_64）
  - INT-005, INT-006, INT-007: ジョブ起動時間短縮（小・中・大イメージ）
  - INT-008: AMIサイズ確認
  - INT-009: AMIビルド時間確認

- [x] **主要な異常系がカバーされている**
  - INT-010: Docker Daemon起動失敗時のエラーハンドリング
  - INT-011: 個別イメージプル失敗時のエラーハンドリング

- [x] **期待結果が明確である**
  - すべてのテストシナリオに「期待結果」セクションを記載
  - 具体的な数値目標を明示（起動時間 < 10秒、AMIサイズ増加 < 3GB、ビルド時間増加 < 10分）
  - 確認項目をチェックリスト形式で列挙（テスト実行時に確認しやすい）

### 追加の品質指標

- [x] **要件定義書の受け入れ基準との対応**
  - AC-1（事前プル機能）: INT-001, INT-002でカバー
  - AC-2（イメージ存在確認）: INT-003, INT-004でカバー
  - AC-3（起動時間短縮）: INT-005, INT-006, INT-007でカバー
  - AC-4（AMIサイズ・ビルド時間）: INT-008, INT-009でカバー
  - AC-5（マルチアーキテクチャ）: すべてのシナリオでARM64/x86_64両方をテスト
  - AC-6（エラーハンドリング）: INT-010, INT-011でカバー
  - AC-7（ドキュメント更新）: 実装フェーズで確認（テストシナリオ外）

- [x] **テストデータが明確である**
  - セクション3で期待値、測定対象、AMI情報、出力形式を詳細定義

- [x] **テスト環境要件が明確である**
  - セクション4でテスト環境、外部サービス、スクリプト要件、IAM権限を詳細定義

---

## 6. テスト実行順序

**推奨実行順序**:

### Phase 1: AMIビルドとイメージ存在確認（必須）
1. INT-001: AMIビルド統合テスト（ARM64）
2. INT-003: Dockerイメージ存在確認テスト（ARM64）
3. INT-002: AMIビルド統合テスト（x86_64）
4. INT-004: Dockerイメージ存在確認テスト（x86_64）

**理由**: AMIビルドが成功しないと、後続のテストが実行できない。イメージ存在確認で12種類すべてのイメージが正常にプルされていることを確認してから、性能測定に進む。

### Phase 2: 性能測定（高優先度）
5. INT-005: ジョブ起動時間測定テスト（小イメージ）
6. INT-006: ジョブ起動時間測定テスト（中イメージ）
7. INT-007: ジョブ起動時間測定テスト（大イメージ）

**理由**: 受け入れ基準の主要項目（起動時間 < 10秒）の検証。小・中・大のイメージでそれぞれ測定し、効果を定量的に確認。

### Phase 3: コスト影響確認（中優先度）
8. INT-008: AMIサイズ確認テスト
9. INT-009: AMIビルド時間確認テスト

**理由**: AMIサイズとビルド時間の増加が許容範囲内であることを確認。コスト影響の評価に使用。

### Phase 4: エラーハンドリング（低優先度、オプション）
10. INT-010: エラーハンドリングテスト（Docker Daemon起動失敗）
11. INT-011: エラーハンドリングテスト（個別イメージプル失敗）

**理由**: エラーハンドリングロジックの確認。テスト用コンポーネント定義の修正が必要なため、時間がある場合に実行。

---

## 7. 次フェーズへの引き継ぎ事項

Phase 4（実装）で実施すべき事項：

### 7.1 実装作業
1. **component-arm.ymlの修正**（優先度: 高）
   - 183行目付近にPullDockerImagesステップを追加
   - 設計書セクション7.1.2のステップ定義を使用

2. **component-x86.ymlの修正**（優先度: 高）
   - component-arm.ymlと同じ内容を追加
   - diff比較で内容が一致することを確認

### 7.2 テストスクリプト作成（Phase 5）
1. **test_docker_images.sh作成**
   - セクション3.4のJSON出力形式を実装
   - SSM Session Managerでdocker imagesコマンド実行
   - 12種類のイメージ存在確認
   - 実行権限付与（chmod +x）

2. **measure_job_startup.sh作成**
   - セクション3.4のMarkdown出力形式を実装
   - Jenkins APIでジョブトリガー
   - Docker Image Pull時間とContainer Startup時間を分離測定
   - before/after比較レポート生成
   - 実行権限付与（chmod +x）

### 7.3 テスト実行時の注意事項
1. **Docker Hubレート制限対策**
   - 可能であればDocker Hub認証を使用（200回/6時間）
   - AMIビルド実行は1日あたり2-3回程度に制限
   - 複数アーキテクチャの同時ビルドは避ける（順次実行）

2. **AMIビルド時間**
   - ビルド完了まで35-50分かかることを想定
   - CI/CDパイプラインのタイムアウト設定に注意

3. **テスト環境のクリーンアップ**
   - テスト用EC2インスタンスは測定後に必ず削除
   - 不要なAMIは定期的に削除（EBSストレージコスト削減）

---

**作成日**: 2025-01-XX
**作成者**: AI Workflow System
**レビュー状態**: テストシナリオレビュー待ち
**次フェーズ**: Phase 4 - 実装
