# serde-dataclass

Helpers for serializing dataclasses to TOML (and JSON) with:

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
pip install serde-dataclass
```

## Example

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
class AppConfig(TomlDataclass): # This subclass-derivation is optional, provides type annotations
    """Application configuration"""  # This docstring will be used as the root comment
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

## Advanced Usage: Custom Types

Custom hooks can be installed for custom types.
The following example handles `numpy` arrays and
`astropy` quantities. The complete, working example
is provided [here](examples/custom_types.py).

#### Custom serializer/deserializer
<!--phmdoctest-skip-->
```python
# %% Encoders and decoders for custom types
# Register tomlkit encoder
@register_encoder
def quantity_to_toml(obj, /, _parent=None, _sort_keys=False):
    """Convert an astropy Quantity to a string representation suitable for TOML serialization.

    Args:
        qty (Quantity): The astropy Quantity to convert.
    Returns:
        str: A string representation of the Quantity in the format "value unit", e.g. "1.0 deg".
    """
    if isinstance(obj, Quantity):
        return tomlitem(f'{obj}')
    elif isinstance(obj, np.ndarray):
        return tomlitem(obj.tolist())
    raise TypeError(f'Object of type {type(obj)} is not a Quantity')
# Generate dacite type hooks
class CustomHooks:
    @staticmethod
    def dacite_quantity_hook(s: str) -> Quantity:
        return Quantity(s)

    @staticmethod
    def dacite_ndarray_hook(s: list) -> np.ndarray:
        return np.array(s)

    @property
    def dacite_hooks(self) -> Dict[Type, Callable[[Any], Any]]:
        return {
            Quantity: self.dacite_quantity_hook,
            np.ndarray: self.dacite_ndarray_hook,
        }
# Custom JSON encoder
class CustomEncoder(JSONEncoder):
    """Custom JSON encoder for astropy Quantity objects."""

    def default(self, o):
        if isinstance(o, Quantity):
            return f'{o}'
        elif isinstance(o, np.ndarray):
            return o.tolist()
        return super().default(o)
```

#### Custom Dataclass
<!--phmdoctest-skip-->
```python
# %% Custom class definition
@dataclass
class Nesting:  # Note: The nested dataclass does not need to
    # derive from TomlDataclass or JsonDataclass
    """A simple nested dataclass to demonstrate nested structures."""
    value: int = field(metadata={'description': 'An integer value'})


@json_config(ser=CustomEncoder, de=Config(type_hooks=CustomHooks().dacite_hooks))
@toml_config(de=Config(type_hooks=CustomHooks().dacite_hooks))
@dataclass
class NpTest(TomlDataclass, JsonDataclass):
    """Test class with a numpy array and an astropy Quantity."""
    arr: np.ndarray = field(metadata={'description': 'A numpy array'})
    qty: Quantity['dimensionless'] = field(
        metadata={'description': 'A dimensionless quantity'})
    nesting: Nesting = field(default_factory=lambda: Nesting(
        42), metadata={'description': 'A nested dataclass'})

    def __eq__(self, other):
        if not isinstance(other, NpTest):
            return NotImplemented
        return np.array_equal(self.arr, other.arr) and self.qty == other.qty
```

#### Usage
<!--phmdoctest-skip-->
```python
# %% Test the class


a = NpTest(
    arr=np.array([[1, 2, 3], [4, 5, 6]]),
    qty=Quantity(1.0, u.dimensionless_unscaled),
)
print(a.to_json(indent=4))
print(a.to_toml())
b = NpTest.from_json(a.to_json())
c = NpTest.from_toml(a.to_toml())
assert a == b
assert b == c
assert c == a
```

This outputs the following JSON:

```json
{
  "arr": [
    [1, 2, 3],
    [4, 5, 6]
  ],
  "qty": "1.0",
  "nesting": {
    "value": 42
  }
}
```

And the following TOML:

```toml
# Test class with a numpy array and an astropy Quantity.

arr = [[1, 2, 3], [4, 5, 6]] # A numpy array
qty = "1.0" # A dimensionless quantity
# A nested dataclass

[nesting]
value = 42 # An integer value
```
