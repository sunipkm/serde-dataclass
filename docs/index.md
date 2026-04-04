# 🐼 serde-dataclass 🐻

Serialize Python dataclasses to TOML and JSON with a small, explicit API.

[`serde-dataclass`](https://github.com/sunipkm/serde-dataclass) is built around two mixins:

- [`TomlDataclass`](api.md/#tomldataclass) for TOML serialization with comments and key renaming
- [`JsonDataclass`](api.md/#jsondataclass) for JSON serialization using the standard library JSON stack

The library is aimed at configuration-style dataclasses where type safety matters and hand-maintaining TOML files becomes repetitive.

## Features

- TOML serialization and deserialization through [`TomlDataclass`](api.md/#tomldataclass)
- JSON serialization and deserialization through [`JsonDataclass`](api.md/#jsondataclass)
- Root document comments from class docstrings or [`toml_config(...)`](api.md/#toml_config)
- Field comments for scalar values, tables, and arrays of tables
- Renamed serialized keys through [`field`](https://docs.python.org/3/library/dataclasses.html#dataclasses.field) metadata
- Nested dataclasses without requiring every nested type to inherit from a mixin
- Support for `list`, `tuple`, `set`, `dict[str, ...]`, `Enum`, `Literal`, and `Optional`
- Custom [`dacite`](https://github.com/konradhalas/dacite) hooks for loading custom types
- Custom JSON encoders and [`tomlkit`](https://tomlkit.readthedocs.io/en/latest/) encoders for serialization
- Per-field custom validators via metadata

## Installation

```bash
pip install serde-dataclass
```

For development and docs work:

```bash
pip install -e .[dev,docs]
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
```

Example TOML output:

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

## Next Steps

- See [Getting Started](getting-started.md) for the configuration model and supported types
- See [API Reference](api.md) for the public API surface
- See [Custom Types](custom-types.md) for `dacite` and encoder integration
