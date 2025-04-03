# LLM Utility Functions



## Executive Summary

{'executive_summary': {'overview': 'This project encompasses a wide range of LLM-related utilities, agents, and API clients, designed to enhance various aspects of research, analysis, and automation. The scope includes tools for interacting with LLMs, managing data, analyzing content, and creating specialized agents for diverse tasks. The primary goal is to provide a comprehensive suite of components that leverage LLMs to improve efficiency and decision-making across different domains.', 'architecture': 'The architecture is component-based, with a mix of core utilities, legacy modules, agent frameworks (smolagents), and API client integrations. Key architectural decisions involve the use of Pydantic for data modeling, structlog for structured logging, and various libraries for LLM interaction (e.g., llama_index, litellm, openai). No specific architectural patterns are explicitly identified, suggesting a more pragmatic approach to component design and integration.', 'components': 'Major components include: 1) `tool_factory.py` and `tool_launcher.py` for managing and launching external tools; 2) `llm_utils.py` for LLM client configuration and request handling; 3) `agents/*` for various AI agents built on smolagents; 4) `api_clients/*` for interacting with different LLM providers (OpenRouter, Gemini, DeepInfra); and 5) a collection of `legacy/*` modules covering tasks like data ingestion, email prioritization, company analysis, and database management. Interactions between components are primarily dependency-based, with agents utilizing tools and API clients to perform specific tasks.', 'issues': 'No critical issues are explicitly identified in the provided data. However, the presence of a large number of `legacy/*` modules suggests potential areas for refactoring and modernization. The lack of explicitly defined architectural patterns could also lead to inconsistencies and maintainability challenges in the long run.', 'next_steps': 'Recommended next steps include: 1) Conduct a thorough review of the `legacy/*` modules to identify opportunities for refactoring and integration with the core components; 2) Define clear architectural patterns and guidelines to ensure consistency and maintainability; 3) Implement comprehensive testing and monitoring to ensure the reliability and performance of the LLM-based utilities and agents; and 4) Explore opportunities for further modularization and abstraction to improve code reusability and reduce dependencies.'}}

## Components

### tool_factory.py

No description available.

#### Responsibilities

- Load and manage available tools.
- Load tools.
- Create tool instances.
- Load tools from a configured file.

#### Dependencies

- importlib library
- __future__ library
- llama_index library

### exceptions_0b0e30bb_1.py

No description available.

#### Responsibilities

- Signal that data persistence failed
- Base exception for database errors
- Signal that data fetching failed
- Provides a common type for catching database issues
- Indicate a failure during database saving
- Indicate a failure during database retrieval

#### Dependencies


### llm_utils.py

No description available.

#### Responsibilities

- Manage LLM client configuration.
- Execute LLM requests with fallback support.
- Parse and clean LLM responses (including JSON).

#### Dependencies

- __future__ library
- exceptions.py for llm functionality
- dotenv library
- api_clients.py for llm functionality
- rich library

### tool_launcher.py

Tool launcher for integrating external CLI tools.

#### Responsibilities

- Initialize the tool launcher
- Check if a tool is currently running
- Manage external CLI tools
- Verify that required tools are installed
- Launch external CLI tools
- Verify required tools are installed

#### Dependencies

- shutil library
- __future__ library
- asyncio library

### exceptions.py

No description available.

#### Responsibilities

- Provides a common error type for LLM operations
- Base class for LLM exceptions

#### Dependencies


### legacy/log_analyzer.py

Mercury Import Log Analyzer.

Monitors mercury_import.log and maintains an error status report.
Uses external deepinfra_client.py for API interactions.

#### Responsibilities

- Configure error classification.
- Store error tracking information.
- Represent a classified error.

#### Dependencies

- subprocess library
- dataclasses library
- pathlib library
- time library

### legacy/image_generation.py

No description available.

#### Responsibilities

- Interact with the Stability AI API.
- Generate images from text prompts.
- Manage output directory for generated images.

#### Dependencies

- pydantic library
- requests library
- __future__ library
- llama_index library
- uuid library

### legacy/db_sync.py

Database sync module.

This module handles syncing the local DuckDB database to the data lake.

#### Responsibilities

- Sync local database to data lake
- Create timestamped backup
- Maintain latest version in data lake

#### Dependencies

- subprocess library
- pathlib library
- datetime library

### legacy/stock_models.py

No description available.

#### Responsibilities

- Store stock-related data
- Provide recommendations based on analysis
- Analyze stock data
- Generate insights from stock data
- Represent a stock being tracked
- Potentially manage updates to stock data

#### Dependencies

- sqlalchemy library

### legacy/xxxx_llm_tool_tracking.py

No description available.

#### Responsibilities

- Represent a database migration.
- Define database schema changes.
- Manage migration application and rollback.

#### Dependencies

- django library

### legacy/email_prioritization.py

Service for prioritizing emails based on user preferences and patterns.

#### Responsibilities

- Score emails based on user preferences.
- Prioritize emails based on scoring.
- Log an edge case for analysis.
- Initialize the prioritizer with configuration.
- Score an email using multiple methods.
- Score an email based on predefined rules.
- Define sources of priority decisions.
- Load a JSON configuration file.
- Score email using DeepInfra API.
- Manage configuration for prioritization.

#### Dependencies

- structlog library
- requests library
- pathlib library
- database library
- django library
- tenacity library

### legacy/format_and_lint.py

Script to format and lint all Python code in the project.

This script provides automated code formatting and linting for the entire project
using Black (formatter) and Flake8 (linter). It processes all Python files in the
'scripts' and 'tests' directories.

The script handles:
- Formatting code according to PEP 8 standards using Black
- Checking code quality and style using Flake8
- Error handling and reporting for both tools
- Recursive directory traversal for Python files

Usage:
    python scripts/format_and_lint.py

#### Responsibilities

- Check Python files for style violations with Flake8
- Format Python files with Black

#### Dependencies

- subprocess library
- pathlib library

### legacy/import_data.py

Import TICK history from CSV file.

Imports historical TICK data from the CSV file into the database.

#### Responsibilities

- Parse a string into an integer TICK value.
- Import TICK history data from a CSV file into a database.

#### Dependencies

- pathlib library
- __future__ library
- sqlalchemy library
- data_store library
- models library
- csv library
- datetime library

### legacy/models.py

No description available.

#### Responsibilities

- Store creation and update timestamps.
- Represent a static page with title, slug, and content.
- Specify the app label for the Page model.
- Generate the absolute URL for the page.
- Return the page title as a string representation.
- Define the default ordering for Page objects.
- Provide a canonical URL.

#### Dependencies

- django library

### legacy/model_config.py

No description available.

#### Responsibilities

- Define available chat model options.
- Provide a way to represent different chat models.
- Act as an enumeration for chat models.

#### Dependencies

- enum library
- dotenv library

### legacy/company_analysis_manager.py

No description available.

#### Responsibilities

- Import necessary libraries.
- Handle file uploads.
- Trigger the analysis workflow.
- Display a preview of the data.
- Validate data and prepare it for analysis.
- Introduce the application.
- Set analysis parameters.
- Process the uploaded CSV file.

#### Dependencies

- marimo library
- pandas library
- datetime library

### legacy/deepinfra_client.py

DeepInfra API Client (Legacy).

Handles error classification requests through the DeepInfra API with
improved error handling, retries, and chunking for large files.

#### Responsibilities

- Parse API response into structured error data.
- Serve as the main entry point for execution.
- Classify errors using the DeepInfra API.
- Write classified errors to a markdown file.

#### Dependencies

- requests library
- hashlib library
- pathlib library
- time library

### legacy/db_migration.py

Database migration script to add enrichment tables and fields.

This script handles the evolution of the database schema to support:
- Contact enrichment data (job titles, LinkedIn profiles, etc.)
- Business opportunity tracking
- Enrichment task management
- Data source tracking
- Historical metadata changes

The migration is idempotent - it can be run multiple times safely as it checks
for existing columns and tables before creating them.

Key Features:
- Safe schema evolution with existence checks
- Comprehensive foreign key relationships
- Indexing for common query patterns
- JSON support for flexible metadata storage
- Timestamp tracking for all changes

#### Responsibilities

- Add enrichment-related schema elements to the database.

#### Dependencies

- scripts library
- sqlite3 library

### legacy/brave_search_engine.py

Brave Search Engine.
================

Provides functionality to perform web and local searches using the Brave Search API.

#### Responsibilities

- Perform local business searches
- Execute web searches using Brave Search API
- Handle rate limiting and retries

#### Dependencies

- aiohttp library
- base library
- __future__ library
- asyncio library

### legacy/controversy_analyzer.py

No description available.

#### Responsibilities

- Categorize a source based on its URL.

#### Dependencies

- prefect library
- __future__ library
- httpx library
- dotenv library
- datetime library

### legacy/form_filling.py

No description available.

#### Responsibilities

- Save the filled-out file.
- Fill missing cells in a CSV file.
- Extract missing cells and generate questions.
- Represent a list of missing cells.
- Fill cell values into a CSV file.
- Get the file name and extension.
- Save the output to a file.
- Represent a missing cell in a table.
- Represent a cell value.
- Extract missing cells and generate questions to fill them.

#### Dependencies

- pydantic library
- __future__ library
- llama_index library
- pandas library
- textwrap library
- app library
- uuid library

### legacy/email_data_generator.py

Script to generate test email data for processing.

This module provides functionality to create realistic test email data for development
and testing purposes. It generates random but structured email content and stores it
in a SQLite database for use in testing email processing pipelines.

The generated data includes:
- Realistic email addresses with name patterns
- Varied job titles and company names
- Random but plausible email content
- Timestamps spread over a 30-day period
- Unique message IDs for each email

The data is stored in the 'enriched_raw_emails' table of the SQLite database.

#### Responsibilities

- Generate and store test emails in a database.
- Generate formatted email content with a signature block.

#### Dependencies

- uuid library
- datetime library
- sqlite3 library
- random library

### legacy/data_ingestion.py

No description available.

#### Responsibilities

- Generate a datasource.
- Ensure an index exists.

#### Dependencies

- llama_index library
- dotenv library
- llama_cloud library
- app library

### legacy/mercury_importer.py

No description available.

#### Responsibilities

- Generate hledger journal entries
- Validate transaction data
- Process Mercury CSV files
- Log audit events
- Classify transactions using an AI model
- Deduplicate transactions
- Get configured categories from classification rules

#### Dependencies

- collections library
- secrets library
- requests library
- hashlib library
- pathlib library
- classification_engine library
- __future__ library
- bin library
- prometheus_client library
- src library
- re library
- shutil library
- subprocess library
- argparse library
- datetime library

### legacy/event_callback.py

No description available.

#### Responsibilities

- Provide a base class for event handling
- Generate tool messages
- Convert to a response object
- Generate retrieval messages
- Handle event start
- Handle event end

#### Dependencies

- collections library
- pydantic library
- contextlib library
- __future__ library
- llama_index library
- asyncio library

### legacy/tagging_engine.py

No description available.

#### Responsibilities

- Apply tags to documents.
- Parse LLM responses.
- Record tagging operations.
- Tag financial metrics.
- Tag document type.
- Create a tagging agent.
- Tag data using LLMs.
- Clear the tagging history.
- Provide a history of tagging events.

#### Dependencies

- enum library
- datetime library
- llama_index library

### legacy/log_manager.py

Centralized logging configuration and management.
Combines functionality from log_config.py and log_manager.py.

#### Responsibilities

- Configure and manage logging.
- Analyze log files for errors and statistics.
- Rotate log files.

#### Dependencies

- pathlib library
- __future__ library
- scripts library
- re library
- datetime library

### legacy/precommit_analyzer.py

No description available.

#### Responsibilities


#### Dependencies

- argparse library
- dataclasses library
- pathlib library
- __future__ library
- enum library
- subprocess library
- importlib library
- datetime library

### legacy/prompts.py

No description available.

#### Responsibilities


#### Dependencies


### legacy/company_analysis.py

No description available.

#### Responsibilities

- Read company data from a CSV file.
- Save analysis results to JSON and Markdown files.

#### Dependencies

- prefect library
- __future__ library
- asyncio library
- csv library
- farfalle library
- datetime library

### legacy/pro_chat.py

No description available.

#### Responsibilities

- Manage dependencies between steps
- Manage resources used by a step
- Execute a single query plan step
- Provide context for query step execution
- Handle errors and exceptions during execution
- Store and retrieve data relevant to a step
- Define the operation to be performed
- Organize and sequence query execution steps
- Represent a single step in a query plan
- Manage the state of a step during execution
- Specify dependencies on other steps
- Provide an execution order for query steps

#### Dependencies

- fastapi library
- collections library
- pydantic library
- backend library
- __future__ library
- asyncio library
- sqlalchemy library

### legacy/db_maintenance.py

Database maintenance utilities.
Handles health checks and optimization tasks.

Note: Most core maintenance functionality is handled by db_connector.py through:
- WAL mode for better concurrency
- Connection pooling and retry logic
- Health checks during connections
- Automatic transaction management

#### Responsibilities

- Check WAL file size for cleanup.
- Determine if WAL file exceeds the size threshold.
- Initialize database maintenance helper.
- Perform routine database maintenance tasks.
- Execute routine database maintenance procedures.
- Initialize maintenance helper with optional database path.

#### Dependencies

- __future__ library
- sqlite3 library

### legacy/llm_interface.py

No description available.

#### Responsibilities

- Implement BaseLLM using LiteLLM and Instructor.
- Provide a base for structured completion.
- Complete prompts using LiteLLM.
- Define the interface for LLM implementations.
- Provide a base for completing prompts.
- Structure completion responses using Instructor.

#### Dependencies

- collections library
- abc library
- instructor library
- litellm library
- llama_index library
- dotenv library

### legacy/merge_data.py

No description available.

#### Responsibilities

- Merge podcast data into the research database.

#### Dependencies

- duckdb library
- pathlib library

### legacy/base_engine.py

Base Engine Module
================

Provides base classes for all research engines in the EthiFinX platform.

#### Responsibilities

- Define the interface for analysis engines
- Require implementation of the 'search' method
- Provide basic configuration
- Set up logging
- Define the interface for search engines
- Require implementation of the 'analyze' method
- Initialize LLM client

#### Dependencies

- core library
- abc library

### legacy/setup.py

No description available.

#### Responsibilities

- Initialize environment variables
- Initialize API tokens

#### Dependencies

- pathlib library
- posting library

### legacy/chat.py

No description available.

#### Responsibilities


#### Dependencies

- fastapi library
- llama_index library
- app library

### legacy/admin.py

Admin interface for Syzygy models.

#### Responsibilities

- Provide a custom admin site for Syzygy
- Manage research results in admin interface
- Manage timeline view in admin interface
- Control add permission
- Configure Syzygy admin interface
- Manage tool usage tracking in admin interface
- Manage research sources in admin interface
- Manage activities in admin interface
- Manage email response drafts in admin interface
- Manage transcript analysis in admin interface
- Control change permission
- Manage excluded companies in admin interface
- Manage tick history in admin interface
- Manage LLM transactions in admin interface
- Manage securities in the investment universe in admin interface
- Initialize app configuration
- Manage research iterations in admin interface
- Manage clients in admin interface
- Manage transcripts in admin interface

#### Dependencies

- django library
- models library
- markdownx library

### legacy/data_migration.py

No description available.

#### Responsibilities

- Import markdown content into research system

#### Dependencies

- duckdb library

### legacy/llm_utils.py

No description available.

#### Responsibilities

- Represent time series embeddings.

#### Dependencies

- llama_index library

### legacy/rag_agent.py

RAG agent for semantic search using pgvector.

#### Responsibilities

- Perform semantic search
- Facilitate RAG operations
- Manage database connection
- Initialize the agent
- Initialize the RAG agent
- Get the system prompt
- Represent a single search result
- Generate responses using retrieved knowledge

#### Dependencies

- structlog library
- pydantic library
- asyncpg library
- dataclasses library
- __future__ library
- base library

### legacy/entity_analyzer.py

No description available.

#### Responsibilities

- Store analysis results
- Analyze entities for controversies
- Interact with the OpenRouter API
- Represent entity analysis results
- Track analyzed companies
- Represent a source of information
- Manage a SQLite database
- Format prompts for analysis

#### Dependencies

- dataclasses library
- __future__ library
- backend library
- asyncio library
- csv library
- datetime library
- sqlite3 library

### legacy/company_analysis_deployment.py

No description available.

#### Responsibilities


#### Dependencies

- company_analysis library
- prefect library

### legacy/ai_config.py

Configuration management for AI models and agents.

#### Responsibilities

- Classify models by cost
- Centralize configuration for AI agents
- Define supported model providers
- Centralize configuration for AI models
- Estimate cost for a model operation
- Get a model configuration for a task
- Classify models by capability
- Configure a specific model

#### Dependencies

- enum library
- dataclasses library
- __future__ library
- structlog library

### legacy/data_models.py

Data models for research and analysis.

#### Responsibilities

- Represent an evaluation of a company
- Represent a source of information
- Represent a link between companies
- Represent a research question

#### Dependencies

- pydantic library
- datetime library

### legacy/llm_analysis.py

No description available.

#### Responsibilities


#### Dependencies

- random library
- aiohttp library
- asyncio library

### legacy/e2b_code_interpreter.py

No description available.

#### Responsibilities

- Initialize the interpreter.
- Kill the interpreter.
- Return the result, stdout, stderr, display_data, and error.
- Save results to disk and return file metadata.
- Execute Python code in a Jupyter notebook cell.
- Manage files used by the code.

#### Dependencies

- pydantic library
- e2b_code_interpreter library
- __future__ library
- llama_index library
- base64 library
- app library
- uuid library

### legacy/transcript_analysis_agent.py

Agent for analyzing meeting transcripts to extract action items and content.

This module provides functionality to:
- Extract actionable items from meeting transcripts
- Identify potential content opportunities
- Link analysis results to client records
- Create follow-up activities in the system

The analysis uses the Phi-2 language model for precise language understanding
and preservation of original phrasing while extracting key information.

Key Features:
- Action item extraction with context preservation
- Content opportunity identification
- Automatic activity creation
- Client record linking
- Confidence scoring for extracted items
- Transcript location tracking

#### Responsibilities

- Store content opportunity details (topic, source quote, suggested title, etc.)
- Store action item details (description, priority, due date, etc.)
- Store the content opportunity's location in the transcript
- Extract action items from meeting transcripts
- Link analysis results to client records
- Identify content opportunities in meeting transcripts
- Represent a potential content opportunity from a transcript
- Initialize the transcript analysis agent with the Phi-2 language model
- Store the action item's location in the transcript
- Represent an action item from a meeting transcript

#### Dependencies

- structlog library
- pydantic library
- __future__ library
- base library
- models library
- datetime library

### legacy/db_init.py

Database initialization script to create all necessary tables and indexes.

This script handles the complete setup of the SQLite database schema including:
- Core tables for email processing and contact management
- Enrichment tracking tables
- Historical metadata tracking
- Indexes for optimized query performance
- Foreign key relationships and constraints

The schema is designed to support:
- Email processing and storage
- Contact enrichment workflows
- Opportunity detection and tracking
- Historical metadata versioning
- Task management for enrichment processes

#### Responsibilities

- Initialize database tables and indexes

#### Dependencies

- scripts library
- sqlite3 library

### legacy/next_question_suggestion.py

No description available.

#### Responsibilities

- Suggest next questions based on conversation history
- Configure the prompt for question suggestion
- Extract questions from the language model's response

#### Dependencies

- llama_index library
- app library
- __future__ library
- re library

### legacy/api_manager.py

No description available.

#### Responsibilities

- Provide data access methods
- Manage API data storage
- Initialize the database connection

#### Dependencies

- marimo library
- aiosqlite library
- datetime library
- asyncio library

### legacy/priority_manager.py

Priority management system for email processing.

Functionality:
- Implements multiple prioritization approaches
- Combines AI analysis with deterministic rules
- Handles edge cases and low-confidence decisions
- Maintains learning from manual corrections

Maintenance Suggestions:
1. Regularly update priority rules
2. Monitor AI model performance
3. Add more sophisticated consensus mechanisms
4. Implement periodic rule reviews

Integration:
- Used by email_operations.py during processing
- Integrated with email_analyzer.py for AI analysis
- Works with gmail_label_learner.py for corrections

Testing:
- Unit tests: tests/test_priority_manager.py
- Test with various email types and priorities
- Verify rule-based prioritization
- Test edge case handling

#### Responsibilities

- Prioritize email using deterministic rules from preferences
- Store priority, confidence, source, reason, and timestamp
- Represent different sources of priority decisions (DeepInfra, Deterministic, LLM, Manual)
- Represent the result of a priority calculation
- Load prioritization preferences from a configuration file
- Log edge cases and priority decisions for future learning
- Configure logging for priority decisions and edge cases
- Prioritize email using DeepInfra API
- Manage email prioritization using multiple approaches
- Prioritize an email using specified methods
- Initialize the PriorityManager with configuration and logging
- Integrate AI analysis and deterministic rules
- Determine final priority from multiple prioritization results
- Handle edge cases and low-confidence decisions

#### Dependencies

- requests library
- dataclasses library
- __future__ library
- scripts library
- enum library
- tenacity library
- datetime library

### legacy/email_triage_workflow.py

Email triage and prioritization workflow.

#### Responsibilities

- Store email metadata for triage.
- Store a draft response to an email.
- Store email type and priority classification.
- Draft email responses.
- Determine email priority.
- Orchestrate email triage.
- Store results from batch email processing.
- Store email content for analysis.

#### Dependencies

- structlog library
- pydantic library
- __future__ library
- asyncio library
- email_processing library
- sentry_sdk library
- base library
- agents library
- datetime library

### legacy/base.py

Base configuration for PydanticAI agents with DeepInfra integration.

#### Responsibilities

- Handle model selection and function calling.
- Create an interaction record in the database.
- Retrieve the DeepInfra API key.
- Update an interaction record in the database.
- Manage AI agent interactions with DeepInfra.
- Provide the system prompt for the agent.
- Track metrics and monitor costs.
- Initialize the agent with configuration parameters.
- Define a callable function for the model.

#### Dependencies

- structlog library
- pydantic library
- logging.py for config functionality
- __future__ library
- django library
- sentry_sdk library
- httpx library
- asgiref library
- models library
- config library
- load_config.py for config functionality
- ulid library
- time library

### legacy/db_converters.py

Database Format Converters.
======================

Handles conversion between workflow outputs and database formats.
Ensures consistent data structure and safe database operations.

This module is specifically for converting between different data formats
and the database schema. It works in conjunction with data_processing.py
which handles the general data processing pipeline.

#### Responsibilities

- Represent analysis data in a database-compatible format
- Serve as a data transfer object for database interactions
- Map to the database schema

#### Dependencies

- datetime library
- research library
- core library
- __future__ library

### legacy/controversy_detection.py

Controversy detection flows for monitoring specific companies.

#### Responsibilities


#### Dependencies

- openai library
- prefect_sqlalchemy library
- prefect library
- pandas library
- aiohttp library
- datetime library

### legacy/validation.py

No description available.

#### Responsibilities

- Validate local model by checking if local models are enabled.
- Validate the given chat model based on its type and environment variables.
- Validate Groq model by checking for API key.
- Validate OpenAI model by checking API key and GPT-4o enablement.

#### Dependencies

- backend library

### legacy/code_generator.py

No description available.

#### Responsibilities

- Handle optional sandbox files and existing code.
- Generate code artifacts based on input.
- Generate a code artifact.
- Initialize the code generator.

#### Dependencies

- pydantic library
- __future__ library
- llama_index library

### agents/docstring_agent.py

No description available.

#### Responsibilities

- Analyze and improve docstrings
- Check docstring style compliance
- Calculates cyclomatic complexity of an AST node
- Analyzes a file and improves its documentation
- Initializes the DocstringAgent
- Extracts code context using AST analysis
- Analyze code complexity

#### Dependencies

- base_agent library
- smolagents library
- pathlib library
- ast library

### agents/self_care_agent.py

Wellness monitoring and self-care intervention agent using smolagents.

#### Responsibilities

- Monitor work patterns
- Suggest a break if needed
- Monitor user wellness
- Initialize the SelfCareAgent
- Suggest self-care interventions

#### Dependencies

- smolagents library
- base_agent library

### agents/triage_agent.py

Triage agent for initial analysis and delegation of incoming items using smolagents.

#### Responsibilities

- Determines appropriate actions for the item
- Analyzes an item and determines appropriate actions
- Analyzes an item
- Initializes the TriageAgent
- Initializes the agent

#### Dependencies

- smolagents library
- base_agent library

### agents/sloane_optimizer.py

Strategic optimization and prioritization agent using smolagents.

#### Responsibilities

- Optimize tasks based on strategic priorities
- Suggest breaks based on work patterns
- Analyze current state and provide optimization recommendations
- Suggest optimal break times and activities

#### Dependencies

- structlog library
- smolagents library
- base_agent library

### agents/agent_creator_agent.py

Agent creator for dynamically generating and configuring AI agents using smolagents.

#### Responsibilities

- Define the structure of agent configurations.
- Create and configure new AI agents.
- Serve as a data transfer object for agent settings.
- Generate function definitions for agents.
- Craft system prompts for agents.
- Hold configuration data for an agent.

#### Dependencies

- structlog library
- smolagents library
- pydantic library
- base_agent library
- __future__ library

### agents/philosophical_agent.py

Philosophical agent using smolagents.

#### Responsibilities

- Generates philosophical discussion content.
- Engages in philosophical discussions.
- Initializes the agent.

#### Dependencies

- smolagents library
- base_agent library

### agents/base_agent.py

Base agent configuration using smolagents framework.

#### Responsibilities

- Initialize agent with task type and model.
- Generate the system prompt based on the task type.
- Define available tools for the agent.
- Return a list of tools available to the agent.
- Return the system prompt for the agent based on the task type.
- Initialize the agent with task type and model name.

#### Dependencies

- smolagents library

### agents/client_advocate_agent.py

Client relationship and task prioritization agent using smolagents.

#### Responsibilities

- Prioritize client work
- Initialize the ClientAdvocateAgent
- Analyze client relationship and generate insights
- Manage client relationships
- Analyze client relationships and generate insights

#### Dependencies

- smolagents library
- base_agent library

### agents/data_ingestion_agent.py

Data analysis and schema recommendation agent.

This module provides tools for analyzing data structures and recommending database schema changes.
It includes functionality for:
- Data structure analysis
- Schema recommendations
- Data quality assessment
- Integration planning
- Impact analysis

The main class is DataIngestionAgent which provides methods to:
- Analyze data structure and content
- Recommend optimal table structures
- Plan necessary schema changes
- Generate migration plans

Key Features:
- Automatic data type inference
- Schema normalization recommendations
- Data quality metrics
- Migration plan generation
- Impact analysis for schema changes

#### Responsibilities

- Represent a recommended database table structure
- Store column definitions and constraints
- Represent a recommended schema change
- Initialize the data ingestion agent
- Represent analysis of a data column
- Recommend schema changes
- Assess data quality
- Store column statistics (unique ratio, sample values, summary)
- Store column metadata (name, type, nullability)
- Store recommendations for keys, indexes, and partitioning
- Analyze data structure

#### Dependencies

- structlog library
- pydantic library
- pathlib library
- __future__ library
- pandas library
- base library

### agents/rag_agent.py

RAG agent for semantic search using pgvector (DEPRECATED).

#### Responsibilities

- Logs deprecation warning during initialization.
- Searches the knowledge base based on a query.
- Searches the knowledge base using semantic similarity.
- Initializes the RAGAgent and logs deprecation warning.
- Filters search results by content type.

#### Dependencies

- structlog library
- smolagents library
- base_agent library

### agents/adversarial_agent.py

Critical analysis and risk identification agent using smolagents.

#### Responsibilities

- Analyze potential risks in a proposal
- Initialize the AdversarialAgent
- Analyze risks and issues in a proposal
- Provide risk analysis with issues and recommendations
- Initialize with risk analysis tool

#### Dependencies

- structlog library
- smolagents library
- base_agent library

### agents/sloane_ghostwriter.py

Content generation and refinement agent in Sloan's voice.

#### Responsibilities

- Define writing style preferences
- Refine content iteratively
- Initialize the ghostwriter agent
- Store generated content
- Generate content in Sloan's voice
- Define the scope of the content
- Adapt to specific content formats
- Enforce stylistic consistency
- Facilitate content refinement
- Provide context for content creation
- Specify writing patterns
- Represent content generation instructions
- Represent a preliminary version of content

#### Dependencies

- structlog library
- pydantic library
- __future__ library
- base library
- chat_history library

### agents/transcript_analysis_agent.py

No description available.

#### Responsibilities

- Extract content from meeting transcripts
- Extract action items from meeting transcripts
- Analyze meeting transcripts to provide actionable insights

#### Dependencies

- smolagents library
- base_agent library

### agents/contact_agents.py

Contact-related AI agents.

#### Responsibilities

- Analyze contact merges.
- Decide on contact merges.
- Analyze similarity between two contacts.

#### Dependencies

- pydantic library
- base library
- database library

### agents/logical_fallacy_agent.py

Logical fallacy detection agent for analyzing reasoning and arguments.

#### Responsibilities

- Store results of fallacy detection
- Store information about a fallacy type
- Detect logical fallacies in text
- Analyze logical fallacies in text
- Load definitions and examples for fallacy types
- Represent a type of logical fallacy
- Construct the prompt for fallacy analysis
- Represent a detected fallacy in text
- Suggest improvements for argumentation
- Initialize the logical fallacy detection agent
- Represent a complete fallacy analysis of text
- Store information about a specific fallacy instance
- Normalize fallacy analysis data

#### Dependencies

- structlog library
- pydantic library
- base library
- __future__ library

### api_clients/openrouter.py

OpenRouter API client with rate limiting.

#### Responsibilities

- Track rate limits for models.
- Fetch rate limits (RPM, TPM) for a model.
- Implement rate limiting.
- Handle retries for failed requests.
- Generate content using OpenRouter's API.
- Check if rate limits are exceeded for a model and prompt.
- Generate content from a prompt using a specified model.
- Check if rate limits have been exceeded.
- Manage cooldown periods.
- Check if a model is in cooldown.

#### Dependencies

- httpx library
- time library
- __future__ library

### api_clients/gemini.py

No description available.

#### Responsibilities

- Enforce rate limits (RPM, TPM, RPD).
- Implement circuit breaking for overloaded models.
- Track API usage across instances.
- Generate content using Google Gemini models.
- Cache context for improved performance.
- Handle rate limiting and fallback mechanisms.

#### Dependencies

- datetime library
- pathlib library
- google library
- __future__ library
- exceptions.py for llm functionality
- api_clients.py for llm functionality
- random library
- rich library
- threading library
- dotenv library
- time library

### api_clients/deepinfra.py

No description available.

#### Responsibilities

- Generate content using DeepInfra's API (alias for chat_completion).
- Provide a streaming version of chat completion.
- Generate a chat completion response from DeepInfra.
- Generate chat completion responses.
- Interact with DeepInfra's OpenAI-compatible API.
- Initialize the DeepInfra client with an API key.
- Save LLM interaction data to a log file.
- Authenticate with the DeepInfra API using an API key.

#### Dependencies

- openai library
- pathlib library
- __future__ library
- exceptions.py for llm functionality
- re library
- time library
- dotenv library
- datetime library

## Architectural Decisions
