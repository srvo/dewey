# Project Management Scripts



## Executive Summary

{'executive_summary': {'overview': 'This project focuses on developing and deploying a suite of Python scripts designed to manage, refactor, analyze, and document a software project. The goal is to improve code quality, reduce redundancy, enforce architectural conventions, and enhance overall project maintainability through automation and LLM integration.', 'architecture': 'The architecture is component-based, with individual scripts responsible for specific tasks such as code refactoring, consolidation, duplicate management, service deployment, and documentation. The system leverages LLMs for code analysis, style correction, and PRD generation. No specific architectural patterns are explicitly defined, suggesting an opportunity to formalize these for better consistency and scalability.', 'components': 'Key components include:\n- `legacy_refactor.py`: Refactors legacy code according to project conventions.\n- `code_consolidator.py`: Identifies and suggests canonical implementations for similar code.\n- `duplicate_manager.py`: Detects and manages duplicate files.\n- `service_deployment.py`: Manages service deployment and backups.\n- `document_directory.py`: Generates documentation and enforces code style.\n- `prd_builder.py`: Assists in creating and managing Product Requirements Documents (PRDs).\n- `analyze_architecture.py`: Analyzes repository architecture based on PRDs.\nThese components interact through file system operations, subprocess calls, and LLM API interactions.', 'issues': 'Currently, there are no explicitly defined critical issues. However, the lack of descriptions for some components (`service_deployment.py`, `consolidated_code_analyzer.py`, `script_mover.py`, `consolidated_mover.py`, `code_uniqueness_analyzer.py`) and the absence of defined architectural patterns suggest potential areas for improvement in terms of documentation and architectural clarity.', 'next_steps': 'Recommended next steps include:\n1.  Complete the descriptions for all components to improve understanding and maintainability.\n2.  Define and document the architectural patterns employed by the system to ensure consistency and scalability.\n3.  Address the dependencies of `consolidated_mover.py`.\n4.  Conduct thorough testing of all components, especially those involving LLM interactions, to ensure reliability and accuracy.\n5.  Consider implementing a centralized configuration management system to manage project conventions and LLM API keys.'}}

## Components

### legacy_refactor.py

Legacy code refactoring script following Dewey project conventions.

#### Responsibilities

- Generate a unique filename with conflict resolution.
- Check if a file is test-related.
- Ensure target path follows project conventions.
- Find and relocate legacy hash-suffixed files.
- Orchestrate the main processing pipeline for refactoring files.
- Check if a file is LLM-related.
- Find all files in the consolidated_functions directory.
- Move legacy file to the appropriate directory with proper naming.
- Check if a non-refactored version already exists.
- Add refactoring metadata as a comment at the top of the file.
- Log refactoring decisions.
- Check if a file belongs to core modules.
- Update imports and references using Ruff.
- Update references to refactored files.

#### Dependencies

- argparse library
- subprocess library
- __future__ library
- re library
- datetime library
- pathlib library
- shutil library

### code_consolidator.py

Advanced code consolidation tool using AST analysis and semantic clustering to identify
similar functionality across scripts and suggest canonical implementations.

#### Responsibilities


#### Dependencies

- tqdm library
- argparse library
- subprocess library
- __future__ library
- re library
- ast library
- datetime library
- pathlib library
- hashlib library
- code_consolidator.py for scripts functionality
- spacy library
- vector_db.py for utils functionality
- llm_utils.py for llm functionality
- collections library
- api_clients.py for llm functionality
- threading library
- concurrent library

### duplicate_manager.py

Advanced directory analysis tool with duplicate management, code quality checks, and structural validation.
Combines collision-resistant duplicate detection with code analysis and project convention enforcement.

#### Responsibilities

- Generate analysis report.
- Initialize the DirectoryAnalyzer.
- Confirm and delete duplicates.
- Check directory structure against conventions.
- Generate consolidated analysis report.
- Validate directory existence and accessibility.
- Find duplicate files by size and hash.
- Analyze code quality.
- Find duplicate files.
- Run code quality checks.
- Calculate SHA-256 hash of a file.

#### Dependencies

- humanize library
- argparse library
- subprocess library
- contextlib library
- pathlib library
- hashlib library

### service_deployment.py

No description available.

#### Responsibilities

- Restore service from backup
- Deploy or update a service
- Create backup of service configuration and data

#### Dependencies

- models library
- datetime library
- pathlib library
- tempfile library
- shutil library

### consolidated_code_analyzer.py

Placeholder for LLM content generation.

#### Responsibilities


#### Dependencies

- subprocess library
- shutil library
- pathlib library
- hashlib library

### script_mover.py

No description available.

#### Responsibilities

- Manage dependencies in pyproject.toml.
- Analyze scripts using LLM.
- Refactor scripts into a project structure.

#### Dependencies

- exceptions.py for llm functionality
- argparse library
- __future__ library
- re library
- ast library
- uuid library
- time library
- pypi_search.py for utils functionality
- pathlib library
- hashlib library
- llm_utils.py for llm functionality
- tomli_w library
- api_clients.py for llm functionality
- tomli library

### consolidated_mover.py

No description available.

#### Responsibilities


#### Dependencies


### document_directory.py

No description available.

#### Responsibilities

- Check if a file has been processed based on content hash.
- Generate a README with quality and structure analysis.
- Calculate SHA256 hash of file contents.
- Load project coding conventions.
- Analyze code in a directory.
- Analyze code using an LLM.
- Process a directory and generate a README.
- Return an LLM client.
- Ensure directory exists and is accessible.
- Generate comprehensive README.
- Suggest a filename using an LLM.
- Load checkpoint data from file.
- Correct code style using an LLM.
- Initialize the DirectoryDocumenter.
- Process the entire project directory.
- Check directory structure against project conventions.
- Correct code style based on project conventions.
- Run code quality checks.
- Save checkpoint data to file.
- Checkpoint a file by saving its content hash.

#### Dependencies

- exceptions.py for llm functionality
- argparse library
- subprocess library
- __future__ library
- pathlib library
- hashlib library
- dotenv library
- api_clients.py for llm functionality
- shutil library

### analyze_architecture.py

Repository architecture analyzer using PRDs and Gemini API.

This script loads PRDs from each repository, analyzes them using Gemini API,
and provides feedback on the overall architecture and suggested improvements.

#### Responsibilities

- Display the architecture analysis.
- Find PRD files in a repository.
- Analyze repository architecture based on PRDs.

#### Dependencies

- rich library
- pathlib library
- llm_utils.py for llm functionality

### prd_builder.py

PRD management system with architectural awareness and LLM integration.

#### Responsibilities

- Guide users through interactive PRD creation.
- Analyze codebases and generate PRDs.
- Handle errors related to LLM interactions.
- Enforce architectural conventions and best practices.

#### Dependencies

- argparse library
- re library
- ast library
- time library
- datetime library
- pathlib library
- rich library
- llm_utils.py for llm functionality
- random library
- typer library

### code_uniqueness_analyzer.py

No description available.

#### Responsibilities

- Generates a report of legacy files.
- Lists files matching the _xxxxxxxx pattern.

#### Dependencies

- re library
- glob library

## Architectural Decisions
