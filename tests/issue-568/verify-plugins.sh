#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TARGET_FILE="${REPO_ROOT}/scripts/jenkins/groovy/install-plugins.groovy"

pass() {
  printf 'PASS: %s\n' "$1"
}

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

if [[ ! -f "${TARGET_FILE}" ]]; then
  fail "VS-002-1 install-plugins.groovy が存在しません"
fi
pass "VS-002-1 install-plugins.groovy が存在します"

if grep -Fq '"monitoring"' "${TARGET_FILE}"; then
  pass 'VS-002-2 monitoring プラグインが定義されています'
else
  fail 'VS-002-2 monitoring プラグインが定義されていません'
fi

if grep -Fq 'モニタリングプラグイン' "${TARGET_FILE}"; then
  pass "VS-002-3 日本語コメントが存在します"
else
  fail "VS-002-3 日本語コメントが存在しません"
fi

plugins_block="$(sed -n '/def plugins = \[/,/\]/p' "${TARGET_FILE}")"
if grep -Eq '^\]$' <<<"${plugins_block}"; then
  pass "VS-002-4 plugins 配列が ] で閉じられています"
else
  fail "VS-002-4 plugins 配列の閉じ括弧 ] が確認できません"
fi
