"""Public package interface for serde-dataclass.

The package exposes two dataclass mixins:

- ``TomlDataclass`` for TOML serialization and deserialization
- ``JsonDataclass`` for JSON serialization and deserialization

TOML support includes:

- root document comments from a class docstring or ``toml_config(...)``
- field comments via dataclass field metadata
- field renaming for serialized keys
- nested dataclasses and arrays of tables
- validation for ``Enum`` and ``Literal`` annotations
- custom loaders through ``dacite.Config``

The expected usage pattern is to inherit from one or both mixins and still
decorate the class with ``@dataclass``.

Example:

    >>> from dataclasses import dataclass, field
    >>> from enum import Enum
    >>> from typing import Literal
    >>>
    >>> class Mode(str, Enum):
    ...     DEV = "dev"
    ...     PROD = "prod"
    ...
    >>> @dataclass
    ... class Database:
    ...     host: str = field(metadata={"description": "Database host"})
    ...     port: int = field(default=5432, metadata={"description": "Database port"})
    ...
    >>> @dataclass
    ... class AppConfig(TomlDataclass):
    ...     '''Application configuration'''
    ...     app_name: str = field(
    ...         default="demo",
    ...         metadata={"description": "Application name", "toml": "app-name"},
    ...     )
    ...     log_level: Literal["debug", "info", "warning", "error"] = field(
    ...         default="info",
    ...         metadata={"description": "Logging verbosity", "toml": "log-level"},
    ...     )
    ...     mode: Mode = field(default=Mode.DEV, metadata={"description": "Runtime mode"})
    ...     database: Database = field(
    ...         default_factory=lambda: Database(host="localhost"),
    ...         metadata={"description": "Database settings"},
    ...     )
    ...
    >>> cfg = AppConfig()
    >>> loaded = AppConfig.from_toml(cfg.to_toml())
    >>> loaded == cfg
    True

For fuller usage guidance, see the repository documentation under ``docs/``.
"""
from importlib.metadata import version

from .iface import JsonDataclass, TomlDataclass, json_config, toml_config
from .core import TypeChecker

__version__ = version(__package__ or "toml_dataclass")

__all__ = [
    "JsonDataclass", "TomlDataclass",
    "json_config", "toml_config",
    "TypeChecker",
    "__version__"
]
