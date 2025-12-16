# テスト実装完了レポート

## テストファイル一覧

| ファイル | テスト数 | カバー対象 |
|---------|---------|-----------|
| `tests/integration/ecs-image/test_ecs_image_pipeline.sh` | 6 | SSM出力、Image Builderパイプライン状態、ContainerRecipe/Distribution/Infrastructure構成、コンポーネント定義 |
| `tests/integration/ecs-image/test_ansible_playbooks.sh` | 2 | デプロイ/削除プレイブックの構文検証、confirmガードの動作確認 |
| `tests/integration/ecs-image/test_pulumi_stack.sh` | 2 | Pulumi previewの完走確認、2回目`pulumi up`でのno changes判定（INT-ECS-IMG-013/014） |
| `tests/integration/ecs-image/test_component_yaml.sh` | 2 | component.ymlの構文/必須フィールド検証、ツール導入・ユーザー作成・entrypoint配置ステップ確認（INT-ECS-IMG-015/016） |

## テストカバレッジ

- ユニットテスト: 0件
- 統合テスト: 12件
- BDDテスト: 0件
- カバレッジ率: N/A（AWS統合検証のため未計測）

## 実行上の補足

- AWS CLIと`jq`、`ansible-playbook`、`pulumi`、`npm`、`yamllint`が必要です。`ENVIRONMENT`/`AWS_REGION`や`PULUMI_STACK`を環境変数で上書きしてターゲット環境を切り替えられます。
- 既存スタックのSSMパラメータが存在する前提で検証を行うため、Pulumiスタックをデプロイ済みの環境で実行してください。Pulumi関連テストはスタック選択後に`pulumi up`を2回実行するため、本番環境での実行時は注意してください。

## 修正履歴

### 修正1: Pulumi preview/idempotence シナリオの自動化
- **指摘内容**: INT-ECS-IMG-013/014（Pulumi previewと冪等性）のテストが欠落している。
- **修正内容**: `tests/integration/ecs-image/test_pulumi_stack.sh` を追加し、`npm install`→`pulumi stack select`→`pulumi preview`でリソースタイプを確認し、`pulumi up`を2回連続実行して2回目に`no changes`が出ることを検証。
- **影響範囲**: `tests/integration/ecs-image/test_pulumi_stack.sh`, `tests/integration/ecs-image/helpers.sh`

### 修正2: Component YAMLの構文/ツール検証の追加
- **指摘内容**: INT-ECS-IMG-015/016（component.ymlの構文チェックとツールインストール確認）が未実装。
- **修正内容**: `tests/integration/ecs-image/test_component_yaml.sh` を追加し、`yamllint`による構文検証、必須フィールド（name/description/schemaVersion, build/validateフェーズ）の存在確認、およびJava21・Node.js20・AWS CLI v2・Pulumi・Ansible・Git・Python3・jenkinsユーザー作成・entrypoint配置の各ステップ存在チェックを実装。
- **影響範囲**: `tests/integration/ecs-image/test_component_yaml.sh`, `pulumi/jenkins-agent-ecs-image/component.yml`（参照のみ）

### 修正3: テストヘルパーの共通化
- **指摘内容**: Task 5-2の共通ユーティリティ未作成により重複が多い。
- **修正内容**: `tests/integration/ecs-image/helpers.sh` を新設し、ロギング・コマンド存在確認・SSMパラメータ取得・正規表現/部分一致アサーション・サマリー初期化/テスト実行ヘルパーを集約。既存スクリプトと新規スクリプトで共通利用。
- **影響範囲**: `tests/integration/ecs-image/helpers.sh`, `tests/integration/ecs-image/test_ecs_image_pipeline.sh`, `tests/integration/ecs-image/test_ansible_playbooks.sh`, `tests/integration/ecs-image/test_pulumi_stack.sh`, `tests/integration/ecs-image/test_component_yaml.sh`
