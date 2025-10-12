#!/bin/bash
# Test runner for evaluation phase tests
# Issue #362 - Phase 6: Testing

set -e

echo "========================================="
echo "Running Evaluation Phase Unit Tests"
echo "========================================="
echo ""

cd /tmp/jenkins-df0aed5c/workspace/AI_Workflow/ai_workflow_orchestrator/scripts/ai-workflow

echo "Test Framework: pytest 7.4.3"
echo "Python Version: $(python --version)"
echo ""

echo "Running unit tests for evaluation phase..."
python -m pytest tests/unit/phases/test_evaluation.py -v --tb=short --color=yes

echo ""
echo "Running unit tests for metadata manager extensions..."
python -m pytest tests/unit/core/test_metadata_manager.py::TestMetadataManagerEvaluationExtensions -v --tb=short --color=yes

echo ""
echo "========================================="
echo "Test Execution Complete"
echo "========================================="
