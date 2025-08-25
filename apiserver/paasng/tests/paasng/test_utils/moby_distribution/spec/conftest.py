# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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
from pathlib import Path

try:
    from pydantic import __version__ as pydantic_version
except ImportError:
    # pydantic <= 1.8.2 does not have __version__
    import pydantic as _pydantic

    pydantic_version = _pydantic.VERSION
import pytest

assets = Path(__file__).parent / "assets"


@pytest.fixture
def docker_manifest_schema1_dict():
    return json.loads((assets / "docker_manifest_schema1.json").read_text())


@pytest.fixture
def docker_manifest_schema2_dict():
    return json.loads((assets / "docker_manifest_schema2.json").read_text())


@pytest.fixture
def oci_manifest_schema1_dict():
    return json.loads((assets / "oci_manifest_schema1.json").read_text())


@pytest.fixture
def auth_response():
    if pydantic_version.startswith("2."):
        return json.loads((assets / "auth_response.pydantic_v2.json").read_text())
    else:
        return json.loads((assets / "auth_response.pydantic_v1.json").read_text())


@pytest.fixture
def image_json_dict():
    if pydantic_version.startswith("2."):
        return json.loads((assets / "image_json.pydantic_v2.json").read_text())
    else:
        return json.loads((assets / "image_json.pydantic_v1.json").read_text())
