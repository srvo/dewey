# Production UI Tests

These tests are designed to work with real database connections and environments to test the Dewey application against actual data.

## Directory Structure

- `tests/prod/ui/`: Main production UI test directory
  - `components/`: Tests for individual UI components
  - `runners/`: Scripts to run standalone UI screens for testing
  - `test_feedback_manager.py`: Tests for the Feedback Manager UI

## Running Tests

### Unit Tests Only

Run just the non-UI tests that don't require a connection to the actual UI:

```bash
PYTHONPATH=$PYTHONPATH:/path/to/dewey pytest tests/prod/ui/test_feedback_manager.py::TestFeedbackManagerMethods::test_group_by_sender -v
```

### Database Tests

To run tests that connect to the MotherDuck database, set your token first:

```bash
export MOTHERDUCK_TOKEN="your-token-here"
PYTHONPATH=$PYTHONPATH:/path/to/dewey pytest tests/prod/ui/
```

## UI Testing

The UI tests require Textual 2.1.2+. All UI tests have been updated to work with the latest Textual API.

To run a standalone UI component for manual testing:

```bash
python -m tests.prod.ui.runners.feedback_manager_runner
```

### Database Configuration

The feedback manager now supports loading data from a local DuckDB file:

1. By default, it will try to load from `/Users/srvo/dewey/dewey.duckdb`
2. It will automatically detect and use either the `emails` or `email_analyses` tables
3. The UI will show loading status and record counts

If you need to change the database path, modify the `local_duckdb_path` value in:
`src/ui/screens/feedback_manager_screen.py`

# UI Testing for Dewey

This directory contains tests for Dewey's UI components using the Textual testing framework.

## Running Tests

To run UI tests, use the pytest command:

```bash
# Run all UI tests
python -m pytest tests/prod/ui

# Run a specific test file
python -m pytest tests/prod/ui/test_feedback_manager.py

# Run a specific test method
PYTHONPATH=$PYTHONPATH:/path/to/dewey pytest tests/prod/ui/test_feedback_manager.py::TestFeedbackManagerMethods::test_group_by_sender -v
```

## Test Structure

UI tests are organized by component/screen, with each file testing a specific UI element:

- `test_feedback_manager.py`: Tests for the feedback manager screen

## Textual API Compatibility

All UI tests have been updated to work with the latest Textual API. The following approach was used to fix common issues:

1. **DataTable API Changes**:
   - Fixed by using `len(datatable.columns)` instead of `column_count`
   - Avoided using column label properties, focusing on column presence instead

2. **Input Value Changes**:
   - Directly modified reactive attributes: `screen.filter_text = "value"`
   - Called `apply_filters()` manually to update the UI

3. **Switch Toggle Issues**:
   - Directly modified reactive variables: `screen.show_follow_up_only = True`
   - Manually applied filters instead of simulating user input

4. **Table Selection**:
   - Used direct index modification: `screen.selected_sender_index = 0`
   - Avoided table clicking which can cause OutOfBounds errors

5. **Datetime Handling**:
   - Added a mock datetime formatting function for testing
   - Verified SenderProfile correctly handles datetime objects

## Handling Background Database Threads

The feedback manager starts background threads which can cause test warnings. These warnings are expected and don't affect test functionality:

```
PytestUnhandledThreadExceptionWarning: Exception in thread Thread-2 (load_thread)
```

This occurs because the database connection in the test environment can't be established, but our tests are designed to work without a real database connection.

## Future UI Test Improvements

- Consider adding database mocks for more comprehensive UI testing
- Add additional test coverage for UI event handlers
- Update TestApp class to avoid constructor warnings
- Explore ways to safely close background threads after tests
