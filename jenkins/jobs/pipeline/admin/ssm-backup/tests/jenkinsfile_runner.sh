#!/usr/bin/env bash
# Lightweight wrapper that emulates the Jenkinsfile runner interface defined in the
# planning documents. It delegates to pipeline_runner.py with the requested scenario.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE_DEFAULT="success"

if [[ $# -gt 0 ]]; then
    case "$1" in
        success|fail_second_region)
            MODE="$1"
            shift
            ;;
        MODE=*)
            MODE="${1#MODE=}"
            shift
            ;;
        *)
            MODE="${MODE:-$MODE_DEFAULT}"
            ;;
    esac
else
    MODE="${MODE:-$MODE_DEFAULT}"
fi

python3 "${SCRIPT_DIR}/pipeline_runner.py" --scenario "${MODE}" "$@"
