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

# Dewey Codebase

This repository contains the Dewey application codebase, which has been reorganized for better maintainability and structure.

## Directory Structure

The codebase follows a modular structure:

```
/src
  /core               # Core functionality 
    /accounting       # Accounting-related modules
    /bookkeeping      # Bookkeeping features
    /crm              # Customer relationship management
    /research         # Research and analysis features
    /personal         # Personal user features
    /automation       # Automation workflows
    /engines          # Integration engines
    /migrations       # Migration scripts
    base_script.py    # Base class for all scripts
  
  /llm                # Language model integration
    /agents           # AI agents
    /api_clients      # LLM API clients
    /prompts          # Prompt templates
  
  /ui                 # User interface components
    /screens          # Screen views
    /components       # Reusable UI components
  
  /pipeline           # Data processing pipelines
  
  /utils              # Utility functions and helpers
  
  /tests              # Test modules
```

## Using BaseScript

All scripts should inherit from `BaseScript` to ensure consistent behavior and error handling.

### Basic Usage

```python
from src.core.base_script import BaseScript

class MyScript(BaseScript):
    def run(self):
        # Your script implementation goes here
        self.logger.info("Running my script")
        
if __name__ == "__main__":
    script = MyScript(name="MyScript", description="This script does something useful")
    exit_code = script.execute()
    exit(exit_code)
```

### Adding Command-line Arguments

Override the `_add_arguments` method to add script-specific command-line arguments:

```python
from src.core.base_script import BaseScript
import argparse

class MyScript(BaseScript):
    def _add_arguments(self, parser: argparse.ArgumentParser):
        parser.add_argument('--input', required=True, help='Input file path')
        parser.add_argument('--output', required=True, help='Output file path')
    
    def run(self):
        input_path = self.args.input
        output_path = self.args.output
        self.logger.info(f"Processing {input_path} -> {output_path}")
        # Process the input file and write to the output file
```

### Lifecycle Methods

`BaseScript` provides three lifecycle methods:

1. `setup()`: Called before `run()`. Override to perform initialization.
2. `run()`: Main script logic. Must be implemented by subclasses.
3. `cleanup()`: Called after `run()`. Override to perform cleanup tasks.

Example:

```python
class MyScript(BaseScript):
    def setup(self):
        self.logger.info("Setting up resources")
        self.temp_files = []
    
    def run(self):
        self.logger.info("Running main logic")
        # Your implementation here
    
    def cleanup(self):
        self.logger.info("Cleaning up resources")
        for file in self.temp_files:
            os.remove(file)
```

### Logging

`BaseScript` automatically sets up logging. Use `self.logger` to log messages:

```python
def run(self):
    self.logger.debug("Debug information")
    self.logger.info("Informational message")
    self.logger.warning("Warning message")
    self.logger.error("Error message")
    self.logger.critical("Critical error message")
```

## Conventions

1. Place each script in the appropriate module directory based on its functionality.
2. All scripts should inherit from `BaseScript`.
3. Implement the `run()` method in all script subclasses.
4. Use the logger provided by `BaseScript` for all logging.
5. Add appropriate command-line arguments using `_add_arguments()`.
6. Return appropriate exit codes from the `run()` method.

## Development

1. Create a virtual environment: `python -m venv venv`
2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Run tests: `python -m pytest`
