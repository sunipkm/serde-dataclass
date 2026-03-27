# API Reference

## `TomlDataclass`

Base class providing TOML serialization and deserialization helpers.

### Methods

- `to_toml() -> str`: serialize an instance to TOML
- `from_toml(text: str) -> Self`: deserialize from TOML text
- `save_toml(path) -> None`: write the TOML representation to a file
- `load_toml(path) -> Self`: load an instance from a TOML file

## `JsonDataclass`

Base class providing JSON serialization and deserialization helpers.

### Methods

- `to_json(**kwargs) -> str`: serialize using `json.dumps`. `**kwargs` are passed directly to `json.dumps`. The `cls` argument is reserved for custom encoders configured through `json_config(...)`.
- `from_json(text: str, **kwargs) -> Self`: deserialize using `json.loads`. `**kwargs` are passed directly to `json.loads`. The `cls` argument is reserved for custom decoders configured through `json_config(...)`.

## `toml_config(...)`

Decorator for configuring TOML behavior on a class.

### Arguments

- `root_comment`: top-of-file TOML comment; defaults to the class docstring when present
- `description_key`: metadata key used for comments; default is `description`
- `rename_key`: metadata key used for serialized field names; default is `toml`
- `typecheck_key`: metadata key used for custom validators; default is `typecheck`
- `de`: `dacite.Config` used during deserialization

### Example

```python
from dataclasses import dataclass, field

from serde_dataclass import TomlDataclass, toml_config


@dataclass
@toml_config(root_comment="Application configuration")
class Config(TomlDataclass):
    value: int = field(metadata={"description": "Example value"})
```

The `Config` class definition above is equivalent to the following without using `toml_config(...)`:

```python
@dataclass
class Config(TomlDataclass):
    """Application configuration"""
    value: int = field(metadata={"description": "Example value"})

```

## `json_config(...)`

Decorator for configuring JSON behavior on a class.

### Arguments

- `ser`: a custom `json.JSONEncoder` subclass for serialization
- `de`: `dacite.Config` used during deserialization

### Dataclass Field Metadata

Dataclass fields can be annotated with the following metadata keys:

- `description`: a string used as a comment in TOML output (can be customized with `description_key` in `toml_config(...)`)
- `toml`: a string used as the serialized key in TOML output (can be customized with `rename_key` in `toml_config(...)`)
- `typecheck`: a callable used for custom validation during deserialization (can be customized with `typecheck_key` in `toml_config(...)`)

#### Type Validation

The type validation is performed during dataclass instantiation. If a field has a `typecheck` validator,
the validator is called with the field value and its annotation. If the validator raises a `ValueError`, the instantiation will fail with the same error. The type checking function has the following signature:

```python
from typing import Any, Annotated, Callable

TypeChecker = Callable[[Any, Annotated], None]
```

### Example

```python
from dataclasses import dataclass
from json import JSONEncoder

from serde_dataclass import JsonDataclass, json_config


class CustomEncoder(JSONEncoder):
    pass


@dataclass
@json_config(ser=CustomEncoder)
class Payload(JsonDataclass):
    name: str
```
