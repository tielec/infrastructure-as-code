# Lambda API Gateway

このディレクトリは、AWS API GatewayとLambda関数を統合するためのPulumiスタックです。

## 📋 概要

API Gatewayは、Lambda関数への「入り口」として機能します。HTTPリクエストを受け取り、適切なLambda関数に転送する役割を持っています。

```
[クライアント] → [API Gateway] → [Lambda関数]
                     ↓
                  APIキー認証
                  ルーティング
                  レート制限
```

## 🏗️ 現在の構成

### エンドポイント構造

```
https://api-gateway-url/
├── /health          → ヘルスチェック（Lambda呼び出しなし、モックレスポンス）
└── /api
    ├── (直接)        → main Lambda関数を呼び出し
    └── /{proxy+}    → すべてのサブパス（/api/users、/api/products等）をmain Lambda関数に転送
```

### 主要コンポーネント

1. **REST API** - API Gatewayの本体
2. **リソース** - URLパスの定義（/health、/api、/api/{proxy+}）
3. **メソッド** - HTTPメソッドの定義（GET、POST、ANY等）
4. **統合** - Lambda関数との接続設定
5. **デプロイメント** - APIの公開
6. **ステージ** - 環境別の設定（dev、staging、prod）
7. **使用プラン** - レート制限とクォータ
8. **APIキー** - 認証用のキー

## 🔄 リクエストの流れ

### 1. ヘルスチェック（/health）
```
クライアント → API Gateway → モックレスポンス
                               （Lambda呼び出しなし）
```
- 認証不要
- 常に`{"status": "healthy"}`を返す
- システムの生存確認用

### 2. API呼び出し（/api/*）
```
クライアント → API Gateway → Lambda権限チェック → main Lambda関数
     ↓              ↓                                    ↓
  APIキー     認証チェック                        実際の処理
```
- APIキー必須（x-api-keyヘッダー）
- すべてのリクエストがmain Lambda関数に転送される
- Lambda関数内でパスに応じた処理を実行

## 🔑 認証とセキュリティ

### APIキー認証
- **bubble用キー**: bubble.io統合用
- **external用キー**: 外部システム統合用

```bash
# APIキーの取得方法
aws ssm get-parameter \
  --name /lambda-api/dev/api-gateway/keys \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text | jq .
```

### 使用方法
```bash
# ヘルスチェック（認証不要）
curl https://your-api-url/health

# API呼び出し（認証必要）
curl -H "x-api-key: YOUR_API_KEY" https://your-api-url/api/users
```

## ⚙️ 環境別設定

| 設定項目 | dev | staging | prod |
|---------|-----|---------|------|
| レート制限 | 100 req/秒 | 100 req/秒 | 1000 req/秒 |
| バースト制限 | 200 | 200 | 2000 |
| 日次クォータ | 10,000 | 10,000 | 1,000,000 |
| ログ保持期間 | 3日 | 7日 | 14日 |
| X-Ray追跡 | 無効 | 無効 | 有効 |

## 📁 ファイル構成

```
lambda-api-gateway/
├── index.ts                 # メイン設定ファイル
├── components/              # コンポーネント
│   ├── ApiGatewayBase.ts   # API Gateway基本設定
│   └── ApiEndpoint.ts      # エンドポイント管理
├── package.json            # 依存関係
└── README.md              # このファイル
```

## 🚀 デプロイ方法

```bash
# 1. ディレクトリに移動
cd pulumi/lambda-api-gateway

# 2. 依存関係インストール
npm install

# 3. ビルド
npm run build

# 4. プレビュー
npm run preview

# 5. デプロイ
npm run deploy
```

## 🔄 Lambda関数との関係

API GatewayはLambda関数への「ゲートキーパー」として機能します：

1. **リクエスト受信**: HTTPリクエストを受け取る
2. **認証チェック**: APIキーを検証
3. **レート制限**: 過剰なリクエストを制限
4. **Lambda呼び出し**: 認証されたリクエストをLambda関数に転送
5. **レスポンス返却**: Lambda関数の結果をクライアントに返す

### プロキシ統合パターン

現在は「プロキシ統合」パターンを使用しています：
- `/api/{proxy+}` がすべてのサブパスをキャッチ
- リクエスト全体がLambda関数に転送される
- Lambda関数内でルーティングを処理

```javascript
// Lambda関数内でのルーティング例
exports.handler = async (event) => {
    const path = event.path;
    
    if (path === '/api/users') {
        // ユーザー処理
    } else if (path === '/api/products') {
        // 商品処理
    }
    // ...
};
```

## 🔧 トラブルシューティング

### APIキーが無効と表示される
```bash
# APIキーが有効か確認
aws apigateway get-api-key --api-key KEY_ID
```

### Lambda関数が呼び出されない
```bash
# Lambda権限を確認
aws lambda get-policy --function-name FUNCTION_NAME
```

### レート制限エラー
- 使用プランの制限に達している可能性
- バースト制限を超えている可能性

## 📝 重要な注意事項

1. **APIキーの管理**: SSM Parameter Storeに暗号化して保存
2. **CORS設定**: 本番環境では特定のドメインのみ許可
3. **ログ**: CloudWatch Logsに自動的に記録
4. **モニタリング**: CloudWatchメトリクスで監視

## 🔮 将来の拡張

### エンドポイント毎のLambda関数分離
現在はすべてのリクエストが単一のmain Lambda関数に転送されていますが、将来的には：

```
/api/users    → users Lambda関数
/api/products → products Lambda関数
/api/orders   → orders Lambda関数
```

このように、エンドポイント毎に専用のLambda関数を割り当てることが可能です。

### 実装方法
1. Lambda Functions側で新しい関数を作成
2. API Gateway側で新しいリソースとメソッドを追加
3. 各エンドポイントを対応するLambda関数に統合

## 📚 関連ドキュメント

- [Lambda Functions README](../lambda-functions/README.md)
- [AWS API Gateway ドキュメント](https://docs.aws.amazon.com/apigateway/)
- [Pulumi AWS API Gateway](https://www.pulumi.com/registry/packages/aws/api-docs/apigateway/)