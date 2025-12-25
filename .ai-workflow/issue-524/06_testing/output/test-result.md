# テスト実行結果

## テスト結果サマリー
- 総テスト数: 8件
- 成功: 4件
- 失敗: 4件
- 成功率: 50%

## 条件分岐
**失敗時（失敗数が1件以上）**:
以下に失敗したテストの詳細を記録します。

### `tests/integration/test_ansible_lint_integration.py::AnsibleLintIntegrationTests::test_ansible_directory_ansible_lint`
- **エラー**: `ansible-lint` が `ansible/` で exit 2 を返し、176件のlint違反（`no-changed-when`, `command-instead-of-module`, `yaml[truthy]`, `name[template]`, `no-jinja-when` など）を報告しました。
- **スタックトレース**:
  ```text
  AssertionError: 0 != 2 : ansible-lint on /tmp/ai-workflow-repos-7-8de8dd07/infrastructure-as-code/ansible failed (exit 2).
  stdout:
  no-changed-when: Commands should not change things if nothing needs doing. (ansible/playbooks/bootstrap-setup.yml:32)
  command-instead-of-module: curl used in place of get_url or uri module. (ansible/playbooks/bootstrap-setup.yml:53)
  yaml[truthy]: truthy value should be one of [false, true]. (ansible/playbooks/bootstrap-setup.yml:87)
  ```

### `tests/integration/test_ansible_lint_integration.py::AnsibleLintIntegrationTests::test_bootstrap_playbook_ansible_lint`
- **エラー**: `ansible-lint` が `ansible/playbooks/bootstrap-setup.yml` で exit 2 を返し、39件のlint違反（`command-instead-of-module`, `no-jinja-when`, `yaml[line-length]`, `name[template]`, `no-changed-when` など）を報告しました。
- **スタックトレース**:
  ```text
  AssertionError: 0 != 2 : ansible-lint on /tmp/ai-workflow-repos-7-8de8dd07/infrastructure-as-code/ansible/playbooks/bootstrap-setup.yml failed (exit 2).
  stdout:
  command-instead-of-module: curl used in place of get_url or uri module. (ansible/playbooks/bootstrap-setup.yml:53)
  name[template]: Jinja templates should only be at the end of 'name'. (ansible/playbooks/bootstrap-setup.yml:137)
  yaml[line-length]: Line too long (171 > 160 characters). (ansible/playbooks/bootstrap-setup.yml:240)
  ```

### `tests/integration/test_ansible_lint_integration.py::AnsibleLintIntegrationTests::test_bootstrap_playbook_dry_run_modes`
- **エラー**: `ansible-playbook --check --diff ansible/playbooks/bootstrap-setup.yml` が exit 2 を返し、`sudo` が見つからないことによって `Gathering Facts` で失敗しました。
- **スタックトレース**:
  ```text
  AssertionError: 0 != 2 : ansible-playbook --check --diff bootstrap-setup.yml failed (exit 2).
  stdout:
  PLAY [Bootstrap Environment Setup for Amazon Linux 2023]
  TASK [Gathering Facts] *****************************************************
  fatal: [localhost]: FAILED! => {"changed": false, "msg": "Task failed: Premature end of stream waiting for become success.\n>>> Standard Error\n/bin/sh: 1: sudo: not found"}
  ```

### `tests/integration/test_ansible_lint_integration.py::AnsibleLintIntegrationTests::test_jenkins_roles_ansible_lint`
- **エラー**: `ansible-lint` が `ansible/roles/jenkins_cleanup_agent_amis` で exit 2 を返し、`var-naming` や `yaml[new-line-at-end-of-file]` などの規則違反を報告しました。
- **スタックトレース**:
  ```text
  AssertionError: 0 != 2 : ansible-lint on /tmp/ai-workflow-repos-7-8de8dd07/infrastructure-as-code/ansible/roles/jenkins_cleanup_agent_amis failed (exit 2).
  stdout:
  yaml[new-line-at-end-of-file]: No new line character at the end of file. (ansible/roles/aws_cli_helper/meta/main.yml:3)
  var-naming[no-role-prefix]: Variables names from within roles should use aws_cli_helper_ as a prefix. (ansible/roles/aws_cli_helper/tasks/_retry_loop.yml:4)
  yaml[line-length]: Line too long (196 > 160 characters). (ansible/roles/aws_cli_helper/tasks/_ssm_check_loop.yml:8)
  ```
