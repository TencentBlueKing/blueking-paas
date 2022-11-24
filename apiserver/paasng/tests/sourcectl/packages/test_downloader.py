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
import pytest

from paasng.dev_resources.sourcectl.package.downloader import download_file_via_http
from paasng.dev_resources.sourcectl.utils import generate_temp_file
from tests.utils.helpers import generate_random_string


@pytest.mark.parametrize(
    "content",
    [
        b"foo\n",
        b"bar\n",
        b"foo\nbar\n",
    ],
)
def test_download_file_via_http(mock_adapter, content):
    url = f"http://foo.com/{generate_random_string()}"
    with generate_temp_file() as source, generate_temp_file() as dest:
        with open(source, mode="wb") as fh:
            fh.write(content)

        mock_adapter.register(url, open(source, mode="rb"))
        download_file_via_http(url, dest)
        assert source != dest
        with open(dest, "rb") as dh:
            assert dh.read() == content
