"""Project-wide attrs and cattrs helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cattrs import Converter

if TYPE_CHECKING:
    import attrs


def validate_non_empty_string(_: object, attribute: attrs.Attribute[str], value: str) -> None:
    """Validate that an attrs field contains a non-empty string.

    :param attribute: Metadata for the attrs field being validated.
    :param value: Field value to validate.
    :raises TypeError: If the value is not a string.
    :raises ValueError: If the value is empty.
    """
    if not isinstance(value, str):
        raise TypeError(f"{attribute.name} must be a string")
    if not value:
        raise ValueError(f"{attribute.name} must not be empty")


def _structure_str(value: object, _: type[str]) -> str:
    """Keep configuration strings strict instead of coercing arbitrary values."""
    if not isinstance(value, str):
        raise TypeError(f"Expected str, got {type(value).__name__}")
    return value


cattrs_converter = Converter(forbid_extra_keys=True)
cattrs_converter.register_structure_hook(str, _structure_str)
