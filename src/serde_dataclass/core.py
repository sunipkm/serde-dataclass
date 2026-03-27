from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
import sys
from typing import Annotated, Any, Callable, Literal, Optional, TypeVar, Union, get_args, get_origin, get_type_hints

import tomlkit

T = TypeVar("T")

TypeChecker = Callable[[Any, Annotated], None]


class _DataclassEnforcer:
    """
    Base class that enforces subclasses are decorated with @dataclass
    before they can be instantiated.
    """

    def __new__(cls, *args, **kwargs):
        if cls is _DataclassEnforcer:
            return super().__new__(cls)

        if not is_dataclass(cls):
            raise TypeError(
                f"{cls.__name__} must be decorated with @dataclass"
            )

        return super().__new__(cls)


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
    """Convert a value to a Python-compatible type for TOML serialization.

    Args:
        value (Any): The value to convert.

    Raises:
        TypeError: If the value is not of a supported type.

    Returns:
        Any: The converted value.
    """
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
    """Normalize the given value for a dataclass.

    Args:
        value (Any): A dictionary to normalize for the given dataclass.
        cls (type[Any]): The dataclass type to normalize for.
        rename_key (str): Rename the key for dataclass.

    Raises:
        TypeError: If the value is not a dictionary.

    Returns:
        dict[str, Any]: The normalized dictionary.
    """
    if not isinstance(value, dict):
        raise TypeError(
            f"Expected TOML root to decode into dict for {cls.__name__}"
        )

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


def _typecheck_dataclass(vdict, typecheck_key: str):
    cls = type(vdict)
    hints = get_type_hints(type(vdict), include_extras=True)

    for f in fields(cls):
        py_name = f.name
        annotation = hints.get(py_name, f.type)
        typecheck = f.metadata.get(typecheck_key, None)

        if typecheck and annotation is not Any:
            value = getattr(vdict, py_name)
            try:
                typecheck(value, annotation)
            except Exception as e:
                raise ValueError(
                    f"Custom typecheck failed for field '{py_name}' with value {value!r}: {e}"
                ) from e


def _normalize_for_type(*, value: Any, annotation: Any, rename_key: str) -> Any:
    """Normalize the given value for a type annotation.

    Args:
        value (Any): Value to normalize.
        annotation (Any): Type annotation for the value.
        rename_key (str): Rename the key for dataclass.

    Raises:
        ValueError: If the value is not valid for the given annotation.
        TypeError: If the value is not of the expected type.

    Returns:
        Any: The normalized value.
    """
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
            rename_key=rename_key,
        )

    if origin is list and isinstance(value, list):
        inner = args[0] if args else Any
        return [
            _normalize_for_type(
                value=v, annotation=inner,
                rename_key=rename_key
            )
            for v in value
        ]

    if origin is tuple and isinstance(value, list):
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(
                _normalize_for_type(
                    value=v, annotation=args[0],
                    rename_key=rename_key
                )
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
            _normalize_for_type(
                value=v, annotation=inner,
                rename_key=rename_key,
            )
            for v in value
        }

    if origin is dict and isinstance(value, dict):
        key_t, val_t = args if len(args) == 2 else (str, Any)
        if key_t not in (str, Any):
            raise TypeError("TOML only supports string dictionary keys")
        return {
            str(k): _normalize_for_type(
                value=v, annotation=val_t,
                rename_key=rename_key,
            )
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
