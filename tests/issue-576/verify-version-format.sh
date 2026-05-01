#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TARGET_FILE="${REPO_ROOT}/pulumi/jenkins-ssm-init/index.ts"

pass() {
  printf 'PASS: %s\n' "$1"
}

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

if [[ ! -f "${TARGET_FILE}" ]]; then
  fail "VS-576-001 pulumi/jenkins-ssm-init/index.ts が存在しません"
fi
pass "VS-576-001 pulumi/jenkins-ssm-init/index.ts が存在します"

jenkins_block="$(sed -n '/const jenkinsVersionParam = new aws.ssm.Parameter/,/});/p' "${TARGET_FILE}")"
if [[ -z "${jenkins_block}" ]]; then
  fail "VS-576-002 jenkinsVersionParam の定義ブロックを抽出できません"
fi
pass "VS-576-002 jenkinsVersionParam の定義ブロックを抽出できました"

# コメントは定義ブロックの直前に置かれているため、前後数行を含めて確認する。
jenkins_context="$(sed -n '/\/\/ Jenkins設定/,/});/p' "${TARGET_FILE}")"

version="$(printf '%s\n' "${jenkins_block}" | sed -n 's/.*value: "\([0-9][0-9.]*\)".*/\1/p' | head -n 1)"
if [[ -z "${version}" ]]; then
  fail "VS-576-003 Jenkins バージョン値を抽出できません"
fi
pass "VS-576-003 Jenkins バージョン値 ${version} を抽出できました"

if [[ "${version}" == "latest" ]]; then
  fail "VS-576-004 Jenkins バージョンに latest が設定されています"
fi
pass "VS-576-004 Jenkins バージョンは latest ではありません"

if [[ "${version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  pass "VS-576-005 Jenkins バージョンが X.Y.Z 形式です"
else
  fail "VS-576-005 Jenkins バージョンが X.Y.Z 形式ではありません: ${version}"
fi

if printf '%s\n' "${jenkins_context}" | grep -Fq 'Issue #576'; then
  pass "VS-576-006 Issue #576 コメントが存在します"
else
  fail "VS-576-006 Issue #576 コメントが存在しません"
fi

if printf '%s\n' "${jenkins_context}" | grep -Fq 'docs/jenkins-upgrade-runbook.md'; then
  pass "VS-576-007 Runbook 参照コメントが存在します"
else
  fail "VS-576-007 Runbook 参照コメントが存在しません"
fi

required_lines=(
  'type: "String",'
  'overwrite: true,'
  'description: "Jenkins version to install",'
  'Environment: environment,'
  'ManagedBy: "pulumi",'
  'Component: "config",'
)

for line in "${required_lines[@]}"; do
  if printf '%s\n' "${jenkins_block}" | grep -Fq "${line}"; then
    pass "VS-576-008 必須メタデータを確認: ${line}"
  else
    fail "VS-576-008 必須メタデータが不足しています: ${line}"
  fi
done
