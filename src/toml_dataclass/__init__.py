# toml_dataclass - A dataclass-based library for TOML serialization with comment support
"""
TOML Dataclass
-----------------

TOML Dataclass provides a decorator `@dataclass_toml` that extends Python's built-in `dataclass` to support serialization and deserialization to and from TOML format, with additional features such as:
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

from .core import dataclass_toml, dataclass_json, JsonCompatible, TomlCompatible

__version__ = version(__package__ or "toml_dataclass")

__all__ = [
    "dataclass_toml", "dataclass_json",
    "JsonCompatible", "TomlCompatible",
    "__version__"
]
