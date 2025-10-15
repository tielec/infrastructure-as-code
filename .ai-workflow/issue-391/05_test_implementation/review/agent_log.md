# Codex Agent 実行ログ

開始日時: 2025/10/15 14:33:38

---

## Turn 1: スレッド開始

**Thread ID**: `0199e84a-77dc-7ad1-92e7-fd9f0799831d`

## Turn 2: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc "cat '@.ai-workflow/issue-391/05_test_implementation/output/test-implementation.md'"`
**ステータス**: failed (exit_code=-1)

```text
No such file or directory (os error 2)
```

## Turn 3: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc ls`
**ステータス**: completed (exit_code=0)

```text
ARCHITECTURE.md
CLAUDE.md
CONTRIBUTION.md
LICENSE
README.md
ansible
bootstrap
docs
jenkins
pulumi
run_tests_issue_322.sh
scripts
```

## Turn 4: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc 'ls -a'`
**ステータス**: completed (exit_code=0)

```text
.
..
.ai-workflow
.claude
.git
.github
.gitignore
ARCHITECTURE.md
CLAUDE.md
CONTRIBUTION.md
LICENSE
README.md
ansible
bootstrap
docs
jenkins
pulumi
run_tests_issue_322.sh
scripts
```

## Turn 5: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc 'cat .ai-workflow/issue-391/05_test_implementation/output/test-implementation.md'`
**ステータス**: completed (exit_code=0)

```text
# テストコード実装ログ

## 実装サマリー
- テスト戦略: UNIT_INTEGRATION
- テストファイル数: 3個
- テストケース数: 9個

## テストファイル一覧

### 新規作成
- `pulumi/jenkins-ssm-backup-s3/__tests__/index.test.ts`: Pulumiスタックのユニットテスト。Config検証エラー、多リージョンバケット生成、SSMメタデータ/互換キー、`bucketMap` エクスポートを検証。
- `jenkins/jobs/pipeline/admin/ssm-backup/tests/test_pipeline_runner.py`: Jenkinsパイプラインの統合テスト。モックAWSと`collect_parameters.sh`を組み合わせて成功/途中失敗シナリオをシミュレート。
- `jenkins/jobs/pipeline/admin/ssm-backup/tests/test_collect_parameters.py`: `collect_parameters.sh` のディレクトリ初期化と成果物生成を検証する統合テスト。

## テストケース詳細

### ファイル: pulumi/jenkins-ssm-backup-s3/__tests__/index.test.ts
- **throws when regions are not configured**: `regions` 未設定時に明示的な例外が出ることを確認。
- **throws when defaultRegion is not part of regions**: `defaultRegion` がリージョン配列に含まれない場合に失敗することを確認。
- **creates regional S3 buckets with encryption and public access block**: 各リージョンで暗号化・公開遮断設定付きバケットが生成されることを確認。
- **emits region-specific SSM parameters and legacy parameter for default region**: リージョン別SSMパラメータとレガシー互換キーが正しく出力されることを確認。
- **publishes region metadata list and default region parameters**: リージョン一覧・デフォルトリージョンのメタデータがSSMに登録されることを確認。
- **exports bucketMap containing all configured regions**: `bucketMap` が全リージョンのバケット名を返すことを確認。

### ファイル: jenkins/jobs/pipeline/admin/ssm-backup/tests/test_pipeline_runner.py
- **test_success_sequence_creates_summaries_for_all_regions**: モックAWSで全リージョン成功時にサマリーが生成されることを確認。
- **test_failure_on_second_region_marks_summary_and_stops**: 2番目のリージョンでAWSエラーが発生した場合に処理が停止し失敗情報が残ることを確認。

### ファイル: jenkins/jobs/pipeline/admin/ssm-backup/tests/test_collect_parameters.py
- **test_region_directory_is_reset_and_artifacts_created**: リージョンディレクトリが初期化され、`backup.json`・`summary.json`・`parameter_names.txt` が生成されることを確認。

## 次のステップ
- Phase 6で `npm test -- --runInBand` および `python -m unittest discover jenkins/jobs/pipeline/admin/ssm-backup/tests` を実行して動作を確認。
```

## Turn 6: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc "sed -n '1,200p' pulumi/jenkins-ssm-backup-s3/__tests__/index.test.ts"`
**ステータス**: completed (exit_code=0)

```text
import * as fs from "fs";
import * as path from "path";
import * as pulumi from "@pulumi/pulumi";
import type { ConfigValue } from "@pulumi/pulumi/config";
import type { MockResourceArgs } from "@pulumi/pulumi/runtime";
import { mockCallerIdentity } from "./fixtures/mock_account";

type ConfigFixture = {
    projectName?: string;
    environment?: string;
    regions?: string[];
    defaultRegion?: string;
    ssmHomeRegion?: string;
};

type RecordedResource = {
    name: string;
    type: string;
    inputs: Record<string, any>;
    state: Record<string, any>;
};

const FIXTURE_DIR = path.resolve(__dirname, "fixtures");
const PROJECT_KEY = "jenkins-ssm-backup-s3";
const MOCK_ACCOUNT_ID = mockCallerIdentity.accountId;

let recordedResources: RecordedResource[] = [];

const loadFixture = (fileName: string): ConfigFixture => {
    const content = fs.readFileSync(path.join(FIXTURE_DIR, fileName), "utf-8");
    return JSON.parse(content) as ConfigFixture;
};

const toConfigMap = (fixture: ConfigFixture): Record<string, ConfigValue> => {
    const config: Record<string, ConfigValue> = {};
    if (fixture.projectName !== undefined) {
        config[`${PROJECT_KEY}:projectName`] = { value: fixture.projectName };
    }
    if (fixture.environment !== undefined) {
        config[`${PROJECT_KEY}:environment`] = { value: fixture.environment };
    }
    if (fixture.regions !== undefined) {
        config[`${PROJECT_KEY}:regions`] = { value: JSON.stringify(fixture.regions) };
    }
    if (fixture.defaultRegion !== undefined) {
        config[`${PROJECT_KEY}:defaultRegion`] = { value: fixture.defaultRegion };
    }
    if (fixture.ssmHomeRegion !== undefined) {
        config[`${PROJECT_KEY}:ssmHomeRegion`] = { value: fixture.ssmHomeRegion };
    }
    return config;
};

const bucketNameFor = (fixture: ConfigFixture, region: string): string => {
    return `${fixture.projectName}-ssm-backup-${fixture.environment}-${MOCK_ACCOUNT_ID}-${region}`;
};

const registerMocks = (fixture: ConfigFixture) => {
    recordedResources = [];
    const pulumiConfig = toConfigMap(fixture);
    const resolvedDefaultRegion = fixture.defaultRegion ?? fixture.regions?.[0] ?? "ap-northeast-1";

    pulumi.runtime.setMocks(
        {
            newResource: (args: MockResourceArgs) => {
                const state: Record<string, any> = { ...args.inputs };

                if (args.type === "pulumi:providers:aws") {
                    recordedResources.push({
                        name: args.name,
                        type: args.type,
                        inputs: args.inputs,
                        state,
                    });
                    return {
                        id: `${args.name}_id`,
                        state,
                    };
                }

                if (args.type === "aws:s3/bucket:Bucket") {
                    const regionTag =
                        (args.inputs?.tags && (args.inputs.tags.Region as string | undefined)) ?? resolvedDefaultRegion;
                    const bucketName = bucketNameFor(fixture, regionTag);
                    state.bucket = bucketName;
                    state.arn = `arn:aws:s3:::${bucketName}`;
                    state.region = regionTag;
                    state.versioning = args.inputs.versioning;
                    state.serverSideEncryptionConfiguration = args.inputs.serverSideEncryptionConfiguration;
                }

                if (args.type === "aws:s3/bucketPolicy:BucketPolicy") {
                    const regionTag =
                        (args.inputs?.tags && (args.inputs.tags.Region as string | undefined)) ?? resolvedDefaultRegion;
                    const bucketName = bucketNameFor(fixture, regionTag);
                    const bucketArn = `arn:aws:s3:::${bucketName}`;
                    state.bucket = args.inputs.bucket;
                    state.policy = JSON.stringify({
                        Version: "2012-10-17",
                        Statemen
... (truncated)
```

## Turn 7: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc "sed -n '200,400p' pulumi/jenkins-ssm-backup-s3/__tests__/index.test.ts"`
**ステータス**: completed (exit_code=0)

```text
// 正常系: 各リージョンで暗号化・公開遮断設定付きのバケットが生成されること
    test("creates regional S3 buckets with encryption and public access block", async () => {
        const fixture = loadFixture("regions_dual.json");
        await importStack<typeof import("../index")>(fixture);

        const buckets = recordedResources.filter(r => r.type === "aws:s3/bucket:Bucket");
        expect(buckets).toHaveLength(fixture.regions?.length ?? 0);

        for (const bucket of buckets) {
            expect(bucket.state.bucket).toMatch(
                new RegExp(`^${fixture.projectName}-ssm-backup-${fixture.environment}-${MOCK_ACCOUNT_ID}-[a-z0-9-]+$`),
            );

            expect(bucket.state.serverSideEncryptionConfiguration?.rule?.applyServerSideEncryptionByDefault?.sseAlgorithm).toBe(
                "AES256",
            );
            expect(bucket.state.versioning?.enabled).toBe(true);
        }

        const accessBlocks = recordedResources.filter(r => r.type === "aws:s3/bucketPublicAccessBlock:BucketPublicAccessBlock");
        expect(accessBlocks).toHaveLength(fixture.regions?.length ?? 0);
        accessBlocks.forEach(block => {
            expect(block.inputs.blockPublicAcls).toBe(true);
            expect(block.inputs.blockPublicPolicy).toBe(true);
            expect(block.inputs.ignorePublicAcls).toBe(true);
            expect(block.inputs.restrictPublicBuckets).toBe(true);
        });
    });

    // 正常系: リージョン別パラメータとレガシー互換パラメータが出力されること
    test("emits region-specific SSM parameters and legacy parameter for default region", async () => {
        const fixture = loadFixture("regions_dual.json");
        const stack = await importStack<typeof import("../index")>(fixture);
        const bucketMap = await stack.bucketMap;
        const defaultBucket = bucketMap[fixture.defaultRegion as string];

        const ssmParameters = recordedResources.filter(r => r.type === "aws:ssm/parameter:Parameter");

        const regionParameters = ssmParameters.filter(r =>
            String(r.state.name).includes(`/jenkins/${fixture.environment}/backup/`) &&
            String(r.state.name).endsWith("/s3-bucket-name"),
        );
        expect(regionParameters).toHaveLength(fixture.regions?.length ?? 0);
        regionParameters.forEach(param => {
            const regionMatch = String(param.state.name).match(/backup\/([^/]+)\/s3-bucket-name$/);
            const region = regionMatch ? regionMatch[1] : undefined;
            expect(region).toBeDefined();
            if (region) {
                expect(param.state.value).toBe(bucketMap[region]);
            }
        });

        const legacyParam = ssmParameters.find(r => r.state.name === `/jenkins/${fixture.environment}/backup/s3-bucket-name`);
        expect(legacyParam).toBeDefined();
        expect(legacyParam?.state.value).toBe(defaultBucket);
    });

    // 正常系: リージョン一覧とデフォルトリージョンのメタデータが SSM に登録されること
    test("publishes region metadata list and default region parameters", async () => {
        const fixture = loadFixture("regions_dual.json");
        await importStack<typeof import("../index")>(fixture);

        const ssmParameters = recordedResources.filter(r => r.type === "aws:ssm/parameter:Parameter");
        const regionListParam = ssmParameters.find(r => r.state.name === `/jenkins/${fixture.environment}/backup/region-list`);
        const defaultRegionParam = ssmParameters.find(
            r => r.state.name === `/jenkins/${fixture.environment}/backup/default-region`,
        );

        expect(regionListParam).toBeDefined();
        expect(defaultRegionParam).toBeDefined();

        const regionListValue = JSON.parse(regionListParam?.state.value ?? "[]");
        expect(regionListValue).toEqual(fixture.regions);
        expect(defaultRegionParam?.state.value).toBe(fixture.defaultRegion);
    });

    // 正常系: bucketMap エクスポートが全リージョンのバケット名を返すこと
    test("exports bucketMap containing all configured regions", async () => {
        const fixture = loadFixture("regions_triple.json");
        const st
... (truncated)
```

## Turn 8: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc 'cat .ai-workflow/issue-391/03_test_scenario/output/test-scenario.md'`
**ステータス**: completed (exit_code=0)

```text
# Issue #391 テストシナリオ: SSMバックアップのマルチリージョン対応

## 1. テスト戦略サマリー
- **テスト戦略**: UNIT_INTEGRATION（Phase 2 決定事項に準拠）
- **テスト対象範囲**: Pulumiスタック（`pulumi/jenkins-ssm-backup-s3`）の多リージョンリソース生成ロジック、Jenkinsパイプライン（Pipeline/Jenkinsfile・DSL・シェルスクリプト）によるリージョン逐次バックアップ処理および通知フロー
- **テスト目的**:
  - FR-1/FR-2/NFRと整合したマルチリージョンS3バケット&SSMメタデータ生成の正当性を検証
  - FR-3/FR-4の逐次実行・失敗制御・UI互換性を担保
  - FR-5および監視観点として、ログ/通知の検証手順を明確化

## 2. Unitテストシナリオ（Pulumi Jest + Mocks）

### テストケース名: validateConfig_regions未設定_異常系
- **目的**: `regions` が未定義または空配列の場合に明示的な例外を発生させ、誤ったPulumi実行を防ぐ（FR-1保守性）
- **前提条件**: Pulumi Configに `regions` を設定しない
- **入力**: `pulumi.Config()` モック値 `{ projectName: "jenkins-infra", environment: "dev" }`
- **期待結果**: `validateConfig()` が `Error("No regions configured")` をthrowし、`pulumi.runtime.setMocks` 起動前にテストが失敗扱いとなる
- **テストデータ**: `__tests__/fixtures/config_no_regions.json`

### テストケース名: validateConfig_defaultRegion不整合_異常系
- **目的**: `defaultRegion` が `regions` に含まれない場合に検知して失敗させる（FR-2互換性）
- **前提条件**: Config: `regions = ["ap-northeast-1"]`, `defaultRegion = "us-west-2"`
- **入力**: Pulumi Configモック
- **期待結果**: `validateConfig()` が `Error("defaultRegion must be included in regions")` をthrow
- **テストデータ**: `__tests__/fixtures/config_invalid_default.json`

### テストケース名: createRegionalResources_正常系
- **目的**: 各リージョンでS3バケット・パブリックアクセスブロック・バケットポリシー・リージョン別SSMパラメータが生成されることを確認（FR-1, NFR-セキュリティ）
- **前提条件**: `regions = ["ap-northeast-1", "us-west-2"]`, `defaultRegion = "ap-northeast-1"`, `projectName = "jenkins-infra"`, `environment = "dev"`
- **入力**: Pulumi mocks (`aws:s3/bucket:Bucket` など) に期待リソースを返させ `require("../index")`
- **期待結果**:
  - バケット名が `<project>-ssm-backup-<env>-<accountId>-<region>` 形式で2リージョン分生成
  - SSE設定 (`AES256`) と PublicAccessBlock が両リージョンで有効
  - `/jenkins/dev/backup/{region}/s3-bucket-name` パラメータが2件作成
- **テストデータ**: `__tests__/fixtures/mock_account.ts`

### テストケース名: emitLegacyParameter_正常系
- **目的**: 旧SSMキー `/jenkins/{env}/backup/s3-bucket-name` が defaultRegion のバケット名に更新されることを確認（FR-2）
- **前提条件**: `defaultRegion = "ap-northeast-1"`, `bucketMap["ap-northeast-1"] = "jenkins-infra-...-ap-northeast-1"`
- **入力**: `emitLegacyParameter(bucketMap)` を実行
- **期待結果**: SSM Parameter resourceが1件追加され、`value` が defaultRegion のバケット名と一致
- **テストデータ**: `__tests__/fixtures/bucket_map.json`

### テストケース名: emitRegionMetadata_JSON整形_正常系
- **目的**: `/jenkins/{env}/backup/region-list` と `/jenkins/{env}/backup/default-region` がJSON/文字列ともに正しく出力されることを確認（FR-1, FR-2, FR-5通知手順依存メタデータ）
- **前提条件**: `regions = ["ap-northeast-1", "us-west-2"]`, `defaultRegion = "ap-northeast-1"`
- **入力**: `emitRegionMetadata(regions, defaultRegion, provider)` 実行
- **期待結果**:
  - `region-list` の `value` が `["ap-northeast-1","us-west-2"]` JSON文字列
  - `default-region` の `value` が `ap-northeast-1`
  - いずれも `ssmHomeRegion` プロバイダーで作成される
- **テストデータ**: `__tests__/fixtures/regions_dual.json`

### テストケース名: bucketMap_export_正常系
- **目的**: `index.ts` のエクスポート `bucketMap` が全リージョンの `{ region: bucketName }` を返すことを確認し、Jenkins統合テストの前提を担保（FR-3/NFR-保守性）
- **前提条件**: `regions` に複数リージョンを設定
- **入力**: `require("../index")` 後の `bucketMap.apply`
- **期待結果**: `bucketMap` の `keys` が `regions` と一致し、各値がPulumi生成バケット名
- **テストデータ**: `__tests__/fixtures/regions_triple.json`

## 3. Integrationテストシナリオ

### シナリオ名: JenkinsPipeline_多リージョン順次バックアップ_正常系
- **目的**: Jenkinsパイプラインがリージョン一覧を取り込み、ステージを動的に生成し順次成功するハッピーパスを検証（FR-3, NFR-パフォーマンス）
- **前提条件**:
  - jenkinsfile-runner Dockerイメージ取得済み
  - テスト用SSMレスポンス `tests/config/regions_sample.json` を `scripts/aws_mock.sh` で返却
  - `DRY_RUN=true` で実行
- **テスト手順**:
  1. `tests/jenkinsfile_runner.sh` を `MODE=success` で実行
  2. Pipeline Initializeで`regionList=["ap-northeast-1","us-west-2"]`が読み込まれる
  3. `stage("Backup ap-northeast-1")` → `collect_parameters.sh` が `data/ap-northeast-1` に成果物を生成
  4. `stage("Backup us-west-2")` が同様に完了
  5. `Finalize Report` で `region_summaries.json` がWORK_DIRに出力
- **期待結果**:
  - Jenkinsログに2つのBackupステージが順序通り表示
  - `region_summaries.json` に各リージョン `status: "SUCCESS"`, `parameterCount > 0`
  - `post { success
... (truncated)
```

## Turn 9: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc "sed -n '1,200p' jenkins/jobs/pipeline/admin/ssm-backup/tests/test_pipeline_runner.py"`
**ステータス**: completed (exit_code=0)

```text
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
```

## Turn 10: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc "sed -n '1,200p' jenkins/jobs/pipeline/admin/ssm-backup/tests/test_collect_parameters.py"`
**ステータス**: completed (exit_code=0)

```text
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
```

## Turn 11: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc "sed -n '1,200p' jenkins/jobs/pipeline/admin/ssm-backup/tests/pipeline_runner.py"`
**ステータス**: completed (exit_code=0)

```text
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

        parameter_count = int(summary.get("parameterCount") or summary.get("para
... (truncated)
```

## Turn 12: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc "sed -n '120,220p' .ai-workflow/issue-391/03_test_scenario/output/test-scenario.md"`
**ステータス**: completed (exit_code=0)

```text
### シナリオ名: collectParameters_リージョン分離動作_正常系
- **目的**: `collect_parameters.sh` がリージョンごとのディレクトリを安全に扱い、既存ファイルを削除して最新の成果物だけを残すことを確認（FR-3/NFR-保守性）
- **前提条件**:
  - `DATA_DIR=/tmp/work/data/us-west-2` が既に存在し、旧ファイルが残っている
- **テスト手順**:
  1. `TARGET_REGION=us-west-2` `DRY_RUN=true` でスクリプトを起動
  2. 実行前に`touch /tmp/work/data/us-west-2/old.json`
  3. スクリプト完了後にディレクトリ内容を確認
- **期待結果**:
  - `old.json` が削除され、新たに `parameter_names.txt`, `parameters.json` のみ生成
  - ログに `Target Region: us-west-2` が出力
- **確認項目**:
  - `DATA_DIR` のパーミッションが保持されていること
  - エラー終了時にはクリーンアップが実施されないこと（別テストで確認済み）

## 4. テストデータ
- `__tests__/fixtures/config_no_regions.json`: `regions` 未設定のPulumi Config
- `__tests__/fixtures/config_invalid_default.json`: `defaultRegion` が `regions` と不整合な設定
- `__tests__/fixtures/regions_dual.json` / `regions_triple.json`: 多リージョン構成のConfigサンプル
- `__tests__/fixtures/mock_account.ts`: Pulumi mocks用の `accountId`・`region` 応答
- `__tests__/fixtures/bucket_map.json`: defaultRegionのバケット情報
- `jenkins/jobs/pipeline/admin/ssm-backup/tests/config/regions_sample.json`: Jenkins統合テスト用SSMレスポンスモック
- `tests/output/slack_payload.json`, `tests/output/region_summaries_failure.json`: Jenkins統合テストで生成される検証用成果物
- `tests/config/jobdsl_baseline.xml`: DSL差分比較のベースライン

## 5. テスト環境要件
- **ローカル/CI要件**:
  - Node.js 18系、npm、`ts-jest`/`@types/jest` をインストール済み
  - Pulumi CLI（プレビュー確認用、ユニットテストではモックを利用）
  - Docker 20.x 以上（jenkinsfile-runnerコンテナ実行用）
- **外部サービス/モック**:
  - AWSサービスは直接呼び出さず、Pulumi mocks と `scripts/aws_mock.sh` で全レスポンスをモック化
  - Slack/メール通知はHTTPサーバモックとローカルSMTPモック（`python -m smtpd` 等）を使用
- **CI/CD統合**:
  - Unitテスト: `npm test -- --runInBand`
  - Integrationテスト: `./jenkins/jobs/pipeline/admin/ssm-backup/tests/jenkinsfile_runner.sh MODE={success|fail_second_region}`
  - DSL差分検証: `./jenkins/jobs/pipeline/admin/ssm-backup/tests/jobdsl_verify.sh`（新規追加予定）

---

- [x] Phase 2の戦略（UNIT_INTEGRATION）に準拠したシナリオである  
- [x] 主要な正常系（Pulumi正常生成、Jenkins順次成功、DSL互換）がカバーされている  
- [x] 主要な異常系（Pulumi config不備、Jenkins途中失敗）がカバーされている  
- [x] 期待結果が各ケースで明確に記載されている
```

## Turn 13: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc "sed -n '1,200p' jenkins/jobs/pipeline/admin/ssm-backup/scripts/collect_parameters.sh"`
**ステータス**: completed (exit_code=0)

```text
#!/bin/bash
# SSM Parameter Collection and Backup Script
# SSMパラメータを収集してバックアップファイルを作成
# 
# 使用方法:
#   このスクリプトは環境変数を通じて設定を受け取ります
#   必須環境変数:
#     - ENVIRONMENT: バックアップ対象の環境 (dev/prod)
#     - ENV_FILTER: パラメータフィルタ文字列 (/dev/, /prod/)
#     - AWS_REGION: AWSリージョン
#     - BACKUP_DATE: バックアップ日付 (YYYY-MM-DD)
#     - BACKUP_TIMESTAMP: バックアップタイムスタンプ
#     - DATA_DIR: データ出力ディレクトリ
#
# 戻り値:
#   0: 正常終了
#   1: エラー発生

set -euo pipefail
SECONDS=0

echo "======================================"
echo "SSM Parameter Collection Script"
echo "======================================"
echo "Environment: ${ENVIRONMENT}"
echo "Filter: ${ENV_FILTER}"
echo "Region: ${AWS_REGION}"
echo "Backup Date: ${BACKUP_DATE}"
echo "Backup Timestamp: ${BACKUP_TIMESTAMP}"
echo "Target Region: ${AWS_REGION}"
echo "======================================"

mkdir -p "${DATA_DIR}"
rm -f "${DATA_DIR}/"*

# AWS認証情報の確認
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity --region ${AWS_REGION}; then
    echo "Error: Failed to get AWS credentials. Please check IAM role or credentials."
    exit 1
fi
echo "AWS credentials verified."

# AWS API呼び出しのリトライ機能
aws_cli_with_retry() {
    local max_retries=5
    local retry_delay=3  # 初期待機時間を長めに設定
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        # AWS CLIを実行（環境変数で制御）
        if output=$(AWS_PAGER="" AWS_CLI_AUTO_PROMPT=off "$@" 2>&1); then
            echo "$output"
            return 0
        else
            if echo "$output" | grep -q "ThrottlingException\|Rate exceeded"; then
                retry_count=$((retry_count + 1))
                echo "  Rate limit hit. Retry ${retry_count}/${max_retries} after ${retry_delay}s..." >&2
                sleep $retry_delay
                retry_delay=$((retry_delay * 2))  # Exponential backoff
                if [ $retry_delay -gt 60 ]; then
                    retry_delay=60  # Max delay 60s
                fi
            else
                echo "Error: $output" >&2
                return 1
            fi
        fi
    done
    
    echo "Error: Max retries reached" >&2
    return 1
}

# パラメータ一覧の取得（ページネーション対応、フィルタリング最適化）
fetch_all_parameters() {
    local next_token=""
    local page=1
    local all_params="[]"
    
    # 初回実行前に待機（レート制限対策）
    echo "Waiting 2 seconds before API calls to avoid rate limiting..." >&2
    sleep 2
    
    while true; do
        echo "Fetching page ${page}..." >&2
        
        # AWS CLIコマンドの実行とエラーハンドリング
        local result
        local error_msg
        
        if [ -n "$next_token" ]; then
            echo "  Executing: aws ssm describe-parameters with filter --region ${AWS_REGION}" >&2
            # パラメータフィルタの値を変数に格納
            local filter_value="${ENV_FILTER:1:-1}"  # /dev/ -> dev
            # リトライ機能を使用（--next-tokenを使用）
            if ! result=$(aws_cli_with_retry aws ssm describe-parameters \
                --next-token "$next_token" \
                --max-results 50 \
                --parameter-filters "Key=Name,Option=Contains,Values=$filter_value" \
                --output json \
                --region ${AWS_REGION}); then
                echo "Error: Failed to describe parameters" >&2
                echo '{"Parameters": [], "NextToken": null}'
                return 1
            fi
        else
            echo "  Executing: aws ssm describe-parameters with filter --region ${AWS_REGION}" >&2
            # パラメータフィルタの値を変数に格納
            local filter_value="${ENV_FILTER:1:-1}"  # /dev/ -> dev
            # リトライ機能を使用
            if ! result=$(aws_cli_with_retry aws ssm describe-parameters \
                --max-results 50 \
                --parameter-filters "Key=Name,Option=Contains,Values=$filter_value" \
                --output json \
                --region ${AWS_REGION}); then
                echo "Error: Failed to describe parameters" >&2
                echo '{"Parameters": [], "NextToken": null}'
                return 1
            fi
        fi
        
        # 結果が空またはエラ
... (truncated)
```

## Turn 14: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc "sed -n '1,120p' jenkins/jobs/pipeline/admin/ssm-backup/tests/config/regions_sample.json"`
**ステータス**: completed (exit_code=0)

```text
{
  "environment": "dev",
  "metadataBasePath": "/jenkins/dev/backup",
  "defaultRegion": "ap-northeast-1",
  "regions": ["ap-northeast-1", "us-west-2"],
  "bucketMap": {
    "ap-northeast-1": "jenkins-infra-ssm-backup-dev-123456789012-ap-northeast-1",
    "us-west-2": "jenkins-infra-ssm-backup-dev-123456789012-us-west-2"
  }
}
```

## Turn 15: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc "sed -n '1,200p' pulumi/jenkins-ssm-backup-s3/index.ts"`
**ステータス**: completed (exit_code=0)

```text
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

type RegionalResources = {
    region: string;
    bucket: aws.s3.Bucket;
    publicAccessBlock: aws.s3.BucketPublicAccessBlock;
    bucketPolicy: aws.s3.BucketPolicy;
    ssmParameter: aws.ssm.Parameter;
};

const config = new pulumi.Config();
const projectName = config.require("projectName");
const environment = config.require("environment");
const configuredRegions = config.requireObject<string[]>("regions");
const defaultRegion = config.require("defaultRegion");
const ssmHomeRegion = config.get("ssmHomeRegion") || defaultRegion;

const regions = Array.from(new Set(configuredRegions));
if (regions.length === 0) {
    throw new Error("No regions configured. Please set 'regions' in Pulumi config.");
}

if (!regions.includes(defaultRegion)) {
    throw new Error("defaultRegion must be included in regions.");
}

const callerIdentity = pulumi.output(aws.getCallerIdentity({}));
const accountId = callerIdentity.apply(identity => identity.accountId);

const ssmProvider = createRegionProvider("ssm-home", ssmHomeRegion);

const regionalResources: Record<string, RegionalResources> = {};
for (const region of regions) {
    const provider = createRegionProvider(`region-${region}`, region);
    regionalResources[region] = createRegionalResources({
        region,
        accountId,
        environment,
        projectName,
        provider,
        ssmProvider,
    });
}

const defaultRegionResources = regionalResources[defaultRegion];
if (!defaultRegionResources) {
    throw new Error(`Failed to locate resources for default region '${defaultRegion}'.`);
}

const legacyParameter = emitLegacyParameter({
    environment,
    bucketName: defaultRegionResources.bucket.bucket,
    provider: ssmProvider,
});

emitRegionMetadata({
    regions,
    defaultRegion,
    environment,
    provider: ssmProvider,
});

export const bucketMap = pulumi
    .all(
        Object.values(regionalResources).map(res =>
            res.bucket.bucket.apply(bucketName => ({
                region: res.region,
                bucketName,
            })),
        ),
    )
    .apply(entries =>
        entries.reduce<Record<string, string>>((acc, entry) => {
            acc[entry.region] = entry.bucketName;
            return acc;
        }, {}),
    );

export const bucketNameOutput = defaultRegionResources.bucket.bucket;
export const bucketArn = defaultRegionResources.bucket.arn;
export const ssmBackupBucketParameter = legacyParameter.name;

interface RegionalResourceArgs {
    region: string;
    accountId: pulumi.Output<string>;
    environment: string;
    projectName: string;
    provider: aws.Provider;
    ssmProvider: aws.Provider | undefined;
}

function createRegionalResources(args: RegionalResourceArgs): RegionalResources {
    const { region, accountId, environment, projectName, provider, ssmProvider } = args;

    const bucketName = pulumi.interpolate`${projectName}-ssm-backup-${environment}-${accountId}-${region}`;

    const bucket = new aws.s3.Bucket(
        `ssm-backup-bucket-${region}`,
        {
            bucket: bucketName,
            versioning: {
                enabled: true,
            },
            serverSideEncryptionConfiguration: {
                rule: {
                    applyServerSideEncryptionByDefault: {
                        sseAlgorithm: "AES256",
                    },
                    bucketKeyEnabled: true,
                },
            },
            lifecycleRules: [
                {
                    id: "delete-old-backups",
                    enabled: true,
                    expiration: {
                        days: 30,
                    },
                    noncurrentVersionExpiration: {
                        days: 7,
                    },
                },
            ],
            objectLockEnabled: false,
            tags: {
                Name: bucketName,
                Environment: environment,
... (truncated)
```

## Turn 16: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc 'rg "interface Output" $(npm root --silent)/@pulumi/pulumi'`
**ステータス**: failed (exit_code=127)

```text
bash: line 1: rg: command not found
```

## Turn 17: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc 'ls jenkins/jobs/pipeline/admin/ssm-backup/tests/bin'`
**ステータス**: completed (exit_code=0)

```text
aws
```

## Turn 18: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc "sed -n '1,160p' jenkins/jobs/pipeline/admin/ssm-backup/tests/bin/aws"`
**ステータス**: completed (exit_code=0)

```text
#!/usr/bin/env python3
"""
Minimal AWS CLI stub for integration tests.

The behaviour is driven by JSON fixtures located in the tests/config directory.
Set AWS_MOCK_SCENARIO to choose which fixture to load.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List


def load_fixture() -> Dict[str, Any]:
    scenario = os.environ.get("AWS_MOCK_SCENARIO", "success")
    base_dir = os.environ.get(
        "AWS_MOCK_BASE",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "config"),
    )
    fixture_path = os.path.join(base_dir, f"aws_{scenario}.json")
    if not os.path.exists(fixture_path):
        raise SystemExit(f"Fixture not found for scenario '{scenario}': {fixture_path}")
    with open(fixture_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_region(args: List[str]) -> str:
    if "--region" in args:
        idx = args.index("--region")
        if idx + 1 < len(args):
            return args[idx + 1]
    return os.environ.get("AWS_REGION", "ap-northeast-1")


def parse_names(args: List[str]) -> List[str]:
    names: List[str] = []
    if "--names" in args:
        idx = args.index("--names") + 1
        while idx < len(args) and not args[idx].startswith("--"):
            names.append(args[idx])
            idx += 1
    return names


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("aws mock expects a service argument")

    fixture = load_fixture()
    service = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else ""
    args = sys.argv[2:]

    if service == "sts" and action == "get-caller-identity":
        print(json.dumps(fixture.get("callerIdentity", {})))
        return

    if service == "ssm" and action == "describe-parameters":
        region = parse_region(args)
        failure_cfg = (
            fixture.get("failures", {})
            .get("describeParameters", {})
            .get(region)
        )
        if failure_cfg:
            stderr = failure_cfg.get("stderr", "Unknown error")
            exit_code = int(failure_cfg.get("exitCode", 1))
            print(stderr, file=sys.stderr)
            sys.exit(exit_code)

        parameters = fixture.get("describeParameters", {}).get(region, [])
        response = {"Parameters": parameters, "NextToken": None}
        print(json.dumps(response))
        return

    if service == "ssm" and action == "get-parameters":
        region = parse_region(args)
        names = parse_names(args)
        store = fixture.get("getParameters", {}).get(region, {})
        parameters = [
            {"Name": name, "Value": store.get(name, "")}
            for name in names
            if name in store
        ]
        response = {"Parameters": parameters, "InvalidParameters": []}
        print(json.dumps(response))
        return

    if service == "s3" and action == "cp":
        # Simulate successful upload in dry-run tests.
        print("upload simulated", file=sys.stderr)
        return

    if service == "s3api" and action == "head-object":
        print("100 2024-01-01T00:00:00Z")
        return

    raise SystemExit(f"Unsupported aws mock call: {' '.join(sys.argv[1:])}")


if __name__ == "__main__":
    main()
```

## Turn 19: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc 'ls jenkins/jobs/pipeline/admin/ssm-backup/tests/config'`
**ステータス**: completed (exit_code=0)

```text
aws_fail_second_region.json
aws_success.json
regions_sample.json
```

## Turn 20: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc 'ls pulumi/jenkins-ssm-backup-s3/__tests__/fixtures'`
**ステータス**: completed (exit_code=0)

```text
bucket_map.json
config_invalid_default.json
config_no_regions.json
mock_account.ts
regions_dual.json
regions_triple.json
```

## Turn 21: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc 'cat pulumi/jenkins-ssm-backup-s3/__tests__/fixtures/mock_account.ts'`
**ステータス**: completed (exit_code=0)

```text
export const mockCallerIdentity = {
  accountId: "123456789012",
  arn: "arn:aws:iam::123456789012:user/mock",
  userId: "AIDACKCEVSQ6C2EXAMPLE",
};

export type MockCallerIdentity = typeof mockCallerIdentity;
```

## Turn 22: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc 'grep -n "backup.json" .ai-workflow/issue-391/03_test_scenario/output/test-scenario.md'`
**ステータス**: failed (exit_code=1)

## Turn 23: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc 'grep -n "parameters.json" -n jenkins/jobs/pipeline/admin/ssm-backup/scripts/collect_parameters.sh'`
**ステータス**: failed (exit_code=1)

## Turn 24: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc 'cat pulumi/jenkins-ssm-backup-s3/__tests__/fixtures/regions_dual.json'`
**ステータス**: completed (exit_code=0)

```text
{
  "projectName": "jenkins-infra",
  "environment": "dev",
  "regions": ["ap-northeast-1", "us-west-2"],
  "defaultRegion": "ap-northeast-1",
  "ssmHomeRegion": "ap-northeast-1"
}
```

## Turn 25: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc "nl -ba pulumi/jenkins-ssm-backup-s3/__tests__/index.test.ts | sed -n '1,200p'"`
**ステータス**: completed (exit_code=0)

```text
1	import * as fs from "fs";
     2	import * as path from "path";
     3	import * as pulumi from "@pulumi/pulumi";
     4	import type { ConfigValue } from "@pulumi/pulumi/config";
     5	import type { MockResourceArgs } from "@pulumi/pulumi/runtime";
     6	import { mockCallerIdentity } from "./fixtures/mock_account";
     7	
     8	type ConfigFixture = {
     9	    projectName?: string;
    10	    environment?: string;
    11	    regions?: string[];
    12	    defaultRegion?: string;
    13	    ssmHomeRegion?: string;
    14	};
    15	
    16	type RecordedResource = {
    17	    name: string;
    18	    type: string;
    19	    inputs: Record<string, any>;
    20	    state: Record<string, any>;
    21	};
    22	
    23	const FIXTURE_DIR = path.resolve(__dirname, "fixtures");
    24	const PROJECT_KEY = "jenkins-ssm-backup-s3";
    25	const MOCK_ACCOUNT_ID = mockCallerIdentity.accountId;
    26	
    27	let recordedResources: RecordedResource[] = [];
    28	
    29	const loadFixture = (fileName: string): ConfigFixture => {
    30	    const content = fs.readFileSync(path.join(FIXTURE_DIR, fileName), "utf-8");
    31	    return JSON.parse(content) as ConfigFixture;
    32	};
    33	
    34	const toConfigMap = (fixture: ConfigFixture): Record<string, ConfigValue> => {
    35	    const config: Record<string, ConfigValue> = {};
    36	    if (fixture.projectName !== undefined) {
    37	        config[`${PROJECT_KEY}:projectName`] = { value: fixture.projectName };
    38	    }
    39	    if (fixture.environment !== undefined) {
    40	        config[`${PROJECT_KEY}:environment`] = { value: fixture.environment };
    41	    }
    42	    if (fixture.regions !== undefined) {
    43	        config[`${PROJECT_KEY}:regions`] = { value: JSON.stringify(fixture.regions) };
    44	    }
    45	    if (fixture.defaultRegion !== undefined) {
    46	        config[`${PROJECT_KEY}:defaultRegion`] = { value: fixture.defaultRegion };
    47	    }
    48	    if (fixture.ssmHomeRegion !== undefined) {
    49	        config[`${PROJECT_KEY}:ssmHomeRegion`] = { value: fixture.ssmHomeRegion };
    50	    }
    51	    return config;
    52	};
    53	
    54	const bucketNameFor = (fixture: ConfigFixture, region: string): string => {
    55	    return `${fixture.projectName}-ssm-backup-${fixture.environment}-${MOCK_ACCOUNT_ID}-${region}`;
    56	};
    57	
    58	const registerMocks = (fixture: ConfigFixture) => {
    59	    recordedResources = [];
    60	    const pulumiConfig = toConfigMap(fixture);
    61	    const resolvedDefaultRegion = fixture.defaultRegion ?? fixture.regions?.[0] ?? "ap-northeast-1";
    62	
    63	    pulumi.runtime.setMocks(
    64	        {
    65	            newResource: (args: MockResourceArgs) => {
    66	                const state: Record<string, any> = { ...args.inputs };
    67	
    68	                if (args.type === "pulumi:providers:aws") {
    69	                    recordedResources.push({
    70	                        name: args.name,
    71	                        type: args.type,
    72	                        inputs: args.inputs,
    73	                        state,
    74	                    });
    75	                    return {
    76	                        id: `${args.name}_id`,
    77	                        state,
    78	                    };
    79	                }
    80	
    81	                if (args.type === "aws:s3/bucket:Bucket") {
    82	                    const regionTag =
    83	                        (args.inputs?.tags && (args.inputs.tags.Region as string | undefined)) ?? resolvedDefaultRegion;
    84	                    const bucketName = bucketNameFor(fixture, regionTag);
    85	                    state.bucket = bucketName;
    86	                    state.arn = `arn:aws:s3:::${bucketName}`;
    87	                    state.region = regionTag;
    88	                    state.versioning = args.inputs.versioning;
    89	                    state.serverSideEncryptionConfiguration = args.in
... (truncated)
```

## Turn 26: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc "nl -ba pulumi/jenkins-ssm-backup-s3/__tests__/index.test.ts | sed -n '200,400p'"`
**ステータス**: completed (exit_code=0)

```text
200	
   201	    // 正常系: 各リージョンで暗号化・公開遮断設定付きのバケットが生成されること
   202	    test("creates regional S3 buckets with encryption and public access block", async () => {
   203	        const fixture = loadFixture("regions_dual.json");
   204	        await importStack<typeof import("../index")>(fixture);
   205	
   206	        const buckets = recordedResources.filter(r => r.type === "aws:s3/bucket:Bucket");
   207	        expect(buckets).toHaveLength(fixture.regions?.length ?? 0);
   208	
   209	        for (const bucket of buckets) {
   210	            expect(bucket.state.bucket).toMatch(
   211	                new RegExp(`^${fixture.projectName}-ssm-backup-${fixture.environment}-${MOCK_ACCOUNT_ID}-[a-z0-9-]+$`),
   212	            );
   213	
   214	            expect(bucket.state.serverSideEncryptionConfiguration?.rule?.applyServerSideEncryptionByDefault?.sseAlgorithm).toBe(
   215	                "AES256",
   216	            );
   217	            expect(bucket.state.versioning?.enabled).toBe(true);
   218	        }
   219	
   220	        const accessBlocks = recordedResources.filter(r => r.type === "aws:s3/bucketPublicAccessBlock:BucketPublicAccessBlock");
   221	        expect(accessBlocks).toHaveLength(fixture.regions?.length ?? 0);
   222	        accessBlocks.forEach(block => {
   223	            expect(block.inputs.blockPublicAcls).toBe(true);
   224	            expect(block.inputs.blockPublicPolicy).toBe(true);
   225	            expect(block.inputs.ignorePublicAcls).toBe(true);
   226	            expect(block.inputs.restrictPublicBuckets).toBe(true);
   227	        });
   228	    });
   229	
   230	    // 正常系: リージョン別パラメータとレガシー互換パラメータが出力されること
   231	    test("emits region-specific SSM parameters and legacy parameter for default region", async () => {
   232	        const fixture = loadFixture("regions_dual.json");
   233	        const stack = await importStack<typeof import("../index")>(fixture);
   234	        const bucketMap = await stack.bucketMap;
   235	        const defaultBucket = bucketMap[fixture.defaultRegion as string];
   236	
   237	        const ssmParameters = recordedResources.filter(r => r.type === "aws:ssm/parameter:Parameter");
   238	
   239	        const regionParameters = ssmParameters.filter(r =>
   240	            String(r.state.name).includes(`/jenkins/${fixture.environment}/backup/`) &&
   241	            String(r.state.name).endsWith("/s3-bucket-name"),
   242	        );
   243	        expect(regionParameters).toHaveLength(fixture.regions?.length ?? 0);
   244	        regionParameters.forEach(param => {
   245	            const regionMatch = String(param.state.name).match(/backup\/([^/]+)\/s3-bucket-name$/);
   246	            const region = regionMatch ? regionMatch[1] : undefined;
   247	            expect(region).toBeDefined();
   248	            if (region) {
   249	                expect(param.state.value).toBe(bucketMap[region]);
   250	            }
   251	        });
   252	
   253	        const legacyParam = ssmParameters.find(r => r.state.name === `/jenkins/${fixture.environment}/backup/s3-bucket-name`);
   254	        expect(legacyParam).toBeDefined();
   255	        expect(legacyParam?.state.value).toBe(defaultBucket);
   256	    });
   257	
   258	    // 正常系: リージョン一覧とデフォルトリージョンのメタデータが SSM に登録されること
   259	    test("publishes region metadata list and default region parameters", async () => {
   260	        const fixture = loadFixture("regions_dual.json");
   261	        await importStack<typeof import("../index")>(fixture);
   262	
   263	        const ssmParameters = recordedResources.filter(r => r.type === "aws:ssm/parameter:Parameter");
   264	        const regionListParam = ssmParameters.find(r => r.state.name === `/jenkins/${fixture.environment}/backup/region-list`);
   265	        const defaultRegionParam = ssmParameters.find(
   266	            r => r.state.name === `/jenkins/${fixture.environment}/backup/default-region`,
   267	        );
   268	
   269	        expect(regionListParam).t
... (truncated)
```

## Turn 27: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc 'nl -ba jenkins/jobs/pipeline/admin/ssm-backup/tests/test_pipeline_runner.py'`
**ステータス**: completed (exit_code=0)

```text
1	import json
     2	import os
     3	import subprocess
     4	import sys
     5	import tempfile
     6	import unittest
     7	from pathlib import Path
     8	
     9	
    10	TESTS_DIR = Path(__file__).resolve().parent
    11	RUNNER = TESTS_DIR / "pipeline_runner.py"
    12	
    13	
    14	class PipelineRunnerTests(unittest.TestCase):
    15	    def run_scenario(self, scenario: str):
    16	        with tempfile.TemporaryDirectory(prefix=f"pipeline-{scenario}-") as tmpdir:
    17	            output_dir = Path(tmpdir) / "artifacts"
    18	            cmd = [
    19	                sys.executable,
    20	                str(RUNNER),
    21	                "--scenario",
    22	                scenario,
    23	                "--output",
    24	                str(output_dir),
    25	            ]
    26	            completed = subprocess.run(
    27	                cmd,
    28	                check=True,
    29	                capture_output=True,
    30	                text=True,
    31	                env=os.environ.copy(),
    32	            )
    33	            summary_path = output_dir / "region_summaries.json"
    34	            self.assertTrue(summary_path.exists(), "region summary artifact should be created")
    35	            with open(summary_path, "r", encoding="utf-8") as handle:
    36	                summaries = json.load(handle)
    37	            return summaries, completed, output_dir
    38	
    39	    # 正常系: 全リージョンが成功し、要約が生成されることを確認
    40	    def test_success_sequence_creates_summaries_for_all_regions(self):
    41	        summaries, completed, _ = self.run_scenario("success")
    42	        self.assertIn("ap-northeast-1", summaries)
    43	        self.assertIn("us-west-2", summaries)
    44	        for region, info in summaries.items():
    45	            self.assertEqual(info["status"], "SUCCESS", f"{region} expected to succeed")
    46	            self.assertTrue(info["bucket"].startswith("jenkins-infra-ssm-backup-dev"), "bucket name should follow convention")
    47	            self.assertTrue(info["dryRun"], "simulation should run in dry-run mode")
    48	            self.assertGreaterEqual(info["parameterCount"], 1)
    49	        self.assertIn("Pipeline scenario 'success' completed.", completed.stdout)
    50	
    51	    # 異常系: 2番目のリージョンで失敗した場合に処理が停止し失敗情報が残ること
    52	    def test_failure_on_second_region_marks_summary_and_stops(self):
    53	        summaries, _, output_dir = self.run_scenario("fail_second_region")
    54	        self.assertEqual(summaries["ap-northeast-1"]["status"], "SUCCESS")
    55	        self.assertEqual(summaries["us-west-2"]["status"], "FAILED")
    56	        self.assertIn("collect_parameters.sh exited with code", summaries["us-west-2"]["message"])
    57	        log_path = output_dir / "pipeline.log"
    58	        self.assertTrue(log_path.exists())
    59	        log_contents = log_path.read_text(encoding="utf-8")
    60	        self.assertIn("ThrottlingException", log_contents)
    61	
    62	
    63	if __name__ == "__main__":  # pragma: no cover
    64	    unittest.main()
```

## Turn 28: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc 'nl -ba jenkins/jobs/pipeline/admin/ssm-backup/tests/test_collect_parameters.py'`
**ステータス**: completed (exit_code=0)

```text
1	import os
     2	import shutil
     3	import subprocess
     4	import sys
     5	import tempfile
     6	import unittest
     7	from pathlib import Path
     8	
     9	
    10	TESTS_DIR = Path(__file__).resolve().parent
    11	CONFIG_DIR = TESTS_DIR / "config"
    12	BIN_DIR = TESTS_DIR / "bin"
    13	COLLECT_SCRIPT = TESTS_DIR.parents[1] / "scripts" / "collect_parameters.sh"
    14	
    15	
    16	class CollectParametersTests(unittest.TestCase):
    17	    # 正常系: リージョンディレクトリが初期化され必要な成果物が生成されること
    18	    def test_region_directory_is_reset_and_artifacts_created(self):
    19	        if shutil.which("jq") is None:
    20	            self.skipTest("jq is required for collect_parameters.sh tests")
    21	
    22	        with tempfile.TemporaryDirectory(prefix="collect-") as tmpdir:
    23	            data_dir = Path(tmpdir) / "data" / "us-west-2"
    24	            data_dir.mkdir(parents=True, exist_ok=True)
    25	            old_file = data_dir / "old.json"
    26	            old_file.write_text("{}", encoding="utf-8")
    27	
    28	            env = os.environ.copy()
    29	            env.update(
    30	                {
    31	                    "ENVIRONMENT": "dev",
    32	                    "ENV_FILTER": "/dev/",
    33	                    "AWS_REGION": "us-west-2",
    34	                    "BACKUP_DATE": "2024-01-01",
    35	                    "BACKUP_TIMESTAMP": "20240101_000001",
    36	                    "DATA_DIR": str(data_dir),
    37	                    "TARGET_REGION": "us-west-2",
    38	                    "PATH": f"{BIN_DIR}:{env.get('PATH', '')}",
    39	                    "AWS_MOCK_BASE": str(CONFIG_DIR),
    40	                    "AWS_MOCK_SCENARIO": "success",
    41	                }
    42	            )
    43	
    44	            result = subprocess.run(
    45	                [str(COLLECT_SCRIPT)],
    46	                env=env,
    47	                check=True,
    48	                capture_output=True,
    49	                text=True,
    50	            )
    51	
    52	            files = {item.name for item in data_dir.iterdir()}
    53	            self.assertNotIn("old.json", files)
    54	            self.assertIn("parameter_names.txt", files)
    55	            self.assertIn("backup.json", files)
    56	            self.assertIn("summary.json", files)
    57	            self.assertIn("Target Region: us-west-2", result.stdout)
    58	
    59	
    60	if __name__ == "__main__":  # pragma: no cover
    61	    unittest.main()
```

## Turn 29: ツール実行

**種別**: コマンド実行
**コマンド**: `bash -lc "sed -n '200,400p' jenkins/jobs/pipeline/admin/ssm-backup/scripts/collect_parameters.sh"`
**ステータス**: completed (exit_code=0)

```text
# パラメータ名を配列に読み込み
    mapfile -t PARAM_NAMES < ${DATA_DIR}/parameter_names.txt
    TOTAL_PARAMS=${#PARAM_NAMES[@]}

    # パラメータを取得してバックアップデータを作成（バッチ処理で高速化）
    echo "Fetching parameter values..."
    for ((i=0; i<$TOTAL_PARAMS; i+=BATCH_SIZE)); do
        end=$((i + BATCH_SIZE))
        if [ $end -gt $TOTAL_PARAMS ]; then
            end=$TOTAL_PARAMS
        fi

        echo "Fetching parameters $((i + 1))-$end of ${TOTAL_PARAMS}..."

        batch_params=()
        for ((j=i; j<end; j++)); do
            batch_params+=("${PARAM_NAMES[$j]}")
        done

        if [ ${#batch_params[@]} -gt 0 ]; then
            BATCH_RESULT=$(aws ssm get-parameters \
                --names "${batch_params[@]}" \
                --with-decryption \
                --output json \
                --region ${AWS_REGION} 2>/dev/null || echo '{"Parameters": [], "InvalidParameters": []}')

            VALID_PARAMS=$(echo "$BATCH_RESULT" | jq '.Parameters // []')
            if [ "$VALID_PARAMS" != "[]" ] && [ "$VALID_PARAMS" != "null" ]; then
                BACKUP_DATA=$(echo "$BACKUP_DATA" | jq --argjson new_params "$VALID_PARAMS" '. + $new_params')
            fi

            INVALID_PARAMS=$(echo "$BATCH_RESULT" | jq -r '.InvalidParameters[]?' 2>/dev/null)
            if [ -n "$INVALID_PARAMS" ]; then
                while IFS= read -r invalid_param; do
                    echo "Warning: Failed to get parameter: $invalid_param"
                    FAILED_PARAMS+=("$invalid_param")
                    FAILED_COUNT=$((FAILED_COUNT + 1))
                done <<< "$INVALID_PARAMS"
            fi
        fi

        if [ $end -lt $TOTAL_PARAMS ]; then
            sleep 2
        fi
    done
else
    echo "WARNING: No parameters found matching filter '${ENV_FILTER}'"
fi

COUNTER=$TOTAL_PARAMS
SUCCESSFUL_COUNT=$((COUNTER - FAILED_COUNT))

echo "Successfully fetched ${SUCCESSFUL_COUNT} parameters"
if [ "$FAILED_COUNT" -gt 0 ]; then
    echo "Failed to fetch ${FAILED_COUNT} parameters"
fi

# バックアップファイルの作成
echo "Creating backup file..."
BACKUP_JSON=$(jq -n \
    --arg date "${BACKUP_DATE}" \
    --arg timestamp "${BACKUP_TIMESTAMP}" \
    --arg environment "${ENVIRONMENT}" \
    --arg count "${SUCCESSFUL_COUNT}" \
    --argjson parameters "$BACKUP_DATA" \
    '{
        backup_date: $date,
        backup_timestamp: $timestamp,
        environment: $environment,
        parameter_count: $count | tonumber,
        parameters: $parameters
    }')

echo "$BACKUP_JSON" | jq '.' > ${DATA_DIR}/backup.json

execution_time=${SECONDS}

echo "======================================"
echo "Backup Summary"
echo "======================================"
echo "Backup file created: ${DATA_DIR}/backup.json"
echo "Total parameters backed up: ${SUCCESSFUL_COUNT}"
echo "Failed parameters: ${FAILED_COUNT}"
echo "======================================"

# サマリーファイルを生成して上位パイプラインで参照できるようにする
echo "Creating summary file..."
jq -n \
    --arg environment "${ENVIRONMENT}" \
    --arg region "${AWS_REGION}" \
    --arg backupDate "${BACKUP_DATE}" \
    --arg backupTimestamp "${BACKUP_TIMESTAMP}" \
    --argjson parameterCount ${SUCCESSFUL_COUNT} \
    --argjson failedCount ${FAILED_COUNT} \
    --argjson executionTimeSec ${execution_time} \
    '{
        environment: $environment,
        region: $region,
        backupDate: $backupDate,
        backupTimestamp: $backupTimestamp,
        parameterCount: $parameterCount,
        failedCount: $failedCount,
        executionTimeSec: $executionTimeSec,
        backup_date: $backupDate,
        backup_timestamp: $backupTimestamp,
        parameter_count: $parameterCount,
        failed_count: $failedCount
    }' > "${DATA_DIR}/summary.json"

echo "Summary file created: ${DATA_DIR}/summary.json"
```

## Turn 30: ツール実行

**種別**: agent_message
**ステータス**: completed

## Turn 31: 実行完了

**ステータス**: completed
**所要時間**: 464678ms
**ターン数**: N/A

---

**経過時間**: 464678ms
**開始**: 2025-10-15T14:33:38.462Z
**終了**: 2025-10-15T14:41:23.140Z