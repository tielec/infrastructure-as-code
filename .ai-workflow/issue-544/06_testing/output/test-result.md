# テスト実行結果

## テスト結果サマリー
- 総テスト数: 5件
- 成功: 3件
- 失敗: 2件
- 成功率: 60%

### `tests/integration/test_jenkins_agent_ami_cloudwatch.py::test_translator_validation_step_present_in_components`
- **エラー**: '-input /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json' not found in component data
- **スタックトレース**:
  ```
  File "tests/integration/test_jenkins_agent_ami_cloudwatch.py", line 137, in test_translator_validation_step_present_in_components
    self.assertIn("-input /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json", data)
  AssertionError: '-input /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json' not found in '... "$TRANSLATOR" -input "$CONFIG_PATH" -format json -output "$OUTPUT_PATH"\n            - cat /tmp/cwagent.translated.json\n\n      - name: EnableCloudWatchAgent\n        action: ExecuteBash\n        inputs:\n          commands:\n            - echo "Enabling CloudWatch Agent service..."\n            - systemctl enable amazon-cloudwatch-agent\n            - echo "CloudWatch Agent will start automatically on instance boot"\n\n      - name: PullDockerImages\n ...'
  ```

### `tests/integration/test_jenkins_agent_ami_cloudwatch.py::test_dashboard_and_alarm_guidance_is_documented`
- **エラー**: Regex didn't match: '(5 ?minutes|5\\s*分)' not found in operations doc content
- **スタックトレース**:
  ```
  File "tests/integration/test_jenkins_agent_ami_cloudwatch.py", line 168, in test_dashboard_and_alarm_guidance_is_documented
    self.assertRegex(content, r"(5 ?minutes|5\\s*分)", "Sustained high-usage period guidance should be present")
  AssertionError: Regex didn't match: '(5 ?minutes|5\\s*分)' not found in '# Jenkins Agent CPU 監視ガイド\n\n...CPU 使用率が **80% 超過** の状態が **5 分間** 継続\n- ディメンション: `AutoScalingGroupName`...'
  ```
