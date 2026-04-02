---
name: jenkins-update-agents
description: AMIビルド済みの状態からSSMパラメータ更新→Agent再デプロイ→アプリケーション設定を実行する
user-invocable: true
---

# Jenkins Agent更新（AMIビルド後の手順）

AMIビルドが完了している前提で、Step 1〜3を順番に実行してください。

## 前提
- 作業ディレクトリ: `/home/ec2-user/infrastructure-as-code/ansible`
- 環境: ユーザーが指定しない場合は `dev` をデフォルトとする

## 手順

### 1. Step 1: SSMパラメータ更新
```bash
ansible-playbook playbooks/jenkins/misc/update_jenkins_ami_ssm.yml -e "env=${ENV}"
```
- `failed=0` を確認

### 2. Step 2: Jenkins Agent再デプロイ
```bash
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_agent.yml -e "env=${ENV}"
```
- `failed=0` を確認

### 3. Step 3: アプリケーション設定
```bash
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_application.yml -e "env=${ENV}"
```
- `failed=0` を確認

## 完了後
- 各ステップの結果（ok数、changed数、failed数）をまとめて報告する

## エラー時の対応
- いずれかのステップで `failed` が発生した場合、エラー内容を表示してユーザーに報告する
- 自動リトライはしない（ユーザーの判断を仰ぐ）
