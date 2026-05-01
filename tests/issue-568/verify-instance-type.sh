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
  fail "VS-001-1 pulumi/jenkins-ssm-init/index.ts が存在しません"
fi
pass "VS-001-1 pulumi/jenkins-ssm-init/index.ts が存在します"

if grep -Fq 'value: "t4g.large"' "${TARGET_FILE}"; then
  pass 'VS-001-2 controller-instance-type に value: "t4g.large" が含まれています'
else
  fail 'VS-001-2 controller-instance-type に value: "t4g.large" が含まれていません'
fi

controller_block="$(sed -n '/controller-instance-type/,/});/p' "${TARGET_FILE}")"
if grep -Fq 't4g.' <<<"${controller_block}"; then
  pass "VS-001-3 controller-instance-type が t4g. プレフィックスを維持しています"
else
  fail "VS-001-3 controller-instance-type が t4g. プレフィックスを維持していません"
fi
