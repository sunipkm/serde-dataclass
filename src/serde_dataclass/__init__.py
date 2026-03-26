# toml_dataclass - A dataclass-based library for TOML serialization with comment support
"""
TOML Dataclass
-----------------

TOML Dataclass provides base classes TomlDataclass and JsonDataclass for easy 
serialization and deserialization of dataclasses to and from TOML and JSON 
formats, respectively.

It supports features such as:
- Support for comments on fields and the root document
- Custom key names for TOML fields
- Nested dataclasses
- Collections (lists, dicts, tuples, sets)
- Support for `Enum` and `Literal` types with validation
- Custom type hooks for serialization and deserialization

Example usage:
```python
from dataclasses import dataclass, field
from toml_dataclass import dataclass_toml
@dataclass_toml(root_comment="Application configuration")
@dataclass
class AppConfig:
    \"\"\"Application configuration\"\"\"  # This docstring will be used as the root comment
    app_name: str = field(
        default="demo",
        metadata={"description": "Application name", "toml": "app-name"},
    )
    log_level: str = field(
        default="info",
        metadata={"description": "Log level", "toml": "log-level"},
    )
# Create an instance
config = AppConfig()
# Serialize to TOML
toml_text = config.to_toml()
print(toml_text)
# Deserialize from TOML
loaded_config = AppConfig.from_toml(toml_text)
print(loaded_config)
```

A `@dataclass_json` decorator is also provided for JSON serialization and deserialization with similar features, without comment support.
"""
from importlib.metadata import version

from .iface import JsonDataclass, TomlDataclass, json_config, toml_config

__version__ = version(__package__ or "toml_dataclass")

__all__ = [
    "JsonDataclass", "TomlDataclass",
    "json_config", "toml_config",
    "__version__"
]
