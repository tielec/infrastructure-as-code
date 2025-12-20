# Jenkins Agent Spot Instance サイジング分析

## 調査日時
2025-12-20

## 現在の問題

### 1. ap-northeast-1cでt3a.mediumが利用不可
- **エラー**: `requested instance type is not supported in the requested Availability Zone`
- **原因**: t3a.mediumはap-northeast-1a、1dでのみ利用可能
- **対応**: PR #504でAZ別にインスタンスタイプを設定（修正済み）

### 2. Fleet Overprovisioned（正常動作）
- **メッセージ**: `Fleet overprovisioned to meet target capacity`
- **原因**: `agent-min-capacity: 0`（オンデマンド起動設定）
- **対応**: 意図的な設定のため対応不要

## 現在の設定（medium）

### インスタンス仕様
| インスタンス | vCPU | メモリ | AZ対応 | 優先度 |
|------------|------|--------|--------|--------|
| t4g.medium | 2    | 4 GiB  | 1a, 1c, 1d | 1 |
| t3a.medium | 2    | 4 GiB  | 1a, 1d | 2 |
| t3.medium  | 2    | 4 GiB  | 1a, 1c, 1d | 3 |

### AZ別設定（PR #504）
- **ap-northeast-1a**: t4g.medium → t3a.medium → t3.medium
- **ap-northeast-1c**: t4g.medium → t3.medium（t3a.mediumを除外）

## 利用可能なインスタンスタイプ（小サイズ）

### ap-northeast-1a（すべて利用可能）
- ✅ t4g.small, t4g.micro (ARM)
- ✅ t3a.small, t3a.micro (x86, AMD)
- ✅ t3.small, t3.micro (x86, Intel)

### ap-northeast-1c（t3aシリーズは利用不可）
- ✅ t4g.small, t4g.micro (ARM)
- ❌ t3a.small, t3a.micro (利用不可)
- ✅ t3.small, t3.micro (x86, Intel)

### ap-northeast-1d
- ✅ すべてのインスタンスタイプ利用可能

## コスト比較（オンデマンド料金、ap-northeast-1）

| インスタンス | vCPU | メモリ | 時間単価(USD) | 月額概算(USD) | mediumとの比較 |
|------------|------|--------|--------------|--------------|---------------|
| t4g.micro  | 2    | 1 GiB  | ~$0.0084     | ~$6.05       | -75% |
| t3.micro   | 2    | 1 GiB  | ~$0.0136     | ~$9.79       | -75% |
| t3a.micro  | 2    | 1 GiB  | ~$0.0122     | ~$8.78       | -75% |
| t4g.small  | 2    | 2 GiB  | ~$0.0168     | ~$12.10      | -50% |
| t3.small   | 2    | 2 GiB  | ~$0.0272     | ~$19.58      | -50% |
| t3a.small  | 2    | 2 GiB  | ~$0.0244     | ~$17.57      | -50% |
| **t4g.medium** | 2    | 4 GiB  | ~$0.0336 | ~$24.19      | 基準（ARM） |
| **t3.medium**  | 2    | 4 GiB  | ~$0.0544 | ~$39.17      | 基準（x86） |
| **t3a.medium** | 2    | 4 GiB  | ~$0.0488 | ~$35.14      | 基準（x86 AMD） |

**注**: Spotインスタンス料金はオンデマンドより60-90%安くなります。

## サイジング推奨案

### オプション1: コスト最適化（軽量ビルド向け）
**推奨**: t4g.small/t3.small をメインに使用

#### 設定イメージ
- **ap-northeast-1a**: t4g.small → t3a.small → t3.small → t4g.medium（フォールバック）
- **ap-northeast-1c**: t4g.small → t3.small → t4g.medium（フォールバック）

#### メリット
- コスト約50%削減
- 2 vCPU, 2GB メモリで軽量～中程度のビルドに対応
- ARMベース（t4g）は更にコスト優位

#### デメリット
- 重量級ビルド（大規模コンパイル、メモリ消費の多いテスト）には不向き
- メモリ不足のリスク

### オプション2: バランス型
**推奨**: small優先、mediumをセーフティネットに

#### 設定イメージ
- **ap-northeast-1a**: t4g.small → t3a.small → t3.small → t4g.medium → t3a.medium → t3.medium
- **ap-northeast-1c**: t4g.small → t3.small → t4g.medium → t3.medium

#### メリット
- 通常はsmallで低コスト
- 必要に応じてmediumにスケール
- Spot Fleet の lowestPrice戦略で自動最適化

#### デメリット
- 設定が複雑
- ビルド時間がインスタンスサイズで変動する可能性

### オプション3: micro追加（最小コスト）
**推奨**: 非常に軽量なビルド専用エージェント

#### 設定イメージ
- **ap-northeast-1a**: t4g.micro → t3a.micro → t3.micro → t4g.small → ...
- **ap-northeast-1c**: t4g.micro → t3.micro → t4g.small → ...

#### メリット
- 最小コスト（mediumの約1/4）
- 1GB メモリで動作する軽量タスク向け

#### デメリット
- メモリ1GBは非常に制約が大きい
- ほとんどのビルドで不足する可能性が高い

### オプション4: 現状維持（推奨）
**推奨**: medium のまま

#### メリット
- 4GB メモリで余裕がある
- ほぼすべてのビルドに対応
- パフォーマンスが安定

#### デメリット
- コストが高い

## 推奨アクション

### 短期（すぐに実施）
1. **PR #504をマージ**: AZ別インスタンスタイプ設定の適用
2. **現状維持**: まずmediumのままで安定稼働を確認

### 中期（運用データ収集後）
1. **ビルドメトリクス収集**:
   - メモリ使用量の最大値
   - CPU使用率
   - ビルド時間
2. **データに基づいてサイジング判断**:
   - メモリ使用量が常に2GB以下 → smallに変更検討
   - メモリ使用量が2-4GB → バランス型（オプション2）
   - メモリ使用量が頻繁に4GB近く → 現状維持

### 長期（最適化）
1. **ビルドタイプ別のエージェントプール**:
   - 軽量ビルド用: small
   - 重量級ビルド用: medium または large
2. **Jenkinsラベル設定**でビルドごとに適切なエージェントを選択

## 技術的制約

### 重要: t3aシリーズのAZ制限
- **ap-northeast-1a**: すべてのt3aインスタンス利用可能
- **ap-northeast-1c**: t3aシリーズすべて利用不可
- **ap-northeast-1d**: すべてのt3aインスタンス利用可能

### Spot Fleet設定での考慮事項
- `allocationStrategy: "lowestPrice"` を使用
- 優先度（priority）設定で希望順を制御
- サブネットごとに異なるインスタンスタイプを設定可能

## 関連Issue/PR
- Issue #503: Spot Fleet設定でap-northeast-1cにてt3a.mediumが利用不可
- PR #504: Spot Fleet設定でAZ別にインスタンスタイプを設定

## 次のステップ
1. ✅ PR #504をマージ
2. ⬜ Pulumiでデプロイ
3. ⬜ Jenkins Agent起動確認
4. ⬜ ビルド実行とメトリクス収集
5. ⬜ データに基づいてサイジング再検討
