# テスト実装完了レポート

## テストファイル一覧

| ファイル | テスト数 | カバー対象 |
|---------|---------|-----------|
| `tests/integration/ecs-image/test_ecs_image_pipeline.sh` | 6 | SSM出力、Image Builderパイプライン状態、ContainerRecipe/Distribution/Infrastructure構成、コンポーネント定義 |
| `tests/integration/ecs-image/test_ansible_playbooks.sh` | 2 | デプロイ/削除プレイブックの構文検証、confirmガードの動作確認 |

## テストカバレッジ

- ユニットテスト: 0件
- 統合テスト: 8件
- BDDテスト: 0件
- カバレッジ率: N/A（AWS統合検証のため未計測）

## 実行上の補足

- AWS CLIと`jq`、`ansible-playbook`が必要です。`ENVIRONMENT`や`AWS_REGION`を環境変数で上書きしてターゲット環境を切り替えられます。
- 既存スタックのSSMパラメータが存在する前提で検証を行うため、Pulumiスタックをデプロイ済みの環境で実行してください。
