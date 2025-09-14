# Ansibleロール リファクタリングガイド

## 概要
このドキュメントは、jenkins_agentロールで実施したリファクタリング手法をまとめたものです。
同様の問題を持つ他のロールにも適用できるように、手順と確認ポイントを記載します。

## 問題の識別パターン

### 1. 無駄なSSMパラメータ取得
**症状:**
- SSMパラメータを取得しているが、表示のみで実際の処理に使われていない
- Pulumiスタックが同じSSMパラメータを直接取得している

**確認方法:**
```bash
# 1. ロール内でSSMパラメータ取得を確認
grep -r "ssm_parameter_store" ansible/roles/{role_name}

# 2. 取得した変数の使用箇所を確認
grep -r "{variable_name}" ansible/

# 3. Pulumiスタックの実装を確認
cat pulumi/{stack_name}/index.ts | grep "aws.ssm.getParameter"
```

### 2. all.ymlパラメータの無効な参照
**症状:**
- all.ymlの値をデフォルト値として設定しているが、実際には使われない
- SSMパラメータが既に存在し、Pulumiが直接SSMから取得する

**確認方法:**
```bash
# jenkins.agent.* のような参照を探す
grep -r "jenkins\." ansible/roles/{role_name}
grep -r "infra\." ansible/roles/{role_name}
```

### 3. 未使用のfact設定
**症状:**
- `set_fact`で変数を設定しているが、他のプレイブックやロールから参照されていない

**確認方法:**
```bash
# set_factで設定している変数を特定
grep "set_fact:" ansible/roles/{role_name}/tasks/*.yml

# その変数が他で使われているか確認
grep -r "{fact_name}" ansible/ --exclude-dir={role_name}
```

## リファクタリング手順

### Step 1: 現状分析
1. ロールの`tasks/deploy.yml`を開く
2. 以下のパターンを探す：
   - SSMパラメータ取得ブロック
   - Pulumiスタックoutputs確認ブロック
   - set_factによる変数設定
   - デバッグ表示

### Step 2: Pulumiスタックの確認
```bash
# 対応するPulumiスタックを確認
cat pulumi/{stack_name}/index.ts | head -50
```
- SSMパラメータを直接取得しているか確認
- Ansibleから値を受け取る必要があるか確認

### Step 3: 削除対象の特定

#### 削除可能なパターン:

1. **SSMパラメータ取得（表示のみ）**
```yaml
# 削除対象の例
- name: Get {parameter} from SSM Parameter Store
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: get_parameter
  vars:
    parameter_name: "/path/to/parameter"
    store_as: "variable_name"

# その後、表示のみで使用
- name: Display configuration
  ansible.builtin.debug:
    msg: "Variable: {{ variable_name }}"
```

2. **Pulumiスタックoutputs確認（依存関係チェック）**
```yaml
# 削除対象の例
- name: Check {stack} stack outputs
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: get_outputs
  vars:
    pulumi_project_path: "{{ pulumi_path }}/{stack}"
    output_name: "outputName"
```
→ Pulumiが内部で依存関係を管理するため不要

3. **デフォルト値設定（使われない）**
```yaml
# 削除対象の例
- name: Set default values from all.yml
  ansible.builtin.set_fact:
    ssm_value: "{{ ssm_value | default(jenkins.agent.instance_type) }}"
```

4. **未使用のfact設定**
```yaml
# 削除対象の例
- name: Set facts for use in other playbooks
  ansible.builtin.set_fact:
    deployed: true
    stack_name: "{{ project_name }}"
```

### Step 4: 段階的な削除

#### 削除順序（推奨）:
1. **まず表示を簡潔化**
   - 冗長なデバッグメッセージを削減
   - 必要最小限の情報のみ表示

2. **SSMパラメータ取得を削除**
   - Pulumiが直接取得するものを削除
   - 表示のみのものを削除

3. **未使用のfact設定を削除**
   - 他で参照されていないものを削除

4. **不要な待機処理を削除**
   - pauseタスクなど

### Step 5: 検証

削除後の確認:
```bash
# 1. Ansibleシンタックスチェック
ansible-playbook playbooks/{playbook}.yml --syntax-check

# 2. ドライラン
ansible-playbook playbooks/{playbook}.yml -e "env=dev" --check

# 3. 削除した変数が他で使われていないことを再確認
grep -r "{deleted_variable}" ansible/
```

## 具体例: jenkins_agentロールでの削除内容

### 削除したもの:
1. **SSMパラメータ取得（10個以上）**
   - project-name
   - vpc-id
   - security-group-id
   - instance-type
   - max-capacity
   - min-capacity
   - spot-price
   - など

2. **Pulumiスタックoutputs確認**
   - jenkins-networkスタックのvpcId
   - jenkins-securityスタックのsecurityGroupId

3. **表示用のSSMパラメータ取得**
   - spotFleetRequestId
   - launch-template-id
   - role-arn
   - keypair-name

4. **未使用のfact**
   - agent_deployed
   - agent_stack_name

### 結果:
- 約120行のコードを削除
- 実行時間の短縮（SSM取得の削減）
- コードの可読性向上

## チェックリスト

リファクタリング実施時のチェックリスト:

- [ ] ロールの`tasks/deploy.yml`を確認
- [ ] 対応するPulumiスタック（`index.ts`）を確認
- [ ] SSMパラメータ取得の必要性を検証
- [ ] 取得した変数の使用箇所を確認
- [ ] all.ymlパラメータの参照を確認
- [ ] set_factの変数が他で使われているか確認
- [ ] デバッグメッセージを簡潔化
- [ ] 削除後のシンタックスチェック実施
- [ ] 削除後のドライラン実施

## 適用候補ロール

同様の問題を持つ可能性があるロール:
- jenkins_controller
- jenkins_config
- jenkins_application
- lambda_network
- lambda_security
- lambda_functions
- その他のインフラ系ロール

## 注意事項

### 削除してはいけないもの:
1. **Pulumiの設定に使われるもの**
   - `set_config`で設定される値
   - Pulumiに渡すパラメータ

2. **条件分岐に使われるSSMパラメータ**
   - when条件で使用
   - 他のタスクの実行制御に使用

3. **他のプレイブックから参照される変数**
   - 必ずgrep検索で確認

### 段階的アプローチ:
- 一度にすべて削除せず、段階的に削除
- 各削除後にコミット
- 問題があればすぐに戻せるように

## まとめ

このリファクタリングの目的:
1. **無駄な処理の削減** - 実行時間短縮
2. **コードの簡潔化** - 保守性向上
3. **本質的な処理への集中** - 可読性向上

基本原則:
- Pulumiが管理すべきものはPulumiに任せる
- Ansibleは orchestration に集中
- 表示は必要最小限に
- 使われない変数は作らない