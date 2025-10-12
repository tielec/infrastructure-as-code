#!/bin/bash
# Issue #322テスト実行スクリプト

set -e

cd /tmp/jenkins-6860a483/workspace/AI_Workflow/ai_workflow_orchestrator/scripts/ai-workflow

echo "======================================"
echo "Issue #322 テスト実行開始"
echo "======================================"
echo ""

echo "--- GitManagerテスト (UT-GM-031～037) ---"
pytest tests/unit/core/test_git_manager.py \
  -k "test_ensure_git_config_with_git_commit_env or \
      test_ensure_git_config_with_git_author_env or \
      test_ensure_git_config_priority or \
      test_ensure_git_config_default or \
      test_ensure_git_config_validation_email or \
      test_ensure_git_config_validation_username_length or \
      test_ensure_git_config_log_output" \
  -v --tb=short

echo ""
echo "--- main.py CLIオプションテスト (UT-MAIN-001～002) ---"
pytest tests/unit/test_main.py::TestCLIGitOptions -v --tb=short

echo ""
echo "======================================"
echo "テスト実行完了"
echo "======================================"
