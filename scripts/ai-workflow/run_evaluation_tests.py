#!/usr/bin/env python3
"""Test runner for evaluation phase tests"""
import subprocess
import sys

# Run pytest with specific options
cmd = [
    sys.executable, '-m', 'pytest',
    'tests/unit/phases/test_evaluation.py',
    '-v',
    '--tb=short',
    '--no-header'
]

print("=" * 80)
print("Running Evaluation Phase Unit Tests")
print("=" * 80)
print(f"Command: {' '.join(cmd)}")
print("=" * 80)
print()

# Execute the command
result = subprocess.run(cmd, capture_output=True, text=True)

# Print output
print(result.stdout)
if result.stderr:
    print("STDERR:")
    print(result.stderr)

# Exit with the same code
sys.exit(result.returncode)
