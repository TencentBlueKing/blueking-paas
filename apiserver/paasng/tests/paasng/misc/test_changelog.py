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
from django.utils.translation import get_language

from paasng.misc.changelog.query import Changelog

TEST_CHANGELOG_FILE_NAMES = [
    {"name": "V1.0.0_2022-10-17.md", "valid": True},
    {"name": "V1.1.17_2022-10-17.md", "valid": True},
    {"name": "V1.0.0-beta_2022-10-17.md", "valid": True},
    {"name": "V1.1.2_2022-10-17.md", "valid": True},
    {"name": "v1.1.2_2022-10-17.md", "valid": False},
    {"name": "V1.0.1-2022-10-17.md", "valid": False},
    {"name": "V1.0.18_2022-13-17.md", "valid": False},
    {"name": "V1.2.0_2022-10-17.txt", "valid": False},
]


class TestChangelog:
    @pytest.fixture(autouse=True)
    def init_changelog_dir(self, tmp_path):
        d = tmp_path / get_language()
        d.mkdir()

        for file in TEST_CHANGELOG_FILE_NAMES:
            f = d / file["name"]
            f.write_text(f"# {file['name'].partition('_')[0]}")  # type: ignore

    def test_list_logs(self, tmp_path):
        logs = Changelog(tmp_path).list_logs()

        # 验证过滤掉非法文件名
        assert len(logs) == len([file for file in TEST_CHANGELOG_FILE_NAMES if file["valid"]])

        # 验证按照版本号语义降序排序
        assert logs[0].version == "V1.1.17"
        assert logs[0].content == "# V1.1.17"
        assert logs[1].version == "V1.1.2"
        assert logs[2].version == "V1.0.0"
        assert logs[3].version == "V1.0.0-beta"
