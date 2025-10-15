#!/usr/bin/env python3
"""
Lightweight pipeline harness that exercises collect_parameters.sh with mocked AWS CLI
to approximate the Jenkins multi-region backup flow.

The script is intentionally self-contained so it can run inside automated tests without
Docker or a full Jenkins controller.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Dict, List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[6]
SCRIPT_PATH = REPO_ROOT / "jenkins" / "jobs" / "pipeline" / "admin" / "ssm-backup" / "scripts" / "collect_parameters.sh"
TESTS_DIR = Path(__file__).resolve().parent
CONFIG_DIR = TESTS_DIR / "config"
BIN_DIR = TESTS_DIR / "bin"


class PipelineFailure(Exception):
    """Raised when a regional execution fails."""


def load_config() -> Dict[str, str]:
    with open(CONFIG_DIR / "regions_sample.json", "r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_dependencies() -> None:
    if not SCRIPT_PATH.exists():
        raise FileNotFoundError(f"collect_parameters.sh not found at {SCRIPT_PATH}")
    if shutil.which("jq") is None:
        raise EnvironmentError("jq is required to execute the integration tests")


def run_collect_parameters(env: Dict[str, str]) -> Tuple[int, str]:
    result = subprocess.run(
        [str(SCRIPT_PATH)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.returncode, result.stdout + result.stderr


def build_env(base_env: Dict[str, str], overrides: Dict[str, str]) -> Dict[str, str]:
    combined = base_env.copy()
    combined.update(overrides)
    return combined


def simulate_pipeline(scenario: str, output_dir: Path) -> Dict[str, Dict[str, object]]:
    ensure_dependencies()
    config = load_config()
    environment = config["environment"]
    bucket_map = config["bucketMap"]
    regions: List[str] = list(config["regions"])
    default_region = config["defaultRegion"]

    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir = output_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    base_env = os.environ.copy()
    base_env.update(
        {
            "ENVIRONMENT": environment,
            "ENV_FILTER": f"/{environment}/",
            "BACKUP_DATE": "2024-01-01",
            "BACKUP_TIMESTAMP": "20240101_000001",
            "WORKSPACE": str(work_dir),
            "PATH": f"{BIN_DIR}:{base_env.get('PATH', '')}",
            "AWS_MOCK_BASE": str(CONFIG_DIR),
            "AWS_MOCK_SCENARIO": scenario,
        }
    )

    region_summaries: Dict[str, Dict[str, object]] = {}
    execution_log: List[str] = []

    for region in regions:
        region_data_dir = work_dir / "data" / region
        region_data_dir.mkdir(parents=True, exist_ok=True)

        env = build_env(
            base_env,
            {
                "AWS_REGION": region,
                "TARGET_REGION": region,
                "DATA_DIR": str(region_data_dir),
            },
        )

        execution_log.append(f"Running backup for region={region}")
        return_code, combined_output = run_collect_parameters(env)
        execution_log.append(combined_output)

        if return_code != 0:
            region_summaries[region] = {
                "status": "FAILED",
                "message": f"collect_parameters.sh exited with code {return_code}",
                "log": combined_output.strip(),
            }
            break

        summary_path = region_data_dir / "summary.json"
        backup_path = region_data_dir / "backup.json"
        if not summary_path.exists() or not backup_path.exists():
            raise PipelineFailure(f"Expected summary outputs missing for region {region}")

        with open(summary_path, "r", encoding="utf-8") as handle:
            summary = json.load(handle)

        parameter_count = int(summary.get("parameterCount") or summary.get("parameter_count") or 0)
        execution_time_sec = int(summary.get("executionTimeSec") or summary.get("execution_time_sec") or 0)
        failed_count = int(summary.get("failedCount") or summary.get("failed_count") or 0)

        s3_key = f"{base_env['BACKUP_DATE']}/{region}/ssm-backup-{environment}-{region}-{base_env['BACKUP_TIMESTAMP']}.json"

        region_summaries[region] = {
            "status": "SUCCESS",
            "parameterCount": parameter_count,
            "bucket": bucket_map[region],
            "s3Key": s3_key,
            "dryRun": True,
            "durationSeconds": execution_time_sec,
            "executionTimeSec": execution_time_sec,
            "failedCount": failed_count,
        }

        # Mirror Jenkins behaviour by copying the backup file to a timestamped name.
        backup_file_target = region_data_dir / f"ssm-backup-{environment}-{region}-{base_env['BACKUP_TIMESTAMP']}.json"
        shutil.copyfile(backup_path, backup_file_target)

    with open(output_dir / "region_summaries.json", "w", encoding="utf-8") as handle:
        json.dump(region_summaries, handle, indent=2)

    with open(output_dir / "pipeline.log", "w", encoding="utf-8") as handle:
        handle.write("\n".join(execution_log))

    return region_summaries


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate Jenkins SSM backup pipeline")
    parser.add_argument(
        "--scenario",
        choices=["success", "fail_second_region"],
        default="success",
        help="Select the AWS mock scenario to execute.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Directory where artifacts should be written (defaults to a temp dir).",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    output_dir = args.output or Path(tempfile.mkdtemp(prefix="pipeline-runner-"))

    try:
        summaries = simulate_pipeline(args.scenario, output_dir)
    except PipelineFailure as exc:
        print(f"Pipeline failed: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    print(
        textwrap.dedent(
            f"""
            Pipeline scenario '{args.scenario}' completed.
            Results written to: {output_dir}
            Regions evaluated : {list(summaries.keys())}
            """
        ).strip()
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
