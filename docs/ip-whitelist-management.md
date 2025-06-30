# Lambda API - IP Whitelist管理ガイド

## 概要
Lambda API WAFのIPホワイトリストは、AWS Secrets Managerを使用して管理されます。

## クイックスタート

### 1. 初期設定
```bash
# IP Whitelist の初期化
./scripts/init-ip-whitelist.sh
```

### 2. IPアドレスの追加
```bash
# 現在の設定を取得
aws secretsmanager get-secret-value \
  --secret-id lambda-api/ip-whitelist/dev \
  --query SecretString --output text > whitelist.json

# whitelist.json を編集
vi whitelist.json

# 更新を適用
aws secretsmanager put-secret-value \
  --secret-id lambda-api/ip-whitelist/dev \
  --secret-string file://whitelist.json
```

## 設定構造

### クライアント設定の例
```json
{
  "version": "1.0",
  "lastUpdated": "2025-06-30T00:00:00Z",
  "clients": [
    {
      "id": "client-001",
      "name": "External Platform",
      "description": "Third-party platform integration",
      "enabled": true,
      "ipAddresses": [
        "192.0.2.0/24",
        "198.51.100.0/24"
      ],
      "tags": {
        "type": "platform",
        "priority": "high"
      }
    }
  ]
}
```

### フィールド説明
- `id`: クライアントの一意識別子
- `name`: わかりやすい名前
- `description`: 用途の説明
- `enabled`: true/false で有効/無効を切り替え
- `ipAddresses`: CIDR形式のIPアドレスリスト
- `tags.type`: `platform` | `api-service` | `internal` | `monitoring` | `other`
- `tags.priority`: `high` | `medium` | `low`

## 基本操作

### IPアドレスの追加
```bash
# jqを使用した例
CURRENT=$(aws secretsmanager get-secret-value \
  --secret-id lambda-api/ip-whitelist/dev \
  --query SecretString --output text)

NEW=$(echo $CURRENT | jq '.clients[0].ipAddresses += ["203.0.113.0/24"]')

aws secretsmanager put-secret-value \
  --secret-id lambda-api/ip-whitelist/dev \
  --secret-string "$NEW"
```

### クライアントの無効化
```bash
CURRENT=$(aws secretsmanager get-secret-value \
  --secret-id lambda-api/ip-whitelist/dev \
  --query SecretString --output text)

NEW=$(echo $CURRENT | jq '.clients |= map(if .id == "client-001" then .enabled = false else . end)')

aws secretsmanager put-secret-value \
  --secret-id lambda-api/ip-whitelist/dev \
  --secret-string "$NEW"
```

## 環境別の管理

| 環境 | Secret名 | 用途 |
|-----|----------|------|
| 開発 | `lambda-api/ip-whitelist/dev` | 開発・テスト用 |
| ステージング | `lambda-api/ip-whitelist/staging` | 検証用 |
| 本番 | `lambda-api/ip-whitelist/prod` | 本番運用 |

## トラブルシューティング

### Q: IPを追加したのにアクセスできない
- クライアントが `enabled: true` になっているか確認
- CIDR表記が正しいか確認（例: 単一IPは `/32`）
- WAFの更新反映まで最大5分かかる場合があります

### Q: 設定を間違えて更新してしまった
```bash
# 更新履歴を確認
aws secretsmanager list-secret-version-ids \
  --secret-id lambda-api/ip-whitelist/dev

# 以前のバージョンに戻す
aws secretsmanager get-secret-value \
  --secret-id lambda-api/ip-whitelist/dev \
  --version-id <VERSION_ID>
```

## セキュリティベストプラクティス

1. **最小限のIP範囲を使用**
   - 可能な限り `/32` (単一IP) を使用
   - 広いサブネット（`/16` など）は避ける

2. **定期的な見直し**
   - 月次でアクセス権限を確認
   - 不要になったIPは速やかに削除

3. **環境の分離**
   - 本番環境のIPは本番のみに設定
   - 開発環境での全許可（`0.0.0.0/0`）は避ける

## 関連ファイル
- WAF設定: `pulumi/lambda-waf/index.ts`
- 初期化スクリプト: `scripts/init-ip-whitelist.sh`
