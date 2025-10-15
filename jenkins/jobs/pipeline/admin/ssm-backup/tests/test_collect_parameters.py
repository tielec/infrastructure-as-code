import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
CONFIG_DIR = TESTS_DIR / "config"
BIN_DIR = TESTS_DIR / "bin"
COLLECT_SCRIPT = TESTS_DIR.parents[1] / "scripts" / "collect_parameters.sh"


class CollectParametersTests(unittest.TestCase):
    # 正常系: リージョンディレクトリが初期化され必要な成果物が生成されること
    def test_region_directory_is_reset_and_artifacts_created(self):
        if shutil.which("jq") is None:
            self.skipTest("jq is required for collect_parameters.sh tests")

        with tempfile.TemporaryDirectory(prefix="collect-") as tmpdir:
            data_dir = Path(tmpdir) / "data" / "us-west-2"
            data_dir.mkdir(parents=True, exist_ok=True)
            old_file = data_dir / "old.json"
            old_file.write_text("{}", encoding="utf-8")

            env = os.environ.copy()
            env.update(
                {
                    "ENVIRONMENT": "dev",
                    "ENV_FILTER": "/dev/",
                    "AWS_REGION": "us-west-2",
                    "BACKUP_DATE": "2024-01-01",
                    "BACKUP_TIMESTAMP": "20240101_000001",
                    "DATA_DIR": str(data_dir),
                    "TARGET_REGION": "us-west-2",
                    "PATH": f"{BIN_DIR}:{env.get('PATH', '')}",
                    "AWS_MOCK_BASE": str(CONFIG_DIR),
                    "AWS_MOCK_SCENARIO": "success",
                }
            )

            result = subprocess.run(
                [str(COLLECT_SCRIPT)],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )

            files = {item.name for item in data_dir.iterdir()}
            self.assertNotIn("old.json", files)
            self.assertIn("parameter_names.txt", files)
            self.assertIn("backup.json", files)
            self.assertIn("summary.json", files)
            self.assertIn("Target Region: us-west-2", result.stdout)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
