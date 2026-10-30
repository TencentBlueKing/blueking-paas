# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""Project-wide attrs and cattrs helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar, get_origin

from cattrs import Converter
from cattrs.cols import list_structure_factory
from cattrs.errors import BaseValidationError
from cattrs.v import format_exception as format_cattrs_exception
from cattrs.v import transform_error

if TYPE_CHECKING:
    from collections.abc import Callable

    import attrs

ConfigT = TypeVar("ConfigT")


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


def make_strict_structure_hook(expected: type, *, reject_bool: bool = False) -> Callable[[object, type], object]:
    """Build a cattrs hook that refuses a value of the wrong JSON type instead of coercing it.

    Example::

        converter.register_structure_hook(int, make_strict_structure_hook(int, reject_bool=True))

    :param expected: The only type a value may already have.
    :param reject_bool: Also refuse bool, which is a subclass of int.
    """

    def structure(value: object, _: type) -> object:
        # bool 是 int 的子类，不单独挡的话 true 会被读成 1。
        if not isinstance(value, expected) or (reject_bool and isinstance(value, bool)):
            raise TypeError(f"Expected {expected.__name__}, got {type(value).__name__}")

        return value

    return structure


def register_strict_list_hook(converter: Converter) -> None:
    """Make converter refuse anything but a list where a list field is declared."""

    def make_hook(type_: type) -> Callable[[object, type], list]:
        structure_items = list_structure_factory(type_, converter)

        def structure(value: object, _: type) -> list:
            # cattrs 默认把任何可迭代对象当成列表：字符串会被拆成单个字符，{} 和 "" 都会变成 []。
            if not isinstance(value, list):
                raise TypeError(f"Expected list, got {type(value).__name__}")

            return structure_items(value, type_)

        return structure

    converter.register_structure_hook_factory(lambda type_: get_origin(type_) is list, make_hook)


cattrs_converter = Converter(forbid_extra_keys=True)
cattrs_converter.register_structure_hook(str, make_strict_structure_hook(str))
register_strict_list_hook(cattrs_converter)


def _describe_failure(exc: BaseException, type_: type | None) -> str:
    """Describe one field-level structuring failure.

    An attrs validator runs inside ``__init__``, i.e. after every field has been structured, so
    cattrs can only attribute it to the class as a whole and words it as a pathless "invalid
    value". The validator's own message is the one that names the field and says what is wrong
    with it, so prefer it whenever there is one.
    """
    if isinstance(exc, (ValueError, TypeError)) and str(exc):
        return str(exc)
    return format_cattrs_exception(exc, type_)


def structure_config(
    raw_config: object,
    config_cls: type[ConfigT],
    *,
    error_cls: type[Exception],
) -> ConfigT:
    """Structure and validate an untyped configuration value into an attrs class.

    Configuration reaches the application as plain JSON or YAML -- from a model column, from a
    settings file -- so the failure it can produce is a library-level one. Callers get a domain
    error of their own instead, which is what keeps cattrs from leaking across module
    boundaries.

    Example::

        config = structure_config(
            {"path": "/tmp/source.tgz"},
            HostTmpPathConfig,
            error_cls=StorageConfigurationError,
        )

    :param raw_config: JSON-compatible value to structure.
    :param config_cls: attrs configuration class to structure the value into.
    :param error_cls: Domain exception raised when the value does not fit ``config_cls``.
    :return: A validated configuration instance.
    :raises Exception: An ``error_cls`` if the value has missing, extra, incorrectly typed, or
        otherwise invalid fields.
    """
    try:
        return cattrs_converter.structure(raw_config, config_cls)
    except BaseValidationError as exc:
        # Detailed validation collects every failure into an exception group whose own str() is
        # just "While structuring X (N sub-exceptions)". Flatten it, or the operator staring at a
        # rejected settings file is never told which key offended.
        reasons = "; ".join(transform_error(exc, format_exception=_describe_failure))
        raise error_cls(f"Invalid {config_cls.__name__}: {reasons}") from exc
    except (AttributeError, TypeError, ValueError) as exc:
        raise error_cls(f"Invalid {config_cls.__name__}: {exc}") from exc
