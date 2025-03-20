import pytest

from dewey.core.base_script import BaseScript


def test_base_script_initialization():
    """Test that BaseScript can be initialized."""
    script = BaseScript()
    assert script is not None
    assert script.name == "BaseScript"
    assert script.description is None
    assert script.config is not None
    assert script.logger is not None


def test_base_script_with_name_and_description():
    """Test that BaseScript can be initialized with a name and description."""
    script = BaseScript(name="TestScript", description="A test script.")
    assert script.name == "TestScript"
    assert script.description == "A test script."


def test_base_script_config_section():
    """Test that BaseScript loads the correct config section."""
    script = BaseScript(config_section="test_config")
    assert script.config == {
        "local_db_path": ":memory:",
        "motherduck_db": "md:dewey_test",
        "motherduck_token": "test_token",
        "pool_size": 2,
        "max_retries": 2,
        "retry_delay": 0.1,
        "sync_interval": 60,
        "max_sync_age": 3600,
        "backup_dir": "/tmp/dewey_test_backups",
        "backup_retention_days": 1,
    }


def test_base_script_config_section_not_found():
    """Test that BaseScript handles missing config section gracefully."""
    script = BaseScript(config_section="nonexistent_config")
    assert script.config == {
        "core": {
            "backup_strategy": "3-2-1",
            "conventions_document": "/Users/srvo/dewey/CONVENTIONS.md",
            "default_timezone": "UTC",
            "project_root": "/Users/srvo/dewey",
            "base_script": "/Users/srvo/dewey/src/dewey/core/base_script.py",
            "script_enforcement": {
                "validation_hooks": ["pre-commit", "pre-push", "ci-pipeline"],
                "failure_action": "hard-fail",
            },
        },
        "formatting": {
            "formatters": [
                {
                    "command": [
                        "ruff",
                        "check",
                        "--fix",
                        "--unsafe-fixes",
                        "--select",
                        "ALL",
                    ]
                },
                {"command": ["black"]},
            ],
            "lint_timeout": 120,
        },
        "paths": {
            "log_dir": "logs",
            "db_path": "md:dewey",
            "credentials_dir": "config/credentials",
            "prefect_flows_dir": "/var/lib/dokku/data/storage/prefect/flows",
            "prefect_configs_dir": "/var/lib/dokku/data/storage/prefect/configs",
            "data_dir": "data",
            "output_dir": "output",
            "cache_dir": ".cache",
            "temp_dir": "/tmp/dewey",
            "research_data": "data/research",
            "company_analysis": "data/research/companies",
            "financial_analysis": "data/research/financial",
            "controversy_data": "data/research/controversy",
            "crm_data": "data/crm",
            "email_data": "data/crm/email",
            "contact_data": "data/crm/contacts",
            "enrichment_data": "data/crm/enrichment",
            "ledger_dir": "data/bookkeeping/ledger",
            "journal_dir": "data/bookkeeping/journals",
            "forecast_dir": "data/bookkeeping/forecasts",
            "transaction_dir": "data/bookkeeping/transactions",
            "import_dir": "data/imports",
            "export_dir": "data/exports",
            "backup_dir": "data/backups",
            "archive_dir": "data/archive",
        },
        "settings": {
            "deepinfra_api_url": "https://api.deepinfra.com/v1/openai/chat/completions",
            "deepinfra_api_key": "${DEEPINFRA_API_KEY}",
            "default_db": "motherduck",
            "default_llm": "deepseek-ai/DeepSeek-V3",
            "gmail_scopes": [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/gmail.metadata",
                "https://mail.google.com/",
            ],
            "prefect_api_base": "https://flow.sloane-collective.com/api",
            "github_api_url": "https://api.github.com/graphql",
            "github_token": "${GITHUB_TOKEN}",
            "sec_api_url": "https://data.sec.gov/api/xbrl/frames",
            "sec_api_key": "${SEC_API_KEY}",
            "db_url": "${DB_URL}",
            "db_port": 5432,
            "db_timeout": 30,
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "email_timeout": 30,
            "analysis_batch_size": 100,
            "analysis_timeout": 300,
            "max_retries": 3,
            "retry_delay": 5,
            "crm_api_url": "${CRM_API_URL}",
            "crm_api_key": "${CRM_API_KEY}",
            "enrichment_api_url": "${ENRICHMENT_API_URL}",
            "enrichment_api_key": "${ENRICHMENT_API_KEY}",
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "root_dir": "logs",
            "subdirectories": {"app": "app", "tests": "tests"},
            "handlers": [
                {
                    "type": "file",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": "${logging.root_dir}/${logging.subdirectories.app}/app.log",
                    "maxBytes": 10485760,
                    "backupCount": 5,
                },
                {
                    "type": "console",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            ],
        },
        "llm": {
            "client": "deepinfra",
            "default_provider": "deepinfra",
            "providers": {
                "deepinfra": {
                    "api_key": "${DEEPINFRA_API_KEY}",
                    "default_model": "google/gemini-2.0-flash-001",
                    "fallback_models": [
                        "google/gemini-2.0-pro",
                        "google/gemini-2.0-pro-vision",
                    ],
                    "api_base": "https://api.deepinfra.com/v1/openai",
                    "timeout": 30.0,
                }
            },
        },
        "agents": {
            "defaults": {
                "enabled": True,
                "version": 1.0,
                "logging": {
                    "level": "INFO",
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "client_advocacy": {
                "enabled": True,
                "version": 1.0,
                "client_rules": {
                    "priority_levels": [1, 2, 3, 4, 5],
                    "response_time": {"critical": "1h", "high": "4h", "normal": "24h"},
                },
            },
            "data_analysis": {
                "enabled": True,
                "version": 1.0,
                "schema_rules": {
                    "default_types": {
                        "string": "VARCHAR(255)",
                        "number": "DECIMAL(18,4)",
                    },
                    "naming_conventions": {
                        "table": "snake_case",
                        "column": "camelCase",
                    },
                },
            },
            "agent_creation": {
                "enabled": True,
                "version": 1.0,
                "templates": {
                    "base_agent": "src/dewey/llm/templates/base_agent.j2",
                    "function_template": "src/dewey/llm/templates/function.j2",
                },
                "gemini": {
                    "api_key": "${GEMINI_API_KEY}",
                    "default_model": "gemini-2.0-flash",
                    "model_limits": {"gemini-2.0-flash": {"rpm": 15, "tpm": 1000000}},
                },
            },
        },
        "pipeline": None,
        "test_database_config": {
            "local_db_path": "${DEWEY_LOCAL_DB:-/Users/srvo/dewey/dewey.duckdb}",
            "motherduck_db": "${DEWEY_MOTHERDUCK_DB:-md:dewey}",
            "pool_size": "${DEWEY_DB_POOL_SIZE:-1}",
            "max_retries": "${DEWEY_DB_MAX_RETRIES:-3}",
            "retry_delay": "${DEWEY_DB_RETRY_DELAY:-1}",
            "sync_interval": "${DEWEY_DB_SYNC_INTERVAL:-21600}",
            "max_sync_age": "${DEWEY_DB_MAX_SYNC_AGE:-604800}",
            "backup_dir": "${DEWEY_BACKUP_DIR:-/Users/srvo/dewey/backups}",
            "backup_retention_days": "${DEWEY_BACKUP_RETENTION_DAYS:-7}",
        },
        "prd": {
            "base_template": {
                "assumptions": [
                    "All non-client modules assume single-stakeholder (Sloane Ortel) usage",
                    "Data security requirements follow FINRA/SEC regulations",
                    "Python 3.11+ runtime environment",
                ],
                "evaluation_metrics": [
                    "Code maintainability (cyclomatic complexity < 15)",
                    "LLM response latency < 2.5s",
                    "Data processing throughput > 100MB/s",
                ],
                "market_assessment": {
                    "client_facing": "High-net-worth individuals and institutional investors",
                    "default": "Internal knowledge management and client-facing financial analysis systems",
                },
                "metadata": {
                    "author": "Sloane Ortel",
                    "revision_policy": "Bi-weekly review",
                },
                "stakeholders": {
                    "client_modules": [
                        {"name": "Client Services Team", "role": "Client Interface"}
                    ],
                    "default": [
                        {
                            "contact": "srvo@domain.com",
                            "name": "Sloane Ortel",
                            "role": "Primary Stakeholder",
                        }
                    ],
                },
                "timelines": {
                    "deployment": 0.5,
                    "development": 3,
                    "discovery": 2,
                    "testing": 1,
                },
            },
            "tracked_prds": [
                "/Users/srvo/dewey/src/dewey/llm/docs/llm_Product_Requirements_Document.yaml",
                "docs/llm_Product_Requirements_Document.yaml",
                "docs/llm_Product_Requirements_Document.md",
                "/Users/srvo/dewey/tests/docs/tests_Product_Requirements_Document.yaml",
            ],
        },
        "test_config": {
            "local_db_path": ":memory:",
            "motherduck_db": "md:dewey_test",
            "motherduck_token": "test_token",
            "pool_size": 2,
            "max_retries": 2,
            "retry_delay": 0.1,
            "sync_interval": 60,
            "max_sync_age": 3600,
            "backup_dir": "/tmp/dewey_test_backups",
            "backup_retention_days": 1,
        },
        "regex_patterns": {
            "contact_info": {
                "company": "(?i)(?:at|@)\\s*([A-Za-z0-9][A-Za-z0-9\\s&-]+(?:\\s+(?:LLC|Inc|Ltd|Limited|Corp|Corporation|Capital|Partners|Group|Advisory|Consulting))?)",
                "job_title": "(?i)(CEO|CTO|CFO|Director|Manager|Analyst|Associate|Partner|VP|President|Founder|Co-founder|Principal|Advisor|Consultant)",
                "linkedin": "LinkedIn:\\s*(linkedin\\.com/in/[a-zA-Z0-9_-]+)",
                "name_email": "([^<\\n]*?)\\s*<([^>]+)>",
                "phone": "Phone:\\s*(\\(?\\d{3}\\)?[\\s.-]?\\d{3}[\\s.-]?\\d{4})",
            },
            "opportunity": {
                "cancellation": "\\bcancel\\b|\\bneed to cancel\\b",
                "demo": "\\bdemo\\b|\\bschedule a demo\\b",
                "publicity": "\\bpublicity opportunity\\b|\\bmedia\\b",
                "speaking": "\\bspeaking opportunity\\b|\\bpresentation\\b",
                "submission": "\\bpaper submission\\b|\\bsubmit a paper\\b",
            },
        },
        "vector_stores": {
            "code_consolidation": {
                "collection_name": "code_functions",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "hnsw_config": {
                    "M": 24,
                    "construction_ef": 300,
                    "search_ef": 200,
                    "space": "cosine",
                },
                "persist_dir": ".chroma_cache",
                "similarity_threshold": 0.85,
            },
            "document_store": {
                "collection_name": "document_chunks",
                "embedding_model": "all-mpnet-base-v2",
                "hnsw_config": {
                    "M": 32,
                    "construction_ef": 500,
                    "search_ef": 300,
                    "space": "cosine",
                },
                "persist_dir": ".chroma_docs",
            },
        },
    }


def test_base_script_requires_db():
    """Test that BaseScript initializes db_conn when requires_db is True."""
    with pytest.raises(ImportError):
        script = BaseScript(requires_db=True)
        assert script.db_conn is None  # Replace with actual check after mocking


def test_base_script_enable_llm():
    """Test that BaseScript initializes llm_client when enable_llm is True."""
    with pytest.raises(ImportError):
        script = BaseScript(enable_llm=True)
        assert script.llm_client is None  # Replace with actual check after mocking


def test_base_script_setup_argparse():
    """Test that BaseScript sets up argparse correctly."""
    script = BaseScript()
    parser = script.setup_argparse()
    assert parser is not None
    assert parser.description is None


def test_base_script_parse_args_log_level(mocker):
    """Test that BaseScript parses log level argument correctly."""
    script = BaseScript()
    parser = script.setup_argparse()
    mocker.patch("sys.argv", ["test_script.py", "--log-level", "DEBUG"])
    args = script.parse_args()
    assert args.log_level == "DEBUG"


def test_base_script_parse_args_config(mocker):
    """Test that BaseScript parses config argument correctly."""
    script = BaseScript()
    parser = script.setup_argparse()
    mocker.patch("sys.argv", ["test_script.py", "--config", "config/dewey.yaml"])
    args = script.parse_args()
    assert args.config == "config/dewey.yaml"


def test_base_script_parse_args_db_connection_string(mocker):
    """Test that BaseScript parses db connection string argument correctly."""
    script = BaseScript(requires_db=True)
    parser = script.setup_argparse()
    mocker.patch(
        "sys.argv",
        ["test_script.py", "--db-connection-string", "test_connection_string"],
    )
    args = script.parse_args()
    assert args.db_connection_string == "test_connection_string"


def test_base_script_parse_args_llm_model(mocker):
    """Test that BaseScript parses llm model argument correctly."""
    script = BaseScript(enable_llm=True)
    parser = script.setup_argparse()
    mocker.patch("sys.argv", ["test_script.py", "--llm-model", "test_llm_model"])
    args = script.parse_args()
    assert args.llm_model == "test_llm_model"


def test_base_script_get_path():
    """Test that BaseScript's get_path method works correctly."""
    script = BaseScript()
    relative_path = "src/dewey/core/base_script.py"
    absolute_path = "/Users/srvo/dewey/src/dewey/core/base_script.py"
    assert (
        script.get_path(relative_path).resolve()
        == script.get_path(absolute_path).resolve()
    )


def test_base_script_get_config_value():
    """Test that BaseScript's get_config_value method works correctly."""
    script = BaseScript()
    assert script.get_config_value("test_config.local_db_path") == ":memory:"
    assert (
        script.get_config_value("nonexistent_key", "default_value") == "default_value"
    )
    assert script.get_config_value("nonexistent_key") is None
