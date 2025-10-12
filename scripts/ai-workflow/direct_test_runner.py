#!/usr/bin/env python3
"""Direct test runner for GitHub progress comment tests - imports and runs tests directly"""
import sys
import os

# Set the working directory
os.chdir('/tmp/jenkins-56a667ea/workspace/AI_Workflow/ai_workflow_orchestrator/scripts/ai-workflow')

# Add current directory to path
sys.path.insert(0, os.getcwd())

# Import pytest
import pytest

# Run the tests
print("=" * 80)
print("Running GitHub Progress Comment Integration Tests (Issue #370)")
print("=" * 80)
print()

# Run pytest programmatically
exit_code = pytest.main([
    'tests/integration/test_github_progress_comment.py',
    '-v',
    '--tb=short'
])

print()
print("=" * 80)
print(f"Test execution completed with exit code: {exit_code}")
print("=" * 80)

sys.exit(exit_code)
