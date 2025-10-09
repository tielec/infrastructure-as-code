#!/bin/bash
cd /workspace/scripts/ai-workflow
pytest tests/unit/core/test_git_manager.py -v --tb=short
