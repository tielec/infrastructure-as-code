#!/bin/bash
# Test runner for Issue #324 TestImplementationPhase
cd /tmp/jenkins-b563edb1/workspace/AI_Workflow/ai_workflow_orchestrator/scripts/ai-workflow
python -m pytest tests/unit/phases/test_test_implementation.py -v
