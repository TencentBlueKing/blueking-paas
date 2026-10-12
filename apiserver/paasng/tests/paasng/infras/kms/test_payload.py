# -*- coding: utf-8 -*-
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

import json

import pytest

from paasng.infras.kms.constants import FROZEN_PAYLOAD_SCHEMA_VERSION, PLAINTEXT_MAX_CHARS
from paasng.infras.kms.exceptions import KMSValidationError
from paasng.infras.kms.payload import build_frozen_payload

CONFIG_VERSION_ID = "0b1f4c2e-8d3a-4f6b-9c1d-2e3f4a5b6c7d"
MODULE_ENV_ID = "6a2e0d4c1b3f4e5a8c7d9e0f1a2b3c4d"


def _build(env_vars):
    return build_frozen_payload(
        config_version_id=CONFIG_VERSION_ID, module_environment_id=MODULE_ENV_ID, env_vars=env_vars
    )


def test_payload_contains_schema_and_identifiers():
    data = json.loads(_build({"DB_PASSWORD": "secret"}))
    assert data == {
        "schema_version": FROZEN_PAYLOAD_SCHEMA_VERSION,
        "config_version_id": CONFIG_VERSION_ID,
        "module_environment_id": MODULE_ENV_ID,
        "env": {"DB_PASSWORD": "secret"},
    }


def test_serialization_is_stable_regardless_of_insertion_order():
    assert _build({"B": "2", "A": "1"}) == _build({"A": "1", "B": "2"})


def test_non_ascii_values_are_kept_as_text():
    assert "蓝鲸" in _build({"NAME": "蓝鲸"})


@pytest.mark.parametrize("env_vars", [{"PORT": 8080}, {"FLAG": None}, {"ENABLED": True}])
def test_rejects_non_string_values(env_vars):
    with pytest.raises(KMSValidationError):
        _build(env_vars)


def test_rejects_payload_over_plaintext_limit():
    base_length = len(_build({"K": ""}))
    too_long = "x" * (PLAINTEXT_MAX_CHARS - base_length + 1)
    with pytest.raises(KMSValidationError):
        _build({"K": too_long})


def test_accepts_payload_exactly_at_plaintext_limit():
    base_length = len(_build({"K": ""}))
    text = _build({"K": "x" * (PLAINTEXT_MAX_CHARS - base_length)})
    assert len(text) == PLAINTEXT_MAX_CHARS
