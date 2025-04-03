# Investment Research & Portfolio Managment



## Executive Summary

This project aims to build a comprehensive investment research and portfolio management platform. The scope encompasses data ingestion, ethical analysis, portfolio tracking, and reporting. The platform will provide tools for analyzing financial data, assessing ethical considerations, managing investment portfolios, and generating insightful reports.

Key components include `populate_stocks.py` for data ingestion and database population, `investments.py` and `portfolio_widget.py` for investment modeling and portfolio management, `ethical_analyzer.py` for ethical analysis, `company_views.py` and `tick_report.py` for company and market analysis, and `financial_pipeline.py` for financial data processing and reporting. Other components provide support for news aggregation, SEC filings, and data visualization.

The architecture relies heavily on a database (likely DuckDB and/or a relational database) for data storage and retrieval. The platform uses libraries like SQLAlchemy, pandas, and textual for data manipulation, UI development, and financial calculations. The project requires careful consideration of data synchronization, error handling, and user interface design to ensure a robust and user-friendly experience.

## Components

### populate_stocks.py

No description available.

#### Responsibilities

- Sanitize string data for database insertion.
- Remove redundant whitespace (e.g., multiple spaces) from a string.
- Add the created TrackedStock objects to the database session.
- Commit the changes to the database.
- Potentially filter or validate stock data before adding it to the database.
- Remove newline characters from a string.
- Define the database connection string.
- Handle potential errors during CSV parsing or database insertion.
- Read stock data related to 'port45' from a CSV file.
- Create TrackedStock objects from the parsed data.
- Create database tables based on SQLAlchemy models (e.g., TrackedStock).
- Remove leading/trailing whitespace from a string.
- Establish a database session for interacting with the database.
- Parse stock data from CSV rows.
- Create a database engine using SQLAlchemy.

#### Dependencies

- models library
- csv library
- datetime library
- sqlalchemy library

### port_database.py

No description available.

#### Responsibilities

- Initialize the database connection pool
- Manage port data (CRUD operations)
- Handle database connection errors
- Potentially interact with Supabase client for data storage/retrieval
- Provide an interface for accessing and modifying port information

#### Dependencies

- datetime library
- asyncpg library
- supabase library

### investments.py

Investment models.

#### Responsibilities

- Allow filtering and sorting of investments based on ESG scores
- Provide historical price data for calculating investment performance
- Represent the rating agency and the date of the rating
- Associate investments with specific AssetTypes and ESGRatings
- Enable time-series analysis of investment prices
- Store ESG (Environmental, Social, Governance) ratings for investments
- Calculate market value based on current price data
- Consider transaction costs (e.g., brokerage fees) in the calculation
- Calculate profit/loss in percentage terms
- Potentially handle different currency conversions if applicable
- Calculate profit/loss based on purchase price and market value
- Categorize investments based on asset class
- Model an investment position, including quantity, purchase price, and date
- Represent different types of investment assets (e.g., Stock, Bond, Real Estate)
- Calculate the current market value of an investment based on its quantity and current price
- Manage relationships with PriceTick data
- Define properties specific to each asset type (e.g., ticker symbol for stocks)
- Track investment performance over time
- Store price tick history for investments at specific timestamps
- Calculate the profit or loss of an investment based on its purchase price and current market value
- Provide access to ESG data from various rating agencies

#### Dependencies

- datetime library
- __future__ library
- sqlalchemy library
- enum library

### portfolio_widget.py

Portfolio management widget.

#### Responsibilities

- Handle user interactions (button clicks, data table selections)
- Display portfolio data in a tabular format (DataTable)
- Provide actions for managing portfolio holdings (e.g., buy, sell)
- Initialize the widget and its internal state
- Utilize Decimal for precise financial calculations
- Manage investment portfolio data (add, remove, update holdings)
- Inherit and extend functionality from BaseWidget
- Compose the widget's UI using Textual TUI elements (DataTable, Buttons, Containers)

#### Dependencies

- base library
- textual library
- decimal library

### universe_breakdown.py

No description available.

#### Responsibilities

- Potentially orchestrates data loading and processing using duckdb
- May interact with the operating system via the 'os' module (e.g., file system operations)
- Entry point of the program

#### Dependencies

- duckdb library

### company_analysis_app.py

No description available.

#### Responsibilities

- Imports necessary libraries such as marimo, json, sqlite3, datetime, pathlib, and pandas.
- Transforms and prepares the data for analysis and visualization.
- Provides an overview of the data's central tendencies and distributions.
- Computes key statistical measures such as mean, median, standard deviation, etc.
- Handles module imports.
- Offers customization options for the exported data.
- Loads data.
- Evaluates the quality, completeness, and accuracy of the data.
- Presents the calculated statistics in a user-friendly format.
- Provides sector-specific data breakdown.
- Handles database connection errors and ensures a stable connection throughout the application's lifecycle.
- Connects to the SQLite database.
- Identifies potential data issues such as missing values, outliers, or inconsistencies.
- Assesses data health.
- Handles the export process and ensures data integrity.
- Provides context and background information on each controversy.
- Allows users to export the analyzed data and visualizations in various formats (e.g., CSV, JSON, PDF).
- May include a welcome message or instructions on how to use the application.
- Presents introductory information.
- Handles potential data loading errors.
- Ensures all required dependencies are available for the application to function correctly.
- Establishes a database connection.
- Presents sector-specific insights and visualizations.
- Provides recommendations for improving data quality.
- Provides context and purpose of the application to the user.
- Calculates summary statistics.
- Provides export options.
- Identifies trends and patterns within each sector.
- Categorizes and analyzes data based on different sectors.
- May include links to relevant sources or documents.
- Reads data from the database or other data sources.
- Displays controversy details.
- Retrieves and presents information about controversies related to the data.

#### Dependencies

- pandas library
- pathlib library
- datetime library
- marimo library
- sqlite3 library

### company_views.py

No description available.

#### Responsibilities

- Handle user selection of a company (navigation to CompanyDetailView)
- Handle layout and styling of the view
- Initialize the view (likely includes data fetching setup)
- Format tick data for display (potentially using pandas)
- Handle user interactions (if any, e.g., zooming on charts)
- Initialize the view (likely includes fetching company list data)
- Fetch historical tick data from a data source (e.g., database, API)
- Render a list of companies (potentially using `rich` library components)
- Retrieve historical tick data (using `get_tick_history` or similar)
- Render the view (likely a method within CompanyDetailView or CompanyListView)
- Return tick data in a usable format (e.g., pandas DataFrame)
- Update the display with new data
- Render company details (using `rich` library components like Layout, Panel, Table, and potentially plotext for charts)
- Handle potential errors during data retrieval

#### Dependencies

- pandas library
- plotext library
- rich library
- celadon library

### cli_tick_manager.py

No description available.

#### Responsibilities

- Manages database connection and schema using DuckDB.
- Orchestrates database setup and schema validation using Alembic.
- B
- C
- e
- s
- p
- Provides command-line interface for tick value operations, including updating, retrieving, and searching tick data.
- z
- V
- U
- I
- M
- a
-
- v
- q
- k
- u
- x
- Handles database queries and updates for tick data, including historical data.
- m
- h
- ,
- g
- Handles logging and error reporting related to tick data operations.
- l
- r
- y
- b
- w
- c
- i
- d
- o
- D
- S
- n
- A
- t
- '
- H
- f
- R
- .

#### Dependencies

- duckdb library
- alembic library

### apitube.py

APITube News Engine
================

Provides functionality to access news articles from over 350,000 verified sources using the APITube API.

#### Responsibilities

- Manages API interactions with external services.
- Retrieves the API key from environment variables (e.g., using os.environ).
- Handles API key retrieval from environment variables or configuration files.
- Implements asynchronous API calls using aiohttp.
- Logs API requests and responses for debugging and monitoring.
- Orchestrates data retrieval from APIs, including error handling and retry logic.
- Handles rate limiting and throttling to avoid exceeding API usage limits.
- Extends BaseEngine for common engine functionalities.
- Initializes an APITubeEngine object.
- Potentially supports retrieving API keys from configuration files or other secure storage mechanisms (future enhancement).
- Retrieves and stores the API key using _get_api_key.
- Handles cases where the API key is missing or invalid, raising appropriate exceptions or logging warnings.
- Configures the aiohttp client session.
- Sets up logging for API interactions.

#### Dependencies

- asyncio library
-  library
- aiohttp library

### financial_pipeline.py

No description available.

#### Responsibilities

- Apply transactions to the account balances.
- Check for untracked files in the repository.
- Parse transaction data into a usable format.
- Check for uncommitted changes in the repository.
- Process Mercury transactions.
- Report any missing or outdated Python packages.
- Handle transaction errors and inconsistencies.
- Automatically categorize transactions based on predefined rules.
- Potentially perform automated cleanup tasks (e.g., removing old temporary files).
- Provide a user interface for managing classification rules.
- Suggest actions to maintain repository integrity (e.g., commit changes).
- Ensure the ledger file conforms to the expected schema.
- Orchestrate the overall workflow of the script.
- Install missing Python packages using pip if possible.
- Ensure all declared accounts are valid and conform to the expected format.
- Verify required Python packages are installed.
- Check for the presence of necessary system tools (e.g., git).
- Potentially email or save generated reports.
- Verify data types of ledger entries.
- Potentially write processed transaction data to a database or other storage.
- Provide options for customizing report parameters (e.g., date range).
- Verify account declarations in the ledger file.
- Verify required dependencies are installed.
- Serve as the script's entry point.
- Use machine learning models or other algorithms for classification.
- Report any validation errors.
- Potentially train the classification model based on verified data.
- Run repository maintenance checks.
- Parse command-line arguments.
- Assign categories to transactions.
- Generate financial reports.
- Validate ledger file format.
- Present classified transactions to the user for review.
- Store classification results.
- Handle exceptions and errors.
- Perform interactive classification verification.
- Read transaction data from the ledger file.
- Run transaction classification steps.
- Calculate account balances and other financial metrics.
- Report any missing system dependencies.
- Call other functions to perform the necessary tasks.
- Report any invalid or missing account declarations.
- Create reports based on processed transaction data.
- Format reports in a human-readable format (e.g., PDF, CSV).
- Update classification rules based on user feedback.
- Log program execution and results.
- Check for syntax errors in the ledger file.
- Allow the user to correct misclassifications.
- Check for specific versions of Python packages if necessary.

#### Dependencies

- pathlib library
- datetime library
- subprocess library
- shutil library
- bin library

### port_cli.py

No description available.

#### Responsibilities

- Initialize the PortCLI object, handling dependencies like console and progress display.
- Handle errors and exceptions gracefully, providing informative messages to the user via the console.
- Provide a command-line interface for the Port Investment Research Platform, parsing user input and dispatching commands.
- Format and display data using rich text formatting for improved readability.
- Manage the application's lifecycle, including setup and teardown.

#### Dependencies

- asyncio library
- click library
- datetime library
- rich library

### tick_processor.py

Tick processor service for periodic updates.

#### Responsibilities

- Potentially manage a list of 'tickable' objects or functions to execute during each tick.
- Use datetime.datetime to track time.
- Start the asynchronous update process using asyncio.
- Calculate and track the time elapsed since the last tick.
- Handle exceptions and logging during the update process.
- Stop the asynchronous update process gracefully.
- Manage periodic updates based on a defined interval.

#### Dependencies

- asyncio library
- datetime library

### research_output_handler.py

Handles the formatting and saving of research workflow outputs.

    This class provides a consistent way to:
    - Generate metadata for research outputs
    - Format company analysis results
    - Save combined results to JSON files

    Output Format:
    {
        "meta": {
            "timestamp": "ISO-8601 timestamp",
            "version": "1.0",
            "type": "ethical_analysis"
        },
        "companies": [
            {
                "company_name": "Company name",
                "symbol": "Stock symbol",
                "primary_category": "Industry category",
                "current_criteria": "Analysis criteria",
                "analysis": {
                    "historical": { ... analysis results ... },
                    "evidence": {
                        "sources": [ ... search results ... ],
                        "query": "search query"
                    },
                    "categorization": {
                        "product_issues": [],
                        "conduct_issues": [],
                        "tags": [],
                        "patterns": {}
                    }
                },
                "metadata": {
                    "analysis_timestamp": "ISO-8601 timestamp",
                    "data_confidence": null,
                    "pattern_confidence": null
                }
            }
        ]
    }

    Example:
        >>> handler = ResearchOutputHandler(output_dir="data")
        >>> handler.save_research_output(results_by_company, companies_data)

#### Responsibilities

- Determines the appropriate file format and storage location based on configuration settings.
- Configures the output format and storage location.
- Applies specific formatting rules based on the type of analysis.
- Initializes the ResearchOutputHandler object with necessary dependencies (e.g., logging, file paths).
- Handles the creation, formatting, and persistence of research output.
- Orchestrates the process of saving research output, including metadata generation and data formatting.
- Handles potential conflicts or inconsistencies between data sources.
- Provides a consistent interface for accessing and manipulating research data.
- Combines results from different research sources or analyses.
- Ensures metadata is consistent and accurate.
- Saves data in JSON format to a specified file path.
- Handles error handling and logging during the saving process.
- Generates metadata for research output, including timestamps, data sources, and version information.
- Ensures data is presented in a user-friendly and easily parsable format.
- Handles potential errors during the saving process (e.g., file access issues).
- Saves research output to specified file formats (e.g., JSON) and locations.
- Ensures the combined results are accurate and representative of the overall research findings.
- Ensures the JSON data is properly formatted and valid.
- May include logic for automatically extracting metadata from research data.
- Formats company analysis data into a standardized structure.
- Sets up internal data structures for storing and managing research data.
- Manages the generation of metadata associated with research findings, including timestamps and data sources.

#### Dependencies

- pathlib library
- datetime library

### sec_filings_manager.py

No description available.

#### Responsibilities

- Returns cached filings if available and valid (e.g., not expired).
- Provides options to selectively clear specific filing types.
- Handles potential errors during data retrieval and caching.
- Potentially loads existing cache metadata during initialization (if implemented).
- Manages cache metadata to reflect cleared entries.
- Creates the cache directory if it doesn't exist.
- Retrieves cached SEC filings for a given company (ticker).
- Supports filtering cached filings by filing type (e.g., 10-K, 10-Q).
- Manages SEC filings data, including retrieval and storage.
- Provides methods to retrieve cached filings based on ticker and filing type.
- Initializes the SECFilingsManager with a specified cache directory.
- Clears the cache for a specific ticker or all tickers.
- Caches SEC filings to improve performance and reduce API calls.
- May trigger retrieval from SEC EDGAR if filings are not cached or are expired.
- Handles file system operations for removing cached files.
- Provides methods to clear cached filings for a specific ticker or all tickers, managing cache size.

#### Dependencies

- pandas library
- pathlib library
- datetime library
- __future__ library
- sec_edgar library

### analysis_tagging_workflow.py

Analysis Tagging Workflow
======================

Provides efficient workflows for tagging and summarizing company analysis data.
Optimizes for token usage and caching by using targeted JSON outputs.

#### Responsibilities

- Manages analysis tags.
- Guides the analysis process.
- Presents key findings.
- Manages the workflow for analysis tagging.
- Provides a user interface for manual tagging.
- Identifies causal relationships.
- Orchestrates the tagging process.
- Prioritizes strategic questions based on importance.
- Predicts future developments.
- Evaluates feasibility.
- r
- Analyzes opportunities.
- e
- Quantifies potential ROI.
- Provides a concise overview.
- Assesses the impact of events or changes.
- s
- p
- Predicts future impacts based on current trends.
- Identifies material trends.
- z
- Defines the scope of inquiry.
- Identifies potential benefits.
- f
- Assesses risks associated with opportunities.
- Visualizes trends using charts and graphs.
- I
- Categorizes data.
- a
-
- Stores and retrieves tags associated with analysis results.
- u
- P
- x
- Enforces tag naming conventions.
- y
- Calculates summary statistics (e.g., average, total).
- Formulates strategic questions.
- m
- h
- Formats summaries for different output formats (e.g., text, JSON).
- l
- Refines questions based on initial analysis results.
- Evaluates consequences.
- Filters trends based on specific criteria (e.g., industry, region).
- Ensures consistent tagging.
- Provides tag-related functionalities.
- Automates the tagging process where possible.
- i
- b
- Generates summaries of analyses.
- c
- n
- t
- Quantifies effects.
- Analyzes data patterns.
- o
- j
- .

#### Dependencies

- datetime library
- dataclasses library
- argparse library
- asyncio library
-  library

### ethical_analysis.py

Ethical Analysis Workflows.

Provides specialized workflows for ethical analysis using the DeepSeek engine.
Each workflow is designed to handle specific types of ethical analysis tasks.

#### Responsibilities

- Provides a user interface or API for interacting with the workflow and accessing results.
- Manages the overall ethical analysis process, including defining and executing analysis steps.
- May read templates from files or databases.
- Initializes the EthicalAnalysisWorkflow object, setting up initial state and configurations.
- May load configuration parameters from external sources.
- Initializes and loads templates used for generating reports, prompts, or other structured outputs.
- Handles template parsing and validation.
- Sets up logging and monitoring.
- Provides a mechanism for managing and updating templates.
- Handles error conditions and exceptions that may arise during the analysis process.
- Orchestrates the workflow by coordinating the execution of individual analysis components or engines (e.g., DeepSeek).
- Potentially initializes connections to data sources or external services.
- Stores, retrieves, and manages analysis data, potentially including intermediate results and final reports.

#### Dependencies

-  library

### tic_delta_workflow.py

TIC Delta Analysis Workflow.

Analyzes changes in TIC scores over time, focusing on material changes
that could affect our assessment of revenue-impact alignment.

#### Responsibilities

- May involve setting up placeholders for dynamic data insertion.
- Orchestrates the entire TIC delta analysis workflow.
- Loads and configures template files.
- Sets up initial state and configurations.
- Transforms raw data into a usable format.
- Filters and sorts research results based on relevance.
- Initializes an object, likely a class instance.
- Handles error handling and logging.
- May involve data enrichment or normalization.
- May calculate statistical measures of change.
- Queries a research database or API.
- Performs analysis on the delta (change) between two sets of TIC data.
- May establish database connections or load configuration files.
- Retrieves company data associated with the TIC changes.
- Retrieves recent research data related to the TIC changes.
- Queries a company database or API.
- Manages data retrieval, analysis, and reporting.
- Represents a change in TIC data.
- Retrieves TIC changes from a data source.
- May involve querying a database or API.
- Identifies significant changes and patterns.
- Handles data validation and error handling.
- Potentially interacts with a database to store results.
- Potentially stores information about the nature and magnitude of the change.
- Initializes templates used for reporting or analysis.

#### Dependencies

- dataclasses library
-  library
- datetime library
- sqlalchemy library

### tick_report.py

TICK Score Analysis Report.

Retrieves and analyzes top companies by TICK score from the database.

#### Responsibilities

- Extract relevant fields from the company data (e.g., company name, score, ranking, tick).
- Potentially include visual elements (e.g., charts, graphs) to enhance the presentation.
- Orchestrate the overall program execution.
- Handle potential database errors or connection issues.
- Handle cases where there are no top companies to display.
- Transform raw company data (likely from CompanyAnalysis objects) into a user-friendly format.
- Handle missing or invalid data gracefully.
- Call `get_top_companies_by_tick` to retrieve the top companies for a specific tick.
- Call `_format_company_data` to format the retrieved company data.
- Convert data types as needed (e.g., format numbers, dates).
- Potentially schedule the execution of the program at regular intervals.
- Handle exceptions and errors that may occur during program execution.
- Retrieve top companies from the database based on a given tick (timestamp or identifier).
- Call `display_top_companies` to display the formatted data to the user.
- Limit the results to the top N companies (where N is a configurable parameter).
- Potentially apply localization or internationalization formatting rules.
- Log program events and errors.
- Format the output for readability and clarity.
- Return a list of CompanyAnalysis objects or a suitable data structure representing the top companies.
- Log display events or errors.
- Order the results in descending order based on a relevant metric (e.g., score, ranking).
- Query the database using SQLAlchemy to fetch CompanyAnalysis records.
- Handle different output formats (e.g., plain text, HTML, JSON).
- Present the formatted top company data to the user (e.g., on the console, in a web page).
- Handle command-line arguments or user input to specify the tick or other parameters.
- Create a dictionary or other structured representation of the formatted company data.

#### Dependencies

- sqlalchemy library
-  library

### companies.py

No description available.

#### Responsibilities

- Stores the complete company response data, including metadata and historical data.
- Represents a simplified view of company information, excluding historical data.
- May aggregate data from CompanyMetadata and HistoricalDataPoint.
- Represents a data point's value and associated timestamp (likely datetime.datetime).
- Provides access to company metadata attributes.
- Stores data required for creating a new company record.
- Includes a list or collection of HistoricalDataPoint instances.
- Validates the input data against defined constraints (e.g., required fields, data types).
- Provides access to the data point's value and timestamp.
- Likely inherits from pydantic.BaseModel for data validation and serialization.
- Stores a single historical data point for a specific company metric (e.g., revenue, employee count).
- Represents the full information returned by the company retrieval endpoint.
- Represents the input data structure for the company creation endpoint.
- Stores core company metadata (e.g., name, industry, location).

#### Dependencies

- pydantic library
- datetime library
- fastapi library

### entity_analysis.py

No description available.

#### Responsibilities


#### Dependencies

- datetime library
- httpx library
- prefect library
- dotenv library
- asyncio library

### financial_analysis.py

No description available.

#### Responsibilities

- Retrieve the current stock universe from the database
- Handle potential data synchronization errors
- Return database connection objects
- Return the universe data in a usable format (e.g., list, dataframe)
- Orchestrate the overall workflow of the application
- Update the database with the latest universe information
- Store or report the analysis results
- Establish database connections to DuckDB
- Synchronize the current stock universe data from external sources
- Analyze changes in financial metrics for stocks in the universe
- Assess the impact of these events on stock prices or financial performance
- Potentially involve fetching data from APIs or files
- Potentially schedule the execution of the analysis
- Potentially use natural language processing (NLP) techniques
- Handle potential connection errors
- Analyze material events (e.g., news, filings) related to stocks in the universe
- Handle command-line arguments or configuration settings
- Call other functions to get database connections, synchronize the universe, and perform analysis
- Filter or transform the data as needed
- Identify significant changes or trends
- Log events and errors
- Potentially calculate financial ratios or indicators

#### Dependencies

- traceback library
- datetime library
- duckdb library

### ethical_analyzer.py

Analyzer for ethical considerations and controversies.

#### Responsibilities

- Creates tables if they don't exist.
- Ensures rclone is properly set up for S3 interaction.
- Generates analysis prompts and saves results.
- Constructs the prompt based on input data and analysis requirements.
- Handles potential errors during the overall synchronization process.
- Sets up the necessary database tables for storing analysis results.
- Handles potential database errors.
- Handles file transfer and potential errors during synchronization.
- Executes the main ethical analysis process.
- Logs the synchronization process.
- Writes the JSON data to a file.
- Orchestrates the synchronization of data to S3.
- Potentially uses templates or predefined structures for prompt generation.
- Orchestrates the ethical analysis process.
- Initializes the EthicalAnalyzer object.
- Saves the analysis results as a JSON file.
- Handles potential errors during the analysis process.
- Logs the progress and results of the analysis.
- Orchestrates the steps involved in the analysis, including data preparation, prompt generation, analysis execution, and result saving.
- Configures rclone for S3 synchronization.
- Formats the prompt for use with the analysis engine.
- Establishes a database connection.
- Sets up logging.
- Formats the analysis data into a JSON structure.
- Handles database interactions for storing analysis results.
- Handles potential errors during rclone configuration.
- Handles potential file writing errors.
- Calls _sync_file_to_s3 to perform the actual synchronization.
- Configures rclone using environment variables or provided parameters.
- Determines the data to be synchronized.
- Synchronizes a local file to an S3 bucket using rclone.
- Manages configuration and data synchronization.
- Ensures the database schema is compatible with the analysis process.
- Generates the prompt used for the ethical analysis.

#### Dependencies

- pandas library
- pathlib library
- datetime library
- subprocess library
- ethifinx library

### dashboard_generator.py

Script to generate dashboards for visualizing email processing insights.

Dependencies:
- SQLite database with processed contacts and opportunities
- pandas for data manipulation
- seaborn and matplotlib for visualization

#### Responsibilities

- Handles missing or invalid data gracefully
- Potentially integrates with a reporting system for automated distribution
- Returns data as a Pandas DataFrame
- Plots the distribution of a specified data series using Seaborn or Matplotlib
- Provides insights into the frequency and distribution of different opportunity types
- Plots the counts of detected business opportunities using Seaborn or Matplotlib
- Creates and saves visualizations for email processing insights
- Categorizes opportunities based on predefined criteria
- Handles potential database connection errors
- Saves the dashboard as an image or interactive HTML file
- Loads data from the database using DBConnector
- Allows customization of plot aesthetics (e.g., title, labels)
- Arranges plots into a coherent dashboard layout

#### Dependencies

- pandas library
- scripts library
- matplotlib library
- seaborn library

### sts_xml_parser.py

No description available.

#### Responsibilities

- Extracts the text content of a direct child element.
- Provides STS namespace-aware parsing functions for simplified element access.
- Returns the text content as a string, or None if the child element does not exist or has no text.
- Fetches the text content of the current STSElement node.
- Initializes an STSElement from an XML string.
- Finds all matching subelements based on a specified XPath-like expression.
- Finds the first matching subelement based on a specified XPath-like expression.
- Wraps a root element name and cElementTree.Element instance, providing a higher-level abstraction.
- Handles potential xml.etree.ElementTree.ParseError exceptions during parsing.
- Returns a list of matching STSElement instances.
- Handles potential XML parsing errors during string conversion.
- Returns the first matching STSElement instance or None if no match is found.
- Provides methods for navigating and extracting data from the XML structure.
- Acts as a constructor or factory method for STSElement instances.
- Parses STS-aware XML data, handling namespaces.
- Returns the text content as a string, or None if the element has no text.

#### Dependencies

- xml library

## Architectural Decisions
