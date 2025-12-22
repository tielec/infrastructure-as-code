# テスト実行結果

## テスト結果サマリー

- 総テスト数: 8件
- 成功: 4件
- 失敗: 4件
- 成功率: 50%

## 条件分岐

### `tests/integration/test_ansible_lint_integration.py::AnsibleLintIntegrationTests::test_ansible_directory_ansible_lint`
- **エラー**: `ansible-lint ansible/` は `ansible/playbooks/bootstrap-setup.yml` を含む多数のファイルで `package-latest`, `command-instead-of-module`, `command-instead-of-shell`, `yaml[truthy]`, `name[template]`, `risky-shell-pipe`, `ignore-errors`, `no-changed-when`、`var-naming` 等の違反を検出し、207件の致命的違反が報告されている (`/tmp/ansible-lint-test.log` 参照)。
- **スタックトレース**: ansible-lint が exit code 2 で終了し、stdout に上述のルール違反が連続して表示されている。

### `tests/integration/test_ansible_lint_integration.py::AnsibleLintIntegrationTests::test_bootstrap_playbook_ansible_lint`
- **エラー**: `ansible-lint bootstrap-setup.yml` は同じルール群を検出し、bootstrap 固有の `package-latest`, `command-instead-of-module`, `yaml[truthy]`, `key-order`, `ignore-errors` などの違反を 2,324 件にわたって報告している。

### `tests/integration/test_ansible_lint_integration.py::AnsibleLintIntegrationTests::test_bootstrap_playbook_dry_run_modes`
- **エラー**: `ansible-playbook --check --diff bootstrap-setup.yml` が exit 1 で失敗。出力に `community.general.yaml` コールバックプラグインが削除されている旨のエラーが出ており、現在の ansible-core では `ansible.builtin.default` の `result_format=yaml` を使う必要がある (`/tmp/ansible-lint-test.log` #7290 付近)。

### `tests/integration/test_ansible_lint_integration.py::AnsibleLintIntegrationTests::test_jenkins_roles_ansible_lint`
- **エラー**: `ansible-lint ansible/roles/jenkins_cleanup_agent_amis` が多数の `var-naming[no-role-prefix]`, `yaml[new-line-at-end-of-file]`, `yaml[line-length]`, `name[template]` 等を報告しており、aws_cli_helper ロール内の変数命名や Jenkins ロールのフォーマットが基準に達していない。

## テスト失敗による実装修正の必要性

### 修正が必要な理由
- `bootstrap-setup.yml` の主要タスクは ansible-lint の基本ルールに違反しており、`package-latest`/`command-instead-of-*`/`yaml[truthy]` などを一掃しない限り何度実行しても `ansible-lint` が exit 2 する。
- `jenkins_cleanup_agent_amis`/`aws_cli_helper` の role では var-naming や Jinja2 のテンプレート警告、末尾改行の欠如などが残存しており、Lint に引っかかる。
- `ansible-playbook --check --diff` が `community.general.yaml` コールバックに依存しており、ansible-core 2.20 以降で削除されているためテストが実行できない。

### 失敗したテスト
- `tests.integration.test_ansible_lint_integration.AnsibleLintIntegrationTests.test_ansible_directory_ansible_lint`
- `tests.integration.test_ansible_lint_integration.AnsibleLintIntegrationTests.test_bootstrap_playbook_ansible_lint`
- `tests.integration.test_ansible_lint_integration.AnsibleLintIntegrationTests.test_bootstrap_playbook_dry_run_modes`
- `tests.integration.test_ansible_lint_integration.AnsibleLintIntegrationTests.test_jenkins_roles_ansible_lint`

### 必要な実装修正
1. `ansible/playbooks/bootstrap-setup.yml` を `package-latest` ルールに従って `state: latest` を避け、`curl` や `shell` を適切なモジュールに置き換え、すべての boolean 値を `true`/`false` に統一し、`yaml[line-length]`/`risky-shell-pipe`/`ignore-errors`/`no-changed-when` などの警告も解消する。
2. `ansible/roles/jenkins_cleanup_agent_amis` および `ansible/roles/aws_cli_helper` 内の変数命名を `jenkins_cleanup_agent_amis_`/`aws_cli_helper_` プレフィックスで統一し、末尾改行や行長制限、Jinja name フォーマットを修正する。
3. `ansible.cfg` もしくは実行環境から `community.general.yaml` コールバックへの依存を除去し、`ansible.builtin.default` の `result_format=yaml` で標準出力のフォーマットを制御する（`community.general` v12 以降で削除済）。
4. 上記修正後、再度 ansible-lint/ansible-playbook を実行して 0 件のエラー・警告を確認し、Phase 6 を再実行する。
