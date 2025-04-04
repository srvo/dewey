# LLM Instructions for Fixing Pre-commit Issues

This document provides instructions for fixing pre-commit issues identified in the codebase. Issues are grouped by file importance and hook type.

## Hook-Based Issues

These issues are often reported by linters without a specific file path or span multiple files. Address them based on the error code.

### D100 Issues (4 instances)

- **Instruction:** Add missing docstrings to public modules.
- **Examples:**
  - `- D100: Missing docstring in public module (line 1) (216 instances)`
  - `- Docstring: D100 Missing docstring in public module (line 1) (214 instances)`
  - `- Issue: D100 Missing docstring in public module (line 1) (194 instances)`
  - ... and 1 more

### G004 Issues (25 instances)

- **Instruction:** Replace f-strings in logging calls with % formatting.
- **Examples:**
  - `- Syntax/parsing error: G004 Logging statement uses f-string (5 instances)`
  - `- Style: G004 Logging statement uses f-string (line 51) (20 instances)`
  - `- Style: G004 Logging statement uses f-string (line 46) (17 instances)`
  - ... and 22 more

### GENERAL Issues (23 instances)

- **Instruction:** Review and fix all instances of GENERAL violations reported by the linter.
- **Examples:**
  - `instead of `logging.error` (11 instances)`
  - `found (3 instances)`
  - `(3 instances)`
  - ... and 20 more

## File-Based Issues

Fix the issues listed for each file below.

