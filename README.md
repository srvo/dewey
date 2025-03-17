## Management Scripts

The `src/dewey/scripts` directory contains a collection of sophisticated management tools that handle various aspects of the project's lifecycle, documentation, and code quality. Here's an analysis of the key scripts:

### Documentation and Architecture

#### PRD Builder (`prd_builder.py`)
- **Purpose**: Manages Product Requirements Documents with architectural awareness
- **Key Features**:
  - Interactive PRD creation and updates
  - Automated repository structure analysis
  - Component and dependency tracking
  - LLM-powered architectural decision documentation
  - Generates both YAML and Markdown formats
  - Convention compliance validation

#### Architecture Analyzer (`analyze_architecture.py`)
- **Purpose**: Analyzes repository architecture using PRDs and Gemini API
- **Key Features**:
  - Overall architecture assessment
  - Module organization analysis
  - Information flow mapping
  - Maintainability evaluation
  - Concrete improvement suggestions
  - Rich console output with detailed diagnostics

### Code Management

#### Code Consolidation Suite
- **Code Consolidator** (`code_consolidator.py`): Merges similar code patterns
- **Code Uniqueness Analyzer** (`code_uniqueness_analyzer.py`): Identifies unique code patterns
- **Consolidated Code Analyzer** (`consolidated_code_analyzer.py`): Analyzes consolidated code quality
- **Consolidated Mover** (`consolidated_mover.py`): Relocates consolidated code to appropriate modules

#### Legacy Management
- **Legacy Refactor** (`legacy_refactor.py`): Refactors hash-suffixed legacy files
- **Script Mover** (`script_mover.py`): Integrates scripts into project structure
- **Duplicate Manager** (`duplicate_manager.py`): Detects and manages code duplicates

### Documentation and Deployment
- **Document Directory** (`document_directory.py`): Generates comprehensive directory documentation
- **Service Deployment** (`service_deployment.py`): Manages service deployment and configuration

### Key Features Across Scripts
1. **LLM Integration**
   - Uses Gemini API for intelligent analysis
   - Fallback to DeepInfra when needed
   - Context-aware code understanding

2. **Quality Assurance**
   - Automated code quality checks
   - Convention compliance validation
   - Duplicate detection and management

3. **Documentation**
   - Automated README generation
   - PRD management and updates
   - Architecture documentation

4. **Project Structure**
   - Enforces project conventions
   - Maintains organized directory structure
   - Handles code relocation and refactoring

5. **Error Handling**
   - Comprehensive logging
   - Graceful fallbacks
   - User-friendly error messages

### Usage Workflow
1. Start with `prd_builder.py` for new components/features
2. Use `analyze_architecture.py` for periodic architecture reviews
3. Apply `code_consolidator.py` and related tools for code cleanup
4. Maintain documentation with `document_directory.py`
5. Deploy services using `service_deployment.py`

### Best Practices
- Run architecture analysis before major refactoring
- Keep PRDs updated as code evolves
- Regularly check for and consolidate duplicate code
- Document all architectural decisions
- Follow the established project conventions

# Dewey

Dewey is a data processing and analysis platform.

## Components

### Data Upload Module

The data upload module provides functionality to upload data from various file formats to a MotherDuck database. It supports:

- Multiple data sources (DuckDB, SQLite, CSV, JSON, Parquet)
- Robust error handling and retry mechanisms
- Optimized handling for large tables and complex schemas
- Multiple deduplication strategies

For more details, see [Data Upload README](src/dewey/core/data_upload/README.md).

### Usage

```bash
python src/dewey/core/data_upload/upload.py --input_dir /path/to/data --target_db your_database
```

## Setup

1. Set the `MOTHERDUCK_TOKEN` environment variable with your MotherDuck token:
   ```bash
   export MOTHERDUCK_TOKEN=your_token_here
   ```

2. Ensure all required Python packages are installed:
   ```bash
   pip install -r requirements.txt
   ```

## Development

### Running Tests

```bash
pytest
```

### Code Style

We follow PEP 8 guidelines for Python code. Use `black` for formatting:

```bash
black src/
```
