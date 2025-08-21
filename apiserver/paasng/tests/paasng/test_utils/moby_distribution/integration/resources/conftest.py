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
import random
import string
from pathlib import Path

import pytest

assets = Path(__file__).parent / "assets"


@pytest.fixture
def repo() -> str:
    return "registry"


@pytest.fixture
def reference() -> str:
    return "2.7.1"


@pytest.fixture
def temp_repo() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=10))


@pytest.fixture
def temp_reference() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=10))


@pytest.fixture
def registry_manifest_schema1():
    return json.loads((assets / "registry_manifest_schema1.json").read_text())


@pytest.fixture
def registry_manifest_schema2():
    return json.loads((assets / "registry_manifest_schema2.json").read_text())


@pytest.fixture
def registry_manifest_schema1_metadata():
    return json.loads((assets / "registry_manifest_schema1_metadata.json").read_text())


@pytest.fixture
def registry_manifest_schema2_metadata():
    return json.loads((assets / "registry_manifest_schema2_metadata.json").read_text())


@pytest.fixture
def alpine_tar():
    return assets / "alpine.tar"


@pytest.fixture
def alpine_append_gzip_layer():
    return assets / "append.tar.gz"


@pytest.fixture
def alpine_append_layer():
    return assets / "append.tar"
