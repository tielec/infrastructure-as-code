---
name: jenkins-status
description: Jenkins環境の現在の状態を確認する（AMIビルド状況、エージェント、コントローラー）
user-invocable: true
---

# Jenkins環境ステータス確認

以下の情報を収集して、まとめて報告してください。

## 前提
- 環境: ユーザーが指定しない場合は `dev` をデフォルトとする
- AWSリージョン: ap-northeast-1
- AWSアカウント: 621593801728

## 確認項目

### 1. AMIビルド状況
Image Builderパイプラインの最新ビルドステータスを確認:
- x86: `arn:aws:imagebuilder:ap-northeast-1:621593801728:image-pipeline/jenkins-infra-agent-pipeline-x86-${ENV}`
- ARM: `arn:aws:imagebuilder:ap-northeast-1:621593801728:image-pipeline/jenkins-infra-agent-pipeline-arm-${ENV}`

```bash
aws imagebuilder list-image-pipeline-images --image-pipeline-arn {ARN} --query 'imageSummaryList[-1].[version,state.status,dateCreated]' --output table
```

### 2. Jenkinsコントローラー
```bash
aws ec2 describe-instances --filters 'Name=tag:Name,Values=*jenkins*' 'Name=instance-state-name,Values=running' --query 'Reservations[*].Instances[*].[InstanceId,Tags[?Key==`Name`].Value|[0],State.Name,InstanceType]' --output table
```

### 3. SpotFleet エージェント状況
各サイズのSpotFleet IDをSSMから取得し、アクティブなインスタンスを確認:
```bash
for size in medium small micro; do
  sfr=$(aws ssm get-parameter --name "/jenkins-infra/${ENV}/agent/spotFleetRequestId-$size" --query 'Parameter.Value' --output text 2>/dev/null)
  echo "=== $size (SFR: $sfr) ==="
  aws ec2 describe-spot-fleet-instances --spot-fleet-request-id "$sfr" --query 'ActiveInstances[*].[InstanceId,InstanceType]' --output table 2>/dev/null || echo "No active instances"
done
```

### 4. 現在のSSM AMI設定
```bash
aws ssm get-parameters-by-path --path "/jenkins-infra/${ENV}/agent-ami/" --query 'Parameters[*].{Name:Name,Value:Value}' --output table
```

## 出力フォーマット
確認結果を以下のような表形式でまとめて報告する:

| 項目 | 状態 |
|------|------|
| AMI (x86) | バージョン / ステータス |
| AMI (ARM) | バージョン / ステータス |
| SSM AMI x86 | AMI ID |
| SSM AMI ARM | AMI ID |
| コントローラー | インスタンスID / 状態 |
| エージェント (medium) | 台数 |
| エージェント (small) | 台数 |
| エージェント (micro) | 台数 |
