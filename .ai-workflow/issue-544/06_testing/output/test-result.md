# テスト実行結果（再実行）

- 実行日時: 2025-12-27 23:23:44 UTC
- 実行コマンド: `/tmp/miniconda/bin/pytest tests/integration/test_jenkins_agent_ami_cloudwatch.py -q`

## サマリー
- 総テスト数: 5
- 成功: 5
- 失敗: 0
- 実行時間: 30.39s

## 詳細
- `test_cloudwatch_agent_config_is_embedded_and_equal_between_architectures`: PASS
- `test_cloudwatch_agent_config_uses_autoscaling_dimensions`: PASS
- `test_translator_validation_step_present_in_components`: PASS（Translator に `-input /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json` と `-output /tmp/cwagent.translated.json` を明示）
- `test_pulumi_preview_diff_is_constrained`: PASS
- `test_dashboard_and_alarm_guidance_is_documented`: PASS（5 分/5 minutes の継続条件を明記）
