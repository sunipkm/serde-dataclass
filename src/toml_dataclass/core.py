from __future__ import annotations

from abc import ABC, abstractmethod, update_abstractmethods
from dataclasses import fields, is_dataclass, asdict as dataclass_asdict
from enum import Enum
from importlib.metadata import version
from pathlib import Path
from typing import Any, Callable, Literal, Optional, Protocol, Self, TypeVar, Union, get_args, get_origin, get_type_hints

import tomlkit
from dacite import Config, from_dict

T = TypeVar("T")


def dataclass_json(
    cls=None
):
    """
    Decorate a dataclass to add JSON serialization/deserialization helpers.

    Features:
    - `to_json(**kwargs)` method to serialize to JSON string (accepts same kwargs as `json.dumps()`)
    - `from_json(text, **kwargs)` classmethod to deserialize from JSON string (accepts same kwargs as `json.loads()`, plus optional `config` for dacite Config)
    """
    def decorator(cls: type[T]) -> type[T]:
        from json import dumps, loads
        if not is_dataclass(cls):
            raise TypeError("@dataclass_json must be applied after @dataclass")

        def to_json(self, **kwargs) -> str:
            return dumps(dataclass_asdict(self), **kwargs)

        def from_json(_cls, text: str, config: Optional[Config] = None, **kwargs) -> T:
            data = loads(text, **kwargs)
            return from_dict(cls, data, config)

        to_json.__isabstractmethod__ = False  # type: ignore
        cls.to_json = to_json  # type: ignore
        # if issubclass(cls, JsonCompatible):
        #     install_classmethod(cls, "from_json", from_json)
        # else:
        cls.from_json = classmethod(from_json)  # type: ignore
        # cls.from_json = from_json
        return cls

    if cls is None:
        return decorator
    else:
        return decorator(cls)


def dataclass_toml(
    cls=None,
    *,
    root_comment: Optional[str] = None,
    metadata_key: str = "comment",
    rename_key: str = "toml",
    config: Optional[Config] = None,
):
    """
    Decorate a dataclass to add TOML load/save helpers.

    Arguments:
    - root_comment: Optional comment to add at the top of the TOML document. Can also be set via the class docstring or __toml_comment__ attribute.
    - metadata_key: The key in field metadata to look for comments (default "comment")
    - rename_key: The key in field metadata to look for TOML key renaming (default "toml")
    - config: Optional dacite Config to use for loading.

    Features:
    - `to_toml()` method to serialize to TOML string
    - `from_toml()` classmethod to deserialize from TOML string
    - `save_toml(path)` method to save to a file
    - `load_toml(path)` classmethod to load from a file

    Field comments:
        field(metadata={"comment": "..."})

    Field key renaming:
        field(metadata={"toml": "log-level"})

    Root comment resolution order:
        1. root_comment=...
        2. cls.__toml_comment__
        3. class docstring
    """

    def decorator(cls: type[T]) -> type[T]:
        if not is_dataclass(cls):
            raise TypeError("@dataclass_toml must be applied after @dataclass")

        resolved_root_comment = (
            root_comment
            or getattr(cls, "__toml_comment__", None)
            or (cls.__doc__.strip() if cls.__doc__ else None)
        )

        cfg = config or Config(
            cast=[tuple],
            check_types=True,
        )

        setattr(cls, "__toml_root_comment__", resolved_root_comment)
        setattr(cls, "__toml_metadata_key__", metadata_key)
        setattr(cls, "__toml_rename_key__", rename_key)
        setattr(cls, "__toml_dacite_config__", cfg)

        def to_toml(self) -> str:
            doc = tomlkit.document()

            if resolved_root_comment:
                for line in resolved_root_comment.splitlines():
                    doc.add(tomlkit.comment(line))
                doc.add(tomlkit.nl())

            _write_dataclass_to_container(
                container=doc,
                obj=self,
                cls=type(self),
                metadata_key=metadata_key,
                rename_key=rename_key,
            )
            return doc.as_string()

        def from_toml(cls, text: str) -> T:
            parsed = tomlkit.parse(text)
            raw = parsed.unwrap()
            normalized = _normalize_for_dataclass(
                value=raw,
                cls=cls,  # type: ignore
                rename_key=rename_key,
            )
            return from_dict(
                data_class=cls,  # type: ignore
                data=normalized,
                config=getattr(cls, "__toml_dacite_config__"),
            )

        def save_toml(self, path: Union[str, Path]) -> None:
            Path(path).write_text(self.to_toml(), encoding="utf-8")

        def load_toml(cls, path: Union[str, Path]) -> T:
            return cls.from_toml(Path(path).read_text(encoding="utf-8"))

        to_toml.__isabstractmethod__ = False  # type: ignore
        save_toml.__isabstractmethod__ = False  # type: ignore
        cls.to_toml = to_toml  # type: ignore
        cls.save_toml = save_toml  # type: ignore
        # if not issubclass(cls, TomlCompatible):
        cls.from_toml = classmethod(from_toml)  # type: ignore
        cls.load_toml = classmethod(load_toml)  # type: ignore
        # else:
        #     install_classmethod(cls, "from_toml", from_toml)
        #     install_classmethod(cls, "load_toml", load_toml)

        return cls

    if cls is None:
        return decorator
    else:
        return decorator(cls)


def _add_comment(container: Any, comment: Optional[str]) -> None:
    if comment:
        for line in str(comment).splitlines():
            container.add(tomlkit.comment(line))


def _write_dataclass_to_container(
    *,
    container: Any,
    obj: Any,
    cls: type[Any],
    metadata_key: str,
    rename_key: str,
) -> None:
    type_hints = get_type_hints(cls, include_extras=True)

    for f in fields(obj):
        py_name = f.name
        toml_name = f.metadata.get(rename_key, py_name)
        value = getattr(obj, py_name)
        annotation = type_hints.get(py_name, f.type)
        comment = f.metadata.get(metadata_key)

        if value is None:
            continue

        item, inline_comment = _to_toml_item(
            value=value,
            annotation=annotation,
            metadata_key=metadata_key,
            rename_key=rename_key,
        )

        if inline_comment:
            if comment:
                item.comment(str(comment))
        else:
            _add_comment(container, str(comment) if comment else None)

        container.add(toml_name, item)


def _to_toml_item(
    *,
    value: Any,
    annotation: Any,
    metadata_key: str,
    rename_key: str,
) -> tuple[Any, bool]:
    """
    Returns (toml_item, supports_inline_comment).
    """
    if is_dataclass(value):
        tbl = tomlkit.table()
        _write_dataclass_to_container(
            container=tbl,
            obj=value,
            cls=type(value),
            metadata_key=metadata_key,
            rename_key=rename_key,
        )
        return tbl, False

    if _is_enum_instance(value):
        return tomlkit.item(value.value), True

    origin = get_origin(annotation)
    args = get_args(annotation)

    if _is_optional(annotation):
        inner = next((a for a in args if a is not type(None)), Any)
        return _to_toml_item(
            value=value,
            annotation=inner,
            metadata_key=metadata_key,
            rename_key=rename_key,
        )

    if _is_literal(annotation):
        return tomlkit.item(value), True

    if isinstance(value, set):
        value = list(value)
        try:
            value.sort()
        except TypeError:
            pass

    if isinstance(value, list):
        if value and all(is_dataclass(v) for v in value):
            arr = tomlkit.aot()
            for elem in value:
                tab = tomlkit.table()
                _write_dataclass_to_container(
                    container=tab,
                    obj=elem,
                    cls=type(elem),
                    metadata_key=metadata_key,
                    rename_key=rename_key,
                )
                arr.append(tab)
            return arr, False

        arr = tomlkit.array()
        for elem in value:
            arr.append(_to_python_compatible(elem))
        return tomlkit.item(arr), True

    if isinstance(value, tuple):
        arr = tomlkit.array()
        for elem in value:
            arr.append(_to_python_compatible(elem))
        return tomlkit.item(arr), True

    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise TypeError("TOML only supports string keys in dictionaries")

        if value and all(is_dataclass(v) for v in value.values()):
            parent = tomlkit.table()
            for k, v in value.items():
                sub = tomlkit.table()
                _write_dataclass_to_container(
                    container=sub,
                    obj=v,
                    cls=type(v),
                    metadata_key=metadata_key,
                    rename_key=rename_key,
                )
                parent.add(k, sub)
            return parent, False

        inline = tomlkit.inline_table()
        for k, v in value.items():
            inline[k] = _to_python_compatible(v)
        return inline, True

    return tomlkit.item(value), True


def _to_python_compatible(value: Any) -> Any:
    if is_dataclass(value):
        return {
            f.name: _to_python_compatible(getattr(value, f.name))
            for f in fields(value)
            if getattr(value, f.name) is not None
        }

    if _is_enum_instance(value):
        return value.value

    if isinstance(value, list):
        return [_to_python_compatible(v) for v in value]

    if isinstance(value, tuple):
        return [_to_python_compatible(v) for v in value]

    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise TypeError("TOML only supports string keys in dictionaries")
        return {k: _to_python_compatible(v) for k, v in value.items()}

    return value


def _normalize_for_dataclass(*, value: Any, cls: type[Any], rename_key: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(
            f"Expected TOML root to decode into dict for {cls.__name__}")

    hints = get_type_hints(cls, include_extras=True)
    out: dict[str, Any] = {}

    for f in fields(cls):
        py_name = f.name
        toml_name = f.metadata.get(rename_key, py_name)
        annotation = hints.get(py_name, f.type)

        if toml_name in value:
            out[py_name] = _normalize_for_type(
                value=value[toml_name],
                annotation=annotation,
                rename_key=rename_key,
            )

    return out


def _normalize_for_type(*, value: Any, annotation: Any, rename_key: str) -> Any:
    if annotation is Any:
        return value

    origin = get_origin(annotation)
    args = get_args(annotation)

    if _is_optional(annotation):
        if value is None:
            return None
        inner = next((a for a in args if a is not type(None)), Any)
        return _normalize_for_type(value=value, annotation=inner, rename_key=rename_key)

    if _is_literal(annotation):
        allowed = args
        if value not in allowed:
            raise ValueError(f"Expected one of {allowed!r}, got {value!r}")
        return value

    if _is_enum_type(annotation):
        try:
            return annotation(value)
        except Exception as e:
            names = [m.name for m in annotation]
            vals = [m.value for m in annotation]
            raise ValueError(
                f"Invalid value {value!r} for enum {annotation.__name__}. "
                f"Expected one of values {vals!r} or names {names!r}."
            ) from e

    if is_dataclass(annotation) and isinstance(value, dict):
        return _normalize_for_dataclass(
            value=value,
            cls=annotation,  # type: ignore
            rename_key=rename_key
        )

    if origin is list and isinstance(value, list):
        inner = args[0] if args else Any
        return [
            _normalize_for_type(value=v, annotation=inner,
                                rename_key=rename_key)
            for v in value
        ]

    if origin is tuple and isinstance(value, list):
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(
                _normalize_for_type(
                    value=v, annotation=args[0], rename_key=rename_key)
                for v in value
            )
        if args:
            return tuple(
                _normalize_for_type(
                    value=v,
                    annotation=args[i] if i < len(args) else Any,
                    rename_key=rename_key,
                )
                for i, v in enumerate(value)
            )
        return tuple(value)

    if origin is set and isinstance(value, list):
        inner = args[0] if args else Any
        return {
            _normalize_for_type(value=v, annotation=inner,
                                rename_key=rename_key)
            for v in value
        }

    if origin is dict and isinstance(value, dict):
        key_t, val_t = args if len(args) == 2 else (str, Any)
        if key_t not in (str, Any):
            raise TypeError("TOML only supports string dictionary keys")
        return {
            str(k): _normalize_for_type(value=v, annotation=val_t, rename_key=rename_key)
            for k, v in value.items()
        }

    if origin is Union:
        last_error: Exception | None = None
        for candidate in args:
            if candidate is type(None):
                continue
            try:
                return _normalize_for_type(
                    value=value,
                    annotation=candidate,
                    rename_key=rename_key,
                )
            except Exception as e:
                last_error = e
        if last_error:
            raise last_error

    return value


def _is_optional(annotation: Any) -> bool:
    origin = get_origin(annotation)
    return origin is Union and any(arg is type(None) for arg in get_args(annotation))


def _is_literal(annotation: Any) -> bool:
    return get_origin(annotation) is Literal


def _is_enum_type(annotation: Any) -> bool:
    return isinstance(annotation, type) and issubclass(annotation, Enum)


def _is_enum_instance(value: Any) -> bool:
    return isinstance(value, Enum)
