from __future__ import annotations

from dataclasses import is_dataclass, asdict as dataclass_asdict
from json import JSONEncoder, loads, dumps
from pathlib import Path
from typing import Literal, Optional, TypeVar, Union
import sys

import tomlkit
from dacite import Config, from_dict

from .core import _DataclassEnforcer, _typecheck_dataclass, _write_dataclass_to_container, _normalize_for_dataclass

T = TypeVar("T")

if sys.version_info >= (3, 11):
    from typing import Self
else:
    Self = TypeVar("Self", bound="_DataclassEnforcer")


class JsonDataclass(_DataclassEnforcer):
    """
    Base class providing JSON serialization/deserialization helpers.

    Configuration is supplied via class attributes, optionally set with
    @json_config(...).
    """

    __json_encoder__: Optional[type[JSONEncoder]] = None
    __json_dacite_config__: Config = Config(
        cast=[tuple],
        check_types=True,
    )
    __json_typecheck_key__: str = "typecheck"

    def to_json(self, **kwargs) -> str:
        """
        Convert this dataclass to a JSON string.

        Arguments:
            **kwargs: Passed through to json.dumps().

        Returns:
            str: JSON string representation of this object.
        """
        ser = type(self).__json_encoder__

        if ser is not None and kwargs.get("cls") is not None:
            raise ValueError(
                "Cannot specify both a custom JSONEncoder and a 'cls' argument to to_json()"
            )

        if ser is not None and not issubclass(ser, JSONEncoder):
            raise TypeError(
                "__json_encoder__ must be a subclass of json.JSONEncoder"
            )

        _preserialize_check(type(self), self, kind="json")  # Ensure type checking is performed before serialization

        kwargs["cls"] = ser
        return dumps(dataclass_asdict(self), **kwargs)  # type: ignore

    @classmethod
    def from_json(cls, text: str, **kwargs) -> Self:
        """
        Create an instance of this class from a JSON string.

        Arguments:
            text: The JSON string to parse.
            kwargs: Passed through to json.loads().

        Returns:
            An instance of this class.
        """
        if not is_dataclass(cls):
            raise TypeError(
                f"{cls.__name__} must be decorated with @dataclass"
            )

        data = loads(text, **kwargs)
        return _perform_type_check(cls, data, kind="json")


class TomlDataclass(_DataclassEnforcer):
    """
    Base class providing TOML serialization/deserialization helpers.

    Configuration is supplied via class attributes, optionally set with
    @toml_config(...).
    """

    __toml_root_comment__: Optional[str] = None
    __toml_metadata_key__: str = "description"
    __toml_rename_key__: str = "toml"
    __toml_dacite_config__: Config = Config(
        cast=[tuple],
        check_types=True,
    )
    __toml_typecheck_key__: str = "typecheck"

    def to_toml(self) -> str:
        """
        Convert this dataclass to a TOML string.

        Returns:
            str: TOML string representation of this object.
        """
        cls = type(self)
        _preserialize_check(cls, self, kind="toml")  # Ensure type checking is performed before serialization
        root_comment = getattr(cls, "__toml_root_comment__", None)
        if root_comment is None and cls.__doc__:
            root_comment = cls.__doc__.strip()

        doc = tomlkit.document()

        if root_comment:
            for line in root_comment.splitlines():
                doc.add(tomlkit.comment(line))
            doc.add(tomlkit.nl())

        _write_dataclass_to_container(
            container=doc,
            obj=self,
            cls=cls,
            metadata_key=getattr(cls, "__toml_metadata_key__", "description"),
            rename_key=getattr(cls, "__toml_rename_key__", "toml"),
        )
        return doc.as_string()

    def save_toml(self, path: Union[str, Path]) -> None:
        """
        Save this dataclass as a TOML file.

        Arguments:
            path: The file path to save to.
        """
        Path(path).write_text(self.to_toml(), encoding="utf-8")

    @classmethod
    def from_toml(cls, text: str) -> Self:
        """
        Create an instance of this class from a TOML string.

        Arguments:
            text: The TOML string to parse.

        Returns:
            An instance of this class.
        """
        if not is_dataclass(cls):
            raise TypeError(
                f"{cls.__name__} must be decorated with @dataclass"
            )

        parsed = tomlkit.parse(text)
        raw = parsed.unwrap()
        normalized = _normalize_for_dataclass(
            value=raw,
            cls=cls,
            rename_key=getattr(cls, "__toml_rename_key__", "toml"),
        )
        return _perform_type_check(cls, normalized, kind="toml")

    @classmethod
    def load_toml(cls, path: Union[str, Path]) -> Self:
        """
        Create an instance of this class from a TOML file.

        Arguments:
            path: The file path to load from.

        Returns:
            An instance of this class.
        """
        if not is_dataclass(cls):
            raise TypeError(
                f"{cls.__name__} must be decorated with @dataclass"
            )

        return cls.from_toml(Path(path).read_text(encoding="utf-8"))


def json_config(
    cls=None,
    /,
    *,
    ser: Optional[type[JSONEncoder]] = None,
    de: Optional[Config] = None,
):
    """
    Configure a JsonDataclass subclass.

    Arguments:
        ser: Optional JSONEncoder subclass to use for to_json serialization.
        de: Optional dacite Config to use for from_json deserialization.
    """

    def decorator(cls: type[T]) -> type[T]:
        if ser is not None:
            if not issubclass(ser, JSONEncoder):
                raise TypeError(
                    "ser argument to json_config must be a subclass of json.JSONEncoder"
                )
            setattr(cls, "__json_encoder__", ser)

        if de is not None:
            setattr(cls, "__json_dacite_config__", de)

        return cls

    if cls is None:
        return decorator
    else:
        return decorator(cls)


def toml_config(
    cls=None,
    /,
    *,
    root_comment: Optional[str] = None,
    description_key: str = "description",
    rename_key: str = "toml",
    typecheck_key: str = "typecheck",
    de: Optional[Config] = None,
):
    """
    Configure a TomlDataclass subclass.

    Arguments:
        root_comment: Optional comment to add at the top of the TOML document.
        description_key: The key in field metadata to look for descriptions. Defaults to "description".
        rename_key: The key in field metadata to look for TOML key renaming. Defaults to "toml".
        typecheck_key: The key in field metadata to look for type checking functions. Defaults to "typecheck".
        de: Optional dacite Config to use for loading.
    """

    def decorator(cls: type[T]) -> type[T]:
        if root_comment is not None:
            resolved_root_comment = root_comment
        else:
            resolved_root_comment = (
                getattr(cls, "__toml_comment__", None)
                or getattr(cls, "__toml_root_comment__", None)
                or (cls.__doc__.strip() if cls.__doc__ else None)
            )

        setattr(cls, "__toml_root_comment__", resolved_root_comment)

        if description_key is not None:
            setattr(cls, "__toml_metadata_key__", description_key)

        if rename_key is not None:
            setattr(cls, "__toml_rename_key__", rename_key)

        if typecheck_key is not None:
            setattr(cls, "__toml_typecheck_key__", typecheck_key)

        if de is not None:
            setattr(cls, "__toml_dacite_config__", de)

        return cls

    if cls is None:
        return decorator
    else:
        return decorator(cls)


def _perform_type_check(cls, normalized, kind: Literal["json", "toml"]):
    dcls = from_dict(
        data_class=cls,
        data=normalized,
        config=getattr(cls, f"__{kind}_dacite_config__"),
    )
    typecheck = getattr(cls, f"__{kind}_typecheck_key__")
    _typecheck_dataclass(dcls, typecheck_key=typecheck)
    return dcls

def _preserialize_check(cls, obj, kind: Literal["json", "toml"]):
    typecheck = getattr(cls, f"__{kind}_typecheck_key__")
    _typecheck_dataclass(obj, typecheck_key=typecheck)