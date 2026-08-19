from typing import TypeVar

import attrs
from cattrs.errors import BaseValidationError

from app_spark_api.repository.storage.exceptions import StorageConfigurationError
from app_spark_api.utils import cattrs_converter, validate_non_empty_string


@attrs.frozen
class HostTmpPathConfig:
    """Configuration for storing a source package on the current host."""

    path: str = attrs.field(validator=validate_non_empty_string)


@attrs.frozen
class BkRepoConfig:
    """Configuration for storing a source package in BkRepo."""

    bucket: str = attrs.field(validator=validate_non_empty_string)
    key: str = attrs.field(validator=validate_non_empty_string)


ConfigT = TypeVar("ConfigT", HostTmpPathConfig, BkRepoConfig)


def structure_storage_config(raw_config: object, config_cls: type[ConfigT]) -> ConfigT:
    """Structure and validate a persisted storage configuration.

    :param raw_config: JSON-compatible value loaded from the model configuration.
    :param config_cls: attrs configuration class to structure the value into.
    :return: A validated attrs configuration instance.
    :raises StorageConfigurationError: If the value has missing, extra, incorrectly
        typed, or otherwise invalid fields.
    """
    try:
        return cattrs_converter.structure(raw_config, config_cls)
    except (BaseValidationError, AttributeError, TypeError, ValueError) as exc:
        raise StorageConfigurationError(f"Invalid {config_cls.__name__}: {exc}") from exc
