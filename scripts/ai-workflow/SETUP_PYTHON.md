# Python環境セットアップガイド

AI Workflow MVP v1.0.0を実行するためのPython環境セットアップ手順

## 現在の状況

Windows環境でbashからPythonが実行できない状態です。
WindowsApps版Pythonがインストールされていますが、bash環境からは利用できません。

## 推奨: Python公式インストーラー

### 1. Pythonのダウンロード

1. https://www.python.org/downloads/ にアクセス
2. "Download Python 3.12.x" ボタンをクリック
3. インストーラーをダウンロード

### 2. インストール

1. ダウンロードした`python-3.12.x-amd64.exe`を実行
2. **重要**: "Add Python to PATH" にチェック ✅
3. "Install Now" をクリック
4. インストール完了を待つ

### 3. 確認（PowerShell）

PowerShellを**新しく開いて**確認:

```powershell
python --version
# 出力: Python 3.12.x

pip --version
# 出力: pip 23.x.x from ...
```

## 代替方法: PowerShellから直接実行

Python環境がセットアップできない場合、PowerShellから直接実行できます。

### PowerShellでの実行手順

```powershell
# 1. PowerShellを開く（管理者として実行は不要）

# 2. プロジェクトディレクトリに移動
cd C:\Users\ytaka\TIELEC\development\infrastructure-as-code\scripts\ai-workflow

# 3. 依存パッケージインストール
pip install -r requirements.txt
pip install -r requirements-test.txt

# 4. ワークフロー初期化
python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/123

# 5. 結果確認
dir ..\..\..\.ai-workflow\issue-123
type ..\..\..\.ai-workflow\issue-123\metadata.json

# 6. BDDテスト実行
behave tests/features/workflow.feature
```

## トラブルシューティング

### Q: "python: command not found"

**A**: PATHが通っていません。

**解決方法**:
1. Pythonを再インストール（"Add Python to PATH"にチェック）
2. または手動でPATHを追加:
   - 設定 → システム → 詳細設定 → 環境変数
   - Path変数に追加: `C:\Users\ytaka\AppData\Local\Programs\Python\Python312`
   - Path変数に追加: `C:\Users\ytaka\AppData\Local\Programs\Python\Python312\Scripts`

### Q: "pip: command not found"

**A**: pipがPATHに含まれていません。

**解決方法**:
```powershell
python -m pip install -r requirements.txt
```

### Q: ModuleNotFoundError: No module named 'click'

**A**: 依存パッケージがインストールされていません。

**解決方法**:
```powershell
pip install -r requirements.txt
pip install -r requirements-test.txt
```

## 次のステップ

Python環境がセットアップできたら:

1. **依存パッケージインストール**:
   ```powershell
   cd scripts/ai-workflow
   pip install -r requirements.txt
   pip install -r requirements-test.txt
   ```

2. **MVP実行**:
   ```powershell
   python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/123
   ```

3. **結果確認**:
   ```powershell
   type ..\..\..\.ai-workflow\issue-123\metadata.json
   ```

4. **BDDテスト実行**:
   ```powershell
   behave tests/features/workflow.feature
   ```

## 参考

- Python公式ダウンロード: https://www.python.org/downloads/
- Pythonインストールガイド: https://docs.python.org/ja/3/using/windows.html
- AI Workflow README: scripts/ai-workflow/README.md
- トラブルシューティング: scripts/ai-workflow/TROUBLESHOOTING.md
