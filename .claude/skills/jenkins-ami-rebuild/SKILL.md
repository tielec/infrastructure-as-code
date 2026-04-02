---
name: jenkins-ami-rebuild
description: Jenkins Agent AMIの再ビルドからエージェント更新・アプリケーション設定まで一気通貫で実行する
user-invocable: true
---

# Jenkins AMI再ビルド & 全更新

以下の手順を順番に自動実行してください。各ステップの完了を確認してから次に進むこと。

## 前提
- 作業ディレクトリ: `/home/ec2-user/infrastructure-as-code/ansible`
- 環境: ユーザーが指定しない場合は `dev` をデフォルトとする

## 手順

### 1. AMIビルドのトリガー
```bash
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_agent_ami.yml -e "env=${ENV}"
```
- 完了後、Image Builderで非同期ビルドが開始される

### 2. AMIビルド完了の待機
- 以下の2パイプラインのステータスを5分間隔で確認する
  - `jenkins-infra-agent-pipeline-x86-${ENV}`
  - `jenkins-infra-agent-pipeline-arm-${ENV}`
- ARN: `arn:aws:imagebuilder:ap-northeast-1:621593801728:image-pipeline/{パイプライン名}`
- 最新ビルド（日付が最新のもの）のステータスが両方とも `AVAILABLE` になるまで待機
- クエリ例: `aws imagebuilder list-image-pipeline-images --image-pipeline-arn {ARN} --query 'imageSummaryList[-1].[version,state.status]' --output text`

### 3. Step 1: SSMパラメータ更新
```bash
ansible-playbook playbooks/jenkins/misc/update_jenkins_ami_ssm.yml -e "env=${ENV}"
```
- `failed=0` を確認

### 4. Step 2: Jenkins Agent再デプロイ
```bash
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_agent.yml -e "env=${ENV}"
```
- `failed=0` を確認

### 5. Step 3: アプリケーション設定
```bash
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_application.yml -e "env=${ENV}"
```
- `failed=0` を確認

## エラー時の対応
- いずれかのステップで `failed` が発生した場合、エラー内容を表示してユーザーに報告する
- 自動リトライはしない（ユーザーの判断を仰ぐ）
