from __future__ import annotations
from dacite import Config
from dacite.exceptions import MissingValueError, UnexpectedDataError, WrongTypeError
from tomlkit.exceptions import ConvertError, ParseError
from tomlkit import register_encoder, item
import astropy.units as astrounits
from astropy.units import Quantity
import numpy as np

from dataclasses import dataclass, field
from enum import Enum
from json import JSONDecodeError, JSONEncoder
from typing import Any, Dict, List, Literal, Optional, Tuple

import pytest

from serde_dataclass import JsonDataclass, TomlDataclass, json_config, toml_config


class Mode(str, Enum):
    DEV = "dev"
    PROD = "prod"


@dataclass
class Credentials:
    username: str = field(metadata={"description": "User name"})
    password: str = field(metadata={"description": "Password"})


@dataclass
class Server:
    host: str = field(metadata={"description": "Host name"})
    port: int = field(default=8080, metadata={"description": "Port number"})


@dataclass
class EmptyConfig(TomlDataclass):
    """An empty configuration
    """
    slits: Dict[str, str] = field(
        default_factory=lambda: {'4861': 'slit'},
        metadata={"description": "Slits dict"}
    )
    name_with_underscore: str = field(
        default="default",
        metadata={"description": "Name with underscore"}
    )

    @classmethod
    def default(cls) -> EmptyConfig:
        return cls(dict({'4861': 'slit'}), name_with_underscore="default")


@dataclass
class AppConfig(TomlDataclass):
    """App configuration"""
    app_name: str = field(
        default="demo",
        metadata={"description": "Application name", "toml": "app-name"},
    )
    log_level: Literal["debug", "info", "warning", "error"] = field(
        default="info",
        metadata={"description": "Logging level", "toml": "log-level"},
    )
    mode: Mode = field(default=Mode.DEV, metadata={"description": "Run mode"})
    debug: bool = field(default=False, metadata={
                        "description": "Enable debug"})
    thresholds: tuple[int, int, int] = field(
        default=(1, 2, 3),
        metadata={"description": "Threshold tuple"},
    )
    tags: list[str] = field(default_factory=lambda: [
                            "a", "b"], metadata={"description": "Tag list"})
    settings: dict[str, str] = field(
        default_factory=lambda: {"theme": "dark", "region": "us-east"},
        metadata={"description": "Settings dict"},
    )
    creds: Credentials = field(
        default_factory=lambda: Credentials(
            username="admin", password="secret"),
        metadata={"description": "Credentials"},
    )
    servers: list[Server] = field(
        default_factory=lambda: [
            Server("localhost", 8080), Server("backup", 8081)],
        metadata={"description": "Server list"},
    )
    note: Optional[str] = field(default=None, metadata={
                                "description": "Optional note"})
    empty: EmptyConfig = field(
        default_factory=EmptyConfig.default,
        metadata={"description": "Empty config"}
    )


def test_to_toml_contains_root_comment_and_comments():
    cfg = AppConfig()
    text = cfg.to_toml()

    assert "# App configuration" in text
    assert 'app-name = "demo" # Application name' in text
    assert 'log-level = "info" # Logging level' in text
    assert 'mode = "dev" # Run mode' in text
    assert '# Credentials\n\n[creds]' in text
    assert '# Server list\n\n[[servers]]' in text
    assert 'username = "admin" # User name' in text
    assert '# Empty config\n\n[empty]' in text


def test_round_trip_preserves_values():
    cfg = AppConfig()
    loaded = AppConfig.from_toml(cfg.to_toml())

    assert loaded == cfg
    assert loaded.mode is Mode.DEV
    assert loaded.log_level == "info"
    assert loaded.thresholds == (1, 2, 3)
    # Test that the nested dataclass also round-trips correctly
    assert loaded == cfg


def test_key_rename_loads_back_into_python_field_names():
    text = """
# App configuration

app-name = "renamed" # Application name
log-level = "warning" # Logging level
mode = "prod" # Run mode
debug = true # Enable debug
thresholds = [4, 5, 6] # Threshold tuple
tags = ["x", "y"] # Tag list
settings = {theme = "light", region = "eu-west"} # Settings dict

# Credentials
[creds]
username = "alice" # User name
password = "pw" # Password

# Server list
[[servers]]
host = "api"
port = 9000
"""
    cfg = AppConfig.from_toml(text)

    assert cfg.app_name == "renamed"
    assert cfg.log_level == "warning"
    assert cfg.mode is Mode.PROD
    assert cfg.thresholds == (4, 5, 6)


def test_literal_validation_rejects_invalid_value():
    text = """
app-name = "demo"
log-level = "verbose"
mode = "dev"
debug = false
thresholds = [1, 2, 3]
tags = ["a"]
settings = {theme = "dark"}

[creds]
username = "u"
password = "p"

[[servers]]
host = "localhost"
port = 8080
"""
    with pytest.raises(ValueError, match="Expected one of"):
        AppConfig.from_toml(text)


def test_enum_validation_rejects_invalid_value():
    text = """
app-name = "demo"
log-level = "info"
mode = "staging"
debug = false
thresholds = [1, 2, 3]
tags = ["a"]
settings = {theme = "dark"}

[creds]
username = "u"
password = "p"

[[servers]]
host = "localhost"
port = 8080
"""
    with pytest.raises(ValueError, match="Invalid value"):
        AppConfig.from_toml(text)


def test_save_and_load(tmp_path):
    cfg = AppConfig()
    path = tmp_path / "config.toml"

    cfg.save_toml(path)
    loaded = AppConfig.load_toml(path)

    assert loaded == cfg


def test_none_field_is_omitted():
    cfg = AppConfig(note=None)
    text = cfg.to_toml()

    assert "note =" not in text


def test_dict_with_non_string_keys_fails():
    @dataclass
    class BadConfig(TomlDataclass):
        data: dict[int, str]

    # BadConfig = dataclass_toml()(BadConfig)
    cfg = BadConfig(data={1: "x"})

    with pytest.raises(TypeError, match="string keys"):
        cfg.to_toml()


def test_nested_list_of_dataclasses_round_trip():
    cfg = AppConfig(
        servers=[
            Server("one", 1001),
            Server("two", 1002),
            Server("three", 1003),
        ]
    )
    loaded = AppConfig.from_toml(cfg.to_toml())

    assert [s.host for s in loaded.servers] == ["one", "two", "three"]
    assert [s.port for s in loaded.servers] == [1001, 1002, 1003]


def test_set():
    @dataclass
    class SetConfig(TomlDataclass):
        items: set[str] = field(default_factory=lambda: {"a", "b"}, metadata={
                                "description": "A set of items"})
    cfg = SetConfig()
    text = cfg.to_toml()

    assert 'items = ["a", "b"] # A set of items' in text

    loaded = SetConfig.from_toml(text)
    assert loaded.items == {"a", "b"}


@register_encoder
def encode_quantity(value, /, _parent=None, _sort_keys=False):
    if isinstance(value, Quantity):
        return item(f'{value}')
    elif isinstance(value, np.ndarray):
        return item(value.tolist())
    else:
        raise ConvertError


def type_hook_ndarray(value):
    arr = np.array(value)
    return arr


def type_hook_quantity(value):
    q = Quantity(value)
    return q


class NumpyEncoder(JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, Quantity):
            return str(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return super().default(o)


de = Config(type_hooks={
    np.ndarray: type_hook_ndarray,
    Quantity: type_hook_quantity,
})


def test_ndarray():

    @json_config(
        ser=NumpyEncoder,
        de=de,
    )
    @toml_config(de=de)
    @dataclass
    class NumpyConfig(JsonDataclass, TomlDataclass):
        array: np.ndarray = field(default_factory=lambda: np.array(
            [[1, 2], [3, 4]]), metadata={"description": "A numpy array"})
        length: Quantity['length'] = field(
            default_factory=lambda: 5 * astrounits.meter, metadata={"description": "A quantity with units"})

    cfg = NumpyConfig()
    text = cfg.to_toml()

    assert 'array = [[1, 2], [3, 4]] # A numpy array' in text

    loaded = NumpyConfig.from_toml(text)
    assert np.array_equal(loaded.array, np.array([[1, 2], [3, 4]]))
    assert loaded.length == 5 * astrounits.meter

    json_text = cfg.to_json()
    json_loaded = NumpyConfig.from_json(json_text)
    assert np.array_equal(json_loaded.array, loaded.array)
    assert json_loaded.length == loaded.length


def test_json_tuple_field_is_cast_back_to_tuple():
    @dataclass
    class JsonTupleConfig(JsonDataclass):
        thresholds: Tuple[int, int, int]

    cfg = JsonTupleConfig(thresholds=(4, 5, 6))
    loaded = JsonTupleConfig.from_json(cfg.to_json())

    assert loaded.thresholds == (4, 5, 6)
    assert isinstance(loaded.thresholds, tuple)


def test_json_config_rejects_non_encoder_type():
    with pytest.raises(TypeError, match="must be a subclass"):

        @json_config(ser=int) # type: ignore
        @dataclass
        class BadEncoderConfig(JsonDataclass):
            value: int


def test_to_json_rejects_duplicate_encoder_specification():
    class LocalEncoder(JSONEncoder):
        pass

    @json_config(ser=LocalEncoder)
    @dataclass
    class Encoded(JsonDataclass):
        value: int

    with pytest.raises(ValueError, match="Cannot specify both"):
        Encoded(value=1).to_json(cls=JSONEncoder)


def test_from_json_requires_dataclass_decorator():
    class NotDecorated(JsonDataclass):
        value: int

    with pytest.raises(TypeError, match="must be decorated with @dataclass"):
        NotDecorated.from_json('{"value": 1}')


def test_from_toml_requires_dataclass_decorator():
    class NotDecorated(TomlDataclass):
        value: int

    with pytest.raises(TypeError, match="must be decorated with @dataclass"):
        NotDecorated.from_toml("value = 1")


def test_json_custom_de_can_preserve_tuple_casting():
    custom_de = Config(cast=[tuple], check_types=True)

    @json_config(de=custom_de)
    @dataclass
    class JsonTupleConfigWithCustomDe(JsonDataclass):
        thresholds: Tuple[int, int, int]

    loaded = JsonTupleConfigWithCustomDe.from_json('{"thresholds": [7, 8, 9]}')
    assert loaded.thresholds == (7, 8, 9)
    assert isinstance(loaded.thresholds, tuple)


def test_from_json_invalid_json_raises_decode_error():
    @dataclass
    class JsonConfig(JsonDataclass):
        value: int

    with pytest.raises(JSONDecodeError):
        JsonConfig.from_json('{"value": 1')


def test_from_toml_invalid_toml_raises_parse_error():
    @dataclass
    class TomlConfig(TomlDataclass):
        value: int

    with pytest.raises(ParseError):
        TomlConfig.from_toml('value = "unterminated')


def test_from_json_missing_required_field_raises_error():
    @dataclass
    class JsonConfig(JsonDataclass):
        value: int
        name: str

    with pytest.raises(MissingValueError):
        JsonConfig.from_json('{"value": 1}')


def test_from_json_wrong_type_raises_error():
    @dataclass
    class JsonConfig(JsonDataclass):
        value: int

    with pytest.raises(WrongTypeError):
        JsonConfig.from_json('{"value": "oops"}')


def test_json_strict_config_rejects_unexpected_fields():
    @json_config(de=Config(strict=True, cast=[tuple], check_types=True))
    @dataclass
    class StrictJsonConfig(JsonDataclass):
        value: int

    with pytest.raises(UnexpectedDataError):
        StrictJsonConfig.from_json('{"value": 1, "extra": 2}')


def test_load_toml_missing_file_raises_file_not_found(tmp_path):
    @dataclass
    class TomlConfig(TomlDataclass):
        value: int

    missing = tmp_path / "missing.toml"
    with pytest.raises(FileNotFoundError):
        TomlConfig.load_toml(missing)


def test_tomldataclass():
    @dataclass
    class MyConfig(TomlDataclass):
        """A config with a custom root comment and metadata keys"""
        value: int = field(
            default=42, metadata={
                "description": "The answer", "toml": "the-value"
            }
        )

    cfg = MyConfig()
    text = cfg.to_toml()  # type: ignore
    output = """# A config with a custom root comment and metadata keys

the-value = 42 # The answer
"""
    assert text == output


def test_custom_typecheck():

    def check_qty_is_length(q: Quantity, _) -> None:
        if not q.unit:
            raise ValueError("Quantity must have units")
        if q.unit.physical_type != "length":
            raise ValueError("Quantity must have length units")

    @dataclass
    @toml_config(de=de)
    class TypeCheckConfig(TomlDataclass):
        value: Quantity['length'] = field(
            default_factory=lambda: 5 * astrounits.meter,
            metadata={
                "description": "A quantity with units",
                "typecheck": check_qty_is_length,
            }
        )

    cfg = TypeCheckConfig()
    text = cfg.to_toml()
    assert 'value = "5.0 m" # A quantity with units' in text
    loaded = TypeCheckConfig.from_toml(text)
    assert loaded.value == 5 * astrounits.meter
    modified = text.replace("5.0 m", "5.0 s")
    # TypeCheckConfig.from_toml(modified)  # Should succeed since typecheck is not set
    with pytest.raises(ValueError, match="Custom typecheck failed"):
        TypeCheckConfig.from_toml(modified)

def check_positive(q: int, _) -> None:
    if q <= 0:
        raise ValueError("Value must be positive")
    
@dataclass
class Nested:
    value: int = field(
        default=1,
        metadata={
            "description": "A positive integer",
            "typecheck": check_positive,
        }
    )

def test_custom_typecheck_nested():
    @dataclass
    class Outer(TomlDataclass):
        inner: Nested = field(
            default_factory=Nested,
            metadata={
                "description": "Nested dataclass with typecheck"
            }
        )
        value: int = field(
            default=10,
            metadata={
                "description": "An integer field",
            }
        )
        innerlist: List[Nested] = field(
            default_factory=lambda: [Nested(value=2), Nested(value=3)],
            metadata={
                "description": "A list of Inner dataclasses"
            }
        )

    cfg = Outer()
    text = cfg.to_toml()
    assert 'value = 1 # A positive integer' in text
    loaded = Outer.from_toml(text)
    assert loaded.inner.value == 1
    cfg.innerlist[-1].value = -1
    with pytest.raises(ValueError, match="Custom typecheck failed"):
        cfg.to_toml()
