# AI駆動開発自動化ワークフロー トラブルシューティング

**バージョン**: 1.0.0
**最終更新**: 2025-10-07

---

## 目次

1. [Python環境に関する問題](#1-python環境に関する問題)
2. [依存パッケージに関する問題](#2-依存パッケージに関する問題)
3. [ワークフロー実行に関する問題](#3-ワークフロー実行に関する問題)
4. [BDDテストに関する問題](#4-bddテストに関する問題)
5. [ファイル・ディレクトリに関する問題](#5-ファイルディレクトリに関する問題)
6. [その他の問題](#6-その他の問題)

---

## 1. Python環境に関する問題

### Q1-1: `python --version` で "Python" とだけ表示される

**症状**:
```bash
$ python --version
Python
```

**原因**:
Windows Store版Pythonがインストールされていますが、bash環境から実行できない制約があります。

**解決方法**:
PowerShellまたはコマンドプロンプトを使用してください。

```powershell
# PowerShellで確認
python --version
# 出力例: Python 3.12.0
```

### Q1-2: Pythonがインストールされていない

**症状**:
```bash
$ python --version
command not found: python
```

**解決方法**:

#### 方法1: Microsoft Store版Python（推奨・Windows）

1. Microsoft Storeを開く
2. "Python 3.12" を検索
3. インストール
4. PowerShellで確認: `python --version`

#### 方法2: 公式インストーラー

1. https://www.python.org/downloads/ にアクセス
2. "Download Python 3.x.x" をクリック
3. インストーラーを実行
4. **重要**: "Add Python to PATH" にチェック
5. インストール完了後、PowerShellを再起動
6. 確認: `python --version`

### Q1-3: Python 3.10未満のバージョンがインストールされている

**症状**:
```bash
$ python --version
Python 3.9.7
```

**要件**: Python 3.10以上が必要

**解決方法**:
最新版のPythonをインストールしてください（Q1-2参照）。

---

## 2. 依存パッケージに関する問題

### Q2-1: `pip: command not found`

**症状**:
```bash
$ pip install -r requirements.txt
pip: command not found
```

**解決方法**:
`python -m pip` を使用してください。

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-test.txt
```

### Q2-2: `pip install` で Permission denied エラー

**症状**:
```bash
$ pip install -r requirements.txt
ERROR: Could not install packages due to an OSError: [Errno 13] Permission denied
```

**解決方法**:
`--user` オプションを使用してユーザーディレクトリにインストールしてください。

```powershell
pip install --user -r requirements.txt
pip install --user -r requirements-test.txt
```

### Q2-3: パッケージバージョンの競合

**症状**:
```bash
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed...
```

**解決方法**:
仮想環境を使用してクリーンな環境を作成してください。

```powershell
# 仮想環境の作成
python -m venv venv

# 仮想環境の有効化（PowerShell）
.\venv\Scripts\Activate.ps1

# 仮想環境の有効化（コマンドプロンプト）
.\venv\Scripts\activate.bat

# 依存パッケージのインストール
pip install -r requirements.txt
pip install -r requirements-test.txt
```

---

## 3. ワークフロー実行に関する問題

### Q3-1: `Error: Workflow already exists`

**症状**:
```bash
$ python main.py init --issue-url https://github.com/.../issues/123
Error: Workflow already exists: .ai-workflow\issue-123
```

**原因**:
同じIssue番号のワークフローが既に存在します。

**解決方法**:

#### オプション1: 既存ワークフローを削除

```powershell
# PowerShell
Remove-Item -Recurse -Force ..\..\..\.ai-workflow\issue-123

# 再度初期化
python main.py init --issue-url https://github.com/.../issues/123
```

#### オプション2: 既存ワークフローを使用

既存のワークフローディレクトリを確認し、必要に応じて `execute` または `review` コマンドを使用してください。

```powershell
# 既存ワークフローの状態確認
type ..\..\..\.ai-workflow\issue-123\metadata.json
```

### Q3-2: `ModuleNotFoundError: No module named 'click'`

**症状**:
```bash
$ python main.py init --issue-url ...
ModuleNotFoundError: No module named 'click'
```

**原因**:
依存パッケージがインストールされていません。

**解決方法**:
```powershell
pip install -r requirements.txt
```

### Q3-3: metadata.json が UTF-8 で読めない

**症状**:
```bash
UnicodeDecodeError: 'charmap' codec can't decode byte ...
```

**原因**:
Windowsのデフォルトエンコーディングが問題。

**解決方法**:
環境変数を設定してUTF-8を強制してください。

```powershell
# PowerShell
$env:PYTHONUTF8 = "1"
python main.py init --issue-url ...
```

または、PowerShellプロファイルに追加：
```powershell
# $PROFILE を編集
notepad $PROFILE

# 以下を追加
$env:PYTHONUTF8 = "1"
```

---

## 4. BDDテストに関する問題

### Q4-1: `behave: command not found`

**症状**:
```bash
$ behave tests/features/workflow.feature
behave: command not found
```

**原因**:
behaveがインストールされていないか、PATHに含まれていません。

**解決方法**:

```powershell
# インストール確認
pip show behave

# インストールされていない場合
pip install -r requirements-test.txt

# python -m で実行
python -m behave tests/features/workflow.feature
```

### Q4-2: BDDテストが Failed になる

**症状**:
```bash
Scenario: ワークフロー初期化とメタデータ作成
  ...
  ならば ワークフローディレクトリ ".ai-workflow/issue-999" が作成される  FAILED
```

**デバッグ方法**:

1. **詳細ログを有効化**:
```powershell
behave --no-capture --no-capture-stderr tests/features/workflow.feature
```

2. **ステップごとに確認**:
```powershell
# 手動で各ステップを実行
cd C:\Users\ytaka\TIELEC\development\infrastructure-as-code\scripts\ai-workflow
python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/999

# ディレクトリ確認
dir ..\..\..\.ai-workflow\issue-999

# metadata.json確認
type ..\..\..\.ai-workflow\issue-999\metadata.json
```

3. **前回のテストファイルをクリーンアップ**:
```powershell
Remove-Item -Recurse -Force ..\..\..\.ai-workflow\issue-999
```

### Q4-3: AssertionError: Field not found

**症状**:
```bash
AssertionError: Field not found: issue_number
```

**原因**:
metadata.jsonの構造が期待と異なります。

**解決方法**:
```powershell
# metadata.jsonの内容を確認
type ..\..\..\.ai-workflow\issue-999\metadata.json

# 期待される構造と比較（README.md参照）
```

---

## 5. ファイル・ディレクトリに関する問題

### Q5-1: `.ai-workflow` ディレクトリが作成されない

**症状**:
ワークフロー初期化後もディレクトリが存在しない。

**解決方法**:

1. **作業ディレクトリを確認**:
```powershell
pwd
# 期待: C:\Users\ytaka\TIELEC\development\infrastructure-as-code\scripts\ai-workflow
```

2. **正しいディレクトリに移動**:
```powershell
cd C:\Users\ytaka\TIELEC\development\infrastructure-as-code\scripts\ai-workflow
```

3. **絶対パスで確認**:
```powershell
dir C:\Users\ytaka\TIELEC\development\infrastructure-as-code\.ai-workflow
```

### Q5-3: ログファイルが上書きされて過去の実行履歴が見つからない

**症状**:
リトライ実行後、以前のログファイルが見つからない。

**原因**:
v1.5.0（Issue #317）以降、ログファイルは連番付きで保存されるため、過去のログは保持されます。

**ログファイルの命名規則**:
- **初回実行**: `agent_log_1.md`, `agent_log_raw_1.txt`, `prompt_1.txt`
- **リトライ1回目**: `agent_log_2.md`, `agent_log_raw_2.txt`, `prompt_2.txt`
- **リトライN回目**: `agent_log_{N+1}.md`, `agent_log_raw_{N+1}.txt`, `prompt_{N+1}.txt`

**確認方法**:
```powershell
# execute ディレクトリ内のログファイルを確認
dir .ai-workflow\issue-304\01_requirements\execute\

# 期待される出力:
#   agent_log_1.md
#   agent_log_2.md
#   agent_log_raw_1.txt
#   agent_log_raw_2.txt
#   prompt_1.txt
#   prompt_2.txt
```

**注意事項**:
- 成果物ファイル（`output/requirements.md` など）は従来通り上書きされます
- ログファイルのみ連番付きで履歴が保持されます

### Q5-2: Permission denied でファイルが書き込めない

**症状**:
```bash
PermissionError: [Errno 13] Permission denied: '.ai-workflow/issue-123/metadata.json'
```

**解決方法**:

1. **ファイルが開かれていないか確認**:
   - エディタやJSONビューアーでファイルを開いている場合は閉じてください

2. **読み取り専用属性を確認**:
```powershell
# 読み取り専用を解除
attrib -r ..\..\..\.ai-workflow\issue-123\metadata.json
```

3. **管理者権限で実行**:
   PowerShellを管理者として実行してください。

---

## 6. その他の問題

### Q6-1: 日本語が文字化けする

**症状**:
metadata.jsonやログ出力で日本語が文字化けします。

**解決方法**:

1. **UTF-8環境変数を設定**（Q3-3参照）:
```powershell
$env:PYTHONUTF8 = "1"
```

2. **PowerShellのエンコーディングを設定**:
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

3. **エディタのエンコーディングを確認**:
   - VS Code: ファイル → 設定 → "files.encoding": "utf8"

### Q6-2: Git関連のエラー

**症状**:
```bash
fatal: not a git repository
```

**原因**:
作業ディレクトリがGitリポジトリではありません。

**解決方法**:
```powershell
# リポジトリルートに移動
cd C:\Users\ytaka\TIELEC\development\infrastructure-as-code

# Git初期化（初回のみ）
git init

# または既存リポジトリをクローン
git clone https://github.com/tielec/infrastructure-as-code.git
```

### Q6-3: メモリ不足エラー

**症状**:
```bash
MemoryError: Unable to allocate ...
```

**原因**:
大量のファイルやデータを処理しています。

**解決方法**:

1. **不要なプロセスを終了**:
   タスクマネージャーで他のアプリケーションを終了

2. **config.yaml のトークン上限を下げる**:
```yaml
codebase_analysis:
  max_files: 20  # デフォルト
  max_tokens: 50000  # → 30000に下げる
```

---

## サポート

### ログの確認

問題が解決しない場合、以下の情報を収集してください：

```powershell
# Python環境
python --version
pip --version

# 依存パッケージ
pip list | Select-String -Pattern "click|behave|anthropic|GitPython|PyYAML|PyGithub"

# 作業ディレクトリ
pwd

# ファイル一覧
dir scripts\ai-workflow

# metadata.json（存在する場合）
type .ai-workflow\issue-XXX\metadata.json
```

### GitHub Issue

バグ報告は以下のテンプレートで GitHub Issue を作成してください：

**タイトル**: [Bug] 簡潔な問題の説明

**本文**:
```markdown
## 環境
- OS: Windows 11
- Python: 3.12.0
- 実行コマンド: python main.py init --issue-url ...

## 症状
（エラーメッセージや期待と異なる動作を記載）

## 再現手順
1. ...
2. ...
3. ...

## ログ
（上記「ログの確認」セクションの情報を貼り付け）
```

---

**バージョン**: 1.0.0 (MVP)
**最終更新**: 2025-10-07
