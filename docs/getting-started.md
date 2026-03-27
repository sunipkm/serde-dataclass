# Getting Started

## Core Concepts

### A Mixin Class
A [mixin](https://en.wikipedia.org/wiki/Mixin) is a class that is not intended for standalone use, but provides methods to be inherited by other classes. [`TomlDataclass`](api.md/#tomldataclass) and [`JsonDataclass`](api.md/#jsondataclass) are mixins that add serialization and deserialization methods to dataclasses.

### Inherit from a mixin

Use [`TomlDataclass`](api.md/#tomldataclass) for TOML support, [`JsonDataclass`](api.md/#jsondataclass) for JSON support, or both.

```python
from dataclasses import dataclass

from serde_dataclass import JsonDataclass, TomlDataclass


@dataclass
class Config(TomlDataclass, JsonDataclass):
    value: int
```

The class itself must still be decorated with `@dataclass`.

### Use field metadata for TOML output

By default, TOML serialization looks for these metadata keys:

- `description`: emitted as a TOML comment
- `toml`: renamed serialized key
- `typecheck`: custom validation callable used after deserialization

```python
from dataclasses import dataclass, field

from serde_dataclass import TomlDataclass


@dataclass
class Config(TomlDataclass):
    retries: int = field(metadata={"description": "Number of retries"})
    log_level: str = field(metadata={"toml": "log-level"})
```

### Nested dataclasses work automatically

Nested dataclasses do not need to inherit from [`TomlDataclass`](api.md/#tomldataclass) or [`JsonDataclass`](api.md/#jsondataclass) unless you want to call serialization methods on them directly.

### TOML omits `None`

Fields with value `None` are skipped in TOML output.

## Supported Types

`serde-dataclass` supports these shapes out of the box:

- Scalars: `str`, `int`, `float`, `bool`
- `Optional[T]`
- `Literal[...]` with value validation
- `Enum` subclasses with value validation
- Nested dataclasses
- `list[T]`
- `tuple[...]` and variadic tuples
- `set[T]` serialized as TOML arrays
- `dict[str, T]`

Following limitations apply:

- dictionary keys must be strings (TOML tables only support string keys)
- unsupported custom objects require serializer and loader hooks

## Validation

### `Literal` and `Enum`

`Literal` fields are checked against the allowed values during deserialization. `Enum` fields are reconstructed from their serialized value and raise `ValueError` on invalid input.

### Custom per-field validation

A validator can be provided in field metadata. The callable receives the loaded value and its annotation, and should raise `ValueError` when the value is invalid.

```python
from dataclasses import dataclass, field

from serde_dataclass import TomlDataclass


def positive(value, _annotation):
    if value <= 0:
        raise ValueError("Value must be positive")


@dataclass
class Limits(TomlDataclass):
    timeout: int = field(
        default=30,
        metadata={
            "description": "Timeout in seconds",
            "typecheck": positive,
        },
    )
```

## Decorator Ordering

When combining [`@dataclass`](https://docs.python.org/3/library/dataclasses.html) with [`@toml_config(...)`](api.md/#toml_config) or [`@json_config(...)`](api.md/#json_config), the decorator ordering is irrelevant.

```python
from dataclasses import dataclass

from serde_dataclass import TomlDataclass, toml_config


@dataclass
@toml_config(root_comment="Example")
class Config(TomlDataclass):
    value: int
```

## Notes and Limitations

- TOML comments are only emitted by TOML serialization, not JSON serialization.
- Arrays of dataclasses are written as TOML arrays of tables.
- Dicts containing dataclass values are written as nested TOML tables.
- Sets are serialized as arrays; ordering is sorted when possible, otherwise no ordering guarantees are provided.
- Deserialization uses [`dacite`](https://github.com/konradhalas/dacite), so advanced coercion should be configured through `dacite.Config`. The configuration can be set globally on a class through [`toml_config(...)`](api.md/#toml_config) and [`json_config(...)`](api.md/#json_config).