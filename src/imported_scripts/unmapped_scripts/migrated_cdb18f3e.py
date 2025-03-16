import logging
import os
from dataclasses import dataclass, field

import duckdb
import pandas as pd
import pytest
import requests

# Configure logging
logging.basicConfig(
    filename="/Users/srvo/local/logs/data_infrastructure.log",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s",
)


# Data Models
@dataclass
class APIConfig:
    name: str
    url: str
    api_key: str
    rate_limit: int = 60  # default rate limit


@dataclass
class DataSource:
    name: str
    type: str  # e.g., 'API', 'Database', 'CSV'
    config: APIConfig
    last_updated: pd.Timestamp = field(default_factory=pd.Timestamp.now)


# AI Helper Class
class AIHelper:
    def __init__(self, api_config: APIConfig) -> None:
        self.api_config = api_config
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {self.api_config.api_key}"},
        )

    def query_model(self, prompt: str) -> str:
        logging.info(f"Querying AI model with prompt: {prompt}")
        try:
            response = self.session.post(
                self.api_config.url,
                json={"prompt": prompt, "max_tokens": 150},
            )
            response.raise_for_status()
            result = response.json().get("choices", [{}])[0].get("text", "").strip()
            logging.info("Received response from AI model.")
            return result
        except requests.exceptions.RequestException as e:
            logging.exception(f"AI model query failed: {e}")
            raise


# Data Handler Class
class DataHandler:
    def __init__(self, db_path: str = "/Users/srvo/local/data/port.duckdb") -> None:
        self.db_path = db_path
        self.connection = duckdb.connect(self.db_path)
        logging.info(f"Connected to DuckDB at {self.db_path}")

    def load_data(self, df: pd.DataFrame, table: str) -> None:
        logging.info(f"Loading data into table {table}")
        try:
            self.connection.execute(
                f"CREATE TABLE IF NOT EXISTS {table} AS SELECT * FROM df LIMIT 0",
            )
            self.connection.execute(f"INSERT INTO {table} SELECT * FROM df")
            logging.info(f"Data loaded successfully into {table}")
        except Exception as e:
            logging.exception(f"Failed to load data into {table}: {e}")
            raise

    def fetch_data(self, query: str) -> pd.DataFrame:
        logging.info(f"Fetching data with query: {query}")
        try:
            df = self.connection.execute(query).fetchdf()
            logging.info("Data fetched successfully.")
            return df
        except Exception as e:
            logging.exception(f"Failed to fetch data: {e}")
            raise

    def close_connection(self) -> None:
        self.connection.close()
        logging.info("DuckDB connection closed.")


# Utility Functions
def validate_dataframe(df: pd.DataFrame, required_columns: list[str]) -> bool:
    logging.info("Validating DataFrame.")
    return (
        all(col in df.columns for col in required_columns)
        and not df.isnull().values.any()
    )


def activate_virtual_env() -> None:
    venv_path = "/Users/srvo/envs/ethical_capital_env/bin/activate"
    activate_script = os.path.join(venv_path)
    activate_command = f"source {activate_script}"
    logging.info(f"Activating virtual environment: {activate_command}")
    os.system(activate_command)


# Example Analytical Function
def calculate_portfolio_weights(df: pd.DataFrame) -> pd.DataFrame:
    logging.info("Calculating portfolio weights.")
    total = df["value"].sum()
    df["weight"] = df["value"] / total
    logging.info("Portfolio weights calculated successfully.")
    return df


# Testing Framework
def test_validate_dataframe() -> None:
    logging.info("Testing validate_dataframe function.")
    df_valid = pd.DataFrame(
        {
            "Open": [100, 200],
            "High": [110, 210],
            "Low": [90, 190],
            "Close": [105, 205],
            "Volume": [1000, 2000],
        },
    )
    df_invalid = pd.DataFrame(
        {
            "Open": [100, 200],
            "High": [110, None],
            "Low": [90, 190],
            "Close": [105, 205],
            "Volume": [1000, 2000],
        },
    )
    assert (
        validate_dataframe(df_valid, ["Open", "High", "Low", "Close", "Volume"]) is True
    )
    assert (
        validate_dataframe(df_invalid, ["Open", "High", "Low", "Close", "Volume"])
        is False
    )
    logging.info("validate_dataframe function passed all tests.")


# AI Helper Tests
def test_ai_helper() -> None:
    logging.info("Testing AIHelper class.")
    api_config = APIConfig(
        name="DeepSeek",
        url="https://api.deepseek.com/v1/query",
        api_key="your_api_key_here",
        rate_limit=100,
    )
    ai_helper = AIHelper(api_config)
    try:
        response = ai_helper.query_model("Test prompt")
        assert isinstance(response, str)
        logging.info("AIHelper query_model function passed.")
    except Exception as e:
        logging.exception(f"AIHelper test failed: {e}")
        raise AssertionError


# Main Execution
if __name__ == "__main__":
    activate_virtual_env()

    # Initialize Data Handler
    data_handler = DataHandler()

    # Example Data Loading
    sample_data = pd.DataFrame(
        {
            "date": pd.date_range(start="2023-01-01", periods=5, freq="D"),
            "open": [100, 102, 104, 103, 105],
            "high": [110, 112, 114, 113, 115],
            "low": [90, 92, 94, 93, 95],
            "close": [105, 107, 109, 108, 110],
            "volume": [1000, 1500, 2000, 2500, 3000],
        },
    )

    if validate_dataframe(sample_data, ["open", "high", "low", "close", "volume"]):
        data_handler.load_data(sample_data, "stock_prices")
    else:
        logging.error("Sample data validation failed.")

    # Calculate Portfolio Weights
    weights = calculate_portfolio_weights(sample_data)
    logging.info(f"Portfolio Weights:\n{weights}")

    # Close Data Handler Connection
    data_handler.close_connection()

    # Run Tests
    pytest.main([__file__, "-v"])
