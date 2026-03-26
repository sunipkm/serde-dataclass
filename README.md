# toml-dataclass

Helpers for serializing dataclasses to TOML with:

- Inline comments for scalar values
- Non-inline comments for tables and arrays of tables
- Root document comment (can be extracted from class docstring)
- Nested dataclasses
- Collections (lists, dicts, tuples, sets)
- Key renaming
- Support for `Enum` and `Literal` types with validation
- Custom type hooks for serialization and deserialization

## Install

```bash
pip install toml-dataclass
```

## Example

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from toml_dataclass import dataclass_toml


class Mode(str, Enum):
    DEV = "dev"
    PROD = "prod"


@dataclass
class Database:
    host: str = field(metadata={"comment": "Database host"})
    port: int = field(default=5432, metadata={"comment": "Database port"})


@dataclass_toml
@dataclass
class AppConfig:
    """Application configuration"""  # This docstring will be used as the root comment
    app_name: str = field(
        default="demo",
        metadata={"comment": "Application name", "toml": "app-name"},
    )
    log_level: Literal["debug", "info", "warning", "error"] = field(
        default="info",
        metadata={"comment": "Logging verbosity", "toml": "log-level"},
    )
    mode: Mode = field(default=Mode.DEV, metadata={"comment": "Runtime mode"})
    database: Database = field(
        default_factory=lambda: Database(host="localhost"),
        metadata={"comment": "Database settings"},
    )

cfg = AppConfig()
text = cfg.to_toml()
loaded = AppConfig.from_toml(text)
```

Example output:

```toml
# Application configuration

app-name = "demo" # Application name
log-level = "info" # Logging verbosity
mode = "dev" # Runtime mode

# Database settings
[database]
host = "localhost" # Database host
port = 5432 # Database port
```
