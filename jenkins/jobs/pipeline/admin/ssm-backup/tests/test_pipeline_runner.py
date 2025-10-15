import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
RUNNER = TESTS_DIR / "pipeline_runner.py"


class PipelineRunnerTests(unittest.TestCase):
    def run_scenario(self, scenario: str):
        with tempfile.TemporaryDirectory(prefix=f"pipeline-{scenario}-") as tmpdir:
            output_dir = Path(tmpdir) / "artifacts"
            cmd = [
                sys.executable,
                str(RUNNER),
                "--scenario",
                scenario,
                "--output",
                str(output_dir),
            ]
            completed = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                env=os.environ.copy(),
            )
            summary_path = output_dir / "region_summaries.json"
            self.assertTrue(summary_path.exists(), "region summary artifact should be created")
            with open(summary_path, "r", encoding="utf-8") as handle:
                summaries = json.load(handle)
            return summaries, completed, output_dir

    # 正常系: 全リージョンが成功し、要約が生成されることを確認
    def test_success_sequence_creates_summaries_for_all_regions(self):
        summaries, completed, _ = self.run_scenario("success")
        self.assertIn("ap-northeast-1", summaries)
        self.assertIn("us-west-2", summaries)
        for region, info in summaries.items():
            self.assertEqual(info["status"], "SUCCESS", f"{region} expected to succeed")
            self.assertTrue(info["bucket"].startswith("jenkins-infra-ssm-backup-dev"), "bucket name should follow convention")
            self.assertTrue(info["dryRun"], "simulation should run in dry-run mode")
            self.assertGreaterEqual(info["parameterCount"], 1)
        self.assertIn("Pipeline scenario 'success' completed.", completed.stdout)

    # 異常系: 2番目のリージョンで失敗した場合に処理が停止し失敗情報が残ること
    def test_failure_on_second_region_marks_summary_and_stops(self):
        summaries, _, output_dir = self.run_scenario("fail_second_region")
        self.assertEqual(summaries["ap-northeast-1"]["status"], "SUCCESS")
        self.assertEqual(summaries["us-west-2"]["status"], "FAILED")
        self.assertIn("collect_parameters.sh exited with code", summaries["us-west-2"]["message"])
        log_path = output_dir / "pipeline.log"
        self.assertTrue(log_path.exists())
        log_contents = log_path.read_text(encoding="utf-8")
        self.assertIn("ThrottlingException", log_contents)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
