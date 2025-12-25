#!/usr/bin/env bash
set -euo pipefail

: "${JENKINS_URL:?JENKINS_URL environment variable is required for Jenkins CLI calls}"
JENKINS_CLI_BIN="${JENKINS_CLI_BIN:-java}"
JENKINS_CLI_JAR="${JENKINS_CLI_JAR:-jenkins-cli.jar}"
readonly -a JENKINS_CLI_BASE=("${JENKINS_CLI_BIN}" "-jar" "${JENKINS_CLI_JAR}" "-s" "${JENKINS_URL}")

TARGET_JOB="Infrastructure_Management/Shutdown-Environment-Scheduler"
SEED_JOB="Admin_Jobs/job-creator"
DOWNSTREAM_JOB="Infrastructure_Management/Shutdown_Jenkins_Environment"

print_step() {
  echo
  echo "=== $1 ==="
}

run_cli() {
  echo "+ ${JENKINS_CLI_BASE[*]} $*"
  "${JENKINS_CLI_BASE[@]}" "$@"
}

extract_next_build() {
  local job="$1"
  local raw
  raw=$(
    run_cli get-job "$job" \
      | grep -o '<nextBuildNumber>[0-9]*</nextBuildNumber>' \
      | tail -n1
  )
  raw="${raw//[^0-9]/}"
  if [[ -z "${raw}" ]]; then
    echo "Unable to parse nextBuildNumber for ${job}" >&2
    exit 1
  fi
  printf '%s' "${raw}"
}

step_current_state() {
  print_step "Phase 3 Step 1: baseline state"
  run_cli get-job "$TARGET_JOB" | grep -i disabled
  run_cli get-job "$TARGET_JOB" | grep -o '<spec>H 15 \* \* \*</spec>'
  run_cli get-job "$TARGET_JOB" | grep -o '<nextBuildNumber>[0-9]*</nextBuildNumber>' | tail -n1
}

run_seed_job() {
  print_step "Phase 3 Step 3: execute seed job"
  run_cli build "$SEED_JOB" -s
  local seed_build
  seed_build=$(extract_next_build "$SEED_JOB")
  seed_build=$((seed_build - 1))
  run_cli console "$SEED_JOB" "$seed_build" | tail -n 20
}

step_verify_disabled() {
  print_step "Phase 3 Step 4: confirm disabled scheduler"
  run_cli get-job "$TARGET_JOB" | grep "<disabled>true</disabled>"
  run_cli get-job "$TARGET_JOB" | grep -A5 -B5 "TimerTrigger"
}

run_manual_dry_run() {
  print_step "Phase 3 Step 2/5: manual DRY_RUN execution"
  run_cli build "$TARGET_JOB" -s -p DRY_RUN=true
  local manual_build
  manual_build=$(extract_next_build "$TARGET_JOB")
  manual_build=$((manual_build - 1))
  if ! run_cli console "$TARGET_JOB" "$manual_build" | grep -i shutdown >/dev/null; then
    echo "Manual build console did not output a shutdown marker" >&2
  fi
}

step_regression_check() {
  print_step "Phase 3 Step 3/6: regression and downstream verification"
  run_cli list-jobs Infrastructure_Management/
  if run_cli get-job "$DOWNSTREAM_JOB" | grep -q "<disabled>true</disabled>"; then
    echo "Downstream job ${DOWNSTREAM_JOB} is disabled unexpectedly" >&2
    exit 1
  fi
}

main() {
  step_current_state
  run_seed_job
  step_verify_disabled
  run_manual_dry_run
  step_regression_check
  echo
  echo "Phase 3 CLI flow complete. Revisit Jenkins UI and logs if additional verification is needed."
}

main "$@"
