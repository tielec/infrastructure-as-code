## 品質ゲート評価

- [x] **実装戦略の判断根拠が明記されている**: PASS - EXTEND選定理由が既存資産の拡張である点と要件対応（FR-1〜4）に結び付けて説明されています (@.ai-workflow/issue-391/02_design/output/design.md:56-60)。
- [x] **テスト戦略の判断根拠が明記されている**: PASS - Pulumiユニット＋Jenkins統合テストの必要性が機能特性と非機能要件に紐づけて整理されています (@.ai-workflow/issue-391/02_design/output/design.md:62-190)。
- [x] **既存コードへの影響範囲が分析されている**: PASS - IaC、パイプライン、DSL、スクリプト、ドキュメントまで網羅されています (@.ai-workflow/issue-391/02_design/output/design.md:74-80)。
- [x] **変更が必要なファイルがリストアップされている**: PASS - 既存/新規ファイルが用途付きで具体的パスとして列挙されています (@.ai-workflow/issue-391/02_design/output/design.md:82-95)。
- [x] **設計が実装可能である**: PASS - 各コンポーネントの詳細設計・手順・実装順が提示されており、作業イメージが明確です (@.ai-workflow/issue-391/02_design/output/design.md:99-244)。

## 詳細レビュー

### 1. 戦略判断の妥当性

**良好な点**:
- Pulumi/Jenkinsいずれも既存資産を拡張するという判断が要件内容に合致しています (@.ai-workflow/issue-391/02_design/output/design.md:56-60)。
- テスト戦略がユニット＋統合の2層で整理され、複雑度とリスクに見合っています (@.ai-workflow/issue-391/02_design/output/design.md:62-190)。

**懸念点**:
- なし。

### 2. 影響範囲分析の適切性

**良好な点**:
- コード、スクリプト、ドキュメント、開発者ガイドまで含めた影響範囲が俯瞰されています (@.ai-workflow/issue-391/02_design/output/design.md:74-80)。

**懸念点**:
- JenkinsfileをScriptedへ全面移行することによる既存Declarative依存の確認ポイントが明示されていない点はリリースリスクになり得ます (@.ai-workflow/issue-391/02_design/output/design.md:131-154)。

### 3. ファイルリストの完全性

**良好な点**:
- 変更/追加ファイルが用途込みで列挙されており、テスト資材やモックまで網羅されています (@.ai-workflow/issue-391/02_design/output/design.md:82-95)。

**懸念点**:
- Runbookファイルが未存在の場合の扱い（新規作成可否）が曖昧です (@.ai-workflow/issue-391/02_design/output/design.md:94-95)。

### 4. 設計の実装可能性

**良好な点**:
- Pulumi側の関数分割・Provider管理・命名規則が明文化され実装しやすい構成です (@.ai-workflow/issue-391/02_design/output/design.md:99-127)。
- Jenkinsパイプラインのステージ構成とエラー処理が詳細に記述されています (@.ai-workflow/issue-391/02_design/output/design.md:131-156)。

**懸念点**:
- 失敗時に未実行リージョンを記録せず停止する設計のため、運用上どのリージョンが未処理か追跡しづらい懸念があります (@.ai-workflow/issue-391/02_design/output/design.md:147-154)。
- `collect_parameters.sh`での`rm -f ${DATA_DIR}/*`は引数検証が無いと誤削除リスクがあるため安全策が欲しいです (@.ai-workflow/issue-391/02_design/output/design.md:167-170)。

### 5. 要件との対応

**良好な点**:
- FR-1〜5がトレーサビリティ表で明確に紐付けられています (@.ai-workflow/issue-391/02_design/output/design.md:193-200)。

**懸念点**:
- なし。

### 6. セキュリティ考慮

**良好な点**:
- バケット暗号化やPublic Access Blockなどの具体施策が明記されています (@.ai-workflow/issue-391/02_design/output/design.md:224-227)。

**改善の余地**:
- Pulumi側で暗号化・Public Access Block設定が失敗した場合のフォールバックや検証手順があると更に安心です。

### 7. 非機能要件への対応

**良好な点**:
- タイムアウト計算やスケーラビリティ確保の方針が整理されています (@.ai-workflow/issue-391/02_design/output/design.md:229-233)。

**改善の余地**:
- Jenkinsパイプラインの順次実行で想定より時間が掛かった際のスローダウン検知（例：メトリクス化）の記載があるとMonitoring設計が補完できます。

## ブロッカー（BLOCKER）

**次フェーズに進めない重大な問題**

- なし。

## 改善提案（SUGGESTION）

**次フェーズに進めるが、改善が望ましい事項**

1. **Scripted移行の影響確認**
   - 現状: DeclarativeからScriptedへの置換理由は記載されていますが、Declarative固有機能（`post`や`options`ブロック、自動パラメータ取り扱い等）への影響評価が示されていません (@.ai-workflow/issue-391/02_design/output/design.md:131-155)。
   - 提案: 既存で利用しているDeclarative特有の機能・プラグイン依存を棚卸しして設計に明記するか、代替手段を示すと安心です。
   - 効果: 予期せぬパイプライン挙動変化や運用手順の差分を事前に抑止。

2. **未実行リージョンのサマリ補完**
   - 現状: 失敗時は即停止し、`regionSummaries`に失敗リージョンのみ記録する想定です (@.ai-workflow/issue-391/02_design/output/design.md:147-154)。
   - 提案: 停止時点で未実行リージョンを`SKIPPED`として記録し、通知で一覧化できるようにすると運用判断が容易です。
   - 効果: どこまで成功したかの把握が簡単になり、再実行範囲の判断が迅速になります。

3. **DATA_DIR削除の安全策**
   - 現状: `rm -f ${DATA_DIR}/*`でクリアする方針ですが、誤った環境変数設定時に他ディレクトリを消すリスクがあります (@.ai-workflow/issue-391/02_design/output/design.md:167-170)。
   - 提案: `DATA_DIR`の値検証（例: 空文字禁止、`/tmp/jenkins`配下限定チェック）や`find ... -maxdepth 1 -type f -delete`など安全な消し方を追記するとリスク低減になります。
   - 効果: テスト・本番双方での誤操作によるデータ消失防止。

4. **Runbook有無の明確化**
   - 現状: `docs/runbooks/ssm-backup.md`が存在しない場合の扱いが曖昧です (@.ai-workflow/issue-391/02_design/output/design.md:94-95)。
   - 提案: 未存在なら新規作成する、あるいは代替ドキュメントを指定する等の判断を明記すると実装時の迷いが減ります。
   - 効果: ドキュメント更新タスクの抜け漏れ防止。

## 総合評価

**主な強み**:
- 実装/テスト戦略が要件と整合し、Pulumi・Jenkins両面で実行手順まで具体化されている点。
- 影響範囲・ファイルリスト・トレーサビリティが体系的にまとめられ、実装フェーズの迷いが少ない。

**主な改善提案**:
- Scripted移行時の互換性確認と失敗時サマリの充実など、運用面のフォローを追記するとより万全。
- スクリプトの安全策やRunbook整備方針を明確化し、リスクと作業指示を一層明瞭にする。

全体として要件を満たす実装方針とテスト計画が示されており、次フェーズ（テストシナリオ策定）へ進む準備は整っています。上記改善提案は運用・安全性を一段高めるための追加検討としてご参照ください。

---
**判定: PASS_WITH_SUGGESTIONS**