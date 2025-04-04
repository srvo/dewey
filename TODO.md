# Dewey Project - TODO List

## Sloane (the human's) priorities

   - [ ] Get bookkeeping scripts up and running, generate financial books and records
   - [ ] Get CRM scripts up and running, begin processing back emails, enriching data, tagging, etc.
   - [ ]


## Project Structure Standardization
   - [ ] Ensure CI/CD pipeline is updated for new structure

1. **Medium Priority**
   - [ ] Add integration tests for UI components

2. **Lower Priority**
   - [ ] Implement code quality checks to enforce structure standards
   - [ ] Migrate old data files to data/ directory
   - [ ] Add missing tests to improve coverage
   - [x] Review and standardize logging approach

## Architecture Refactoring

1. **High Priority**
   - [ ] Implement event-driven architecture for cross-module communication
   - [ ] Decouple core modules (crm, research, bookkeeping, llm) using abstraction layers
   - [ ] Create service interfaces and dependency injection in BaseScript

2. **Medium Priority**
   - [ ] Refactor existing code to use the new event system
   - [ ] Update documentation to reflect architectural changes
   - [ ] Add unit tests for event system components

## Documentation System

*issues*
   - [ ] configuration of sphinx continues to confound
   - [ ] is it worth generating self-maintaining docs?

1. **Completed**
   - [ ] Configured Sphinx documentation framework
   - [ ] Implemented autodoc for Python modules
   - [x] Added Mermaid diagram support
   - [x] Fixed all documentation build warnings
   - [x] Implemented pre-commit validation

2. **Pending**
   - [ ] Add API reference examples
   - [ ] Generate documentation for all core modules
   - [ ] Set up documentation CI/CD pipeline



## Database Migration

1. **High Priority**
   - [ ] Update tests to use mock PostgreSQL interfaces
   - [ ] Fix mock implementations in tests to handle `local_only` parameter
   - [ ] Implement schema version tracking mechanism

2. **Medium Priority**
   - [ ] Set up proper schema migration framework (Alembic recommended)
   - [ ] Implement PostgreSQL backup strategy (logical backups with pg_dump)
   - [ ] Configure connection pooling for performance optimization
   - [ ] Add database health monitoring as specified in CONVENTIONS.md

3. **Completed**
   - [x] Migrate database config from DuckDB to PostgreSQL
   - [x] Implement PostgreSQL connection pooling in utils/database.py
   - [x] Create working motherduck_to_postgres migration script
   - [x] Refactor imports to use absolute paths and prevent circular dependencies

## Feature Development

1. **Pending Features**
   - [ ] Implement updated CRM functionality
   - [ ] Enhance bookkeeping classification engine
   - [ ] Improve LLM agent reliability

## Technical Debt

1. **Code Quality**
   - [ ] Fix linting issues across codebase
   - [ ] Address TODOs in code
   - [ ] Improve error handling and logging
   - [ ] Ensure abstract methods are implemented in all subclasses
   - [ ] Fix test failures in bookkeeping module classes

## Recent Fixes

## Pre-commit Issues (Last updated: 2025-04-03 10:46:03)

### Syntax Errors
  - Syntax/parsing error: TRY400 Use `logging.exception` instead of `logging.error` (11 instances)
  - Syntax/parsing error: T201 `print` found (3 instances)
  - Syntax/parsing error: BLE001 Do not catch blind exception: `Exception` (3 instances)
  - Issue: SyntaxError: Simple statements must be separated by newlines or semicolons (line 175) (3 instances)
  - Issue: SyntaxError: Simple statements must be separated by newlines or semicolons (line 114) (2 instances)
  - Issue: SyntaxError: Simple statements must be separated by newlines or semicolons (line 257) (2 instances)
  - Issue: SyntaxError: Simple statements must be separated by newlines or semicolons (line 111) (2 instances)
  - Issue: SyntaxError: Simple statements must be separated by newlines or semicolons (line 173) (2 instances)
  - Issue: SyntaxError: Simple statements must be separated by newlines or semicolons (line 255) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_setup_argparse` (line 87) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_setup_argparse` (line 87) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_base_parse_args` (line 101) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_base_parse_args` (line 120) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_args` (line 101) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_args_file_not_found` (line 120) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_json` (line 133) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_list` (line 161) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_timestamp` (line 84) (2 instances)
  - Syntax/parsing error: PTH123 `open()` should be replaced by `Path.open()`
- [ ] *390 more syntax errors not shown*

### Docstring Issues
  - D104: Missing docstring in public package (line 1) (46 instances)
  - Issue: D104 Missing docstring in public package (line 1) (44 instances)
  - Docstring: D104 Missing docstring in public package (line 1) (40 instances)
  - D400: First line should end with a period (line 1) (23 instances)
  - D415: First line should end with a period, question mark, or exclamation point (line 1) (23 instances)
  - Issue: D415 First line should end with a period, question mark, or exclamation point (line 1) (23 instances)
  - Docstring: D415 First line should end with a period, question mark, or exclamation point (line 1) (23 instances)
  - Issue: D400 First line should end with a period (line 1) (21 instances)
  - Docstring: D400 First line should end with a period (line 1) (21 instances)
  - D205: 1 blank line required between summary line and description (line 3) (12 instances)
  - Docstring: D205 1 blank line required between summary line and description (line 3) (12 instances)
  - D400: First line should end with a period (line 2) (11 instances)
  - Docstring: D400 First line should end with a period (line 2) (11 instances)
  - D415: First line should end with a period, question mark, or exclamation point (line 2) (11 instances)
  - Issue: D415 First line should end with a period, question mark, or exclamation point (line 2) (11 instances)
  - Docstring: D415 First line should end with a period, question mark, or exclamation point (line 2) (11 instances)
  - D205: 1 blank line required between summary line and description (line 2) (10 instances)
- [ ] *4554 more docstring issues not shown*

### Style Violations
  - Style: D104 Missing docstring in public package (line 1) (46 instances)
  - Style: D400 First line should end with a period (line 1) (23 instances)
  - Style: D415 First line should end with a period, question mark, or exclamation point (line 1) (23 instances)
  - Style: I001 [*] Import block is un-sorted or un-formatted (line 3) (19 instances)
  - Style: S101 Use of `assert` detected (line 35) (15 instances)
  - Style: S101 Use of `assert` detected (line 34) (14 instances)
  - Style: S101 Use of `assert` detected (line 36) (14 instances)
  - Style: D205 1 blank line required between summary line and description (line 3) (12 instances)
- [ ] *8153 more style violations not shown*

### Implementation Issues
  - Issue: ANN201 Missing return type annotation for public function `test_run_not_implemented` (line 138) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_run_not_implemented` (line 62) (2 instances)

### Other Issues
  - I001: [*] Import block is un-sorted or un-formatted (line 3) (19 instances)
  - Issue: I001 [*] Import block is un-sorted or un-formatted (line 3) (18 instances)
  - S101: Use of `assert` detected (line 35) (15 instances)
  - Issue: S101 Use of `assert` detected (line 35) (15 instances)
  - S101: Use of `assert` detected (line 34) (14 instances)
  - Issue: S101 Use of `assert` detected (line 34) (14 instances)
  - S101: Use of `assert` detected (line 36) (14 instances)
- [ ] *5213 more other issues not shown*

## Pre-commit WIP

(No issues currently in progress)

- [ ] Fix issue in `scripts/test_and_fix.py`: Syntax error: expected an indented block after function definition on line 36 (<unknown>, line 37)
- [ ] Class 'EthicalAnalysisWorkflow' needs to implement 'execute' method (in unknown file)
- [ ] Class 'MigrationManager' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ScreenManager' needs to implement 'execute' method (in unknown file)
- [ ] Class 'DatabaseModule' needs to implement 'execute' method (in unknown file)
- [ ] Class 'AnalysisTaggingWorkflow' needs to implement 'execute' method (in unknown file)
- [ ] Class 'DropJVTables' needs to implement 'execute' method (in unknown file)
- [ ] Class 'UploadDb' needs to implement 'execute' method (in unknown file)
- [ ] Class 'EventsModule' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CleanupTables' needs to implement 'execute' method (in unknown file)
- [ ] Class 'AdversarialAgent' needs to implement 'execute' method (in unknown file)
- [ ] Class 'EmailProcessor' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CSVInferSchema' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ImportInstitutionalProspects' needs to implement 'execute' method (in unknown file)
- [ ] Class 'Script' needs to implement 'execute' method (in unknown file)
- [ ] Class 'Service' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CodeUniquenessAnalyzer' needs to implement 'execute' method (in unknown file)
- [ ] Class 'GmailService' needs to implement 'execute' method (in unknown file)
- [ ] Class 'Bing' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CliTickManager' needs to implement 'execute' method (in unknown file)
- [ ] Class 'DataAnalysisScript' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CompanyAnalysisManager' needs to implement 'execute' method (in unknown file)
- [ ] Class 'Companies' needs to implement 'execute' method (in unknown file)
- [ ] Class 'EnrichmentModule' needs to implement 'execute' method (in unknown file)
- [ ] Class 'EntityAnalysis' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ContactAgent' needs to implement 'execute' method (in unknown file)
- [ ] Class 'RssFeedManager' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ModuleScreen' needs to implement 'execute' method (in unknown file)
- [ ] Class 'TUIApp' needs to implement 'execute' method (in unknown file)
- [ ] Class 'AnalyzeTables' needs to implement 'execute' method (in unknown file)
- [ ] Class 'DeweyManager' needs to implement 'execute' method (in unknown file)
- [ ] Class 'EventCallback' needs to implement 'execute' method (in unknown file)
- [ ] Class 'PrdBuilder' needs to implement 'execute' method (in unknown file)
- [ ] Class 'GenerateLegacyTodos' needs to implement 'execute' method (in unknown file)
- [ ] Class 'LogManager' needs to implement 'execute' method (in unknown file)
- [ ] Class 'VerifyDb' needs to implement 'execute' method (in unknown file)
- [ ] Class 'EmailClassifier' needs to implement 'execute' method (in unknown file)
- [ ] Class 'Utils' needs to implement 'execute' method (in unknown file)
- [ ] Class 'DropSmallTablesScript' needs to implement 'execute' method (in unknown file)
- [ ] Class 'RFDocstringAgent' needs to implement 'execute' method (in unknown file)
- [ ] Class 'PolygonEngine' needs to implement 'execute' method (in unknown file)
- [ ] Class 'RFDocstringAgent' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CleanupTables' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ScriptInitMigrator' needs to implement 'execute' method (in unknown file)
- [ ] Class 'PriorityModule' needs to implement 'execute' method (in unknown file)
- [ ] Class 'TUIApp' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CrmModule' needs to implement 'execute' method (in unknown file)
- [ ] Class 'Workers' needs to implement 'execute' method (in unknown file)
- [ ] Class 'AnalyzeLocalDbs' needs to implement 'execute' method (in unknown file)
- [ ] Class 'Prompts' needs to implement 'execute' method (in unknown file)
- [ ] Class 'DocsScript' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ResearchWorkflow' needs to implement 'execute' method (in unknown file)
- [ ] Class 'DashboardGenerator' needs to implement 'execute' method (in unknown file)
- [ ] Class 'SecFilingsManager' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CheckDataScript' needs to implement 'execute' method (in unknown file)
- [ ] Class 'PrecommitAnalyzer' needs to implement 'execute' method (in unknown file)
- [ ] Class 'Serper' needs to implement 'execute' method (in unknown file)
- [ ] Class 'GithubAnalyzer' needs to implement 'execute' method (in unknown file)
- [ ] Class 'APIServer' needs to implement 'execute' method (in unknown file)
- [ ] Class 'Workers' needs to implement 'execute' method (in unknown file)
- [ ] Class 'TicDeltaWorkflow' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CrmCataloger' needs to implement 'execute' method (in unknown file)
- [ ] Fix issue in `tests/prod/llm/test_litellm_integration.py`: Invalid characters and syntax errors due to encoding issues.
- [ ] Fix issue in `scripts/test_and_fix.py`: Syntax error: expected an indented block after function definition on line 36 (<unknown>, line 37)
- [ ] Class 'EthicalAnalysisWorkflow' needs to implement 'execute' method (in unknown file)
- [ ] Class 'MigrationManager' needs to implement 'execute' method (in unknown file)
- [ ] Class 'DatabaseModule' needs to implement 'execute' method (in unknown file)
- [ ] Class 'AnalysisTaggingWorkflow' needs to implement 'execute' method (in unknown file)
- [ ] Class 'DropJVTables' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CleanupTables' needs to implement 'execute' method (in unknown file)
- [ ] Class 'EmailProcessor' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CSVInferSchema' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ImportInstitutionalProspects' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ModuleScreen' needs to implement 'execute' method (in unknown file)
- [ ] Fix issue in `scripts/test_and_fix.py`: Syntax error: expected an indented block after function definition on line 36 (<unknown>, line 37)
- [ ] Class 'TUIApp' needs to implement 'execute' method (in unknown file)
- [ ] Class 'AnalyzeTables' needs to implement 'execute' method (in unknown file)
- [ ] Class 'PrdBuilder' needs to implement 'execute' method (in unknown file)
- [ ] Class 'GenerateLegacyTodos' needs to implement 'execute' method (in unknown file)
- [ ] Class 'VerifyDb' needs to implement 'execute' method (in unknown file)
- [ ] Class 'EmailClassifier' needs to implement 'execute' method (in unknown file)
- [ ] Class 'Utils' needs to implement 'execute' method (in unknown file)
- [ ] Class 'RFDocstringAgent' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CleanupTables' needs to implement 'execute' method (in unknown file)
- [ ] Class 'Workers' needs to implement 'execute' method (in unknown file)
- [ ] Class 'AnalyzeLocalDbs' needs to implement 'execute' method (in unknown file)
- [ ] Class 'Prompts' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ResearchWorkflow' needs to implement 'execute' method (in unknown file)
- [ ] Class 'PrecommitAnalyzer' needs to implement 'execute' method (in unknown file)
- [ ] Class 'TickProcessor' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ExceptionsScript' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CsvContactIntegration' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CodeUniquenessAnalyzer' needs to implement 'execute' method (in unknown file)
- [ ] Class 'Sheets' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ResearchUtils' needs to implement 'execute' method (in unknown file)
- [ ] Class 'TestWriter' needs to implement 'execute' method (in unknown file)
- [ ] Class 'MyUtils' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ServiceItem' needs to implement 'execute' method (in unknown file)
- [ ] Class 'STSXmlParser' needs to implement 'execute' method (in unknown file)
- [ ] Class 'TaggingEngine' needs to implement 'execute' method (in unknown file)
- [ ] Class 'UploadDb' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CsvContactIntegration' needs to implement 'execute' method (in unknown file)
- [ ] Class 'Config' needs to implement 'execute' method (in unknown file)
- [ ] Class 'JsonResearchIntegration' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ContactConsolidation' needs to implement 'execute' method (in unknown file)
- [ ] Class 'DropOtherTables' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CleanupOtherFiles' needs to implement 'execute' method (in unknown file)
- [ ] Class 'TranscriptsModule' needs to implement 'execute' method (in unknown file)
- [ ] Class 'TranscriptMatcher' needs to implement 'execute' method (in unknown file)
- [ ] Class 'EmailDataGenerator' needs to implement 'execute' method (in unknown file)
- [ ] Class 'OpenRouterClient' needs to implement 'execute' method (in unknown file)
- [ ] Class 'PypiSearch' needs to implement 'execute' method (in unknown file)

  - Syntax/parsing error: G004 Logging statement uses f-string (5 instances)
  - D100: Missing docstring in public module (line 1) (216 instances)
  - Docstring: D100 Missing docstring in public module (line 1) (214 instances)
  - Issue: D100 Missing docstring in public module (line 1) (194 instances)
  - Style: D100 Missing docstring in public module (line 1) (216 instances)
  - Style: G004 Logging statement uses f-string (line 51) (20 instances)
  - Style: G004 Logging statement uses f-string (line 46) (17 instances)
  - Style: G004 Logging statement uses f-string (line 49) (15 instances)
  - Style: G004 Logging statement uses f-string (line 47) (15 instances)
  - Style: G004 Logging statement uses f-string (line 54) (14 instances)
  - Style: G004 Logging statement uses f-string (line 42) (14 instances)
  - Style: G004 Logging statement uses f-string (line 56) (12 instances)
  - Style: G004 Logging statement uses f-string (line 59) (12 instances)
  - Style: G004 Logging statement uses f-string (line 78) (12 instances)
  - Style: G004 Logging statement uses f-string (line 81) (12 instances)
  - Style: G004 Logging statement uses f-string (line 61) (12 instances)
  - G004: Logging statement uses f-string (line 51) (20 instances)
  - Issue: G004 Logging statement uses f-string (line 51) (20 instances)
  - G004: Logging statement uses f-string (line 46) (17 instances)
  - Issue: G004 Logging statement uses f-string (line 46) (17 instances)
  - G004: Logging statement uses f-string (line 49) (15 instances)
  - Issue: G004 Logging statement uses f-string (line 49) (15 instances)
  - G004: Logging statement uses f-string (line 47) (15 instances)
  - Issue: G004 Logging statement uses f-string (line 47) (15 instances)
  - G004: Logging statement uses f-string (line 54) (14 instances)
  - G004: Logging statement uses f-string (line 42) (14 instances)
  - Issue: G004 Logging statement uses f-string (line 42) (14 instances)
  - Issue: G004 Logging statement uses f-string (line 54) (13 instances)
  - G004: Logging statement uses f-string (line 56) (12 instances)
## Pre-commit Resolved

- [ ] Address Pydantic and litellm warnings.
- [ ] Fix issue in `scripts/quick_fix.py`: Syntax error: invalid decimal literal (<unknown>, line 1)
- [ ] Fix issue in `scripts/aider_refactor.py`: Syntax error: invalid syntax (<unknown>, line 39)
- [ ] Fix issue in `src/dewey/core/automation/docs/__init__.py`: Syntax error: expected an indented block after function definition on line 36 (<unknown>, line 37)
- [ ] Class 'EthicalAnalysisWorkflow' needs to implement 'execute' method (in unknown file)
- [ ] Class 'MigrationManager' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ScreenManager' needs to implement 'execute' method (in unknown file)
- [ ] Class 'DatabaseModule' needs to implement 'execute' method (in unknown file)
- [ ] Class 'AnalysisTaggingWorkflow' needs to implement 'execute' method (in unknown file)
- [ ] Class 'DropJVTables' needs to implement 'execute' method (in unknown file)
  - Syntax/parsing error: TRY400 Use `logging.exception` instead of `logging.error` (11 instances)
  - Syntax/parsing error: G004 Logging statement uses f-string (5 instances)
  - Syntax/parsing error: BLE001 Do not catch blind exception: `Exception` (3 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_json` (line 132) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_list` (line 160) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_setup_argparse` (line 87) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_setup_argparse` (line 87) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_base_parse_args` (line 101) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_base_parse_args` (line 120) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_args` (line 101) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_args_file_not_found` (line 120) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_timestamp` (line 83) (2 instances)
  - Syntax/parsing error: D213 [*] Multi-line docstring summary should start at the second line
  - Syntax/parsing error: TRY300 Consider moving this statement to an `else` block
  - Syntax/parsing error: Replace with `exception`
  - Syntax/parsing error: G201 Logging `.exception(...)` should be used instead of `.error(..., exc_info=True)`
  - D100: Missing docstring in public module (line 1) (230 instances)
  - Docstring: D100 Missing docstring in public module (line 1) (227 instances)
  - Issue: D100 Missing docstring in public module (line 1) (206 instances)
  - D213: [*] Multi-line docstring summary should start at the second line (line 1) (96 instances)
  - Issue: D213 [*] Multi-line docstring summary should start at the second line (line 1) (90 instances)
  - Docstring: D213 [*] Multi-line docstring summary should start at the second line (line 1) (89 instances)
  - D213: [*] Multi-line docstring summary should start at the second line (line 7) (61 instances)
  - Issue: D213 [*] Multi-line docstring summary should start at the second line (line 7) (61 instances)
  - Docstring: D213 [*] Multi-line docstring summary should start at the second line (line 7) (60 instances)
  - D213: [*] Multi-line docstring summary should start at the second line (line 5) (48 instances)
  - Issue: D213 [*] Multi-line docstring summary should start at the second line (line 5) (48 instances)
  - Docstring: D213 [*] Multi-line docstring summary should start at the second line (line 5) (48 instances)
  - D213: [*] Multi-line docstring summary should start at the second line (line 2) (34 instances)
  - Docstring: D213 [*] Multi-line docstring summary should start at the second line (line 2) (34 instances)
  - D213: [*] Multi-line docstring summary should start at the second line (line 14) (32 instances)
  - Issue: D213 [*] Multi-line docstring summary should start at the second line (line 14) (32 instances)
  - Docstring: D213 [*] Multi-line docstring summary should start at the second line (line 14) (32 instances)
  - Style: D100 Missing docstring in public module (line 1) (230 instances)
  - Style: D213 [*] Multi-line docstring summary should start at the second line (line 1) (96 instances)
  - Style: D213 [*] Multi-line docstring summary should start at the second line (line 7) (61 instances)
  - Style: D213 [*] Multi-line docstring summary should start at the second line (line 5) (48 instances)
  - Style: D213 [*] Multi-line docstring summary should start at the second line (line 2) (34 instances)
  - Style: D213 [*] Multi-line docstring summary should start at the second line (line 14) (32 instances)
  - Style: D213 [*] Multi-line docstring summary should start at the second line (line 16) (24 instances)
  - Style: D213 [*] Multi-line docstring summary should start at the second line (line 20) (21 instances)
  - Style: D213 [*] Multi-line docstring summary should start at the second line (line 12) (21 instances)
  - Style: G004 Logging statement uses f-string (line 43) (20 instances)
  - Style: G004 Logging statement uses f-string (line 48) (20 instances)
  - Style: D213 [*] Multi-line docstring summary should start at the second line (line 3) (18 instances)
  - Style: D213 [*] Multi-line docstring summary should start at the second line (line 15) (17 instances)
  - Style: G004 Logging statement uses f-string (line 58) (16 instances)
  - Style: D213 [*] Multi-line docstring summary should start at the second line (line 25) (16 instances)
  - Style: D213 [*] Multi-line docstring summary should start at the second line (line 24) (15 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_run_not_implemented` (line 138) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_run_not_implemented` (line 62) (2 instances)
  - G004: Logging statement uses f-string (line 43) (20 instances)
  - Issue: G004 Logging statement uses f-string (line 43) (20 instances)
  - G004: Logging statement uses f-string (line 48) (20 instances)
  - Issue: G004 Logging statement uses f-string (line 48) (20 instances)
  - G004: Logging statement uses f-string (line 58) (16 instances)
  - Issue: G004 Logging statement uses f-string (line 58) (16 instances)
  - G004: Logging statement uses f-string (line 37) (15 instances)
  - Issue: G004 Logging statement uses f-string (line 37) (15 instances)
  - G004: Logging statement uses f-string (line 47) (15 instances)
  - Issue: G004 Logging statement uses f-string (line 47) (15 instances)
  - G004: Logging statement uses f-string (line 53) (15 instances)
  - Issue: G004 Logging statement uses f-string (line 53) (15 instances)
  - S101: Use of `assert` detected (line 34) (14 instances)
  - Issue: S101 Use of `assert` detected (line 34) (14 instances)
  - S101: Use of `assert` detected (line 35) (14 instances)
  - G004: Logging statement uses f-string (line 61) (13 instances)
  - Issue: G004 Logging statement uses f-string (line 61) (13 instances)
  - G004: Logging statement uses f-string (line 81) (13 instances)
  - Syntax/parsing error: TRY400 Use `logging.exception` instead of `logging.error` (11 instances)
  - Syntax/parsing error: G004 Logging statement uses f-string (5 instances)
  - Syntax/parsing error: BLE001 Do not catch blind exception: `Exception` (3 instances)
  - Syntax/parsing error: T201 `print` found (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_setup_argparse` (line 87) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_setup_argparse` (line 87) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_base_parse_args` (line 101) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_base_parse_args` (line 120) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_args` (line 101) (2 instances)
  - Syntax/parsing error: TRY400 Use `logging.exception` instead of `logging.error` (11 instances)
  - Syntax/parsing error: G004 Logging statement uses f-string (5 instances)
  - Syntax/parsing error: BLE001 Do not catch blind exception: `Exception` (3 instances)
  - Syntax/parsing error: T201 `print` found (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_setup_argparse` (line 87) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_setup_argparse` (line 87) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_base_parse_args` (line 101) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_base_parse_args` (line 120) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_args` (line 101) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_args_file_not_found` (line 120) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_json` (line 133) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_list` (line 161) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_timestamp` (line 84) (2 instances)
  - Syntax/parsing error: PTH123 `open()` should be replaced by `Path.open()`
  - D100: Missing docstring in public module (line 1) (228 instances)
  - Docstring: D100 Missing docstring in public module (line 1) (226 instances)
  - Issue: D100 Missing docstring in public module (line 1) (204 instances)
  - Style: D100 Missing docstring in public module (line 1) (228 instances)
  - Style: G004 Logging statement uses f-string (line 51) (20 instances)
  - Style: G004 Logging statement uses f-string (line 46) (17 instances)
  - Style: G004 Logging statement uses f-string (line 49) (16 instances)
  - Style: G004 Logging statement uses f-string (line 54) (15 instances)
  - Style: S101 Use of `assert` detected (line 35) (15 instances)
  - Style: G004 Logging statement uses f-string (line 59) (14 instances)
  - Style: G004 Logging statement uses f-string (line 47) (14 instances)
  - Style: S101 Use of `assert` detected (line 34) (14 instances)
  - Style: S101 Use of `assert` detected (line 36) (14 instances)
  - Style: G004 Logging statement uses f-string (line 42) (13 instances)
  - Style: G004 Logging statement uses f-string (line 56) (12 instances)
  - Style: G004 Logging statement uses f-string (line 71) (12 instances)
  - Style: G004 Logging statement uses f-string (line 78) (12 instances)
  - Style: G004 Logging statement uses f-string (line 61) (12 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_run_not_implemented` (line 138) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_run_not_implemented` (line 62) (2 instances)
  - G004: Logging statement uses f-string (line 51) (20 instances)
  - Issue: G004 Logging statement uses f-string (line 51) (20 instances)
  - G004: Logging statement uses f-string (line 46) (17 instances)
  - Issue: G004 Logging statement uses f-string (line 46) (17 instances)
  - G004: Logging statement uses f-string (line 49) (16 instances)
  - Issue: G004 Logging statement uses f-string (line 49) (16 instances)
  - G004: Logging statement uses f-string (line 54) (15 instances)
  - S101: Use of `assert` detected (line 35) (15 instances)
  - Issue: S101 Use of `assert` detected (line 35) (15 instances)
  - G004: Logging statement uses f-string (line 59) (14 instances)
  - Issue: G004 Logging statement uses f-string (line 59) (14 instances)
  - Issue: G004 Logging statement uses f-string (line 54) (14 instances)
  - G004: Logging statement uses f-string (line 47) (14 instances)
  - Issue: G004 Logging statement uses f-string (line 47) (14 instances)
  - S101: Use of `assert` detected (line 34) (14 instances)
  - Issue: S101 Use of `assert` detected (line 34) (14 instances)
  - S101: Use of `assert` detected (line 36) (14 instances)
  - G004: Logging statement uses f-string (line 42) (13 instances)
  - Syntax/parsing error: TRY400 Use `logging.exception` instead of `logging.error` (11 instances)
  - Syntax/parsing error: TRY400 Use `logging.exception` instead of `logging.error` (11 instances)
  - Syntax/parsing error: G004 Logging statement uses f-string (5 instances)
  - Syntax/parsing error: BLE001 Do not catch blind exception: `Exception` (3 instances)
  - Syntax/parsing error: T201 `print` found (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_setup_argparse` (line 87) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_setup_argparse` (line 87) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_base_parse_args` (line 101) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_base_parse_args` (line 120) (2 instances)
  - D100: Missing docstring in public module (line 1) (223 instances)
  - Docstring: D100 Missing docstring in public module (line 1) (221 instances)
  - Issue: D100 Missing docstring in public module (line 1) (200 instances)
  - Style: D100 Missing docstring in public module (line 1) (223 instances)
  - Style: G004 Logging statement uses f-string (line 51) (20 instances)
  - Style: G004 Logging statement uses f-string (line 46) (17 instances)
  - Style: G004 Logging statement uses f-string (line 49) (15 instances)
  - Style: S101 Use of `assert` detected (line 35) (15 instances)
  - Syntax/parsing error: TRY400 Use `logging.exception` instead of `logging.error` (11 instances)
  - Syntax/parsing error: G004 Logging statement uses f-string (5 instances)
  - Syntax/parsing error: T201 `print` found (3 instances)
  - Syntax/parsing error: BLE001 Do not catch blind exception: `Exception` (3 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_setup_argparse` (line 87) (2 instances)
  - Syntax/parsing error: TRY400 Use `logging.exception` instead of `logging.error` (11 instances)
  - Syntax/parsing error: G004 Logging statement uses f-string (5 instances)
  - Syntax/parsing error: T201 `print` found (3 instances)
  - Syntax/parsing error: BLE001 Do not catch blind exception: `Exception` (3 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_setup_argparse` (line 87) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_setup_argparse` (line 87) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_base_parse_args` (line 101) (2 instances)
  - Issue: ANN001 Missing type annotation for function argument `mock_base_parse_args` (line 120) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_args` (line 101) (2 instances)
  - Issue: ANN201 Missing return type annotation for public function `test_parse_args_file_not_found` (line 120) (2 instances)
  - Syntax/parsing error: TRY400 Use `logging.exception` instead of `logging.error` (11 instances)
  - Syntax/parsing error: G004 Logging statement uses f-string (5 instances)
  - Syntax/parsing error: T201 `print` found (3 instances)
  - Syntax/parsing error: BLE001 Do not catch blind exception: `Exception` (3 instances)
