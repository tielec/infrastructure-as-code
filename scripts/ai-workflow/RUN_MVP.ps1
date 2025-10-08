# AI Workflow MVP v1.0.0 実行スクリプト
# PowerShellで実行してください

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "AI Workflow MVP v1.0.0 実行" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Python環境確認
Write-Host "[1/5] Python環境確認..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "Python Version: $pythonVersion" -ForegroundColor Green
Write-Host ""

# 2. 作業ディレクトリ確認
Write-Host "[2/5] 作業ディレクトリ確認..." -ForegroundColor Yellow
$currentDir = Get-Location
Write-Host "Current Directory: $currentDir" -ForegroundColor Green

# scripts/ai-workflowディレクトリに移動
Set-Location -Path (Join-Path $PSScriptRoot ".")
Write-Host "Working Directory: $(Get-Location)" -ForegroundColor Green
Write-Host ""

# 3. 依存パッケージ確認（インストールはスキップ、確認のみ）
Write-Host "[3/5] 依存パッケージ確認..." -ForegroundColor Yellow
Write-Host "必要なパッケージ:" -ForegroundColor Cyan
Get-Content requirements.txt | ForEach-Object { Write-Host "  - $_" -ForegroundColor White }
Write-Host ""
Write-Host "注意: 依存パッケージのインストールは手動で行ってください:" -ForegroundColor Red
Write-Host "  pip install -r requirements.txt" -ForegroundColor White
Write-Host "  pip install -r requirements-test.txt" -ForegroundColor White
Write-Host ""
Read-Host "Enterキーを押して続行（依存パッケージがインストール済みの場合）"

# 4. ワークフロー初期化（テスト用Issue番号: 999）
Write-Host "[4/5] ワークフロー初期化..." -ForegroundColor Yellow
$issueUrl = "https://github.com/tielec/infrastructure-as-code/issues/999"
Write-Host "Issue URL: $issueUrl" -ForegroundColor Cyan

# 既存のワークフローディレクトリを削除（存在する場合）
$workflowDir = "..\..\..\.ai-workflow\issue-999"
if (Test-Path $workflowDir) {
    Write-Host "既存のワークフローディレクトリを削除: $workflowDir" -ForegroundColor Yellow
    Remove-Item -Recurse -Force $workflowDir
}

# ワークフロー初期化実行
Write-Host "実行: python main.py init --issue-url $issueUrl" -ForegroundColor Cyan
$initResult = python main.py init --issue-url $issueUrl 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ ワークフロー初期化成功" -ForegroundColor Green
    Write-Host $initResult
} else {
    Write-Host "✗ ワークフロー初期化失敗" -ForegroundColor Red
    Write-Host $initResult
    exit 1
}
Write-Host ""

# 5. metadata.json確認
Write-Host "[5/5] metadata.json確認..." -ForegroundColor Yellow
$metadataPath = "..\..\..\.ai-workflow\issue-999\metadata.json"
if (Test-Path $metadataPath) {
    Write-Host "✓ metadata.json が生成されました" -ForegroundColor Green
    Write-Host "パス: $metadataPath" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "--- metadata.json 内容 ---" -ForegroundColor Yellow
    Get-Content $metadataPath | Write-Host
    Write-Host "--- 終了 ---" -ForegroundColor Yellow
} else {
    Write-Host "✗ metadata.json が見つかりません" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 成功メッセージ
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "✓ MVP実行完了" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Yellow
Write-Host "1. BDDテストを実行: behave tests/features/workflow.feature" -ForegroundColor White
Write-Host "2. ワークフローディレクトリを確認: dir $workflowDir" -ForegroundColor White
Write-Host ""
