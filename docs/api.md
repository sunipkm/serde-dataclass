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

<!--phmdoctest-skip-->

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

## Dataclass Field Metadata

Dataclass fields can be annotated with the following metadata keys:

- `description`: a string used as a comment in TOML output (can be customized with `description_key` in `toml_config(...)`)
- `toml`: a string used as the serialized key in TOML output (can be customized with `rename_key` in `toml_config(...)`)
- `typecheck`: a callable used for custom validation during deserialization (can be customized with `typecheck_key` in `toml_config(...)`)

### Type Validation

The type validation is performed during dataclass instantiation. If a field has a `typecheck` validator,
the validator is called with the field value and its annotation. If the validator raises a `ValueError`, the instantiation will fail with the same error. The type checking function has the following signature:

```python
from typing import Any, Annotated, Callable

TypeChecker = Callable[[Any, Annotated], None]
```

### Example

```python
from dataclasses import dataclass, field
from typing import Annotated, Any

from serde_dataclass import TomlDataclass, toml_config

def positive_int_checker(value: Any, annotation: Annotated) -> None:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"Expected a positive integer, got {value!r}")

@dataclass
@toml_config(typecheck_key="typecheck")
class Config(TomlDataclass):
    value: int = field(default=1, metadata={"typecheck": positive_int_checker})

cfg = Config(value=5)
cfg.to_toml()  # This will succeed
cfg.value = -1
try:
    cfg.to_toml()  # This will raise a ValueError due to failed type check
except ValueError as e:
    print(f"Type check failed as expected: {e}")
```

## Nesting and Composition

The `TomlDataclass` and `JsonDataclass` base classes can be used in nested dataclass structures without any special configuration. Type checking and custom metadata will work as expected in nested contexts.
Nesting is supported regardless of whether the nested dataclasses also inherit from `TomlDataclass` or `JsonDataclass`. This allows for flexible composition of dataclasses with different serialization needs.

### Example

<!--phmdoctest-skip-->

```python
from typing import List, Any, Annotated
from dataclasses import dataclass, field
from serde_dataclass import TomlDataclass, toml_config

def positive_int_checker(value: Any, annotation: Annotated) -> None:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"Expected a positive integer, got {value!r}")

@dataclass
class InnerConfig:
    value: int = field(default=1, metadata={"description": "A positive integer", "typecheck": positive_int_checker})

@dataclass
@toml_config(typecheck_key="typecheck")
class OuterConfig(TomlDataclass):
    inner: List[InnerConfig] = field(default_factory=[InnerConfig(i) for i in range(10)], metadata={"description": "Nested configuration"})
    value: int = field(default=10, metadata={"description": "Another positive integer"})

cfg = OuterConfig()
text = cfg.to_toml()  # This will succeed
cfg.inner[0].value = -1
try:
    cfg.to_toml()  # This will raise a ValueError due to failed type check in the nested dataclass
except ValueError as e:
    print(f"Type check failed as expected: {e}")
```
