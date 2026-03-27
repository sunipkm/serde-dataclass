# %% Imports
from __future__ import annotations
from typing import Any, Callable, Dict, Type
from dacite import Config
from serde_dataclass import JsonDataclass, TomlDataclass, json_config, toml_config
from dataclasses import dataclass, field
from json import JSONEncoder
from astropy import units as u
from astropy.units import Quantity
import numpy as np

from tomlkit import register_encoder, item as tomlitem

from tempfile import TemporaryFile

# %% Encoders and decoders for custom types


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

    @property
    def dacite_conf(self) -> Config:
        return Config(type_hooks=self.dacite_hooks)


class CustomEncoder(JSONEncoder):
    """Custom JSON encoder for astropy Quantity objects."""

    def default(self, o):
        if isinstance(o, Quantity):
            return f'{o}'
        elif isinstance(o, np.ndarray):
            return o.tolist()
        return super().default(o)

# %% Custom class definition


@dataclass
class Nesting:  # Note: The nested dataclass does not need to be
    # decorated with dataclass_json or dataclass_toml
    """A simple nested dataclass to demonstrate nested structures."""
    value: int = field(metadata={'description': 'An integer value'})


@dataclass
@json_config(ser=CustomEncoder, de=CustomHooks().dacite_conf)
@toml_config(de=CustomHooks().dacite_conf)
class NpTest(JsonDataclass, TomlDataclass):
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

# %% Test the class


a = NpTest(
    arr=np.array([[1, 2, 3], [4, 5, 6]]),
    qty=Quantity(1.0, u.dimensionless_unscaled),
)
print(a.to_json(indent=4))
print(a.to_toml())
b = NpTest.from_json(a.to_json())
# print(b)
c = NpTest.from_toml(a.to_toml())
# print(c)
assert a == b
assert b == c
assert c == a

tempfile = TemporaryFile(mode='a+')
tempfile.write(a.to_json())
tempfile.seek(0)
b_from_file = NpTest.from_json(tempfile.read())
assert a == b_from_file

tempfile.seek(0)
tempfile.write(a.to_toml())
tempfile.seek(0)
c_from_file = NpTest.from_toml(tempfile.read())
assert a == c_from_file
# %% Custom type checking


def check_quantity_length(value: Quantity, annotation: Any):
    if value.unit is None:
        raise ValueError(f"Value {value} must have units")
    # Just check that it's a length, but don't raise an error
    if not value.unit.is_equivalent(u.meter):
        raise ValueError(f"Value {value} is not a length")


@dataclass
@toml_config(de=CustomHooks().dacite_conf)
class TypeCheckConfig(TomlDataclass):
    value: Quantity['length'] = field(
        default_factory=lambda: 5 * u.meter,
        metadata={
            "description": "A quantity with units",
            "typecheck": check_quantity_length,
        }
    )


cfg = TypeCheckConfig()
text = cfg.to_toml()
assert 'value = "5.0 m" # A quantity with units' in text
loaded = TypeCheckConfig.from_toml(text)
assert loaded.value == 5 * u.meter
modified = text.replace("5.0 m", "5.0 s")

try:
    TypeCheckConfig.from_toml(modified)  # Should fail since it's not a length
except ValueError as e:
    print(f"Type check failed as expected: {e}")
# %%
