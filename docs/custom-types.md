# Custom Types

Custom types need two pieces:

1. A serializer for output.
   - For TOML, a [`tomlkit` encoder](https://tomlkit.readthedocs.io/en/latest/api/#tomlkit.register_encoder). The encoder is a function that takes an object, and optionally the parent container and a boolean indicating whether to sort keys, and returns a TOML item. This function is registered with the `@register_encoder` decorator from `tomlkit`. Note, the registration process appends the encoder to a global list of encoders, so it will be used for all `TomlDataclass` instances in the program. This may create interesting scenarios with registration ordering if there are encoders for subclasses of a type.
   - For JSON, a custom [`JSONEncoder`](https://docs.python.org/3/library/json.html#json.JSONEncoder) class that implements the `default` method to handle the custom type. This encoder is specified in the `ser` parameter of `json_config(...)`.
2. A `dacite.Config(type_hooks=...)` entry for loading. This is specified in the `de` parameter of `json_config(...)` for JSON, and `toml_config(...)` for TOML. The `type_hooks` dictionary maps types to functions that take a string and return an instance of the type. The deserialization process will call the appropriate hook function when it encounters a value that should be deserialized into the custom type.

For TOML, register a [`tomlkit` encoder](https://tomlkit.readthedocs.io/en/latest/api/#tomlkit.register_encoder). For JSON, provide a custom [`JSONEncoder`](https://docs.python.org/3/library/json.html#json.JSONEncoder) if the standard library encoder cannot handle the object.

## Minimal Example

The following example shows how to serialize and deserialize `numpy.ndarray` objects.

```python
from dataclasses import dataclass, field
from json import JSONEncoder

import numpy as np
from dacite import Config
from tomlkit import item as tomlitem, register_encoder

from serde_dataclass import JsonDataclass, TomlDataclass, json_config, toml_config


@register_encoder
def encode_ndarray(obj, /, _parent=None, _sort_keys=False):
    if isinstance(obj, np.ndarray):
        return tomlitem(obj.tolist())
    raise TypeError(f"Unsupported type: {type(obj)!r}")


class ArrayEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


array_hooks = Config(type_hooks={np.ndarray: np.array})


@dataclass
@json_config(ser=ArrayEncoder, de=array_hooks)
@toml_config(de=array_hooks)
class ArrayConfig(TomlDataclass, JsonDataclass):
    data: np.ndarray = field(metadata={"description": "Matrix values"})
```

## Full Example

A complete example with `numpy` and `astropy` is available in the repository at [`examples/custom_types.py`](https://github.com/sunipkm/serde-dataclass/blob/master/examples/custom_types.py).
