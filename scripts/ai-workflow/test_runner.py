#!/usr/bin/env python3
"""Simple test runner to execute GitManager tests and capture results"""
import subprocess
import sys
import os

# Change to the correct directory
os.chdir('/workspace/scripts/ai-workflow')

# Run pytest with specific options
cmd = [
    sys.executable, '-m', 'pytest',
    'tests/unit/core/test_git_manager.py',
    '-v',
    '--tb=short',
    '--no-header'
]

print("=" * 80)
print("Running GitManager Unit Tests")
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
