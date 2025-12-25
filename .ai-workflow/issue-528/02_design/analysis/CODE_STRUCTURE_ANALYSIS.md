# PR Comment Generator - Comprehensive Code Structure Analysis

## Executive Summary

The pr_comment_generator project is a 1985-line monolithic Python file that has been partially refactored into a modular package structure. The main file (pr_comment_generator.py) contains 5 major classes handling diverse responsibilities, while a package (pr_comment_generator/) with 6 modules has extracted some functionality. A separate github_utils.py module handles GitHub API interactions.

---

## 1. MAIN FILE: pr_comment_generator.py

**File Path:** `/tmp/ai-workflow-repos-9-4357d776/infrastructure-as-code/jenkins/jobs/pipeline/docs-generator/pull-request-comment-builder/src/pr_comment_generator.py`

**Size:** 1985 lines, 89KB

### 1.1 Classes Defined in Main File

#### 1. PRInfo (Lines 23-46)
- **Purpose:** Data class holding PR basic information
- **Status:** ALREADY EXTRACTED to package/models.py
- **Fields:**
  - title, number, body, author, base_branch, head_branch, base_sha, head_sha
- **Methods:**
  - `from_json()`: Creates instance from JSON dict

#### 2. FileChange (Lines 49-71)
- **Purpose:** Data class holding file change information
- **Status:** ALREADY EXTRACTED to package/models.py
- **Fields:**
  - filename, status, additions, deletions, changes, patch, content_before, content_after, context_diff
- **Methods:**
  - `from_json()`: Creates instance from JSON dict

#### 3. PromptTemplateManager (Lines 73-131)
- **Purpose:** Manages prompt templates for OpenAI API
- **Status:** ALREADY EXTRACTED to package/prompt_manager.py
- **Responsibilities:**
  - Load template files from disk
  - Format prompts for chunk analysis
  - Format prompts for summary generation
- **Methods:**
  - `__init__()`: Initialize with template directory
  - `_load_templates()`: Read template files
  - `get_chunk_analysis_prompt()`: Format chunk analysis prompt
  - `get_summary_prompt()`: Format summary prompt
  - `format_prompt()`: Generic prompt formatter

#### 4. TokenEstimator (Lines 132-173)
- **Purpose:** Estimate token counts and truncate text
- **Status:** ALREADY EXTRACTED to package/token_estimator.py
- **Constants:**
  - AVERAGE_TOKEN_PER_CHAR_JA = 0.6
  - AVERAGE_TOKEN_PER_CHAR_EN = 0.25
- **Methods:**
  - `estimate_tokens()`: Static method to estimate token count
  - `truncate_to_token_limit()`: Static method to truncate text

#### 5. OpenAIClient (Lines 174-1425) [LARGE CLASS]
- **Purpose:** Handle OpenAI API interactions and response processing
- **Status:** NOT YET EXTRACTED (Major refactoring target)
- **Responsibilities:**
  - OpenAI API calls with retry logic
  - Token counting and usage tracking
  - Prompt/result saving for debugging
  - Chunk analysis execution
  - Input size management and optimization
- **Methods Count:** 57 methods
- **Key Method Categories:**
  
  **Initialization (lines 187-234):**
  - `__init__()`: Initialize with prompt manager and retry config
  - `_setup_logging()`: Configure logging
  
  **API Communication (lines 247-520):**
  - `_save_prompt_and_result()`: Save prompts for debugging
  - `_call_openai_api()`: Main API call with retries
  - `_prepare_prompt_content()`: Prepare prompt content
  - `_make_api_request()`: Execute API request
  - `_process_successful_response()`: Handle successful response
  - `_record_token_usage()`: Track token usage
  - `_log_response_info()`: Log response details
  - `_determine_retry_strategy()`: Decide retry behavior
  - `_is_rate_limit_error()`: Check for rate limit errors
  - `_handle_rate_limit_error()`: Handle rate limit (extract wait time)
  - `_wait_before_retry()`: Sleep before retry
  - `_extract_wait_time_from_error()`: Parse wait time from error
  
  **Prompt Generation (lines 519-1125):**
  - `generate_comment()`: Main method to generate PR comment
  - `_load_and_validate_data()`: Load PR info and diff
  - `_get_all_files_from_diff()`: Extract all files
  - `_log_load_results()`: Log file loading results
  - `_create_empty_files_result()`: Create result for empty files
  - `_perform_chunk_analyses()`: Analyze file chunks
  - `_analyze_single_chunk()`: Analyze one chunk
  - `_generate_summary_and_title()`: Generate summary and title
  - `_create_success_result()`: Format successful result
  - `_create_error_result()`: Format error result
  
  **File Change Processing (lines 719-860):**
  - `_preprocess_file_changes()`: Filter and prepare file changes
  - `_should_skip_file()`: Check if file should be skipped
  - `_truncate_large_file_content()`: Truncate large files
  - `_calculate_optimal_chunk_size()`: Calculate chunk size
  - `_split_changes_into_chunks()`: Split files into chunks
  - `_analyze_chunk()`: Analyze a chunk (wrapper)
  
  **Input JSON Management (lines 868-1095):**
  - `_prepare_input_json()`: Create input JSON for API
  - `_create_pr_json()`: Format PR info as JSON
  - `_create_change_json()`: Format file change as JSON
  - `_process_patch()`: Process patch content
  - `_truncate_patch()`: Truncate patch to size limit
  - `_process_context()`: Process context information
  - `_manage_input_size()`: Manage and optimize input size
  - `_reduce_input_size_phase1()`: First size reduction phase
  - `_extract_important_patch_lines()`: Extract key lines from patch
  - `_reduce_input_size_phase2()`: Second reduction phase
  - `_reduce_input_size_final()`: Final reduction phase
  - `_extract_sample_lines()`: Extract sample lines
  - `_execute_chunk_analysis()`: Execute the actual analysis
  
  **Output Processing (lines 1126-1416):**
  - `_truncate_content()`: Truncate content to max length
  - `_limit_diff_context()`: Limit diff context
  - `_estimate_chunk_tokens()`: Estimate tokens in chunk
  - `_clean_markdown_format()`: Clean markdown output
  - `_generate_final_summary()`: Generate final summary
  - `_is_single_chunk_without_skipped_files()`: Check if single chunk
  - `_log_summary_generation_info()`: Log summary info
  - `_collect_all_file_names()`: Collect all file names
  - `_prepare_chunk_analyses()`: Prepare analyses for summary
  - `_build_analyses_text()`: Build analyses text
  - `_format_chunk_analyses()`: Format chunk analyses
  - `_format_file_list()`: Format file list
  - `_format_skipped_files_info()`: Format skipped files info
  - `_manage_analyses_token_size()`: Manage analyses token size
  - `_truncate_chunk_analyses()`: Truncate analyses
  - `_rebuild_truncated_analyses_text()`: Rebuild after truncation
  - `_generate_summary_from_analyses()`: Generate summary
  - `_prepare_summary_prompt()`: Prepare summary prompt
  - `_build_file_list_instructions()`: Build file list instructions
  - `_build_summary_messages()`: Build summary messages
  - `_generate_title_from_summary()`: Generate title from summary
  - `get_usage_stats()`: Return token usage statistics

#### 6. PRCommentGenerator (Lines 1426-1907)
- **Purpose:** Main facade/orchestrator for the comment generation process
- **Status:** NOT YET EXTRACTED (High-level orchestrator, should remain as facade)
- **Responsibilities:**
  - Initialize all dependencies (OpenAI, GitHub clients, prompt manager)
  - Load PR data from files
  - Filter large files
  - Fetch file contents from GitHub
  - Orchestrate comment generation workflow
  - Handle parallel/sequential processing
- **Methods Count:** 11 methods
- **Key Methods:**
  - `__init__()`: Initialize all clients and managers
  - `_setup_logging()`: Setup logging
  - `load_pr_data()`: Load PR info and diff, fetch file contents
  - `_filter_large_files()`: Filter files by size
  - `_is_binary_file()`: Check if file is binary
  - `_fetch_file_contents_sequential()`: Fetch file contents sequentially
  - `_fetch_file_contents_parallel()`: Fetch file contents in parallel
  - `_normalize_file_paths()`: Normalize file paths
  - `_rebuild_file_section()`: Rebuild file section in comment
  - `_extract_file_section()`: Extract file section from comment
  - `_collect_file_infos()`: Collect file information
  - `_parse_file_line()`: Parse individual file line
  - `_normalize_single_file_path()`: Normalize single file path
  - `_build_new_file_section()`: Build new file section
  - `generate_comment()`: Main method to generate comment

### 1.2 Main File Dependencies

**Standard Library Imports:**
```python
import argparse
import concurrent.futures
import datetime
import json
import logging
import os
import random
import re
import time
import traceback
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
```

**Third-Party:**
```python
from openai import OpenAI
```

**Local Modules:**
```python
from github_utils import GitHubClient
```

### 1.3 main() Function (Lines 1909-1985)

Entry point for CLI usage with arguments:
- `--pr-diff`: PR diff JSON file path
- `--pr-info`: PR info JSON file path
- `--output`: Output JSON file path
- `--log-level`: Logging level
- `--parallel`: Use parallel processing
- `--save-prompts`: Save prompts and results
- `--prompt-output-dir`: Directory for prompt output

---

## 2. EXISTING PACKAGE: pr_comment_generator/

**Path:** `/tmp/ai-workflow-repos-9-4357d776/infrastructure-as-code/jenkins/jobs/pipeline/docs-generator/pull-request-comment-builder/src/pr_comment_generator/`

**Total Package Size:** 742 lines (including __init__.py)

### 2.1 Package Modules Summary

#### __init__.py (50 lines)
- **Purpose:** Package initialization and backwards compatibility facade
- **Exports:**
  - PRInfo, FileChange (from models)
  - TokenEstimator (from token_estimator)
  - PromptTemplateManager (from prompt_manager)
  - PRCommentStatistics (from statistics)
  - CommentFormatter (from formatter)
- **Features:**
  - Deprecation warning for old import paths
  - Version info: __version__ = '2.0.0'

#### models.py (80 lines)
- **Purpose:** Define core data models
- **Classes:**
  - `PRInfo`: PR basic information dataclass (23 lines)
  - `FileChange`: File change information dataclass (27 lines)
- **Responsibilities:**
  - Type-safe representation of PR and file data
  - Factory methods for JSON deserialization

#### token_estimator.py (87 lines)
- **Purpose:** Token estimation utilities
- **Class:** `TokenEstimator`
- **Responsibilities:**
  - Estimate token count from text (mixed Japanese/English)
  - Truncate text to fit token limits
- **Key Features:**
  - Language-aware token estimation
  - Binary search for efficient truncation

#### prompt_manager.py (122 lines)
- **Purpose:** Manage OpenAI prompt templates
- **Class:** `PromptTemplateManager`
- **Responsibilities:**
  - Load prompt templates from files
  - Format prompts for different analysis stages
  - Generate prompts with PR context
- **Templates:**
  - base_template.md: Base prompt structure
  - chunk_analysis_extension.md: Chunk analysis instructions
  - summary_extension.md: Summary generation instructions

#### statistics.py (149 lines)
- **Purpose:** Statistics and file analysis
- **Class:** `PRCommentStatistics`
- **Responsibilities:**
  - Calculate file change statistics
  - Determine optimal chunk size based on file sizes
  - Estimate chunk token counts
- **Key Methods:**
  - `calculate_optimal_chunk_size()`: Adaptive chunking
  - `estimate_chunk_tokens()`: Token estimation for chunks
  - `calculate_statistics()`: Compute file statistics

#### formatter.py (254 lines) [LARGEST PACKAGE MODULE]
- **Purpose:** Markdown comment formatting
- **Class:** `CommentFormatter`
- **Responsibilities:**
  - Clean markdown formatting
  - Format chunk analyses
  - Format file lists
  - Format skipped files info
  - Rebuild file sections
  - Find best matching file paths
- **Key Methods:**
  - `clean_markdown_format()`: Remove markdown artifacts
  - `format_chunk_analyses()`: Format analysis results
  - `format_file_list()`: Format changed files list
  - `format_skipped_files_info()`: Format skipped files section
  - `rebuild_file_section()`: Normalize file paths
  - `format_final_comment()`: Compose final comment

### 2.2 Package Interdependencies

```
formatter.py
  └─ depends on: models.FileChange, logging

statistics.py
  └─ depends on: models.FileChange, token_estimator.TokenEstimator, logging

token_estimator.py
  └─ depends on: logging

prompt_manager.py
  └─ depends on: models.PRInfo, os

models.py
  └─ depends on: dataclasses, typing
```

---

## 3. SEPARATE MODULE: github_utils.py

**Path:** `/tmp/ai-workflow-repos-9-4357d776/infrastructure-as-code/jenkins/jobs/pipeline/docs-generator/pull-request-comment-builder/src/github_utils.py`

**Size:** Not counted in main analysis (separate utility)

### 3.1 GitHub Utilities

**Class:** `GitHubClient`

**Responsibilities:**
- GitHub API authentication (PAT or GitHub App)
- Fetch file contents at specific commits
- Extract change context from patches
- Rate limit checking and handling

**Key Methods:**
- `get_file_content()`: Get file before/after content
- `get_change_context()`: Extract context around changes
- `_parse_patch()`: Parse diff patch
- `_refresh_token_if_needed()`: Token refresh for GitHub Apps

**Exception:** `GitHubClientError`

---

## 4. EXISTING TEST COVERAGE

**Total Test Files:** 12 test files (2076 lines)

### 4.1 Unit Tests (1179 lines)

#### test_facade.py (132 lines)
- **Coverage:** __init__.py backwards compatibility
- **Tests:**
  - Deprecation warning display
  - Re-export functionality
  - Version info availability
  - Public API availability

#### test_models.py (161 lines)
- **Coverage:** models.PRInfo and models.FileChange
- **Tests:**
  - PRInfo instantiation and from_json()
  - FileChange instantiation and from_json()
  - Field validation

#### test_formatter.py (292 lines)
- **Coverage:** formatter.CommentFormatter
- **Tests:**
  - Markdown formatting cleanup
  - Chunk analyses formatting
  - File list formatting
  - Skipped files formatting
  - File section rebuilding

#### test_prompt_manager.py (189 lines)
- **Coverage:** prompt_manager.PromptTemplateManager
- **Tests:**
  - Template loading
  - Prompt generation
  - Format methods

#### test_token_estimator.py (171 lines)
- **Coverage:** token_estimator.TokenEstimator
- **Tests:**
  - Token estimation (Japanese/English)
  - Text truncation
  - Binary search accuracy

#### test_statistics.py (233 lines)
- **Coverage:** statistics.PRCommentStatistics
- **Tests:**
  - Optimal chunk size calculation
  - File statistics calculation
  - Large file detection
  - Token estimation for chunks

### 4.2 Integration Tests (507 lines)

#### test_compatibility_layer.py (202 lines)
- **Coverage:** Package compatibility after refactoring
- **Tests:**
  - Old import paths still work
  - Classes function correctly
  - No breaking changes

#### test_module_integration.py (305 lines)
- **Coverage:** Module interactions
- **Tests:**
  - Statistics + TokenEstimator integration
  - Formatter + Models integration
  - Full end-to-end workflows

### 4.3 BDD Tests (388 lines)

#### test_bdd_pr_comment_generation.py (388 lines)
- **Coverage:** Full PR comment generation workflow
- **Tests:**
  - End-to-end comment generation
  - Error handling
  - Large PR handling
  - File skipping logic

### 4.4 Test Gaps & Missing Coverage

**NOT TESTED OR LIGHTLY TESTED:**
- `OpenAIClient` (entire class - 57 methods)
- `PRCommentGenerator` (entire class - 15 methods)
- GitHub API interactions in `github_utils.py`
- Retry logic and error handling
- Token counting accuracy beyond basic tests
- Parallel processing (_fetch_file_contents_parallel)
- Rate limiting handling
- File content fetching with GitHub client

---

## 5. CURRENT REFACTORING STATUS

### 5.1 Already Extracted (Stable)

| Component | Status | Module | Lines | Tests |
|-----------|--------|--------|-------|-------|
| PRInfo | Extracted | models.py | 23 | Yes |
| FileChange | Extracted | models.py | 27 | Yes |
| TokenEstimator | Extracted | token_estimator.py | 87 | Yes |
| PromptTemplateManager | Extracted | prompt_manager.py | 122 | Yes |
| PRCommentStatistics | Extracted | statistics.py | 149 | Yes |
| CommentFormatter | Extracted | formatter.py | 254 | Yes |

### 5.2 NOT Yet Extracted (Refactoring Targets)

| Component | Status | Current Location | Lines | Methods | Tests |
|-----------|--------|------------------|-------|---------|-------|
| OpenAIClient | Monolithic | pr_comment_generator.py | 1252 | 57 | No |
| PRCommentGenerator | Monolithic | pr_comment_generator.py | 481 | 15 | Partial |

---

## 6. RESPONSIBILITY MATRIX

### OpenAIClient (Lines 174-1425) - 57 Methods

**Should be broken into:**

1. **API Communication Layer** (~20 methods)
   - `_call_openai_api()`
   - `_make_api_request()`
   - `_process_successful_response()`
   - `_determine_retry_strategy()`
   - `_is_rate_limit_error()`
   - `_handle_rate_limit_error()`
   - `_wait_before_retry()`
   - `_extract_wait_time_from_error()`
   - Retry/backoff logic
   - Token usage recording

2. **Input Preparation & Optimization** (~15 methods)
   - `_prepare_input_json()`
   - `_create_pr_json()`
   - `_create_change_json()`
   - `_process_patch()`
   - `_truncate_patch()`
   - `_process_context()`
   - `_manage_input_size()`
   - `_reduce_input_size_phase1()` / `phase2()` / `final()`
   - `_extract_important_patch_lines()`
   - `_extract_sample_lines()`
   - `_limit_diff_context()`
   - `_truncate_content()`
   - Token management

3. **Chunk Analysis** (~8 methods)
   - `generate_comment()`
   - `_load_and_validate_data()`
   - `_perform_chunk_analyses()`
   - `_analyze_single_chunk()`
   - `_analyze_chunk()`
   - `_execute_chunk_analysis()`
   - `_estimate_chunk_tokens()`
   - `_get_all_files_from_diff()`

4. **Output Processing & Formatting** (~14 methods)
   - `_generate_final_summary()`
   - `_generate_summary_from_analyses()`
   - `_generate_title_from_summary()`
   - `_collect_all_file_names()`
   - `_prepare_chunk_analyses()`
   - `_build_analyses_text()`
   - `_format_chunk_analyses()`
   - `_format_file_list()`
   - `_format_skipped_files_info()`
   - `_manage_analyses_token_size()`
   - `_truncate_chunk_analyses()`
   - `_rebuild_truncated_analyses_text()`
   - `_prepare_summary_prompt()`
   - `_build_file_list_instructions()`
   - `_build_summary_messages()`
   - `_clean_markdown_format()`

### PRCommentGenerator (Lines 1426-1907) - 15 Methods

**Current Responsibilities:**
- Orchestration/Facade pattern
- GitHub data loading
- File content fetching
- Large file filtering
- File path normalization
- Parallel/sequential processing

**Should delegate to:**
- `OpenAIClient` for analysis
- `GitHubClient` for data fetching
- Utility modules for formatting

---

## 7. KEY ARCHITECTURAL ISSUES

### 7.1 Code Duplication

| Item | Location 1 | Location 2 | Issue |
|------|-----------|-----------|-------|
| PRInfo dataclass | pr_comment_generator.py lines 23-46 | models.py lines 17-47 | DUPLICATED - only models.py should exist |
| FileChange dataclass | pr_comment_generator.py lines 49-71 | models.py lines 51-81 | DUPLICATED - only models.py should exist |
| PromptTemplateManager | pr_comment_generator.py lines 73-131 | prompt_manager.py lines 18-123 | DUPLICATED - only prompt_manager.py should exist |
| TokenEstimator | pr_comment_generator.py lines 132-173 | token_estimator.py lines 15-88 | DUPLICATED - only token_estimator.py should exist |

**Action Needed:** Remove duplicates from pr_comment_generator.py and import from package instead.

### 7.2 Missing Abstractions

- **OpenAIClient** is too large (1252 lines)
  - Contains API communication, data preparation, analysis, and output formatting
  - Should be split into 3-4 focused classes
  
- **PRCommentGenerator** still directly instantiates dependencies
  - Could benefit from dependency injection
  - File fetching logic could be abstracted

### 7.3 Import Issues

Current main file still has:
- Classes that duplicate the package modules
- Imports from github_utils (external, correct)
- No imports from the package itself (should import duplicated classes from package)

---

## 8. DEPENDENCY GRAPH

```
pr_comment_generator.py (MONOLITH - BEING REFACTORED)
├── Duplicates: PRInfo, FileChange, PromptTemplateManager, TokenEstimator
│   └── These SHOULD import from package instead
├── OpenAIClient (1252 lines)
│   ├── Uses: PromptTemplateManager
│   └── Uses: (internally defined) TokenEstimator
├── PRCommentGenerator (481 lines)
│   ├── Uses: PromptTemplateManager
│   ├── Uses: OpenAIClient
│   └── Uses: GitHubClient
└── main() function
    └── Uses: PRCommentGenerator

pr_comment_generator/ (PACKAGE)
├── models.py (PRInfo, FileChange)
├── token_estimator.py (TokenEstimator)
├── prompt_manager.py (PromptTemplateManager)
│   └── Uses: models.PRInfo
├── statistics.py (PRCommentStatistics)
│   ├── Uses: models.FileChange
│   └── Uses: token_estimator.TokenEstimator
└── formatter.py (CommentFormatter)
    ├── Uses: models.FileChange
    └── Uses: logging

github_utils.py (EXTERNAL)
└── GitHubClient
    ├── Uses: github (PyGithub)
    └── Uses: standard libraries
```

---

## 9. SUMMARY TABLE: What's Where

| Responsibility | Current Location | Extracted Location | Status |
|---|---|---|---|
| **Data Models** |
| PRInfo dataclass | pr_comment_generator.py:23-46 | models.py:17-47 | DUPLICATE |
| FileChange dataclass | pr_comment_generator.py:49-71 | models.py:51-81 | DUPLICATE |
| **Utilities** |
| Token estimation | pr_comment_generator.py:132-173 | token_estimator.py | DUPLICATE |
| Text truncation | pr_comment_generator.py:154-173 | token_estimator.py:57-88 | DUPLICATE |
| **Template Management** |
| Prompt templates | pr_comment_generator.py:73-131 | prompt_manager.py:18-123 | DUPLICATE |
| **Statistics & Optimization** |
| Chunk sizing | pr_comment_generator.py:779-806 | statistics.py:35-82 | SPLIT |
| Token estimation (chunks) | pr_comment_generator.py:1150-1182 | statistics.py:105-119 | SPLIT |
| **Formatting** |
| Markdown cleanup | pr_comment_generator.py:1183-1189 | formatter.py:30-53 | SPLIT |
| Format analyses | pr_comment_generator.py:1267-1276 | formatter.py:55-78 | SPLIT |
| Format file list | pr_comment_generator.py:1274-1277 | formatter.py:80-105 | SPLIT |
| Format skipped files | pr_comment_generator.py:1278-1287 | formatter.py:107-135 | SPLIT |
| **API Communication** |
| OpenAI API calls | pr_comment_generator.py:319-520 | NOT EXTRACTED | MONOLITHIC |
| Retry logic | pr_comment_generator.py:446-520 | NOT EXTRACTED | MONOLITHIC |
| **Analysis & Processing** |
| Chunk analysis | pr_comment_generator.py:627-1095 | NOT EXTRACTED | MONOLITHIC |
| Summary generation | pr_comment_generator.py:1190-1416 | NOT EXTRACTED | MONOLITHIC |
| **Orchestration** |
| Main generator | pr_comment_generator.py:1426-1907 | NOT EXTRACTED | MONOLITHIC |
| GitHub integration | pr_comment_generator.py:1471-1792 | NOT EXTRACTED | MONOLITHIC |

---

## 10. RECOMMENDATIONS FOR REFACTORING

### Phase 1: Remove Duplication (High Priority)
1. Remove PRInfo, FileChange, PromptTemplateManager, TokenEstimator from main file
2. Import them from the package instead
3. Update pr_comment_generator.py imports

### Phase 2: Extract OpenAIClient (Medium Priority)
1. Create new module: `pr_comment_generator/api_client.py`
2. Move OpenAIClient class and supporting methods
3. Create separate classes for:
   - API communication (with retry logic)
   - Input optimization
   - Output formatting
   - Analysis coordination

### Phase 3: Extract PRCommentGenerator Support (Low Priority)
1. Consider extracting GitHub integration logic
2. Create data loader module for file handling
3. Improve dependency injection

### Phase 4: Add Missing Tests (High Priority)
1. Add unit tests for OpenAIClient
2. Add unit tests for PRCommentGenerator
3. Add integration tests for GitHub interactions
4. Add tests for error handling and edge cases

---

## Appendix: File Size Breakdown

```
pr_comment_generator.py          1985 lines  (100%)
├── PRInfo                         24 lines  (1.2%)
├── FileChange                     23 lines  (1.2%)
├── PromptTemplateManager          59 lines  (3.0%)
├── TokenEstimator                 42 lines  (2.1%)
├── OpenAIClient                1252 lines  (63.1%)
├── PRCommentGenerator            481 lines  (24.2%)
└── main() function                76 lines  (3.8%)

pr_comment_generator/ (package)    742 lines  (100%)
├── __init__.py                    50 lines  (6.7%)
├── models.py                      80 lines (10.8%)
├── token_estimator.py             87 lines (11.7%)
├── prompt_manager.py             122 lines (16.4%)
├── statistics.py                 149 lines (20.1%)
└── formatter.py                  254 lines (34.2%)

Total Code:                      2727 lines
```

