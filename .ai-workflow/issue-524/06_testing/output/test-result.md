# テスト実行結果

## テスト結果サマリー

- 総テスト数: 8件
- 成功: 4件
- 失敗: 4件
- 成功率: 50%

## 条件分岐

**失敗時（失敗数が1件以上）**:

### `tests/integration/test_ansible_lint_integration.py::AnsibleLintIntegrationTests::test_ansible_directory_ansible_lint`
- **エラー**: `AssertionError: 0 != 2 : ansible-lint on /tmp/ai-workflow-repos-9-b33178e4/infrastructure-as-code/ansible failed (exit 2)`
- **スタックトレース**:
  ```
  AssertionError: 0 != 2 : ansible-lint on /tmp/ai-workflow-repos-9-b33178e4/infrastructure-as-code/ansible failed (exit 2).
  stdout:
  (多数のルール違反、yaml[truthy]/var-naming/command-instead-of-module 等が継続)
  WARNING  Listing 181 violation(s) that are fatal
  # Rule Violation Summary
    5  jinja
  139  var-naming
    8  yaml
    3  yaml
  ```

### `tests/integration/test_ansible_lint_integration.py::AnsibleLintIntegrationTests::test_bootstrap_playbook_ansible_lint`
- **エラー**: `AssertionError: 0 != 2 : ansible-lint on /tmp/ai-workflow-repos-9-b33178e4/infrastructure-as-code/ansible/playbooks/bootstrap-setup.yml failed (exit 2)`
- **スタックトレース**:
  ```
  stdout:
  no-changed-when: Commands should not change things if nothing needs doing.
  command-instead-of-module: curl used in place of get_url or uri.
  yaml[line-length]: Line too long (177 > 160 characters).
  yaml[truthy]: Truthy value should be one of [false, true].
  WARNING  Listing 39 violation(s) that are fatal
  ```

### `tests/integration/test_ansible_lint_integration.py::AnsibleLintIntegrationTests::test_bootstrap_playbook_dry_run_modes`
- **エラー**: `AssertionError: 0 != 2 : ansible-playbook --check --diff /tmp/ai-workflow-repos-9-b33178e4/infrastructure-as-code/ansible/playbooks/bootstrap-setup.yml failed (exit 2)`
- **スタックトレース**:
  ```
  PLAY [Bootstrap Environment Setup for Amazon Linux 2023] *********************************
  TASK [Gathering Facts] *****************************************************************
  [ERROR]: Task failed: Premature end of stream waiting for become success.
  >>> Standard Error
  /bin/sh: 1: sudo: not found
  fatal: [localhost]: FAILED! => {"changed": false, "msg": "Task failed: Premature end of stream waiting for become success.\n>>> Standard Error\n/bin/sh: 1: sudo: not found"}
  ```

### `tests/integration/test_ansible_lint_integration.py::AnsibleLintIntegrationTests::test_jenkins_roles_ansible_lint`
- **エラー**: `AssertionError: 0 != 2 : ansible-lint on /tmp/ai-workflow-repos-9-b33178e4/infrastructure-as-code/ansible/roles/jenkins_cleanup_agent_amis failed (exit 2)`
- **スタックトレース**:
  ```
  stdout:
  yaml[new-line-at-end-of-file]: No new line character at the end of file (aws_cli_helper/meta/main.yml)
  var-naming[no-role-prefix]: Variables names within roles should use aws_cli_helper_ or jenkins_cleanup_agent_amis_ prefixes.
  yaml[trailing-spaces]: Trailing spaces detected in aws_cli_helper/tasks/execute.yml
  WARNING  Listing 176 violation(s) that are fatal
  ```

## 備考
- `pytest tests/integration/test_ansible_lint_integration.py` を実行しましたが、ansible-lint ならびに ansible-playbook が既存ルール違反や `sudo` 未導入のため失敗しました。
- Phase 6 再実行前に`ansible/`一式の lint 違反と `sudo` 依存を除去する修正が必要です。
