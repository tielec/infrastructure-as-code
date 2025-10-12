#!/bin/bash
cd /tmp/jenkins-56a667ea/workspace/AI_Workflow/ai_workflow_orchestrator/scripts/ai-workflow
pytest tests/integration/test_github_progress_comment.py -v --tb=short
