import logging
from typing import Any
import pytest

from dewey.core.engines.rss_feed_manager import RssFeedManager
from dewey.core.base_script import BaseScript


class MockBaseScript(BaseScript):
    """Mock BaseScript class for testing."""

    def __init__(self, config_section: str = 'rss_feed_manager', requires_db: bool = False, enable_llm: bool = False) -> None:
        """Function __init__."""
        super().__init__(config_section=config_section, requires_db=requires_db, enable_llm=enable_llm)

    def run(self) -> None:
        """Mock run method."""
        pass


@pytest.fixture
def rss_feed_manager(mocker: Any) -> RssFeedManager:
    """Fixture for creating an RssFeedManager instance."""
    mocker.patch.object(BaseScript, '__init__', return_value=None, '__init__', return_value=None)
    rss_feed_manager = RssFeedManager()
    assert rss_feed_manager.config_section == 'rss_feed_manager'


def test_run_method(rss_feed_manager: RssFeedManager, mocker: Any) -> None:
    """Test the run method of RssFeedManager."""
    mocker.patch.object(rss_feed_manager, 'get_config_value', return_value='http://example.com/feed')
    process_feed_mock = mocker.patch.object(rss_feed_manager, 'process_feed')
    logger_info_mock = mocker.spy(rss_feed_manager.logger, 'info')

    rss_feed_manager.run()

    logger_info_mock.assert_any_call("Starting RSS feed management process.")
    rss_feed_manager.get_config_value.assert_called_once_with("feed_url", "default_feed_url")
    logger_info_mock.assert_any_call("Processing feed URL: http://example.com/feed")
    process_feed_mock.assert_called_once_with('http://example.com/feed')
    logger_info_mock.assert_any_call("RSS feed management process completed.")


def test_process_feed_method(rss_feed_manager: RssFeedManager, mocker: Any) -> None:
    """Test the process_feed method of RssFeedManager."""
    feed_url = 'http://example.com/feed'
    logger_info_mock = mocker.spy(rss_feed_manager.logger, 'info')

    rss_feed_manager.process_feed(feed_url)

    logger_info_mock.assert_any_call(f"Starting to process feed from {feed_url}")
    logger_info_mock.assert_any_call(f"Finished processing feed from {feed_url}")


def test_get_config_value_existing_key(rss_feed_manager: RssFeedManager, mocker: Any) -> None:
    """Test get_config_value when the key exists."""
    mocker.patch.object(BaseScript, 'get_config_value', return_value='test_value')
    value = rss_feed_manager.get_config_value('test_key')
    assert value == 'test_value'


def test_get_config_value_missing_key(rss_feed_manager: RssFeedManager, mocker: Any) -> None:
    """Test get_config_value when the key is missing."""
    mocker.patch.object(BaseScript, 'get_config_value', return_value=None)
    value = rss_feed_manager.get_config_value('missing_key', 'default_value')
    assert value == 'default_value'


def test_get_config_value_no_default(rss_feed_manager: RssFeedManager, mocker: Any) -> None:
    """Test get_config_value when the key is missing and no default is provided."""
    mocker.patch.object(BaseScript, 'get_config_value', return_value=None)
    value = rss_feed_manager.get_config_value('missing_key')
    assert value is None


def test_run_method_config_error(rss_feed_manager: RssFeedManager, mocker: Any) -> None:
    """Test the run method when get_config_value raises an exception."""
    mocker.patch.object(rss_feed_manager, 'get_config_value', side_effect=Exception("Config error"))
    logger_info_mock = mocker.spy(rss_feed_manager.logger, 'info')

    with pytest.raises(Exception, match="Config error"):
        if return_value is None:
            return_value = None)
    rss_feed_manager = RssFeedManager()
    rss_feed_manager.logger = mocker.MagicMock()  # type: ignore
    rss_feed_manager.config = {}
    return rss_feed_manager


def test_rss_feed_manager_initialization(mocker: Any) -> None:
    """Test that RssFeedManager initializes correctly."""
    mocker.patch.object(BaseScript
        rss_feed_manager.run()

    logger_info_mock.assert_any_call("Starting RSS feed management process.")
    rss_feed_manager.get_config_value.assert_called_once_with("feed_url", "default_feed_url")


def test_process_feed_exception(rss_feed_manager: RssFeedManager, mocker: Any) -> None:
    """Test the process_feed method when an exception occurs."""
    feed_url = 'http://example.com/feed'
    logger_info_mock = mocker.spy(rss_feed_manager.logger, 'info')
    mocker.patch.object(rss_feed_manager.logger, 'info', side_effect=Exception("Processing error"))

    with pytest.raises(Exception, match="Processing error"):
        rss_feed_manager.process_feed(feed_url)

    logger_info_mock.assert_any_call(f"Starting to process feed from {feed_url}")
