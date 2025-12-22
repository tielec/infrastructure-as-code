# テスト実行結果

## テスト結果サマリー

- 総テスト数: 8件
- 成功: 3件
- 失敗: 5件
- 成功率: 38%

## 条件分岐

**失敗時（失敗数が1件以上）**:

### `tests/integration/test_ansible_lint_integration.py::AnsibleLintIntegrationTests::test_all_playbooks_syntax_check`
- **エラー**: `ansible-playbook --syntax-check` が `jenkins_agent` などのロールを見つけられず exit code 1 で失敗。
- **スタックトレース**:
  ```
  stderr:
  [WARNING]: No inventory was parsed, only implicit localhost is available
  [WARNING]: provided hosts list is empty, only localhost is available. Note that the implicit localhost does not match 'all'
  [ERROR]: the role 'jenkins_agent' was not found in .../ansible/playbooks/jenkins/deploy/roles:...:...:...:.../ansible/playbooks/jenkins/deploy
  Origin: .../ansible/playbooks/jenkins/deploy/deploy_jenkins_agent.yml:29:7
  ```

### `tests/integration/test_ansible_lint_integration.py::AnsibleLintIntegrationTests::test_ansible_directory_ansible_lint`
- **エラー**: `ansible-lint ansible/` が `package-latest`・`command-instead-of-module`・`yaml[truthy]` などの既存違反で exit code 2。
- **スタックトレース**:
  ```
  stdout:
  package-latest: Package installs should not use latest.
  ansible/playbooks/bootstrap-setup.yml:31 Task/Handler: Update system packages
  command-instead-of-module: curl used in place of get_url or uri module
  ansible/playbooks/bootstrap-setup.yml:54 Task/Handler: Check curl availability
  command-instead-of-shell: Use shell only when shell functionality is required.
  ansible/playbooks/bootstrap-setup.yml:65 Task/Handler: Check if AWS CLI v2 is installed
  ```

### `tests/integration/test_ansible_lint_integration.py::AnsibleLintIntegrationTests::test_bootstrap_playbook_ansible_lint`
- **エラー**: `ansible-lint bootstrap-setup.yml` が何千件規模の `var-naming`・`yaml[line-length]`・`risky-shell-pipe` などの違反で exit code 2。
- **スタックトレース**:
  ```
  Failed: 2070 failure(s), 13 warning(s) in 192 files processed of 201 encountered.
  Rule Violation Summary includes var-naming (~1000件) や yaml[truthy]/package-latest/risky-shell-pipe などの重複エラー
  ```

### `tests/integration/test_ansible_lint_integration.py::AnsibleLintIntegrationTests::test_bootstrap_playbook_dry_run_modes`
- **エラー**: `ansible-playbook --check --diff bootstrap-setup.yml` が `sudo: not found` により become できず exit code 2。
- **スタックトレース**:
  ```
  TASK [Update system packages] ... [ERROR]: Task failed: Premature end of stream waiting for become success.
  >>> Standard Error
  /bin/sh: 1: sudo: not found
  Origin: .../ansible/playbooks/bootstrap-setup.yml:31:7
  fatal: [localhost]: FAILED! => {"changed": false, "msg": "... sudo: not found"}
  ```

### `tests/integration/test_ansible_lint_integration.py::AnsibleLintIntegrationTests::test_jenkins_roles_ansible_lint`
- **エラー**: `ansible-lint ansible/roles/jenkins_cleanup_agent_amis` が多数の `var-naming`・`yaml[trailing-spaces]`・`name[template]` を報告して exit code 2。
- **スタックトレース**:
  ```
  stdout:
  yaml[new-line-at-end-of-file]: No new line character at the end of file (ansible/roles/aws_cli_helper/meta/main.yml:3)
  var-naming[no-role-prefix]: Variables should use aws_cli_helper_ as a prefix (ansible/roles/aws_cli_helper/tasks/_retry_loop.yml:4:5)
  name[template]: Jinja templates should only be at the end of 'name' (aws_cli_helper/tasks/_retry_loop.yml:8:9)
  var-naming[no-role-prefix]: Many vars in aws_cli_helper and jenkins_cleanup_agent_amis defaults/tasks lack the required prefix.
  ```
