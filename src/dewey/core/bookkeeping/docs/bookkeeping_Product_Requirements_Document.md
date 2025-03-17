# Product Requirements Document



## Executive Summary

{'executive_summary': {'overview': 'This project encompasses a suite of tools designed to automate and improve financial transaction processing, categorization, and validation. The goal is to streamline accounting workflows, ensure data accuracy, and provide forecasting capabilities.', 'architecture': 'The architecture is component-based, with individual modules responsible for specific tasks such as data validation, classification, journal entry management, and rule conversion. No specific architectural patterns were identified in the provided data.', 'components': 'Key components include: `deferred_revenue.py` (processes Altruist income), `journal_writer.py` (manages journal file writing), `duplicate_checker.py` (identifies duplicate ledger files), `mercury_data_validator.py` (validates Mercury CSV data), `classification_engine.py` (classifies data using AI and rules), `forecast_generator.py` (generates financial forecasts), `journal_fixer.py` (corrects journal entries), `journal_splitter.py` (splits journal files), `auto_categorize.py` (automatically categorizes transactions), `transaction_categorizer.py` (categorizes transactions in journal files), `rules_converter.py` (converts classification rules), `ledger_checker.py` (validates hledger format), `hledger_utils.py` (provides hledger utilities), and `transaction_verifier.py` (verifies transactions interactively). These components interact to process, validate, and categorize financial data, ultimately generating journal entries and forecasts.', 'issues': 'No critical issues were explicitly identified in the provided data.', 'next_steps': 'Next steps include: (1) Thoroughly test each component individually and in integration. (2) Document component interactions and data flows. (3) Address any performance bottlenecks identified during testing. (4) Implement a robust error handling and logging strategy. (5) Consider incorporating user feedback mechanisms to improve classification accuracy and overall usability.'}}

## Components

### deferred_revenue.py

No description available.

#### Responsibilities

- Update the journal file with new transactions.
- Find Altruist income transactions in journal content.
- Recognize and process Altruist income in a journal file.
- Generate deferred revenue and fee income transactions.
- Generate fee income and deferred revenue entries.

#### Dependencies

- re library
- dateutil library
- datetime library

### journal_writer.py

No description available.

#### Responsibilities

- Manage journal file writing.
- Write journal entries to files.
- Signal journal writing failures.
- Generate classification quality metrics.

#### Dependencies

- collections library
- shutil library
- logging.py for config functionality
- pathlib library
- datetime library

### duplicate_checker.py

No description available.

#### Responsibilities

- Group filepaths by hash
- Calculate file hashes
- Find ledger files
- Check for duplicate ledger files

#### Dependencies

- hashlib library
- fnmatch library

### mercury_data_validator.py

No description available.

#### Responsibilities

- Validate and normalize a single transaction row.
- Normalize transaction data.
- Raise exceptions for invalid data.
- Signal invalid transaction data.
- Validate raw transaction data from Mercury CSV files.

#### Dependencies

- re library
- datetime library

### classification_engine.py

Exception for classification failures.

#### Responsibilities

- Parse data using AI
- Return available categories
- Load classification rules
- Export classification rules to Paisa template format
- Export classification rules to hledger format
- Classify data into categories
- Load classification rules from a source
- Represent a classification error
- Classify data based on rules
- Initialize an object
- Validate a category
- Compile patterns for rule matching
- Save classification overrides
- Process user feedback on classifications
- Parse user feedback

#### Dependencies

- fnmatch library
- src library
- bin library
- re library
- pathlib library
- datetime library

### forecast_generator.py

No description available.

#### Responsibilities

- Create the acquisition journal entry
- Append the acquisition entry to the ledger file
- Initializes the forecast ledger file
- Validates key assumptions with user input
- Create a depreciation journal entry
- Generates journal entries and appends them to journal files
- Creates revenue-related journal entries

#### Dependencies

- __future__ library
- logging.py for config functionality
- dateutil library
- argparse library
- pathlib library
- datetime library

### journal_fixer.py

No description available.

#### Responsibilities

- Parse a single transaction from a list of lines.
- Process transactions and return fixed journal content.
- Process all journal files.
- Parse transactions from journal content.
- Process a journal file and fix all transactions.

#### Dependencies

- logging.py for config functionality
- re library
- shutil library

### journal_splitter.py

No description available.

#### Responsibilities

- Process all journal files
- Split journal file by year

#### Dependencies

- pathlib library

### auto_categorize.py

Load classification rules from JSON files.

#### Responsibilities

- Serialize transactions
- Load classification rules
- Process transactions
- Parse journal entries
- Write journal file
- Execute the main program logic

#### Dependencies

- shutil library
- fnmatch library
- load_config.py for config functionality
- logging  # Centralized logging.py for config functionality
- re library
- pathlib library

### transaction_categorizer.py

No description available.

#### Responsibilities

- Process journal files organized by year within a base directory.
- Process all journal files.
- Load classification rules from a JSON file.
- Classify a transaction based on provided rules.
- Process a journal file and categorize transactions.
- Create a backup of a journal file.

#### Dependencies

- shutil library
- re library
- pathlib library

### rules_converter.py

No description available.

#### Responsibilities

- Standardize category strings
- Generate a JSON file with classification rules
- Extract classification patterns from a rules file
- Find transaction examples for classification patterns
- Orchestrate rule parsing, analysis, and generation

#### Dependencies

- re library
- pathlib library

### ledger_checker.py

No description available.

#### Responsibilities

- Performs basic hledger format checks.
- Reads a journal file.
- Orchestrates all format checks.

#### Dependencies


### hledger_utils.py

No description available.

#### Responsibilities

- Execute the main program logic.
- Retrieve account balance at a specific date.
- Update opening balances in the journal file.

#### Dependencies

- subprocess library
- re library
- pathlib library
- datetime library

### transaction_verifier.py

No description available.

#### Responsibilities

- Run interactive verification workflow.
- Get sample transactions.
- Get AI classification suggestions.

#### Dependencies

- duckdb library
- prompt_toolkit library
- subprocess library
- src library
- dotenv library
- pathlib library

## Architectural Decisions

