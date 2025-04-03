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
   - [ ] Review and migrate remaining files from backup/ backups/ directories
   - [ ] Add integration tests for UI components
   - [ ] Standardize docstrings across all files
   - [ ] Enforce BaseScript usage in all scripts
   - [ ] Update development documentation to reflect new structure
   - [ ] Add pre-commit hook to verify abstract methods (execute) are implemented

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

## Pre-commit Issues (Last updated: 2025-04-03 02:16:33)\n\n- [ ] Fix issue in `scripts/aider_refactor.py`: Syntax error: invalid syntax (<unknown>, line 39)\n- [ ] Fix issue in `src/dewey/core/automation/docs/__init__.py`: Syntax error: expected an indented block after function definition on line 36 (<unknown>, line 37)\n- [ ] Class 'EthicalAnalysisWorkflow' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'MigrationManager' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'ScreenManager' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'DatabaseModule' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'AnalysisTaggingWorkflow' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'DropJVTables' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'UploadDb' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'EventsModule' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'CleanupTables' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'AdversarialAgent' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'EmailProcessor' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'CSVInferSchema' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'ImportInstitutionalProspects' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'Script' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'Service' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'CodeUniquenessAnalyzer' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'GmailService' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'Bing' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'CliTickManager' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'DataAnalysisScript' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'CompanyAnalysisManager' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'Companies' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'EnrichmentModule' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'EntityAnalysis' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'ContactAgent' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'RssFeedManager' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'ModuleScreen' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'TUIApp' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'AnalyzeTables' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'DeweyManager' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'EventCallback' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'PrdBuilder' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'GenerateLegacyTodos' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'LogManager' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'VerifyDb' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'EmailClassifier' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'Utils' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'DropSmallTablesScript' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'RFDocstringAgent' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'PolygonEngine' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'RFDocstringAgent' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'CleanupTables' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'ScriptInitMigrator' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'PriorityModule' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'TUIApp' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'CrmModule' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'Workers' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'AnalyzeLocalDbs' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'Prompts' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'DocsScript' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'ResearchWorkflow' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'DashboardGenerator' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'SecFilingsManager' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'CheckDataScript' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'PrecommitAnalyzer' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'Serper' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'GithubAnalyzer' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'APIServer' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'Workers' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'TicDeltaWorkflow' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'CrmCataloger' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'TickProcessor' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'ExceptionsScript' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'CsvContactIntegration' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'CodeUniquenessAnalyzer' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'Sheets' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'ResearchUtils' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'PrecommitAnalyzer' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'TestWriter' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'MyUtils' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'ServiceItem' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'STSXmlParser' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'TaggingEngine' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'UploadDb' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'CsvContactIntegration' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'Config' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'JsonResearchIntegration' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'ContactConsolidation' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'DropOtherTables' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'CleanupOtherFiles' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'TranscriptsModule' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'TranscriptMatcher' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'EmailDataGenerator' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'OpenRouterClient' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'PypiSearch' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'SetupAuth' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'PriorityManager' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'EmailClassifier' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'ConfigHandler' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'TestWriter' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'CsvIngestor' needs to implement 'execute' method (in unknown file)\n- [ ] Class 'AdminTasks' needs to implement 'execute' method (in unknown file)\n
