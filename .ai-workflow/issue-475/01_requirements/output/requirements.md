# 要件定義書: Issue #475

**Issue番号**: #475
**タイトル**: [BugFix] dot_processor.py インポートエラーの修正
**作成日**: 2025-01-17
**優先度**: Critical

---

## 0. Planning Documentの確認

Planning Phase（`.ai-workflow/issue-475/00_planning/output/planning.md`）で以下の開発計画が策定されています：

### 計画のサマリー

- **複雑度**: 簡単（Easy）
- **見積もり工数**: 1~2時間
- **実装戦略**: CREATE（新規ファイル作成）
- **テスト戦略**: UNIT_ONLY（既存ユニットテストの実行確認）
- **テストコード戦略**: EXTEND_TEST（既存テストで十分）
- **総合リスク**: 低（Low）

### 重要な発見

Planning Phaseの調査により、以下の事実が判明しました：

**Issueの記述**:
> これらのモジュールが実際には作成されていません：
> - `urn_processor.py` - `UrnProcessor`クラス
> - `node_label_generator.py` - `NodeLabelGenerator`クラス
> - `resource_dependency_builder.py` - `ResourceDependencyBuilder`クラス

**実態**:
- **すべてのモジュールが既に実装済み**であることを確認
- `urn_processor.py`: 296行、詳細なドキュメント付き
- `node_label_generator.py`: 177行、詳細なドキュメント付き
- `resource_dependency_builder.py`: 342行、詳細なドキュメント付き
- `dot_processor.py`: 463行、すべてのインポートが正しく記述されている

**根本原因**:
- **`src/__init__.py`が存在しない**ため、Pythonが`src/`ディレクトリをパッケージとして認識できない
- これにより、`from urn_processor import UrnProcessor`のようなインポート文が`ModuleNotFoundError`を引き起こす

### 本要件定義書の方針

Planning Documentで策定された戦略に基づき、以下の方針で要件定義を実施します：

1. **スコープ**: `src/__init__.py`の作成（空ファイル）
2. **既存コード変更なし**: すべてのモジュールが実装済みのため、新規作成のみ
3. **テスト**: 既存ユニットテストが正常に実行できることの確認
4. **リスク**: 低（Pythonの標準的な問題解決）

---

## 1. 概要

### 背景

Jenkins CI/CDパイプラインで使用されているPulumiデプロイメントレポート生成機能において、モジュールインポートエラーが発生し、レポート生成が完全に失敗しています。

エラーログ:
```
ModuleNotFoundError: No module named 'urn_processor'
```

このエラーは、Issue #448のリファクタリング作業（Phase 2-3: #463）によって`dot_processor.py`が外部モジュール（`urn_processor`、`node_label_generator`、`resource_dependency_builder`）に依存するように変更された結果、発生しています。

### 目的

**主要な目的**:
- Pulumiデプロイメントレポート生成機能の復旧
- `delivery-management-jobs/development/pulumi-deployments`配下のすべてのJenkinsジョブを正常動作させる

**技術的目的**:
- Pythonパッケージ構造の正常化（`src/__init__.py`の作成）
- 既存のインポート文が正常に動作することの確認
- CI/CDパイプラインの信頼性回復

### ビジネス価値・技術的価値

**ビジネス価値**:
- **CI/CDパイプラインの可用性回復**: 本番環境のデプロイメントフローが正常化
- **可視性の回復**: Pulumiスタックの変更内容をHTMLレポートで確認可能に
- **運用効率の向上**: デプロイメント履歴の自動記録と可視化

**技術的価値**:
- **保守性の向上**: Pythonパッケージ構造が標準化される
- **拡張性の確保**: 今後のモジュール追加が容易になる
- **技術的負債の削減**: Issue #448のリファクタリングが完全に機能する

---

## 2. 機能要件

### 機能要件1: `src/__init__.py`の作成（優先度: 高）

**説明**:
Pythonが`src/`ディレクトリをパッケージとして認識するため、空の`__init__.py`ファイルを作成します。

**詳細**:
- ファイルパス: `jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/__init__.py`
- ファイル内容: 空ファイル（0バイト）
- ファイル権限: 644（rw-r--r--）
- 文字エンコーディング: UTF-8

**検証可能性**:
- `ls -la jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/__init__.py`でファイルが存在すること
- `stat -c "%a" jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/__init__.py`で権限が644であること

---

### 機能要件2: 既存モジュールのインポートエラー解消（優先度: 高）

**説明**:
`dot_processor.py`が以下のモジュールを正常にインポートできるようにします：
- `from urn_processor import UrnProcessor`
- `from node_label_generator import NodeLabelGenerator`
- `from resource_dependency_builder import ResourceDependencyBuilder`

**詳細**:
- `__init__.py`の作成により、`src/`ディレクトリがPythonパッケージとして認識される
- 既存のインポート文は**変更不要**（現状のまま動作する）

**検証可能性**:
- `python3 -c "from src.dot_processor import DotFileGenerator"`が正常に実行される
- `python3 -c "from src.urn_processor import UrnProcessor"`が正常に実行される

---

### 機能要件3: Jenkinsfileのファイルコピー処理更新（優先度: 中）

**説明**:
Jenkinsfileのline 806-813のファイルコピー処理に`__init__.py`を明示的に追加します。

**現在のコピー処理**（Jenkinsfile line 806-813）:
```groovy
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/main.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/config.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/dot_processor.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/report_generator.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/data_processor.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/charts.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/graph_processor.py .
```

**追加する処理**（line 806の前に挿入）:
```groovy
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/__init__.py . || true
```

**詳細**:
- `|| true`を付けることで、ファイルが存在しない場合でもエラーにならない（後方互換性）
- `__init__.py`は最初にコピー（慣例的な順序）

**検証可能性**:
- Jenkinsfileの該当行に`cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/__init__.py . || true`が追加されていること
- Jenkinsジョブ実行時のコンソールログに`__init__.py`のコピー処理が表示されること

---

### 機能要件4: 既存の依存モジュールの確認（優先度: 低）

**説明**:
以下のモジュールが既に実装済みであることを確認します（Planning Documentの調査結果の検証）。

**確認対象**:
- `urn_processor.py` - `UrnProcessor`クラス（296行）
- `node_label_generator.py` - `NodeLabelGenerator`クラス（177行）
- `resource_dependency_builder.py` - `ResourceDependencyBuilder`クラス（342行）

**検証可能性**:
- 各ファイルが`src/`ディレクトリに存在すること
- 各クラスが適切に定義されていること
- `dot_processor.py`のインポート文と一致していること

---

## 3. 非機能要件

### パフォーマンス要件

- **レスポンス時間**: `__init__.py`の作成によるパフォーマンスへの影響はゼロ（空ファイル）
- **インポート時間**: Pythonパッケージ認識の遅延は無視できるレベル（ミリ秒以下）

### セキュリティ要件

- **ファイル権限**: `__init__.py`は644（rw-r--r--）に設定
- **実行権限なし**: `__init__.py`は実行可能にしない（セキュリティベストプラクティス）
- **コード検証**: `__init__.py`は空ファイルのため、悪意のあるコードは含まれない

### 可用性・信頼性要件

- **CI/CDパイプラインの可用性**: 修正後、Pulumiデプロイメントレポート生成が100%成功する
- **エラー回復**: `__init__.py`が欠落しても、Jenkinsfileの`|| true`により処理が継続する（後方互換性）

### 保守性・拡張性要件

- **Pythonパッケージ標準化**: 標準的なパッケージ構造（`__init__.py`）を採用
- **将来の拡張**: 新しいモジュールを`src/`に追加する際、自動的にパッケージに含まれる
- **ドキュメント**: `__init__.py`の目的をREADMEまたはコメントで明記（オプション）

---

## 4. 制約事項

### 技術的制約

- **Pythonバージョン**: Python 3.8以上（Jenkins AgentのAMIに含まれる）
- **既存コード変更禁止**: すべてのモジュールが実装済みのため、`dot_processor.py`等の既存ファイルは**変更しない**
- **ファイル名固定**: `__init__.py`はPythonの予約ファイル名のため、変更不可

### リソース制約

- **時間**: 1~2時間（Planning Documentの見積もり）
- **工数**: 1人で実施可能（簡単な作業）
- **環境**: 開発環境（dev）で先に実施、本番環境（prod）は後続

### ポリシー制約

- **セキュリティポリシー**: ファイル権限は644に制限（実行権限なし）
- **コーディング規約**: CLAUDE.mdに従う（日本語コメント、日本語ドキュメント）
- **Git運用**: Gitリポジトリに`__init__.py`をコミット対象に追加

---

## 5. 前提条件

### システム環境

- **Jenkins**: Jenkins Controller + EC2 Fleet Agent
- **Python**: Python 3.8以上（Jenkins AgentのAMI）
- **Git**: Gitリポジトリへのアクセス権限
- **OS**: Amazon Linux 2023（Jenkins Agent）

### 依存コンポーネント

- **既存モジュール**:
  - `urn_processor.py` - 実装済み
  - `node_label_generator.py` - 実装済み
  - `resource_dependency_builder.py` - 実装済み
  - `dot_processor.py` - 実装済み（インポート文のみ機能していない）

- **Jenkinsfile**: `jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/Jenkinsfile`

### 外部システム連携

- **Pulumiバックエンド**: S3バックエンド（既存）
- **SSMパラメータストア**: Pulumi設定の取得（既存）
- **GitHub**: ソースコードリポジトリ（既存）

---

## 6. 受け入れ基準

### 受け入れ基準1: `__init__.py`の作成

**Given**: `src/`ディレクトリが存在する
**When**: `__init__.py`を作成する
**Then**:
- ファイルが`src/__init__.py`に存在すること
- ファイル権限が644であること
- ファイル内容が空（0バイト）であること
- Gitリポジトリにコミット可能な状態であること

---

### 受け入れ基準2: インポートエラーの解消

**Given**: `__init__.py`が作成されている
**When**: `dot_processor.py`をインポートする
**Then**:
- `python3 -c "from src.dot_processor import DotFileGenerator"`が成功すること
- `python3 -c "from src.urn_processor import UrnProcessor"`が成功すること
- `ModuleNotFoundError`が発生しないこと

---

### 受け入れ基準3: 既存ユニットテストの成功

**Given**: `__init__.py`が作成されている
**When**: 既存のユニットテスト（`tests/test_dot_processor.py`が存在する場合）を実行する
**Then**:
- すべてのテストケースが成功すること
- インポートエラーが発生しないこと

---

### 受け入れ基準4: Jenkinsfileの更新

**Given**: Jenkinsfileのline 806-813にファイルコピー処理が存在する
**When**: `__init__.py`のコピー処理を追加する
**Then**:
- `cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/__init__.py . || true`が追加されていること
- 既存のファイルコピー処理が影響を受けないこと
- Jenkinsfileの構文が正しいこと

---

### 受け入れ基準5: Jenkinsジョブの成功

**Given**: `__init__.py`とJenkinsfileが更新されている
**When**: `delivery-management-jobs/development/pulumi-deployments`のJenkinsジョブを実行する
**Then**:
- レポート生成処理が成功すること
- HTMLレポートが生成されること
- `ModuleNotFoundError`が発生しないこと
- ビルドステータスが`SUCCESS`または`UNSTABLE`であること（`UNSTABLE`はPulumiアクションのエラーのみ）

---

## 7. スコープ外

### 明確にスコープ外とする事項

1. **既存モジュールの修正**:
   - `urn_processor.py`、`node_label_generator.py`、`resource_dependency_builder.py`は実装済みのため、修正不要
   - `dot_processor.py`のロジック変更は不要（インポート文は既に正しい）

2. **新規ユニットテストの作成**:
   - 既存のテストが十分であるため、新規テスト作成は不要
   - `__init__.py`に対するテストは不要（空ファイル）

3. **リファクタリング作業**:
   - Issue #448のその他のPhaseは別Issue
   - コードの品質改善は今回のスコープ外

4. **ドキュメント更新**:
   - README.mdやCONTRIBUTION.mdの更新は不要（軽微な修正のため）
   - Issue #475のコメントに根本原因と解決方法を記載するのみ

### 将来的な拡張候補

1. **`__init__.py`のドキュメント化**:
   - パッケージの目的を説明するdocstringの追加（オプション）

2. **自動テストの追加**:
   - CI/CDパイプラインでインポートエラーを自動検出するテスト

3. **パッケージ構造の最適化**:
   - `__init__.py`で公開APIを明示的にエクスポート（`__all__`の定義）

---

## 付録A: ファイル構造

### 修正前

```
jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/
├── src/
│   ├── (NO __init__.py)  ← これが原因
│   ├── main.py
│   ├── config.py
│   ├── dot_processor.py  ← インポートエラー発生
│   ├── report_generator.py
│   ├── data_processor.py
│   ├── charts.py
│   ├── graph_processor.py
│   ├── urn_processor.py  ← 実装済み
│   ├── node_label_generator.py  ← 実装済み
│   └── resource_dependency_builder.py  ← 実装済み
├── templates/
│   ├── pulumi_report.html
│   └── pulumi_styles.css
└── Jenkinsfile
```

### 修正後

```
jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/
├── src/
│   ├── __init__.py  ← **NEW: 空ファイル**
│   ├── main.py
│   ├── config.py
│   ├── dot_processor.py  ← インポート成功
│   ├── report_generator.py
│   ├── data_processor.py
│   ├── charts.py
│   ├── graph_processor.py
│   ├── urn_processor.py  ← 既存
│   ├── node_label_generator.py  ← 既存
│   └── resource_dependency_builder.py  ← 既存
├── templates/
│   ├── pulumi_report.html
│   └── pulumi_styles.css
└── Jenkinsfile  ← __init__.pyのコピー処理を追加
```

---

## 付録B: インポートエラーの詳細

### エラートレースバック

```
Traceback (most recent call last):
  File ".../main.py", line 9, in <module>
    from report_generator import PulumiReportGenerator
  File ".../report_generator.py", line 11, in <module>
    from graph_processor import DependencyGraphProcessor
  File ".../graph_processor.py", line 10, in <module>
    from dot_processor import DotFileGenerator, DotFileProcessor
  File ".../dot_processor.py", line 7, in <module>
    from urn_processor import UrnProcessor
ModuleNotFoundError: No module named 'urn_processor'
```

### 根本原因

Pythonは`src/`ディレクトリに`__init__.py`がないため、`src/`を**通常のディレクトリ**として扱います。

**問題**:
- `from urn_processor import UrnProcessor`は、`sys.path`上の`urn_processor.py`を探す
- しかし、`urn_processor.py`は`src/`ディレクトリ内にある
- `src/`がパッケージとして認識されていないため、`urn_processor`が見つからない

**解決方法**:
- `src/__init__.py`を作成することで、Pythonが`src/`を**パッケージ**として認識
- `from src.urn_processor import UrnProcessor`または相対パス内での`from urn_processor import UrnProcessor`が機能する

---

## 付録C: Jenkinsfileの該当箇所

### 現在の処理（line 806-813）

```groovy
# Pythonスクリプトファイルのコピー
echo "Pythonスクリプトファイルのコピー..."
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/main.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/config.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/dot_processor.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/report_generator.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/data_processor.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/charts.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/graph_processor.py .
```

### 修正後（line 806に挿入）

```groovy
# Pythonスクリプトファイルのコピー
echo "Pythonスクリプトファイルのコピー..."
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/__init__.py . || true  # ← **NEW**
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/main.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/config.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/dot_processor.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/report_generator.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/data_processor.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/charts.py .
cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/graph_processor.py .
```

**理由**:
- `|| true`を付けることで、`__init__.py`が存在しない場合でもエラーにならない
- 後方互換性を確保（古いバージョンのリポジトリでもビルドが失敗しない）

---

## 品質ゲート（Phase 1）確認結果

以下の品質ゲートを満たしていることを確認します：

- ✅ **機能要件が明確に記載されている**
  - 4つの機能要件が具体的かつ測定可能な形で定義されている
  - 各要件に検証可能性が明記されている

- ✅ **受け入れ基準が定義されている**
  - 5つの受け入れ基準がGiven-When-Then形式で記載されている
  - 各基準がテスト可能である

- ✅ **スコープが明確である**
  - スコープ内（`__init__.py`作成、Jenkinsfile更新）が明確
  - スコープ外（既存モジュール修正、新規テスト作成）が明示されている

- ✅ **論理的な矛盾がない**
  - Planning Documentの調査結果と整合性がある
  - 機能要件と受け入れ基準が対応している
  - 非機能要件が技術的制約と矛盾していない

---

**次のステップ**: Phase 2（設計フェーズ）に進み、実装の詳細設計を行います。
