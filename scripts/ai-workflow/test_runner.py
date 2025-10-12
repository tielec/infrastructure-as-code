#!/usr/bin/env python3
"""Test runner for GitHub progress comment integration tests (Issue #370)"""
import subprocess
import sys
import os

# Change to the correct directory
os.chdir('/tmp/jenkins-56a667ea/workspace/AI_Workflow/ai_workflow_orchestrator/scripts/ai-workflow')

# Run pytest with specific options
cmd = [
    sys.executable, '-m', 'pytest',
    'tests/integration/test_github_progress_comment.py',
    '-v',
    '--tb=short',
    '--no-header'
]

print("=" * 80)
print("Running GitHub Progress Comment Integration Tests (Issue #370)")
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
