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

from typing import TypeVar

import attrs

from app_spark_api.repository.storage.exceptions import StorageConfigurationError
from app_spark_api.utils import structure_config, validate_non_empty_string


@attrs.frozen
class HostTmpPathConfig:
    """Configuration for storing a blob on the current host."""

    path: str = attrs.field(validator=validate_non_empty_string)


@attrs.frozen
class BkRepoConfig:
    """Configuration for storing a blob in BkRepo."""

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
    return structure_config(raw_config, config_cls, error_cls=StorageConfigurationError)
