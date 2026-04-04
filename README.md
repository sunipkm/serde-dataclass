# 🐼 serde-dataclass 🐻

TOML and JSON serialization for Python dataclasses is provided through a small, explicit API.

Comment-preserving TOML output, renamed keys, nested dataclasses, and typed round-trips are supported.

## Documentation

Project documentation is provided through MkDocs.

```bash
pip install -e .[docs]
mkdocs serve
```

Detailed usage is documented in `docs/`.

## Installation

```bash
pip install serde-dataclass
```

For development and example dependencies:

```bash
pip install -e .[dev]
```

## Quick Start

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from serde_dataclass import TomlDataclass


class Mode(str, Enum):
    DEV = "dev"
    PROD = "prod"


@dataclass
class Database:
    host: str = field(metadata={"description": "Database host"})
    port: int = field(default=5432, metadata={"description": "Database port"})


@dataclass
class AppConfig(TomlDataclass):
    """Application configuration"""

    app_name: str = field(
        default="demo",
        metadata={"description": "Application name", "toml": "app-name"},
    )
    log_level: Literal["debug", "info", "warning", "error"] = field(
        default="info",
        metadata={"description": "Logging verbosity", "toml": "log-level"},
    )
    mode: Mode = field(default=Mode.DEV, metadata={"description": "Runtime mode"})
    database: Database = field(
        default_factory=lambda: Database(host="localhost"),
        metadata={"description": "Database settings"},
    )


cfg = AppConfig()
text = cfg.to_toml()
loaded = AppConfig.from_toml(text)

assert loaded == cfg
print(text)
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

## Summary

- `TomlDataclass` and `JsonDataclass` are provided as base [mixins](https://en.wikipedia.org/wiki/Mixin).
- Root comments, field comments, renamed keys, and nested dataclasses are supported.
- `Enum`, `Literal`, `Optional`, lists, tuples, sets, and `dict[str, T]` are supported.
- Custom loading is configured through `dacite.Config`.
- Custom serialization is integrated through `json.JSONEncoder` and `tomlkit` encoders.

## Notes

- TOML comments are emitted only for TOML serialization.
- Dictionary keys are required to be strings.
- Fields with `None` values are omitted from TOML output.

## Development

```bash
pytest -q
```

## License

MIT
