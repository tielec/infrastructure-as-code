# VPC Endpoints Role

AWS VPCエンドポイントを管理するAnsibleロール。プライベートサブネット内のEC2インスタンスがNATやインターネットゲートウェイを経由せずにAWSサービスに接続できるようにします。

## 概要

このロールは以下のVPCエンドポイントを作成・管理します：

- **インターフェース型エンドポイント**
  - SSM (Systems Manager)
  - SSM Messages (Session Manager用)
  - EC2 Messages (SSMエージェント用)
  - EC2
  
- **ゲートウェイ型エンドポイント**
  - S3

## 必要条件

- ネットワークスタック（VPC、サブネット）がデプロイ済み
- セキュリティスタック（セキュリティグループ）がデプロイ済み
- Pulumiスタック `jenkins-vpc-endpoints` が存在

## 使用方法

### デプロイ

```yaml
- name: Deploy VPC Endpoints
  ansible.builtin.include_role:
    name: vpc_endpoints
  vars:
    operation: deploy  # デフォルトなので省略可
    env_name: dev
```

### 削除

```yaml
- name: Destroy VPC Endpoints
  ansible.builtin.include_role:
    name: vpc_endpoints
  vars:
    operation: destroy
    force_destroy: true  # 確認プロンプトをスキップ
```

## 変数

### 必須変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `env_name` | 環境名 | `deploy_env` または `'dev'` |

### オプション変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `operation` | 実行操作（deploy/destroy） | `'deploy'` |
| `preview_only` | プレビューのみ実行 | `false` |
| `force_destroy` | 削除時の確認をスキップ | `false` |
| `aws_region_name` | AWSリージョン | `'ap-northeast-1'` |
| `vpc_endpoints_debug` | デバッグ出力を有効化 | `false` |

## 依存関係

このロールは以下のヘルパーロールに依存します（`meta/main.yml`で定義）：

- `pulumi_helper` - Pulumiスタック操作
- `ssm_parameter_store` - SSMパラメータ管理
- `aws_cli_helper` - AWS CLI操作

## SSMパラメータ

### 必要なパラメータ（入力）

- `/jenkins-infra/{env}/network/vpc-id`
- `/jenkins-infra/{env}/network/private-subnet-a-id`
- `/jenkins-infra/{env}/network/private-subnet-b-id`
- `/jenkins-infra/{env}/security/jenkins-sg-id`

### 作成されるパラメータ（出力）

- `/jenkins-infra/{env}/vpc-endpoints/security-group-id`
- `/jenkins-infra/{env}/vpc-endpoints/ssm-endpoint-id`
- `/jenkins-infra/{env}/vpc-endpoints/ssm-messages-endpoint-id`
- `/jenkins-infra/{env}/vpc-endpoints/ec2-messages-endpoint-id`
- `/jenkins-infra/{env}/vpc-endpoints/ec2-endpoint-id`
- `/jenkins-infra/{env}/vpc-endpoints/s3-endpoint-id`
- `/jenkins-infra/{env}/vpc-endpoints/deployed-at`

## 実行例

```bash
# デプロイ
ansible-playbook -i inventory/hosts playbooks/deploy-vpc-endpoints.yml -e deploy_env=dev

# プレビュー
ansible-playbook -i inventory/hosts playbooks/deploy-vpc-endpoints.yml -e deploy_env=dev -e preview_only=true

# 削除
ansible-playbook -i inventory/hosts playbooks/destroy-vpc-endpoints.yml -e deploy_env=dev -e force_destroy=true
```