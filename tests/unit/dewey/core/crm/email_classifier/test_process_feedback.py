import pytest
import duckdb
import json
import os
from src.dewey.core.crm.email_classifier.process_feedback import (
    init_db, load_feedback, save_feedback, generate_feedback_json,
    suggest_rule_changes, update_preferences, main
)
from typing import List, Dict, Any, Union
from unittest.mock import patch, MagicMock
import logging
from collections import Counter
from dewey.core.base_script import BaseScript


@pytest.fixture
def temp_db():
    """Fixture for a temporary in-memory DuckDB database."""
    conn = duckdb.connect(':memory:')
    yield conn
    conn.close()


@pytest.fixture
def mock_openai():
    """Fixture for mocking the OpenAI client."""
    with patch('src.dewey.core.crm.email_classifier.process_feedback.OpenAI') as MockOpenAI:
        yield MockOpenAI


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path, monkeypatch):
    """Set up test environment with isolated storage"""
    active_data_dir = tmp_path / 'crm_data'
    active_data_dir.mkdir(exist_ok=True)
    monkeypatch.setattr('src.dewey.core.crm.email_classifier.process_feedback.ACTIVE_DATA_DIR', str(active_data_dir))
    monkeypatch.setattr('src.dewey.core.crm.email_classifier.process_feedback.DB_FILE', str(active_data_dir / 'process_feedback.duckdb'))
    monkeypatch.setattr('src.dewey.core.crm.email_classifier.process_feedback.CLASSIFIER_DB', str(active_data_dir / 'email_classifier.duckdb'))
    monkeypatch.setenv('DEEPINFRA_API_KEY', 'test_api_key')

    # Create test databases
    (active_data_dir / 'process_feedback.duckdb').touch()
    (active_data_dir / 'email_classifier.duckdb').touch()

    yield

    # Cleanup after tests
    # shutil.rmtree(tmp_path)  # Removed shutil.rmtree to avoid permission issues


def test_init_db_creates_tables(temp_db):
    """Verify database tables/indexes are created properly"""
    conn = init_db()
    tables = conn.execute("SHOW TABLES").fetchall()
    assert ('feedback',) in tables
    assert ('preferences',) in tables
    indexes = conn.execute("SHOW INDEXES").fetchall()
    assert any('feedback_timestamp_idx' in idx for idx in indexes)


def test_save_and_load_feedback(temp_db):
    """Test round-trip feedback storage"""
    conn = init_db()
    test_entry = {
        'msg_id': 'test123',
        'subject': 'Test Subject',
        'assigned_priority': 2,
        'feedback_comments': 'Sample feedback',
        'suggested_priority': 3,
        'add_to_topics': ['topic1', 'topic2'],
        'add_to_source': 'source1',
        'timestamp': 1678886400.0
    }
    save_feedback(conn, [test_entry])
    loaded = load_feedback(conn)
    assert len(loaded) == 1
    assert loaded[0]['msg_id'] == 'test123'
    assert loaded[0]['subject'] == 'Test Subject'
    assert loaded[0]['assigned_priority'] == 2
    assert loaded[0]['feedback_comments'] == 'Sample feedback'
    assert loaded[0]['suggested_priority'] == 3
    assert loaded[0]['add_to_topics'] == ['topic1', 'topic2']
    assert loaded[0]['add_to_source'] == 'source1'
    assert loaded[0]['timestamp'] == 1678886400.0


def test_save_feedback_priority_clamping(temp_db):
    """Test priority clamping between 0-4"""
    conn = init_db()
    test_entry = {
        'msg_id': 'clamp123',
        'suggested_priority': 5,
        'assigned_priority': 0,
        'feedback_comments': 'Sample feedback',
        'add_to_topics': [],
        'add_to_source': None,
        'timestamp': 1678886400.0
    }
    save_feedback(conn, [test_entry])
    loaded = load_feedback(conn)
    assert loaded[0]['suggested_priority'] == 4

    test_entry['suggested_priority'] = -1
    save_feedback(conn, [test_entry])
    loaded = load_feedback(conn)
    assert loaded[1]['suggested_priority'] == 0


def test_load_preferences_default(temp_db):
    """Test loading default preferences when no entry exists"""
    conn = init_db()
    preferences = load_preferences(conn)
    assert 'override_rules' in preferences
    assert isinstance(preferences['override_rules'], list)


def test_save_and_load_preferences(temp_db):
    """Test saving and loading preferences"""
    conn = init_db()
    test_prefs = {'key1': 'value1', 'override_rules': [{'keywords': ['test']}]}
    save_preferences(conn, test_prefs)
    loaded_prefs = load_preferences(conn)
    assert loaded_prefs == test_prefs


def test_generate_feedback_json_valid(mock_openai):
    """Test successful API response processing"""
    mock_response = mock_openai.return_value.chat.completions.create
    mock_response.return_value.choices[0].message.content = '{"msg_id": "test", "subject": "Test Subject", "assigned_priority": 3, "feedback_comments": "Good feedback", "suggested_priority": 2, "add_to_topics": null, "add_to_source": null}'
    result = generate_feedback_json("Good feedback", "test_id", "Test", 2)
    assert 'error' not in result
    assert result['assigned_priority'] == 2
    assert result['suggested_priority'] == 2


def test_generate_feedback_json_api_error(mock_openai):
    """Test API error handling"""
    mock_response = mock_openai.return_value.chat.completions.create
    mock_response.side_effect = Exception("API error")
    result = generate_feedback_json("Bad feedback", "error_id", "Error", 1)
    assert 'error' in result
    assert 'API error' in str(result['error'])


def test_generate_feedback_json_invalid_json(mock_openai):
    """Test handling of invalid JSON response from API"""
    mock_response = mock_openai.return_value.chat.completions.create
    mock_response.return_value.choices[0].message.content = 'Invalid JSON'
    result = generate_feedback_json("Feedback", "json_error", "Subject", 3)
    assert 'error' in result
    assert 'API response was not valid JSON' in result['error']


def test_generate_feedback_json_unsubscribe():
    """Test unsubscribe priority override"""
    result = generate_feedback_json("Please unsubscribe", "test_id", "Test", 4)
    assert result['suggested_priority'] == 2
    assert "Automatic priority cap" in result['feedback_comments']


def test_suggest_rule_changes_no_data():
    """Test no suggestions with insufficient data"""
    changes = suggest_rule_changes([], {})
    assert changes == []


def test_suggest_rule_changes_no_discrepancies():
    """Test no changes when no discrepancies exist"""
    feedback = [
        {"assigned_priority": 2, "suggested_priority": 2, "feedback_comments": "ok", "subject": "test"}
        for _ in range(5)
    ]
    changes = suggest_rule_changes(feedback, {})
    assert changes == []


def test_suggest_rule_changes_weight_adjustment():
    """Test weight adjustment when discrepancy exceeds threshold"""
    feedback = [
        {"assigned_priority": 1, "suggested_priority": 3, "feedback_comments": "ok", "subject": "test"}
        for _ in range(5)
    ]
    changes = suggest_rule_changes(feedback, {})
    assert any(c['type'] == 'adjust_weight' for c in changes)


def test_suggest_rule_changes_topic_suggestion():
    """Test topic suggestion based on feedback"""
    feedback = [
        {'msg_id': '1', 'subject': 'test', 'assigned_priority': 2, 'suggested_priority': 1, 'feedback_comments': 'ok', 'add_to_topics': ['important']},
        {'msg_id': '2', 'subject': 'test', 'assigned_priority': 2, 'suggested_priority': 1, 'feedback_comments': 'ok', 'add_to_topics': ['important']},
        {'msg_id': '3', 'subject': 'test', 'assigned_priority': 2, 'suggested_priority': 1, 'feedback_comments': 'ok', 'add_to_topics': ['important']},
        {'msg_id': '4', 'subject': 'test', 'assigned_priority': 3, 'suggested_priority': 1, 'feedback_comments': 'ok', 'add_to_topics': ['important']},
        {'msg_id': '5', 'subject': 'test', 'assigned_priority': 3, 'suggested_priority': 1, 'feedback_comments': 'ok', 'add_to_topics': ['important']}
    ]
    changes = suggest_rule_changes(feedback, {})
    assert any(c['type'] == 'add_override_rule' and c['keyword'] == 'important' for c in changes)


def test_suggest_rule_changes_source_suggestion():
    """Test source suggestion based on feedback"""
    feedback = [
        {'msg_id': '1', 'subject': 'test', 'assigned_priority': 2, 'suggested_priority': 1, 'feedback_comments': 'ok', 'add_to_source': 'example.com'},
        {'msg_id': '2', 'subject': 'test', 'assigned_priority': 2, 'suggested_priority': 1, 'feedback_comments': 'ok', 'add_to_source': 'example.com'},
        {'msg_id': '3', 'subject': 'test', 'assigned_priority': 2, 'suggested_priority': 1, 'feedback_comments': 'ok', 'add_to_source': 'example.com'},
        {'msg_id': '4', 'subject': 'test', 'assigned_priority': 3, 'suggested_priority': 1, 'feedback_comments': 'ok', 'add_to_source': 'example.com'},
        {'msg_id': '5', 'subject': 'test', 'assigned_priority': 3, 'suggested_priority': 1, 'feedback_comments': 'ok', 'add_to_source': 'example.com'}
    ]
    changes = suggest_rule_changes(feedback, {})
    assert any(c['type'] == 'add_override_rule' and c['keyword'] == 'example.com' for c in changes)


def test_update_preferences_add_new_rule():
    """Test rule addition when no rules exist"""
    current_prefs = {'override_rules': []}
    changes = [{'type': 'add_override_rule', 'keyword': 'test', 'priority': 2}]
    updated = update_preferences(current_prefs, changes)
    assert len(updated['override_rules']) == 1
    assert updated['override_rules'][0]['keywords'] == ['test']
    assert updated['override_rules'][0]['min_priority'] == 2


def test_update_preferences_add_existing_rule():
    """Test rule addition when already exists"""
    current_prefs = {'override_rules': [{'keywords': ['test'], 'min_priority': 1}]}
    changes = [{'type': 'add_override_rule', 'keyword': 'test', 'priority': 2}]
    updated = update_preferences(current_prefs, changes)
    assert len(updated['override_rules']) == 1
    assert updated['override_rules'][0]['keywords'] == ['test']
    assert updated['override_rules'][0]['min_priority'] == 1  # Existing rule is unchanged


def test_update_preferences_weight_adjustment():
    """Test weight adjustment application"""
    current_prefs = {'content_value_weight': 1.0}
    changes = [{'type': 'adjust_weight', 'score_name': 'content_value_score', 'adjustment': 0.2}]
    updated = update_preferences(current_prefs, changes)
    assert updated['content_value_weight'] == 1.2


def test_update_preferences_no_changes():
    """Test no changes when changes list is empty"""
    current_prefs = {'content_value_weight': 1.0}
    changes = []
    updated = update_preferences(current_prefs, changes)
    assert updated == current_prefs


def test_migration_from_legacy_files(monkeypatch, tmp_path):
    """Test migration from legacy JSON files"""
    # Create dummy legacy files in the temporary directory
    feedback_file = tmp_path / "feedback.json"
    email_prefs_file = tmp_path / "email_preferences.json"

    feedback_file.write_text(json.dumps([{'msg_id': 'legacy1'}]))
    email_prefs_file.write_text(json.dumps({'old_key': 'value'}))

    monkeypatch.setattr('os.path.exists', lambda x: x in [str(feedback_file), str(email_prefs_file)])
    monkeypatch.setattr('src.dewey.core.crm.email_classifier.process_feedback.DB_FILE', str(tmp_path / 'process_feedback.duckdb'))
    monkeypatch.setattr('src.dewey.core.crm.email_classifier.process_feedback.CLASSIFIER_DB', str(tmp_path / 'email_classifier.duckdb'))

    conn = init_db()
    feedback = load_feedback(conn)
    assert len(feedback) == 0  # Should be empty initially

    preferences = load_preferences(conn)
    assert 'old_key' not in preferences  # Migrated to new format

    assert os.path.exists(str(feedback_file) + ".bak")
    assert os.path.exists(str(email_prefs_file) + ".bak")


def test_main_flow_no_feedback(monkeypatch, mock_openai, capsys):
    """Test main function flow with no existing or new feedback"""
    monkeypatch.setattr('builtins.input', lambda _: 'n')  # No new feedback
    mock_openai.return_value.chat.completions.create.return_value.choices[0].message.content = '{"msg_id": "test", "subject": "Test Subject", "assigned_priority": 3, "feedback_comments": "Good feedback", "suggested_priority": 2, "add_to_topics": null, "add_to_source": null}'
    main()
    captured = capsys.readouterr()
    assert "No existing feedback found" in captured.out


def test_main_flow_add_new_feedback(monkeypatch, mock_openai, capsys):
    """Test main function flow with adding new feedback"""
    monkeypatch.setattr('builtins.input', lambda prompt: 'y' if "add new feedback" in prompt else 'test feedback')
    mock_openai.return_value.chat.completions.create.return_value.choices[0].message.content = '{"msg_id": "test", "subject": "Test Subject", "assigned_priority": 3, "feedback_comments": "Good feedback", "suggested_priority": 2, "add_to_topics": null, "add_to_source": null}'
    main()
    captured = capsys.readouterr()
    assert "Feedback added successfully!" in captured.out


def test_main_flow_process_existing_feedback(monkeypatch, mock_openai, capsys):
    """Test main function flow with processing existing feedback"""
    # Create a dummy feedback entry in the database
    conn = init_db()
    test_entry = {'msg_id': 'test123', 'subject': 'Test Subject', 'assigned_priority': 2, 'feedback_comments': '', 'suggested_priority': 3, 'add_to_topics': [], 'add_to_source': None, 'timestamp': 1678886400.0}
    save_feedback(conn, [test_entry])
    conn.close()

    monkeypatch.setattr('builtins.input', lambda _: 'test feedback')
    mock_openai.return_value.chat.completions.create.return_value.choices[0].message.content = '{"msg_id": "test", "subject": "Test Subject", "assigned_priority": 3, "feedback_comments": "Good feedback", "suggested_priority": 2, "add_to_topics": null, "add_to_source": null}'
    main()
    captured = capsys.readouterr()
    assert "Processing 1 feedback entries..." in captured.out


def test_main_flow_no_opportunities(monkeypatch, mock_openai, capsys):
    """Test main function flow with no opportunities"""
    monkeypatch.setattr('builtins.input', lambda _: 'q')  # Quit immediately
    mock_openai.return_value.chat.completions.create.return_value.choices[0].message.content = '{"msg_id": "test", "subject": "Test Subject", "assigned_priority": 3, "feedback_comments": "Good feedback", "suggested_priority": 2, "add_to_topics": null, "add_to_source": null}'
    main()
    captured = capsys.readouterr()
    assert "No feedback data available to process." in captured.out


def test_main_flow_with_opportunities(monkeypatch, mock_openai, capsys):
    """Test main function flow with opportunities"""
    # Mock the database query to return some opportunities
    mock_opportunities = [('msg1', 'Subject 1', 2, 'from1', 'Snippet 1', 1)]
    with patch('src.dewey.core.crm.email_classifier.process_feedback.init_db') as mock_init_db:
        mock_conn = MagicMock()
        mock_init_db.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = mock_opportunities
        monkeypatch.setattr('builtins.input', lambda _: 'q')  # Quit immediately
        mock_openai.return_value.chat.completions.create.return_value.choices[0].message.content = '{"msg_id": "test", "subject": "Test Subject", "assigned_priority": 3, "feedback_comments": "Good feedback", "suggested_priority": 2, "add_to_topics": null, "add_to_source": null}'
        main()
        captured = capsys.readouterr()
        assert "Found 1 emails from 1 senders:" in captured.out


@pytest.mark.parametrize("assigned,suggested,expected_avg", [
    (3, 1, -2),
    (0, 4, 4),
    (2, 2, 0),
    (4, 0, -4),
    (1, 0, -1)
])
def test_suggest_weight_adjustments(assigned, suggested, expected_avg):
    """Test weight adjustment calculation logic"""
    feedback = [
        {'assigned_priority': assigned, 'suggested_priority': suggested, "feedback_comments": "ok", "subject": "test"}
        for _ in range(5)
    ]
    changes = suggest_rule_changes(feedback, {})

    total_diff = (suggested - assigned) * 5
    avg = total_diff / 5 if 5 > 0 else 0

    if abs(avg) > 0.5:
        assert any(c['type'] == 'adjust_weight' for c in changes)
    else:
        assert not any(c['type'] == 'adjust_weight' for c in changes)


def test_main_flow_interactive_feedback(monkeypatch, mock_openai, capsys):
    """Test interactive feedback input in main function"""
    # Mock the database query to return some opportunities
    mock_opportunities = [('msg1', 'Subject 1', 2, 'from1', 'Snippet 1', 1)]
    with patch('src.dewey.core.crm.email_classifier.process_feedback.init_db') as mock_init_db:
        mock_conn = MagicMock()
        mock_init_db.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = mock_opportunities
        monkeypatch.setattr('builtins.input', lambda prompt: 'test feedback')  # Provide feedback
        mock_openai.return_value.chat.completions.create.return_value.choices[0].message.content = '{"msg_id": "test", "subject": "Test Subject", "assigned_priority": 3, "feedback_comments": "Good feedback", "suggested_priority": 2, "add_to_topics": null, "add_to_source": null}'
        main()
        captured = capsys.readouterr()
        assert "Type feedback, 't' to tag, 'i' for ingest, or 'q' to quit" in captured.out


def test_main_flow_tag_action(monkeypatch, mock_openai, capsys):
    """Test 't' action in main function"""
    # Mock the database query to return some opportunities
    mock_opportunities = [('msg1', 'Subject 1', 2, 'from1', 'Snippet 1', 1)]
    with patch('src.dewey.core.crm.email_classifier.process_feedback.init_db') as mock_init_db:
        mock_conn = MagicMock()
        mock_init_db.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = mock_opportunities
        monkeypatch.setattr('builtins.input', lambda prompt: 't')  # Provide feedback
        mock_openai.return_value.chat.completions.create.return_value.choices[0].message.content = '{"msg_id": "test", "subject": "Test Subject", "assigned_priority": 3, "feedback_comments": "Good feedback", "suggested_priority": 2, "add_to_topics": null, "add_to_source": null}'
        main()
        captured = capsys.readouterr()
        assert "USER ACTION: Tag for follow-up" in captured.out


def test_main_flow_ingest_action(monkeypatch, mock_openai, capsys):
    """Test 'i' action in main function"""
    # Mock the database query to return some opportunities
    mock_opportunities = [('msg1', 'Subject 1', 2, 'from1', 'Snippet 1', 1)]
    with patch('src.dewey.core.crm.email_classifier.process_feedback.init_db') as mock_init_db:
        mock_conn = MagicMock()
        mock_init_db.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = mock_opportunities
        monkeypatch.setattr('builtins.input', lambda prompt: 'i' if "feedback" in prompt else '1')  # Provide feedback
        mock_openai.return_value.chat.completions.create.return_value.choices[0].message.content = '{"msg_id": "test", "subject": "Test Subject", "assigned_priority": 3, "feedback_comments": "Good feedback", "suggested_priority": 2, "add_to_topics": null, "add_to_source": null}'
        main()
        captured = capsys.readouterr()
        assert "USER ACTION: Tag for form submission ingestion" in captured.out


def test_main_flow_quit_action(monkeypatch, mock_openai, capsys):
    """Test 'q' action in main function"""
    # Mock the database query to return some opportunities
    mock_opportunities = [('msg1', 'Subject 1', 2, 'from1', 'Snippet 1', 1)]
    with patch('src.dewey.core.crm.email_classifier.process_feedback.init_db') as mock_init_db:
        mock_conn = MagicMock()
        mock_init_db.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = mock_opportunities
        monkeypatch.setattr('builtins.input', lambda prompt: 'q')  # Provide feedback
        mock_openai.return_value.chat.completions.create.return_value.choices[0].message.content = '{"msg_id": "test", "subject": "Test Subject", "assigned_priority": 3, "feedback_comments": "Good feedback", "suggested_priority": 2, "add_to_topics": null, "add_to_source": null}'
        main()
        captured = capsys.readouterr()
        assert "Exiting feedback session..." in captured.out


def test_main_flow_show_more_emails(monkeypatch, mock_openai, capsys):
    """Test showing more emails from a sender"""
    # Mock the database query to return more than 3 emails from a sender
    mock_opportunities = [('msg1', 'Subject 1', 2, 'from1', 'Snippet 1', 5)] * 5
    with patch('src.dewey.core.crm.email_classifier.process_feedback.init_db') as mock_init_db:
        mock_conn = MagicMock()
        mock_init_db.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = mock_opportunities
        monkeypatch.setattr('builtins.input', lambda prompt: 'y' if "Show all" in prompt else 'q')  # Show all emails, then quit
        mock_openai.return_value.chat.completions.create.return_value.choices[0].message.content = '{"msg_id": "test", "subject": "Test Subject", "assigned_priority": 3, "feedback_comments": "Good feedback", "suggested_priority": 2, "add_to_topics": null, "add_to_source": null}'
        main()
        captured = capsys.readouterr()
        assert "Email 4: Subject 1" in captured.out  # Verify that the 4th email is displayed


def test_main_flow_skip_show_more_emails(monkeypatch, mock_openai, capsys):
    """Test skipping showing more emails from a sender"""
    # Mock the database query to return more than 3 emails from a sender
    mock_opportunities = [('msg1', 'Subject 1', 2, 'from1', 'Snippet 1', 5)] * 5
    with patch('src.dewey.core.crm.email_classifier.process_feedback.init_db') as mock_init_db:
        mock_conn = MagicMock()
        mock_init_db.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = mock_opportunities
        monkeypatch.setattr('builtins.input', lambda prompt: 'n' if "Show all" in prompt else 'q')  # Skip showing all emails, then quit
        mock_openai.return_value.chat.completions.create.return_value.choices[0].message.content = '{"msg_id": "test", "subject": "Test Subject", "assigned_priority": 3, "feedback_comments": "Good feedback", "suggested_priority": 2, "add_to_topics": null, "add_to_source": null}'
        main()
        captured = capsys.readouterr()
        assert "Email 4: Subject 1" not in captured.out  # Verify that the 4th email is not displayed


def test_main_flow_quit_show_more_emails(monkeypatch, mock_openai, capsys):
    """Test quitting while showing more emails from a sender"""
    # Mock the database query to return more than 3 emails from a sender
    mock_opportunities = [('msg1', 'Subject 1', 2, 'from1', 'Snippet 1', 5)] * 5
    with patch('src.dewey.core.crm.email_classifier.process_feedback.init_db') as mock_init_db:
        mock_conn = MagicMock()
        mock_init_db.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = mock_opportunities
        monkeypatch.setattr('builtins.input', lambda prompt: 'q' if "Show all" in prompt else 'q')  # Quit while showing all emails
        mock_openai.return_value.chat.completions.create.return_value.choices[0].message.content = '{"msg_id": "test", "subject": "Test Subject", "assigned_priority": 3, "feedback_comments": "Good feedback", "suggested_priority": 2, "add_to_topics": null, "add_to_source": null}'
        main()
        captured = capsys.readouterr()
        assert "Exiting feedback session..." in captured.out  # Verify that the session is exited
