from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from json import JSONEncoder
from typing import Any, Literal, Optional

import pytest

from toml_dataclass import dataclass_toml, dataclass_json


class Mode(str, Enum):
    DEV = "dev"
    PROD = "prod"


@dataclass
class Credentials:
    username: str = field(metadata={"comment": "User name"})
    password: str = field(metadata={"comment": "Password"})


@dataclass
class Server:
    host: str = field(metadata={"comment": "Host name"})
    port: int = field(default=8080, metadata={"comment": "Port number"})


@dataclass_toml
@dataclass
class EmptyConfig:
    """An empty configuration
    """
    slits: dict[str, str] = field(
        default_factory=dict(
            {'4861': 'slit'}), metadata={"comment": "Slits dict"})
    name_with_underscore: str = field(default="default", metadata={
                                      "comment": "Name with underscore"})

    @classmethod
    def default(cls) -> EmptyConfig:
        return cls(dict({'4861': 'slit'}), name_with_underscore="default")


@dataclass_toml(root_comment="App configuration")
@dataclass
class AppConfig:
    app_name: str = field(
        default="demo",
        metadata={"comment": "Application name", "toml": "app-name"},
    )
    log_level: Literal["debug", "info", "warning", "error"] = field(
        default="info",
        metadata={"comment": "Logging level", "toml": "log-level"},
    )
    mode: Mode = field(default=Mode.DEV, metadata={"comment": "Run mode"})
    debug: bool = field(default=False, metadata={"comment": "Enable debug"})
    thresholds: tuple[int, int, int] = field(
        default=(1, 2, 3),
        metadata={"comment": "Threshold tuple"},
    )
    tags: list[str] = field(default_factory=lambda: [
                            "a", "b"], metadata={"comment": "Tag list"})
    settings: dict[str, str] = field(
        default_factory=lambda: {"theme": "dark", "region": "us-east"},
        metadata={"comment": "Settings dict"},
    )
    creds: Credentials = field(
        default_factory=lambda: Credentials(
            username="admin", password="secret"),
        metadata={"comment": "Credentials"},
    )
    servers: list[Server] = field(
        default_factory=lambda: [
            Server("localhost", 8080), Server("backup", 8081)],
        metadata={"comment": "Server list"},
    )
    note: Optional[str] = field(default=None, metadata={
                                "comment": "Optional note"})
    empty: EmptyConfig = field(default_factory=EmptyConfig.default, metadata={
                               "comment": "Empty config"})


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
    class BadConfig:
        data: dict[int, str]

    BadConfig = dataclass_toml()(BadConfig)
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
    @dataclass_toml
    @dataclass
    class SetConfig:
        items: set[str] = field(default_factory=lambda: {"a", "b"}, metadata={
                                "comment": "A set of items"})
    cfg = SetConfig()
    text = cfg.to_toml()

    assert 'items = ["a", "b"] # A set of items' in text

    loaded = SetConfig.from_toml(text)
    assert loaded.items == {"a", "b"}


try:
    import numpy as np
    from astropy.units import Quantity
    import astropy.units as astrounits
    USENUMPY = True
    from tomlkit import register_encoder, item, string
    from tomlkit.exceptions import ConvertError
    from tomlkit.items import Item

    @register_encoder
    def encode_quantity(value, /, _parent=None, _sort_keys=False):
        if isinstance(value, Quantity):
            return item(f'{value}')
        else:
            raise ConvertError

    @register_encoder
    def encode_ndarray(value, /, _parent=None, _sort_keys=False) -> Item:
        if isinstance(value, np.ndarray):
            return item(value.tolist())
        else:
            raise ConvertError

    def test_ndarray():
        if not USENUMPY:
            pytest.skip("NumPy not available, skipping ndarray test")
        else:
            from dacite import Config

            def type_hook_ndarray(value):
                arr = np.array(value)
                return arr

            def type_hook_quantity(value):
                q = Quantity(value)
                return q

            @dataclass_json
            @dataclass_toml(
                config=Config(
                    type_hooks={np.ndarray: type_hook_ndarray, Quantity: type_hook_quantity})
            )
            @dataclass
            class NumpyConfig:
                array: np.ndarray = field(default_factory=lambda: np.array(
                    [[1, 2], [3, 4]]), metadata={"comment": "A numpy array"})
                length: Quantity['length'] = field(
                    default_factory=lambda: 5 * astrounits.meter, metadata={"comment": "A quantity with units"})

            cfg = NumpyConfig()
            text = cfg.to_toml() # type: ignore

            assert 'array = [[1, 2], [3, 4]] # A numpy array' in text

            loaded = NumpyConfig.from_toml(text) # type: ignore
            assert np.array_equal(loaded.array, np.array([[1, 2], [3, 4]]))
            assert loaded.length == 5 * astrounits.meter

            class NumpyEncoder(JSONEncoder):
                def default(self, o: Any) -> Any:
                    if isinstance(o, Quantity):
                        return str(o)
                    if isinstance(o, np.ndarray):
                        return o.tolist()
                    return super().default(o)
            json_text = cfg.to_json(cls=NumpyEncoder)
            json_loaded = NumpyConfig.from_json(json_text, config=Config(
                type_hooks={np.ndarray: type_hook_ndarray, Quantity: type_hook_quantity}))
            assert np.array_equal(json_loaded.array, loaded.array)
            assert json_loaded.length == loaded.length


except ImportError:
    USENUMPY = False


def test_tomldataclass():
    @dataclass_toml
    @dataclass
    class MyConfig:
        """A config with a custom root comment and metadata keys"""
        value: int = field(
            default=42, metadata={
                "comment": "The answer", "toml": "the-value"
            }
        )

    cfg = MyConfig()
    text = cfg.to_toml() # type: ignore
    output = """# A config with a custom root comment and metadata keys

the-value = 42 # The answer
"""
    assert text == output
