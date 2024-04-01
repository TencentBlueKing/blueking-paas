# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import zipfile

import pytest

from paasng.platform.smart_app.path import ZipPath
from paasng.platform.sourcectl.utils import generate_temp_file
from tests.paasng.platform.sourcectl.packages.utils import gen_zip


class TestZipPath:
    @pytest.mark.parametrize(
        ("contents", "path", "expected"),
        [
            ({"中文名称": "1"}, "中文名称", True),
            ({"中文名称": "1"}, "./中文名称", True),
            ({"中文名称/中文名称": "1"}, "中文名称", False),
            ({"中文名称/中文名称": "1"}, "./中文名称", False),
            ({"中文名称/中文名称": "1"}, "中文名称/中文名称", True),
            ({"中文名称/中文名称": "1"}, "./中文名称/中文名称", True),
        ],
    )
    def test_is_file(self, contents, path, expected):
        with generate_temp_file() as file_path:
            gen_zip(file_path, contents)
            with zipfile.ZipFile(file_path) as zf:
                assert ZipPath(zf, path).is_file() == expected

    @pytest.mark.parametrize(
        ("contents", "path", "expected"),
        [
            ({"中文名称": "1"}, "中文名称", False),
            ({"中文名称": "1"}, "./中文名称", False),
            ({"中文名称/中文名称": "1"}, "中文名称", True),
            ({"中文名称/中文名称": "1"}, "./中文名称", True),
            ({"中文名称/中文名称": "1"}, "中文名称/", True),
            ({"中文名称/中文名称": "1"}, "./中文名称/", True),
            ({"中文名称/中文名称": "1"}, "中文名称/中文名称", False),
            ({"中文名称/中文名称": "1"}, "./中文名称/中文名称", False),
        ],
    )
    def test_is_dir(self, contents, path, expected):
        with generate_temp_file() as file_path:
            gen_zip(file_path, contents)
            with zipfile.ZipFile(file_path) as zf:
                assert ZipPath(zf, path).is_dir() == expected
