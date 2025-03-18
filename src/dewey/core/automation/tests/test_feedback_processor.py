import pytest
import duckdb
import time
import json
from unittest.mock import patch, MagicMock
from contextlib import contextmanager
from src.dewey.core.automation.feedback_processor import (
    init_db,
    load_feedback,
    save_feedback,
    generate_feedback_json,
    suggest_rule_changes,
    update_preferences,
    save_preferences
)

@contextmanager
def temporary_database():
    conn = duckdb.connect(':memory:')
    try:
        yield conn
    finally:
        conn.close()

@pytest.fixture
def db_conn():
    with temporary_database() as conn:
        init_db(conn)  # Initialize schema
        yield conn

def test_init_db_creates_tables(db_conn):
    """Verify tables and indexes are created properly"""
    tables = db_conn.execute("SHOW TABLES").fetchall()
    assert ('feedback' in tables) and ('preferences' in tables)
    indexes = db_conn.execute("SHOW INDEXES ON feedback").fetchall()
    assert len(indexes) >= 1

def test_load_feedback_empty(db_conn):
    """Test loading from empty database"""
    assert load_feedback(db_conn) == []

def test_save_feedback_clamps_priority(db_conn):
    """Verify priority clamping between 0-4"""
    entry = {
        'msg_id': 'test1',
        'assigned_priority': 5,
        'suggested_priority': 6
    }
    save_feedback(db_conn, [entry])
    result = load_feedback(db_conn)
    assert result[0]['suggested_priority'] == 4

def test_generate_feedback_json_unsubscribe():
    """Test automatic priority cap for unsubscribe mentions"""
    result = generate_feedback_json(
        feedback_text="Unsubscribe me please",
        msg_id="test_id",
        subject="Test",
        assigned_priority=3
    )
    assert result['suggested_priority'] == 2
    assert "priority cap" in result['feedback_comments']

@patch('openai.ChatCompletion.create')
def test_generate_feedback_json_api_success(mock_api):
    """Test successful API response parsing"""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        '{"msg_id":"test","subject":"Test","assigned_priority":3'
        ',"feedback_comments":"Sample","suggested_priority":2'
        ',"add_to_topics":null,"add_to_source":null'
        f',"timestamp":{time.time()}}}'
    )
    mock_api.return_value = mock_response

    result = generate_feedback_json(
        "Valid feedback",
        "test_id",
        "Test Subject",
        3
    )
    assert result['msg_id'] == 'test'
    assert 'error' not in result

@patch('openai.ChatCompletion.create')
def test_generate_feedback_json_api_error(mock_api):
    """Test invalid JSON response handling"""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "<html>Not Found</html>"
    mock_api.return_value = mock_response

    result = generate_feedback_json(
        "Invalid response",
        "test_id",
        "Test",
        3
    )
    assert 'error' in result
    assert 'HTML error' in result['error']

def test_suggest_rule_changes_min_data():
    """Test insufficient data returns empty suggestions"""
    changes = suggest_rule_changes([], {})
    assert changes == []

def test_update_preferences_add_rule():
    """Test adding new override rule"""
    changes = [{'type':'add_override_rule','keyword':'test','priority':2}]
    updated = update_preferences({'override_rules':[]}, changes)
    assert any('test' in r['keywords'] for r in updated['override_rules'])

def test_suggest_rule_changes_discrepancies():
    """Test discrepancy analysis triggers suggestions"""
    feedback = [
        {'assigned_priority':1, 'suggested_priority':3, 'add_to_topics':['topic1']},
        {'assigned_priority':1, 'suggested_priority':3, 'add_to_topics':['topic1']},
        {'assigned_priority':1, 'suggested_priority':3, 'add_to_topics':['topic1']}
    ]
    changes = suggest_rule_changes(feedback, {})
    assert any(c['keyword']=='topic1' for c in changes)

@pytest.mark.parametrize("discrepancy_sum,expected", [
    (2.5, 'content_value_score'),
    (-1.5, 'automation_score')
])
def test_suggest_weight_adjustments(discrepancy_sum, expected):
    """Test weight adjustment suggestions"""
    with patch('builtins.print'):
        changes = suggest_rule_changes([
            {'assigned_priority':0, 'suggested_priority':2}
        ], {})
    assert any(c['score_name'] == expected for c in changes)

def test_save_preferences(db_conn):
    """Verify preferences storage"""
    preferences = {'test_key': 'test_value'}
    save_preferences(db_conn, preferences)
    stored = db_conn.execute("SELECT config FROM preferences").fetchone()[0]
    assert json.loads(stored) == preferences
