## 品質ゲート評価
- [x] **Phase 3のテストシナリオがすべて実装されている**: PASS - Pulumiの検証6件とパイプライン/collect_parametersの統合シナリオがそれぞれ `index.test.ts` と `test_pipeline_runner.py`, `test_collect_parameters.py` に落とし込まれています。
- [x] **テストコードが実行可能である**: PASS - Jest/Pulumiモックと Python unittest のいずれも依存関係を満たせばそのまま動作する構成で、テスト内で環境/一時ディレクトリを完結に構築しています。
- [x] **テストの意図がコメントで明確**: PASS - 各テスト定義直前に日本語コメントで狙いと期待値が示されており、意図が追いやすいです。

## 詳細レビュー

### 1. テストシナリオとの整合性
**良好な点**:
- Pulumi設定の異常系2件を `pulumi/jenkins-ssm-backup-s3/__tests__/index.test.ts:185-199` で明確にカバーしており、シナリオ通りの例外メッセージを確認しています。
- バケット作成・SSMメタデータ・legacyキー・exportの正常系が `pulumi/jenkins-ssm-backup-s3/__tests__/index.test.ts:201-292` でシナリオ通り検証されています。
- Jenkinsパイプラインの成功/2リージョン目失敗シナリオが `jenkins/jobs/pipeline/admin/ssm-backup/tests/test_pipeline_runner.py:39-60` に実装されています。
- collect_parameters のディレクトリ初期化シナリオが `jenkins/jobs/pipeline/admin/ssm-backup/tests/test_collect_parameters.py:17-57` で再現されています。

**懸念点**:
- `ssmHomeRegion` プロバイダの利用有無はシナリオ上の重要点ですが、`pulumi/jenkins-ssm-backup-s3/__tests__/index.test.ts:258-275` では値のみを検証しており、リージョンを取り違えても検知できません（fixtureも defaultRegion と同一）。

### 2. テストカバレッジ
**良好な点**:
- Pulumi側はバケット/SSM両リソースを網羅し、legacyエクスポートやOutput検証まで行っているため主要機能を押さえています（`index.test.ts:201-292`）。
- パイプライン統合テストが成果物(JSON)とログ両面をチェックし、成功・途中失敗の挙動差分を抑えています（`test_pipeline_runner.py:41-60`）。
- collect_parameters テストは旧ファイル削除と主要成果物生成の確認で期待アウトカムを押さえています（`test_collect_parameters.py:52-56`）。

**改善の余地**:
- `ssmHomeRegion` を defaultRegion と異なる値で設定し、モックがそのプロバイダを使っているかを検証できるようにするとリージョン取り違えの退行を防げます。

### 3. テストの独立性
**良好な点**:
- Pulumi側は `registerMocks` で毎回 state を初期化し（`index.test.ts:58-175`）、jest のモジュールキャッシュもリセットしているためテスト間の汚染がありません。
- Python側は `tempfile.TemporaryDirectory` を用いて都度作業パスを分離しており（`test_pipeline_runner.py:16-37`, `test_collect_parameters.py:22-36`）、状態共有が起きにくい構造です。

**懸念点**:
- 特になし。

### 4. テストの可読性
**良好な点**:
- 期待シナリオがコメントで明示され、日本語での Given/When/Then が読み取りやすいです（例: `index.test.ts:185-229`、`test_pipeline_runner.py:39-60`）。
- 変数名も `recordedResources`, `run_scenario` など意図が把握しやすいものになっています。

**改善の余地**:
- 特になし（現状でも十分把握しやすいです）。

### 5. モック・スタブの使用
**良好な点**:
- Pulumiの `setMocks` を拡張して S3/SSM リソースの期待値をモック計算しており（`index.test.ts:58-158`）、実リソースに頼らず挙動を追える設計です。
- Jenkins統合テストではカスタム `aws` スタブを PATH に挿入して CLI 応答を固定化しているため、外部依存を排除できています（`test_collect_parameters.py:38-41`）。

**懸念点**:
- `RecordedResource` に provider 情報が残らないため、 `ssmHomeRegion` が正しいリージョンで使われたか検証できません。

### 6. テストコードの品質
**良好な点**:
- Pulumi Output を `await` して実際のマップ値を確認するなど、アサーションが具体的で役に立ちます（`index.test.ts:230-292`）。
- Pythonテストも subprocess の stdout/成果物ファイルを検査しており、振る舞いを直接検証しています（`test_pipeline_runner.py:41-60`, `test_collect_parameters.py:44-57`）。

**懸念点**:
- 特になし。

## ブロッカー（BLOCKER）
**次フェーズに進めない重大な問題**
- なし

## 改善提案（SUGGESTION）
1. **SSMホームリージョンの検証強化**  
   - 現状: `publishes region metadata...` テストでは値のみを確認しており、`ssmHomeRegion` が defaultRegion と同じためプロバイダの取り違えを検知できません（`pulumi/jenkins-ssm-backup-s3/__tests__/index.test.ts:258-275`）。  
   - 提案: フィクスチャで `ssmHomeRegion` を別リージョンにし、`MockResourceArgs` から provider 情報（`args.provider` や `state.region`）を記録して SSM パラメータがホームリージョン向けプロバイダで作成されていることを主張する。  
   - 効果: メタデータを誤ったリージョンに書き込む退行を防ぎ、シナリオで求められていた要件を確実に守れます。

## 総合評価
**主な強み**:
- Pulumi・Jenkins 双方の主要シナリオが漏れなくテスト化されており、異常系も押さえています。
- モックと一時ディレクトリを活用した独立性の高いテスト設計で、再現性と可読性が高いです。

**主な改善提案**:
- `ssmHomeRegion` の利用リージョン検証を追加し、リージョン設定まわりの退行検出力をさらに高めるとより安心です。

総じて次フェーズへ進める品質であり、上記の改善を取り込めばテストの信頼性が一段と向上します。

---
**判定: PASS_WITH_SUGGESTIONS**