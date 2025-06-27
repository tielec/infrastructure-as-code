# 複雑度解析レポート生成の詳細ガイド

## 関数別の具体的な改善パターン

### 1. 高い認知的複雑度（15以上）への対処法

#### パターンA: 深いネストの解消
```python
# 問題: 3重以上のネスト
def process_orders(orders):
    for order in orders:
        if order.status == 'pending':
            for item in order.items:
                if item.available:
                    # 処理...

# 改善: 早期continueとメソッド抽出
def process_orders(orders):
    pending_orders = [o for o in orders if o.status == 'pending']
    for order in pending_orders:
        process_order_items(order)

def process_order_items(order):
    available_items = [i for i in order.items if i.available]
    for item in available_items:
        # 処理...
```

#### パターンB: 複雑な条件分岐の整理
```python
# 問題: 複雑な条件式
if (user.age >= 18 and user.country in ['US', 'CA'] and 
    user.verified and not user.banned and 
    (user.subscription == 'premium' or user.trial_active)):

# 改善: 意味のある名前を持つメソッドに
def can_access_premium_content(user):
    return (is_adult(user) and 
            is_from_supported_region(user) and
            is_verified_active_user(user) and
            has_premium_access(user))
```

### 2. 高い循環的複雑度（10以上）への対処法

#### パターンA: Switch文/多分岐の最適化
```python
# 問題: 多数のif-elif
def calculate_discount(customer_type):
    if customer_type == 'gold':
        return 0.20
    elif customer_type == 'silver':
        return 0.15
    elif customer_type == 'bronze':
        return 0.10
    # ... 続く

# 改善: 辞書マッピング
DISCOUNT_RATES = {
    'gold': 0.20,
    'silver': 0.15,
    'bronze': 0.10,
    # ...
}

def calculate_discount(customer_type):
    return DISCOUNT_RATES.get(customer_type, 0.0)
```

#### パターンB: ポリモーフィズムの活用
```python
# 問題: タイプ別の処理分岐
def process_payment(payment):
    if payment.type == 'credit_card':
        # クレジットカード処理
    elif payment.type == 'paypal':
        # PayPal処理
    elif payment.type == 'bank_transfer':
        # 銀行振込処理

# 改善: Strategy パターン
class PaymentProcessor:
    def process(self, payment):
        processor = self._get_processor(payment.type)
        return processor.process(payment)
```

## 複雑度別の対応テンプレート

### 🔴 非常に高い複雑度（認知的 > 20）

```markdown
**緊急対応が必要**: `関数名`
- 現在の認知的複雑度: XX（閾値の X 倍）
- 主な問題:
  - [ ] X重のネストレベル
  - [ ] Y個の条件分岐
  - [ ] Z個の異なる処理フロー
- 推奨アクション:
  1. まず、処理を3-4個の小関数に分割
  2. 各関数は単一の責任を持つように設計
  3. 共通処理を抽出してヘルパーメソッド化
```

### 🟠 高い複雑度（認知的 15-20）

```markdown
**改善推奨**: `関数名`
- 現在の認知的複雑度: XX
- 改善ポイント:
  - 条件分岐を早期リターンで簡略化
  - 複雑な条件式を説明的な変数に抽出
  - 必要に応じて処理を2つの関数に分割
```

### 🟡 警告レベル（認知的 10-14）

```markdown
**監視対象**: `関数名`
- 現在の認知的複雑度: XX
- 注意点: 今後の変更で複雑度が増加しないよう注意
- 可能であれば、次回のリファクタリング時に改善を検討
```

## 言語別の特記事項

### Python
- リスト内包表記やジェネレータで複雑度を下げられる場合がある
- `@property`デコレータでゲッター/セッターの複雑度を分散
- 型ヒントを活用して可読性を向上

### JavaScript/TypeScript
- async/awaitで非同期処理の複雑度を削減
- Optional chainingで null チェックを簡略化
- 分割代入で変数の取り出しを簡潔に

### Java
- Stream APIで繰り返し処理の複雑度を削減
- Optional型でnullチェックを簡略化
- ビルダーパターンで複雑なオブジェクト生成を整理

### Go
- エラーハンドリングは複雑度を上げるが、これは言語仕様
- インターフェースを活用して条件分岐を削減
- goroutineで並行処理の複雑度を管理

## レポートの差別化要素

### 1. 段階的改善プラン
```markdown
## 📋 段階的改善プラン

### Phase 1（1-2時間）
- [ ] `function1`の早期リターン適用
- [ ] `function2`の条件式抽出

### Phase 2（半日）
- [ ] `function3`を3つの小関数に分割
- [ ] 共通処理をユーティリティクラスに移動

### Phase 3（1日）
- [ ] 全体的なアーキテクチャの見直し
- [ ] デザインパターンの適用検討
```

### 2. ビジネスインパクトの説明
- 🐛 バグリスク: 複雑度が高いとバグ混入率がX倍に
- 🔧 保守性: 新メンバーの理解にかかる時間が増加
- 🧪 テスト: 必要なテストケース数が指数関数的に増加

### 3. 成功指標の提示
```markdown
## 📊 改善後の目標値
- 平均認知的複雑度: 現在 X.X → 目標 Y.Y
- 最大認知的複雑度: 現在 XX → 目標 YY
- 閾値超過関数数: 現在 X個 → 目標 0個
```