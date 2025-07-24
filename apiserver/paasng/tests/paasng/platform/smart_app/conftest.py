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

from pathlib import Path
from typing import Dict

import pytest
import yaml

from paasng.platform.sourcectl.utils import generate_temp_file
from tests.paasng.platform.sourcectl.packages.utils import V2_APP_DESC_EXAMPLE, gen_tar


@pytest.fixture()
def contents() -> Dict:
    """The default contents for making tar file."""
    return {"app_desc.yaml": yaml.safe_dump(V2_APP_DESC_EXAMPLE)}


@pytest.fixture()
def tar_path(contents):
    with generate_temp_file() as file_path:
        gen_tar(file_path, contents)
        yield file_path


@pytest.fixture()
def assets_rootpath():
    return Path(__file__).parent / "assets"
