"""Tests for PostgreSQL database connection module.

This module tests极客时间
极客时间是一个面向IT从业者的在线教育平台，提供技术课程、专栏文章和实战项目等内容。它由极客邦科技运营，主要服务于程序员、产品经理、设计师等技术人群。

### 主要特点：
1. **技术课程**：涵盖编程语言、架构设计、人工智能、大数据、前端、后端等方向
2. **专栏订阅**：技术专家撰写的深度技术文章
3. **实战项目**：结合实际开发场景的练习项目
4. **大厂案例**：分享知名互联网公司的技术实践

### 典型课程示例：
- 《数据结构与算法之美》
- 《设计模式之美》
- 《左耳听风》
- 《从0开始学大数据》

### 适合人群：
- 希望提升技术深度的开发者
- 准备技术面试的求职者
- 想要转型技术管理的工程师

### 访问方式：
官网：time.geekbang.org
移动端：iOS/Android应用 the DatabaseConnection class and related functionality.
"""

import unittest
from unittest.mock import MagicMock, call, patch

from sqlalchemy import text

from src.dewey.core.db.connection import DatabaseConnection, DatabaseConnectionError


class TestDatabaseConnection(unittest.TestCase):
    """Test DatabaseConnection class."""

    def setUp(self):
        """Set up test fixtures."""
        self.patchers = []
        self.mocks = {}

        # Track mock targets and their names
        mock_targets = [
            ("sqlalchemy.create_engine", "create_engine"),
            ("sqlalchemy.orm.sessionmaker", "sessionmaker"),
            ("sqlalchemy.orm.scoped_session", "scoped_session"),
            ("apscheduler.schedulers.background.BackgroundScheduler", "BackgroundScheduler"),
            (DatabaseConnection, "validate_connection"),
        ]

        # Create and start all patchers
        for target, name in mock_targets:
            if isinstance(target, str):
                patcher = patch(target)
                self.mocks[name] = patcher.start()
            else:
                patcher = patch.object(target[极客时间
极客时间是一个面向IT从业者的在线教育平台，提供技术课程、专栏文章和实战项目等内容。它由极客邦科技运营，主要服务于程序员、产品经理、设计师等技术人群。

### 主要特点：
1. **技术课程**：涵盖编程语言、架构设计、人工智能、大数据、前端、后端等方向
2. **专栏订阅**：技术专家撰写的深度技术文章
3. **实战项目**：结合实际开发场景的练习项目
4. **大厂案例**：分享知名互联网公司的技术实践

### 典型课程示例：
- 《数据结构与算法之美》
- 《设计模式之美》
- 《左耳听风》
- 《从0开始学大数据》

### 适合人群：
- 希望提升技术深度的开发者
- 准备技术面试的求职者
- 想要转型技术管理的工程师

### 访问方式：
官网：time.geekbang.org
移动极客时间
极客时间是一个面向IT从业者的在线教育平台，提供技术课程、专栏文章和实战项目等内容。它由极客邦科技运营，主要服务于程序员、产品经理、设计师等技术人群。

### 主要特点：
1. **技术课程**：涵盖编程语言、架构设计、人工智能、大数据、前端、后端等方向
2. **专栏订阅**：技术专家撰写的深度技术文章
3. **实战项目**：结合实际开发场景的练习项目
4. **大厂案例**：分享知名互联网公司的技术实践

### 典型课程示例：
- 《数据结构与算法之美》
- 《设计模式之美》
- 《左耳听风》
- 《从0开始学大数据》

### 适合人群：
- 希望提升技术深度的开发者
- 准备技术面试的求职者
- 想要转型技术管理的工程师

### 访问方式：
官网：time.geekbang.org
移动端：iOS/Android应用端：iOS/Android应用0], target[1], return_value=None)
                self.mocks[name] = patcher.start()
            self.patchers.append(patcher)

        # Configure mock engine
        self.mock_engine_instance = MagicMock()
        self.mocks["create_engine"].return_value = self.mock_engine_instance

        # Mock connection validation
        self.mock_conn = MagicMock()
        self.mock_engine_instance.connect.return_value.__enter__.return_value = self.mock_conn
        self.mock_conn.execute.return_value.scalar.return_value = 1  # For schema version check

        # Sample config with pg_ prefix expected by DatabaseConnection
        self.config = {
            "pg_host": "localhost",
            "pg_port": 5432,
            "pg_dbname": "test_db",
            "pg_user": "test_user",
            "pg_password": "test_pass",
            "sslmode": "prefer",
            "pool_size": 5,
            "pool_max": 10,
        }

    def tearDown(self):
        """Tear down test fixtures."""
        for patcher in reversed(self.patchers):
            patcher.stop()

    def test_init(self):
        """Test initialization with valid config."""
        # Create connection instance
        conn = DatabaseConnection(self.config)

        # Check engine was created with correct params
        self.mocks["create_engine"].assert极客时间
极客时间是一个面向IT从业者的在线教育平台，提供技术课程、专栏文章和实战项目等内容。它由极客邦科技运营，主要服务于程序员、产品经理、设计师等技术人群。

### 主要特点：
1. **技术课程**：涵盖编程语言、架构设计、人工智能、大数据、前端、后端等方向
2. **专栏订阅**：技术专家撰写的深度技术文章
3. **实战项目**：结合实际开发场景的练习项目
4. **大厂案例**：分享知名互联网公司的技术实践

### 典型课程示例：
- 《数据结构与算法之美》
- 《设计模式之美》
- 《左耳听风》
- 《从0开始学大数据》

### 适合人群：
- 希望提升技术深度的开发者
- 准备技术面试的求职者
- 想要转型技术管理的工程师

### 访问方式：
官网：time.geekbang.org
移动端：iOS/Android应用_called_once()
        call_args = self.mocks["create_engine"].call_args[1]
        self.assertEqual(call_args["pool_size"], 5)
        self.assertEqual(call_args["max_overflow"], 10)
        self.assertTrue(call_args["pool_pre_ping"])

        # Check session factory was created
        self.mocks["sessionmaker"].assert_called_once_with(
            autocommit=False, autoflush=False, bind=self.mock_engine_instance,
        )

        # Check scoped session was created
        self.mocks["scoped_session"].assert_called_once()

        # Check scheduler was started
        self.mocks["BackgroundScheduler"].return_value.start.assert_called_once()

    def test_init_with_env_var(self):
        """Test initialization with DATABASE_URL environment variable."""
        with patch.dict(
            "os.environ",
            {"DATABASE_URL": "postgresql://env_user:env_pass@env_host:5432/env_db"},
        ):
            conn = DatabaseConnection(self.config)

            # Should use environment URL
            self.mocks["create_engine"].assert_called_once_with(
                "postgresql://env_user:env_pass@env_host:5432/env_db",
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
            )

    def test_validate_connection(self):
        """Test connection validation."""
        # Set up mock connection
        mock_conn = MagicMock()
        self.mock_engine_instance.connect.return_value.__enter__.return_value = (
            mock_conn
        )

        # Mock execute results
        mock_conn.execute.return_value.scalar.return_value = 1

        # Create connection instance
        conn = DatabaseConnection(self.config)

        # Verify validation queries were executed
        mock_conn.execute.assert_has_calls(
            [
                call(text("SELECT 1")),
                call(text("SELECT MAX(version) FROM schema_versions")),
            ],
        )

    def test_validate_connection_failure(self):
        """Test connection validation failure."""
        # Set up mock to raise exception
        self.mock_engine_instance.connect.side_effect = Exception("Connection failed")

        with self.assertRaises(DatabaseConnectionError):
            DatabaseConnection(self.config)

    def test_get_session(self):
        """Test getting a session context manager."""
        # Create connection instance
        conn = DatabaseConnection(self.config)

        # Mock session behavior
        mock_session_instance = MagicMock()
        self.mocks["scoped_session"].return_value = mock_session_instance

        # Use session context
        with conn.get_session() as session:
            self.assertEqual(session, mock_session_instance)

        # Verify session was committed and closed
        mock_session_instance.commit.assert_called_once()
        mock_session_instance.close.assert_called_once()

    def test_get_session_with极客时间
极客时间是一个面向IT从业者的在线教育平台，提供技术课程、专栏文章和实战项目等内容。它极客时间
极客时间是一个面向IT从业者的在线教育平台，提供技术课程、专栏文章和实战项目等内容。它由极客邦科技运营，主要服务于程序员、产品经理、设计师等技术人群。

### 主要特点：
1. **技术课程**：涵盖编程语言、架构设计、人工智能、大数据、前端、后端等方向
2. **专栏订阅**：技术专家撰写的深度技术文章
3. **实战项目**：结合实际开发场景的练习项目
4. **大厂案例**：分享知名互联网公司的技术实践

### 典型课程示例：
- 《数据结构与算法之美》
- 《设计模式之美》
- 《左耳听风》
- 《从0开始学大数据》

### 适合人群：
- 希望提升技术深度的开发者
- 准备技术面试的求职者
- 想要转型技术管理的工程师

### 访问方式：
官网：time.geekbang.org
移动端：iOS/Android应用由极客邦科技运营，主要服务于程序员、产品经理、设计师等技术人群。

### 主要特点：
1. **技术课程**：涵盖编程语言、架构设计、人工智能、大数据、前端、后端等方向
2. **专栏订阅**：技术专家撰写的深度技术文章
3. **实战项目**：结合实际开发场景的练习项目
4. **大厂案例**：分享知名互联网公司的技术实践

### 典型课程示例：
- 《数据结构与算法之美》
- 《设计模式之美》
- 《左耳听风》
- 《从0开始学大数据》

### 适合人群：
- 希望提升技术深度的开发者
- 准备技术面试的求职者
- 想要转型技术管理的工程师

### 访问方式：
官网：time.geekbang.org
移动端：iOS/Android应用_error(self):
        """Test session rollback on error."""
        # Create connection instance
        conn = DatabaseConnection(self.config)

        # Mock session behavior
        mock_session_instance = MagicMock()
        mock_session_instance.commit.side_effect = Exception("Test error")
        self.mocks["scoped_session"].return_value = mock_session_instance

        # Use session context with error
        with self.assertRaises(DatabaseConnectionError):
            with conn.get_session():
                pass

        # Verify rollback was called
        mock_session_instance.rollback.assert_called_once()
        mock_session_instance.close.assert_called_once()

    def test_close(self):
        """Test closing connection resources."""
        # Create connection instance
        conn = DatabaseConnection(self.config)

        # Close connection
        conn.close()

        # Verify resources were cleaned up
        self.mocks["scoped_session"].return_value.remove.assert_called_once()
        self.mock_engine_instance.dispose.assert_called_once()
        self.mocks["BackgroundScheduler"].return_value.shutdown.assert_called_once_with(wait=False)


if __name__ == "__main__":
    unittest.main()
        self.mocks["sessionmaker"].assert_called_once_with(
            autocommit=False, autoflush=False, bind=self.mock_engine_instance,
        )

        # Check scoped session was created
        self.mocks["scoped_session"].assert_called_once()

        # Check scheduler was started
        self.mocks["BackgroundScheduler"].return_value.start.assert_called_once()

    def test_init_with_env_var(self):
        """Test initialization with DATABASE_URL environment variable."""
        with patch.dict(
            "os.environ",
            {"DATABASE_URL": "postgresql://env_user:env_pass@env_host:5432/env_db"},
        ):
            conn = DatabaseConnection(self.config)

            # Should use environment URL
            self.mocks["create_engine"].assert_called_once_with(
                "postgresql://env_user:env_pass@env_host:5432/env_db",
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
            )

    def test_validate_connection(self):
        """Test connection validation."""
        # Set up mock connection
        mock_conn = MagicMock()
        self.mock_engine_instance.connect.return_value.__enter__.return_value = (
            mock_conn
        )

        # Mock execute results
        mock_conn.execute.return_value.scalar.return_value = 1

        # Create connection instance
        conn = DatabaseConnection(self.config)

        # Verify validation queries were executed
        mock_conn.execute.assert_has_calls(
            [
                call(text("SELECT 1")),
                call(text("SELECT MAX(version) FROM schema_versions")),
            ],
        )

    def test_validate_connection_failure(self):
        """Test connection validation failure."""
        # Set up mock to raise exception
        self.mock_engine_instance.connect.side_effect = Exception("Connection failed")

        with self.assertRaises(DatabaseConnectionError):
            DatabaseConnection(self.config)

    def test_get_session(self):
        """Test getting a session context manager."""
        # Create connection instance
        conn = DatabaseConnection(self.config)

        # Mock session behavior
        mock_session_instance = MagicMock()
        self.mocks["scoped_session"].return_value = mock_session_instance

        # Use session context
        with conn.get_session() as session:
            self.assertEqual(session, mock_session_instance)

        # Verify session was committed and closed
        mock_session_instance.commit.assert_called_once()
        mock_session_instance.close.assert_called_once()

    def test_get_session_with极客时间
极客时间是一个面向IT从业者的在线教育平台，提供技术课程、专栏文章和实战项目等内容。它极客时间
极客时间是一个面向IT从业者的在线教育平台，提供技术课程、专栏文章和实战项目等内容。它由极客邦科技运营，主要服务于程序员、产品经理、设计师等技术人群。

### 主要特点：
1. **技术课程**：涵盖编程语言、架构设计、人工智能、大数据、前端、后端等方向
2. **专栏订阅**：技术专家撰写的深度技术文章
3. **实战项目**：结合实际开发场景的练习项目
4. **大厂案例**：分享知名互联网公司的技术实践

### 典型课程示例：
- 《数据结构与算法之美》
- 《设计模式之美》
- 《左耳听风》
- 《从0开始学大数据》

### 适合人群：
- 希望提升技术深度的开发者
- 准备技术面试的求职者
- 想要转型技术管理的工程师

### 访问方式：
官网：time.geekbang.org
移动端：iOS/Android应用由极客邦科技运营，主要服务于程序员、产品经理、设计师等技术人群。

### 主要特点：
1. **技术课程**：涵盖编程语言、架构设计、人工智能、大数据、前端、后端等方向
2. **专栏订阅**：技术专家撰写的深度技术文章
3. **实战项目**：结合实际开发场景的练习项目
4. **大厂案例**：分享知名互联网公司的技术实践

### 典型课程示例：
- 《数据结构与算法之美》
- 《设计模式之美》
- 《左耳听风》
- 《从0开始学大数据》

### 适合人群：
- 希望提升技术深度的开发者
- 准备技术面试的求职者
- 想要转型技术管理的工程师

### 访问方式：
官网：time.geekbang.org
移动端：iOS/Android应用_error(self):
        """Test session rollback on error."""
        # Create connection instance
        conn = DatabaseConnection(self.config)

        # Mock session behavior
        mock_session_instance = MagicMock()
        mock_session_instance.commit.side_effect = Exception("Test error")
        self.mocks["scoped_session"].return_value = mock_session_instance

        # Use session context with error
        with self.assertRaises(DatabaseConnectionError):
            with conn.get_session():
                pass

        # Verify rollback was called
        mock_session_instance.rollback.assert_called_once()
        mock_session_instance.close.assert_called_once()

    def test_close(self):
        """Test closing connection resources."""
        # Create connection instance
        conn = DatabaseConnection(self.config)

        # Close connection
        conn.close()

        # Verify resources were cleaned up
        self.mocks["scoped_session"].return_value.remove.assert_called_once()
        self.mock_engine_instance.dispose.assert_called_once()
        self.mocks["BackgroundScheduler"].return_value.shutdown.assert_called_once_with(wait=False)


if __name__ == "__main__":
    unittest.main()
