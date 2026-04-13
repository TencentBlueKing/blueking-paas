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

from paasng.platform.sourcectl.utils import find_content_root


class TestFindContentRoot:
    def test_single_top_level_dir(self, tmp_path: Path):
        """When archive extracts to a single directory, return that directory."""
        inner = tmp_path / "myproject"
        inner.mkdir()
        (inner / "app.py").write_text("print('hi')")
        assert find_content_root(tmp_path) == inner

    def test_multiple_entries(self, tmp_path: Path):
        """When archive extracts to multiple entries, return the extract dir itself."""
        (tmp_path / "app.py").write_text("print('hi')")
        (tmp_path / "Dockerfile").write_text("FROM python:3.11")
        assert find_content_root(tmp_path) == tmp_path
