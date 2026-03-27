# Custom Types

Custom types need two pieces:

1. A serializer for output.
2. A `dacite.Config(type_hooks=...)` entry for loading.

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

## JSON Example

JSON support maps directly onto standard library JSON encoding.

```python
from dataclasses import dataclass

from serde_dataclass import JsonDataclass


@dataclass
class Payload(JsonDataclass):
    name: str
    count: int


payload = Payload(name="jobs", count=3)
text = payload.to_json(indent=2)
loaded = Payload.from_json(text)

assert loaded == payload
```
