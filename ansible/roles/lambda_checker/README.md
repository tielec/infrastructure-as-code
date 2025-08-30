# lambda_checker ロール

Lambda API環境の動作確認とヘルスチェックを実行するAnsibleロール。

## 概要

このロールは、Lambda API環境のコンポーネントが正しくデプロイされ、動作しているかを確認します。

## 機能

- VPCとネットワーク構成のチェック
- セキュリティグループの確認
- VPCエンドポイントの検証
- Lambda関数の状態確認
- API Gatewayの設定確認
- CloudWatch Logsの確認
- APIエンドポイントのテスト（オプション）

## 使用方法

### プレイブックから呼び出し

```yaml
- name: Lambda環境をチェック
  ansible.builtin.include_role:
    name: lambda_checker
  vars:
    operation: check
    environment: dev
    detailed_mode: true
    enable_api_test: true
```

### 直接実行

```bash
# 基本チェック
ansible-playbook playbooks/check_lambda_environment.yml -e "env=dev"

# 詳細チェック
ansible-playbook playbooks/check_lambda_environment.yml -e "env=dev detailed=true"

# APIテスト付き
ansible-playbook playbooks/check_lambda_environment.yml -e "env=dev test_api=true"
```

## 変数

### 必須変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `environment` | チェック対象の環境 | `dev` |
| `operation` | 実行する操作 (check/validate) | `check` |

### オプション変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `detailed_mode` | 詳細チェックモード | `false` |
| `enable_api_test` | APIテストの実行 | `false` |
| `api_endpoint_path` | テストするAPIパス | `/health` |
| `check_vpc` | VPCチェックの有効化 | `true` |
| `check_security_groups` | セキュリティグループチェック | `true` |
| `check_vpce` | VPCエンドポイントチェック | `true` |
| `check_lambda_functions` | Lambda関数チェック | `true` |
| `check_api_gateway` | API Gatewayチェック | `true` |
| `check_cloudwatch_logs` | CloudWatchログチェック | `true` |
| `api_test_timeout` | APIテストのタイムアウト（秒） | `10` |

## チェック結果

チェック結果は `check_results` 変数に格納されます：

```yaml
check_results:
  total: 10        # 総チェック数
  passed: 8        # 成功数
  warnings: 1      # 警告数
  failed: 1        # 失敗数
  failures:        # 失敗詳細
    - name: "Lambda functions"
      reason: "No functions found"
  details: {}      # 詳細情報
```

## 依存関係

このロールは以下のヘルパーロールに依存します：

- `ssm_parameter_store` - SSMパラメータの取得
- `aws_cli_helper` - AWS CLIコマンドの実行

## 出力例

```
========================================
Lambda Environment Health Check
========================================
Environment: dev
Detailed Check: true
API Test: false

✅ VPC ID: vpc-0123456789abcdef0
✅ Private Subnets: subnet-xxx,subnet-yyy
✅ Lambda Security Group: sg-0123456789abcdef0
✅ VPC Endpoint Security Group: sg-0123456789abcdef1
✅ Found 5 VPC Endpoints
✅ Lambda Functions Found: 3
✅ API Gateway ID: abc123def456
✅ API Endpoint: https://api-id.execute-api.ap-northeast-1.amazonaws.com/dev
✅ Deployment Stages: dev
✅ CloudWatch Log Groups Found: 3

========================================
Check Summary
========================================
Total Checks: 10
Passed: 9
Warnings: 1
Failed: 0

✅ All checks passed successfully!
========================================
```

## トラブルシューティング

### チェックが失敗する場合

1. AWS認証情報が正しく設定されているか確認
2. 必要なIAM権限があるか確認
3. SSMパラメータが正しく初期化されているか確認

### APIテストが失敗する場合

1. API Gatewayが正しくデプロイされているか確認
2. APIキーが正しく設定されているか確認
3. ネットワーク接続を確認

## 関連ドキュメント

- [Ansible README](../../README.md)
- [Lambda Setup Pipeline](../lambda_setup_pipeline.yml)