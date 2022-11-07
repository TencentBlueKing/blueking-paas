# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import pytest

from paasng.dev_resources.sourcectl.models import SPStat
from paasng.dev_resources.sourcectl.package.uploader import generate_storage_path

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "stat, package_name",
    [
        (
            SPStat(name="name", version="v1", size=1, meta_info={}, sha256_signature="signature"),
            "v1:signature:name",
        ),
        (
            SPStat(name="name.tar", version="v2", size=1, meta_info={}, sha256_signature="signature"),
            "v2:signature:name.tar",
        ),
    ],
)
def test_generate_storage_path(bk_module, stat, package_name):
    app_info_prefix = f"{bk_module.application.name}/{bk_module.name}"
    expected = f"{bk_module.region}/{app_info_prefix}/{package_name}"
    assert generate_storage_path(bk_module, stat) == expected
