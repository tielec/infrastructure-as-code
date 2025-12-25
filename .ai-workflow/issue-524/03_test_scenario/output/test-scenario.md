# テストシナリオ書: ansible-lint スタイル違反の修正 (Issue #524)

## 0. テスト戦略サマリー

### Planning DocumentとRequirements/Design Documentとの整合性

本テストシナリオは、以下の文書から決定されたテスト戦略に基づいて作成されています：

- **実装戦略**: REFACTOR - 既存のAnsibleコードベースのフォーマットとスタイルを改善
- **テスト戦略**: INTEGRATION_ONLY - ansible-lint実行とplaybook動作確認に特化
- **見積もり工数**: 2時間（フォーマット修正0.5h + Jinja2修正0.5h + テスト・検証1h）
- **リスク評価**: 低（動作に影響しないスタイル修正のみ）

### 選択されたテスト戦略: INTEGRATION_ONLY

**判断根拠**:
- フォーマット・スタイル修正では、実際のAnsible playbook実行による統合テストのみが有効
- 修正対象がすべて既存のAnsible実行環境との互換性確認であり、以下の理由から：
  - **ユニットテスト**: Ansibleのフォーマット修正には不適切（YAMLの構文レベルの変更のため）
  - **BDDテスト**: エンドユーザーストーリーに影響しない内部品質改善のため不要
  - **インテグレーション**: Ansibleコマンド実行による構文・動作確認が最適

### テスト対象の範囲

1. **修正対象ファイル（7ファイル）**:
   - `ansible/playbooks/bootstrap-setup.yml`
   - `ansible/inventory/group_vars/all.yml`
   - `ansible/roles/jenkins_cleanup_agent_amis/tasks/process_ami_retention.yml`
   - `ansible/roles/jenkins_cleanup_agent_amis/tasks/process_pipeline_outputs.yml`
   - `ansible/roles/jenkins_cleanup_agent_amis/tasks/process_image_versions.yml`
   - `ansible/roles/jenkins_cleanup_agent_amis/tasks/delete_snapshots.yml`
   - `ansible/roles/jenkins_agent_ami/tasks/cleanup_amis.yml`

2. **修正内容**:
   - フォーマット関連エラー11個の修正
   - Jinja2スペーシング警告10個の修正

### テストの目的

- **主目的**: ansible-lint準拠のコードベース確立
- **技術的検証**: 修正後のファイルがansible-lint標準に準拠していることの確認
- **動作保証**: 既存のAnsibleplaybook実行結果に影響がないことの確認
- **品質向上**: CI/CDパイプラインでのlintチェック成功の確認

## 1. Integrationテストシナリオ

### シナリオ1: ansible-lintとコードベースの統合テスト

**目的**: 修正後のファイルがansible-lint標準に完全準拠していることを検証

**前提条件**:
- ansible-lint v6.0以上がインストール済み
- 修正対象の全7ファイルの修正が完了している
- 作業ディレクトリがリポジトリルート（`/tmp/ai-workflow-repos-7-738ec53c/infrastructure-as-code/`）である

**テスト手順**:
1. **全ファイル対象でのansible-lint実行**
   ```bash
   ansible-lint ansible/
   ```

2. **個別ファイル検証 - bootstrap-setup.yml**
   ```bash
   ansible-lint ansible/playbooks/bootstrap-setup.yml
   ```

3. **個別ファイル検証 - group_vars/all.yml**
   ```bash
   ansible-lint ansible/inventory/group_vars/all.yml
   ```

4. **個別ファイル検証 - Jenkins関連ロール**
   ```bash
   ansible-lint ansible/roles/jenkins_cleanup_agent_amis/
   ansible-lint ansible/roles/jenkins_agent_ami/
   ```

**期待結果**:
- 全てのansible-lint実行でエラー件数: 0件
- 全てのansible-lint実行で警告件数: 0件
- 実行ステータス: 成功（exit code 0）

**確認項目**:
- [ ] フォーマット関連エラー（trailing-spaces, yaml[truthy], yaml[document-start], yaml[new-line-at-end-of-file]）が0件
- [ ] Jinja2スペーシング警告が0件
- [ ] 新たなlintエラーが発生していない
- [ ] CI環境でのansible-lint実行が成功する

---

### シナリオ2: Ansible構文チェックとの統合テスト

**目的**: 修正によりPlaybook構文に問題が発生していないことを検証

**前提条件**:
- Ansible 2.9以上がインストール済み
- 修正対象ファイルの修正が完了している
- 必要なAnsible collectionsがインストール済み

**テスト手順**:
1. **bootstrap-setup.ymlの構文チェック**
   ```bash
   ansible-playbook --syntax-check ansible/playbooks/bootstrap-setup.yml
   ```

2. **その他のplaybook構文チェック（存在する場合）**
   ```bash
   find ansible/playbooks/ -name "*.yml" -exec ansible-playbook --syntax-check {} \;
   ```

3. **ロール内タスクファイルの構文確認（Playbook経由）**
   ```bash
   # 修正されたロールを使用するPlaybookで構文確認
   ansible-playbook --syntax-check ansible/playbooks/bootstrap-setup.yml --extra-vars "check_jenkins_roles=true"
   ```

**期待結果**:
- 全ての構文チェックが成功
- 「playbook: [ファイルパス] Syntax OK」メッセージが表示される
- エラーメッセージが表示されない

**確認項目**:
- [ ] YAML構文エラーが発生していない
- [ ] Ansible特有の構文エラーが発生していない
- [ ] Jinja2テンプレート構文が正常
- [ ] 変数参照に問題がない

---

### シナリオ3: Ansible Dry-Runモードでの動作統合テスト

**目的**: 修正されたPlaybookが実際の実行環境で正常動作することを検証

**前提条件**:
- テスト可能なAnsible実行環境（ローカルまたはCI環境）
- 必要なインベントリファイルが存在
- 実行に必要な権限・認証情報が設定済み

**テスト手順**:
1. **Check モード（Dry-run）での実行**
   ```bash
   ansible-playbook ansible/playbooks/bootstrap-setup.yml --check --diff
   ```

2. **限定的なタスク実行（安全なタスクのみ）**
   ```bash
   ansible-playbook ansible/playbooks/bootstrap-setup.yml --tags "debug,facts" --check
   ```

3. **変数展開の検証**
   ```bash
   ansible-playbook ansible/playbooks/bootstrap-setup.yml --check --extra-vars "debug_mode=true"
   ```

**期待結果**:
- Dry-runモードで正常完了
- 修正前と同じタスク実行計画が生成される
- Jinja2テンプレートが正常に展開される
- エラーやwarningが発生しない

**確認項目**:
- [ ] 実行計画が修正前と同一
- [ ] 変数展開が正常
- [ ] 条件分岐が正常動作
- [ ] ループ処理が正常動作
- [ ] Jinja2修正箇所が正常に評価される

---

### シナリオ4: CI/CD環境との統合テスト

**目的**: CI/CD環境でのansible-lint実行が成功することを検証

**前提条件**:
- GitHub Actions等のCI環境が利用可能
- ansible-lintがCI環境にインストール済み
- 修正されたコードがPull Request等で検証可能

**テスト手順**:
1. **Pull Requestの作成とCI実行**
   ```bash
   # 修正内容をcommitし、Pull Requestを作成
   git add .
   git commit -m "Fix ansible-lint style violations

   - Remove trailing spaces in bootstrap-setup.yml
   - Standardize truthy values to true/false
   - Add document start markers
   - Fix Jinja2 spacing in Jenkins roles

   Resolves #524"

   # Push and create PR
   git push origin feature/fix-ansible-lint-524
   ```

2. **CI環境でのansible-lint実行確認**
   - GitHub ActionsまたはJenkins CIでのパイプライン実行
   - ansible-lintステップの成功確認

3. **継続的な品質チェック体制の確認**
   - 今後のcommitでansible-lintが自動実行されることの確認

**期待結果**:
- CI環境でのansible-lint実行が成功（緑）
- Pull Requestのマージが可能状態
- 継続的品質チェックが有効化

**確認項目**:
- [ ] CI環境でのansible-lint実行が成功
- [ ] 他のCIテストに影響していない
- [ ] Pull Requestのマージブロッカーが解消
- [ ] 今後のcommitでlintチェックが継続実行される

---

## 2. テストデータ

### 2.1 修正前のサンプルデータ（問題のあるコード例）

**末尾空白があるYAML例**:
```yaml
  tasks:
    - name: Example task
      debug:
        msg: "hello"
```

**Truthy値の問題例**:
```yaml
become: yes
gather_facts: True
remote_user: no
```

**Jinja2スペーシング問題例**:
```yaml
- name: Process AMI data
  set_fact:
    ami_id: "{{ ami_list[0] }}"
    image_name: "{{ ami_data['ImageName'] }}"
```

### 2.2 修正後の期待データ

**修正後のYAML例**:
```yaml
---
  tasks:
    - name: Example task
      debug:
        msg: "hello"
```

**修正後のTruthy値**:
```yaml
become: true
gather_facts: true
remote_user: false
```

**修正後のJinja2スペーシング**:
```yaml
- name: Process AMI data
  set_fact:
    ami_id: "{{ ami_list[ 0 ] }}"
    image_name: "{{ ami_data[ 'ImageName' ] }}"
```

### 2.3 テスト実行用のコマンドセット

**基本的なlintチェック**:
```bash
# 全体チェック
ansible-lint ansible/

# 詳細出力でのチェック
ansible-lint -v ansible/

# 特定のルールのみチェック
ansible-lint --warn-list trailing-spaces ansible/playbooks/bootstrap-setup.yml
```

**構文チェック用コマンド**:
```bash
# 基本構文チェック
ansible-playbook --syntax-check ansible/playbooks/bootstrap-setup.yml

# Dry-run実行
ansible-playbook --check ansible/playbooks/bootstrap-setup.yml

# 詳細diff表示
ansible-playbook --check --diff ansible/playbooks/bootstrap-setup.yml
```

## 3. テスト環境要件

### 3.1 必要なソフトウェア環境

**必須コンポーネント**:
- ansible-lint v6.0以上
- Ansible v2.9以上
- Python 3.8以上
- Git (バージョン管理用)

**インストールコマンド**:
```bash
# ansible-lintのインストール
pip3 install ansible-lint

# Ansibleのインストール
pip3 install ansible

# バージョン確認
ansible-lint --version
ansible --version
```

### 3.2 テスト実行環境

**ローカル環境**:
- Ubuntu 20.04 LTS以上 または macOS 10.15以上
- 8GB RAM以上
- 2GB以上の空きディスク容量

**CI/CD環境**:
- GitHub Actions または Jenkins
- Docker環境（ansible-lint実行用）
- 必要なAnsible collections事前インストール

### 3.3 外部依存関係

**Ansible Collections**:
```yaml
# requirements.yml (存在する場合)
collections:
  - name: community.general
    version: ">=4.0.0"
  - name: ansible.posix
    version: ">=1.0.0"
```

**ネットワーク要件**:
- インターネット接続（collections取得用）
- CI環境へのアクセス権限

## 4. テスト実行スケジュール

### 4.1 テスト実行順序

1. **Phase 1**: 修正前状態の確認（0.1h）
   - 現在のansible-lint実行結果の確認
   - ベースラインの確立

2. **Phase 2**: 修正実装中の段階的テスト（0.5h）
   - フォーマット修正後の個別ファイル確認
   - Jinja2修正後の個別ファイル確認

3. **Phase 3**: 統合テスト実行（0.5h）
   - 全ファイル対象でのansible-lint実行
   - 構文チェック実行
   - Dry-runモード実行

4. **Phase 4**: CI/CD環境での最終確認（0.5h）
   - Pull Request作成とCI実行
   - 継続的品質チェック体制の確認

### 4.2 合格/不合格の判定基準

**合格基準**:
- [ ] ansible-lint実行でエラー0件、警告0件
- [ ] ansible-playbook --syntax-check で成功
- [ ] Dry-runモードで正常完了
- [ ] CI環境でのパイプライン成功

**不合格時の対応**:
1. エラー内容の分析と修正
2. 該当テストの再実行
3. 全テストの再実行

## 5. 品質ゲート確認

### Phase 3の品質ゲート要件

✅ **Phase 2の戦略に沿ったテストシナリオである**
- INTEGRATION_ONLYテスト戦略に完全準拠
- ansible-lint実行、構文チェック、動作確認に特化したシナリオ

✅ **主要な正常系がカバーされている**
- 全修正対象ファイルのlintチェック
- Playbook構文チェック
- 実際の実行環境での動作確認
- CI/CD環境での自動化チェック

✅ **主要な異常系がカバーされている**
- 修正ミスによる構文エラーの検出
- 意図しない動作変更の検出
- CI環境での失敗ケースの検出

✅ **期待結果が明確である**
- 各テストシナリオで具体的な成功条件を定義
- 検証可能な確認項目をチェックリスト形式で明記
- コマンド実行結果の期待値を具体的に記載

## 6. リスクと軽減策

### 6.1 テスト実行上のリスク

**リスク1**: 修正漏れによるlintエラーの残存
- **確率**: 中
- **影響**: 中
- **軽減策**: 個別ファイル単位でのlintチェック実行、修正箇所の二重確認

**リスク2**: CI環境でのansible-lintバージョン相違
- **確率**: 低
- **影響**: 高
- **軽減策**: CI環境でのバージョン確認、ローカル環境との統一

**リスク3**: Ansible実行環境の設定不備
- **確率**: 低
- **影響**: 中
- **軽減策**: 構文チェックでの事前確認、段階的な動作確認

### 6.2 品質保証のための追加施策

**コードレビュー**:
- 修正内容の差分レビュー
- ansible-lint出力結果の確認
- テスト実行結果の確認

**ドキュメント化**:
- テスト実行ログの保存
- 修正前後の比較結果記録
- 今後の開発ガイドライン更新

## まとめ

本テストシナリオは、ansible-lintスタイル違反修正というリファクタリングタスクに対して、INTEGRATION_ONLYテスト戦略に基づく実用的なテストアプローチを提供しています。

**テストの特徴**:
- **実践的**: 実際のAnsible実行環境での検証に重点
- **効率的**: フォーマット修正に適したテスト手法に特化
- **包括的**: lint、構文、動作の3段階での検証
- **継続的**: CI/CD環境での自動化による品質維持

このテストシナリオの実行により、ansible-lint準拠のコードベース確立と、継続的な品質チェック体制の構築が実現されます。