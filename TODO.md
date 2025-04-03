# Dewey Project - TODO List

## Project Structure Standardization

1. **High Priority**
   - [x] Reorganize tests into unit/ and integration/ directories
   - [x] Move files from src/dewey root to appropriate modules
   - [x] Standardize config management approach using BaseScript
   - [x] Create README file explaining the standard project structure
   - [x] Fix imports in moved test files to ensure they work in new locations
   - [x] Run test suite to validate reorganized structure works correctly
   - [x] Centralize configuration in config/dewey.yaml and remove scattered config files
   - [x] Consolidate scripts from project root and src/dewey/maintenance into scripts/
   - [x] Reorganize src/dewey/core/ directory structure (maintenance/, migrations/, sync/, tui/, tests/)
   - [ ] Ensure CI/CD pipeline is updated for new structure

2. **Medium Priority**
   - [x] Review and migrate remaining files from backup/ backups/ directories
   - [ ] Add integration tests for UI components
   - [ ] Standardize docstrings across all files
   - [ ] Enforce BaseScript usage in all scripts
   - [ ] Update development documentation to reflect new structure
   - [x] Add pre-commit hook to verify abstract methods (execute) are implemented

3. **Lower Priority**
   - [ ] Implement code quality checks to enforce structure standards
   - [ ] Migrate old data files to data/ directory
   - [ ] Add missing tests to improve coverage
   - [x] Review and standardize logging approach

## Database Migration

1. **High Priority**
   - [ ] Complete PostgreSQL connection manager implementation
   - [ ] Develop database migration scripts
   - [ ] Update tests to use mock PostgreSQL interfaces
   - [ ] Fix mock implementations in tests to handle `local_only` parameter

## Feature Development

1. **Pending Features**
   - [ ] Implement updated CRM functionality
   - [ ] Enhance bookkeeping classification engine
   - [ ] Improve LLM agent reliability
   - [x] Fix circular imports in ethifinx package
   - [x] Fix LiteLLMClient configuration handling
   - [x] Consolidated ethifinx files into core modules

## Technical Debt

1. **Code Quality**
   - [ ] Fix linting issues across codebase
   - [ ] Address TODOs in code
   - [ ] Improve error handling and logging
   - [ ] Ensure abstract methods are implemented in all subclasses
   - [ ] Fix test failures in bookkeeping module classes

## Recent Fixes

1. **Completed**
   - [x] Fixed circular imports in ethifinx package
   - [x] Fixed LiteLLMClient configuration loading and tests
   - [x] Updated test patching approach to make tests more robust
   - [x] Centralized configuration in config/dewey.yaml
   - [x] Standardized logging approach
   - [x] Consolidated all scripts into designated scripts/ directory
   - [x] Reorganized src/dewey/core/ directory structure

## Pre-commit Issues (Last updated: 2025-04-03 02:52:04)

- [ ] Fix issue in `scripts/test_and_fix.py`: Syntax error: expected an indented block after function definition on line 36 (<unknown>, line 37)
- [ ] Class 'EthicalAnalysisWorkflow' needs to implement 'execute' method (in unknown file)
- [ ] Class 'MigrationManager' needs to implement 'execute' method (in unknown file)
- [ ] Class 'DatabaseModule' needs to implement 'execute' method (in unknown file)
- [ ] Class 'AnalysisTaggingWorkflow' needs to implement 'execute' method (in unknown file)
- [ ] Class 'DropJVTables' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CleanupTables' needs to implement 'execute' method (in unknown file)
- [ ] Class 'EmailProcessor' needs to implement 'execute' method (in unknown file)
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
- [ ] Class 'TickProcessor' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ExceptionsScript' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CsvContactIntegration' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CodeUniquenessAnalyzer' needs to implement 'execute' method (in unknown file)
- [ ] Class 'Sheets' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ResearchUtils' needs to implement 'execute' method (in unknown file)
- [ ] Class 'PrecommitAnalyzer' needs to implement 'execute' method (in unknown file)
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
- [ ] Class 'SetupAuth' needs to implement 'execute' method (in unknown file)
- [ ] Class 'PriorityManager' needs to implement 'execute' method (in unknown file)
- [ ] Class 'EmailClassifier' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ConfigHandler' needs to implement 'execute' method (in unknown file)
- [ ] Class 'TestWriter' needs to implement 'execute' method (in unknown file)
- [ ] Class 'CsvIngestor' needs to implement 'execute' method (in unknown file)
- [ ] Class 'AdminTasks' needs to implement 'execute' method (in unknown file)

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
## Pre-commit Resolved

- [ ] Fix issue in `scripts/quick_fix.py`: Syntax error: invalid decimal literal (<unknown>, line 1)
- [ ] Fix issue in `scripts/aider_refactor.py`: Syntax error: invalid syntax (<unknown>, line 39)
- [ ] Fix issue in `src/dewey/core/automation/docs/__init__.py`: Syntax error: expected an indented block after function definition on line 36 (<unknown>, line 37)
- [ ] Class 'EthicalAnalysisWorkflow' needs to implement 'execute' method (in unknown file)
- [ ] Class 'MigrationManager' needs to implement 'execute' method (in unknown file)
- [ ] Class 'ScreenManager' needs to implement 'execute' method (in unknown file)
- [ ] Class 'DatabaseModule' needs to implement 'execute' method (in unknown file)
- [ ] Class 'AnalysisTaggingWorkflow' needs to implement 'execute' method (in unknown file)
- [ ] Class 'DropJVTables' needs to implement 'execute' method (in unknown file)
