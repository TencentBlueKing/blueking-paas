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
from pathlib import PosixPath

import pytest

from paasng.changelog.log import Changelog


class TestChangelog:
    @pytest.mark.parametrize(
        'file_name, is_valid',
        [
            ('v1.0.0_2022-10-17.md', True),
            ('V1.0.0_2022-10-17.md', True),
            ('V1.0.0-beta_2022-10-17.md', True),
            ('V1.0.1-2022-10-17.md', False),
            ('V1.0.1_2022-13-17.md', False),
            ('v1.0.0_2022-10-17.txt', False),
        ],
    )
    def test_is_valid_file_name(self, file_name, is_valid):
        changelog = Changelog()
        assert changelog._is_valid_file_name(PosixPath(file_name)) is is_valid
