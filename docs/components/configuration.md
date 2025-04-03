g# Configuration System

## Overview
The Dewey project uses a centralized YAML configuration system with:
- Environment variable expansion
- Hierarchical structure
- Type safety
- Validation

```mermaid
flowchart TD
    A[config/dewey.yaml] --> B[load_config()]
    B --> C[Expand env vars]
    C --> D[Return config dict]
```

## Configuration File Structure
The main configuration file is `config/dewey.yaml` with sections for:

```yaml
# Core system settings
core:
  logging:
    level: INFO
    format: "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
  
  database:
    host: ${DB_HOST}
    port: ${DB_PORT}
    dbname: ${DB_NAME}
    user: ${DB_USER}
    password: ${DB_PASSWORD}

# LLM configuration  
llm:
  model: gpt-4
  api_key: ${OPENAI_API_KEY}
  timeout: 60

# Pipeline configurations
pipelines:
  data_ingestion:
    batch_size: 100
    timeout: 300
```

## Key Features

### Environment Variable Expansion
Use `${VAR_NAME}` syntax to reference environment variables:

```yaml
database:
  password: ${DB_PASSWORD}  # Will be replaced with os.getenv("DB_PASSWORD")
```

### Hierarchical Structure
Organize settings by functional area:
- `core`: Fundamental system settings
- `llm`: Language model configurations  
- `pipelines`: Data processing pipelines
- `engines`: Integration engines

### Type Safety
Configuration values maintain their Python types:
- Strings, numbers, booleans, lists, and dicts are preserved

## Usage

### Loading Configuration
```python
from dewey.core.config.loader import load_config

# Load entire config
config = load_config()

# Access specific section
db_config = config["core"]["database"]
```

### Accessing Values
```python
# Get nested value with dot notation
model = config.get("llm.model", "gpt-3.5-turbo")

# Get with default
timeout = config.get("llm.timeout", 60)
```

## Best Practices

1. **Keep sensitive data in env vars** - Never commit secrets
2. **Use descriptive section names** - Group related settings
3. **Document configurations** - Add comments in YAML
4. **Validate early** - Check required values on startup
5. **Use defaults** - Provide fallback values

## Validation
The system doesn't enforce schema validation but recommends:

```python
# Example validation
required_db_keys = ["host", "port", "dbname", "user", "password"]
missing = [k for k in required_db_keys if k not in config["core"]["database"]]
if missing:
    raise ValueError(f"Missing database config: {missing}")
```

## Advanced Usage

### Custom Config Paths
Override the default path:

```python
def load_custom_config(path: str):
    with open(path) as f:
        return yaml.safe_load(f)
```

### Dynamic Reloading
For development, watch for changes:

```python
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigWatcher(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith("dewey.yaml"):
            reload_config()
```

## Troubleshooting

**Missing Config File**:
- Ensure `config/dewey.yaml` exists
- Check file permissions

**Env Vars Not Expanded**:
- Verify `${VAR}` syntax
- Check env vars are set

**Type Errors**:
- Validate expected types in code
- Use YAML type tags if needed (`!!str`, `!!int`)