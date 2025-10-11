#!/usr/bin/env python3
"""
Test runner script for Phase 6 testing
Runs the TestImplementationPhase unit tests and captures output
"""
import subprocess
import sys
import os
from pathlib import Path

# Change to the correct directory
os.chdir(Path(__file__).parent / "scripts" / "ai-workflow")

# Run pytest
cmd = [
    sys.executable,
    "-m", "pytest",
    "tests/unit/phases/test_test_implementation.py",
    "-v",
    "--tb=short",
    "--color=yes"
]

print(f"Running command: {' '.join(cmd)}")
print(f"Working directory: {os.getcwd()}")
print("=" * 80)

result = subprocess.run(cmd, capture_output=True, text=True)

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr, file=sys.stderr)

sys.exit(result.returncode)
