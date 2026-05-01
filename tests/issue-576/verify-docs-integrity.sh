#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
RUNBOOK="${REPO_ROOT}/docs/jenkins-upgrade-runbook.md"
JENKINS_README="${REPO_ROOT}/jenkins/README.md"
CLAUDE_MD="${REPO_ROOT}/CLAUDE.md"
JENKINS_MGMT="${REPO_ROOT}/docs/operations/jenkins-management.md"

pass() {
  printf 'PASS: %s\n' "$1"
}

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

assert_file() {
  local path="$1"
  local code="$2"
  if [[ -f "${path}" ]]; then
    pass "${code} $(basename "${path}") が存在します"
  else
    fail "${code} ${path} が存在しません"
  fi
}

assert_contains() {
  local path="$1"
  local needle="$2"
  local code="$3"
  if grep -Fq "${needle}" "${path}"; then
    pass "${code} ${needle} を確認しました"
  else
    fail "${code} ${needle} が見つかりません"
  fi
}

assert_markdown_link() {
  local path="$1"
  local target="$2"
  local code="$3"
  if grep -Eq "\\[[^]]+\\]\\(${target//\//\\/}\\)" "${path}"; then
    pass "${code} ${target} の Markdown リンク形式を確認しました"
  else
    fail "${code} ${target} の Markdown リンク形式が見つかりません"
  fi
}

assert_relative_path_exists() {
  local base_file="$1"
  local relative_path="$2"
  local code="$3"
  local base_dir resolved_path
  base_dir="$(cd "$(dirname "${base_file}")" && pwd)"
  resolved_path="$(cd "${base_dir}" && cd "$(dirname "${relative_path}")" && pwd)/$(basename "${relative_path}")"
  if [[ -f "${resolved_path}" ]]; then
    pass "${code} ${relative_path} のリンク先が実在します"
  else
    fail "${code} ${relative_path} のリンク先が存在しません: ${resolved_path}"
  fi
}

extract_section() {
  local title="$1"
  sed -n "/^## ${title}$/,/^## /p" "${RUNBOOK}" | sed '$d'
}

assert_section_contains() {
  local title="$1"
  local needle="$2"
  local code="$3"
  local section_text
  section_text="$(extract_section "${title}")"
  if [[ -z "${section_text}" ]]; then
    fail "${code} ${title} セクションを抽出できません"
  fi
  if printf '%s\n' "${section_text}" | grep -Fq "${needle}"; then
    pass "${code} ${title} セクション内の ${needle} を確認しました"
  else
    fail "${code} ${title} セクション内に ${needle} が見つかりません"
  fi
}

assert_section_matches() {
  local title="$1"
  local regex="$2"
  local code="$3"
  local section_text
  section_text="$(extract_section "${title}")"
  if [[ -z "${section_text}" ]]; then
    fail "${code} ${title} セクションを抽出できません"
  fi
  if printf '%s\n' "${section_text}" | grep -Eq "${regex}"; then
    pass "${code} ${title} セクション内の正規表現 ${regex} を確認しました"
  else
    fail "${code} ${title} セクション内に正規表現 ${regex} が見つかりません"
  fi
}

assert_file "${RUNBOOK}" "DS-576-001"
assert_file "${JENKINS_README}" "DS-576-002"
assert_file "${CLAUDE_MD}" "DS-576-003"
assert_file "${JENKINS_MGMT}" "DS-576-004"

required_sections=(
  '## 事前準備'
  '## dev環境での検証'
  '## staging環境への展開'
  '## prod環境への展開'
  '## ロールバック手順'
  '## CVE対応の特例'
  '## 運用方針'
)

for section in "${required_sections[@]}"; do
  assert_contains "${RUNBOOK}" "${section}" "DS-576-010"
done

checklist_count="$(grep -c '^- \[ \]' "${RUNBOOK}")"
if [[ "${checklist_count}" -ge 10 ]]; then
  pass "DS-576-011 チェックリスト項目が ${checklist_count} 件あります"
else
  fail "DS-576-011 チェックリスト項目が不足しています: ${checklist_count} 件"
fi

assert_contains "${RUNBOOK}" 'deploy_jenkins_ssm_init.yml' "DS-576-012"
assert_contains "${RUNBOOK}" 'deploy_jenkins_application.yml' "DS-576-013"
assert_contains "${RUNBOOK}" 'https://www.jenkins.io/doc/upgrade-guide/' "DS-576-014"
assert_contains "${RUNBOOK}" 'https://www.jenkins.io/changelog-stable/' "DS-576-015"

assert_section_contains "事前準備" "Upgrade Guide" "DS-576-016"
assert_section_contains "事前準備" "Changelog" "DS-576-017"
assert_section_contains "事前準備" "プラグイン" "DS-576-018"
assert_section_contains "事前準備" "JCasC" "DS-576-019"
assert_section_matches "dev環境での検証" '1[[:space:]]*週間' "DS-576-020"
assert_section_matches "staging環境への展開" '3[〜-]5[[:space:]]*日' "DS-576-021"
assert_section_matches "prod環境への展開" '24[[:space:]]*時間' "DS-576-022"
assert_section_contains "ロールバック手順" "SSM" "DS-576-023"
assert_section_contains "ロールバック手順" "deploy_jenkins_application.yml" "DS-576-024"
assert_section_contains "ロールバック手順" "プラグイン" "DS-576-025"
assert_section_contains "CVE対応の特例" "Critical" "DS-576-026"
assert_section_contains "CVE対応の特例" "High" "DS-576-027"
assert_section_contains "運用方針" "LTS 固定" "DS-576-028"

assert_markdown_link "${JENKINS_README}" '../docs/jenkins-upgrade-runbook.md' "DS-576-030"
assert_relative_path_exists "${JENKINS_README}" '../docs/jenkins-upgrade-runbook.md' "DS-576-031"
assert_contains "${CLAUDE_MD}" 'docs/jenkins-upgrade-runbook.md' "DS-576-032"
assert_relative_path_exists "${CLAUDE_MD}" 'docs/jenkins-upgrade-runbook.md' "DS-576-033"
assert_contains "${CLAUDE_MD}" 'latest' "DS-576-034"
assert_contains "${CLAUDE_MD}" 'LTS 固定バージョン' "DS-576-035"
assert_markdown_link "${JENKINS_MGMT}" '../jenkins-upgrade-runbook.md' "DS-576-036"
assert_relative_path_exists "${JENKINS_MGMT}" '../jenkins-upgrade-runbook.md' "DS-576-037"

management_row="$(grep 'Jenkinsバージョン更新' "${JENKINS_MGMT}" || true)"
if [[ -n "${management_row}" ]] && [[ "${management_row}" == *"Runbook"* ]] && [[ "${management_row}" == *"jenkins-upgrade-runbook.md"* ]]; then
  pass "DS-576-038 Jenkinsバージョン更新の行に Runbook 参照があります"
else
  fail "DS-576-038 Jenkinsバージョン更新の行に Runbook 参照がありません"
fi
