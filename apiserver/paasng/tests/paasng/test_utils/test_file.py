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

import pytest

from paasng.utils.file import path_may_escape


@pytest.mark.parametrize(
    ("input_path", "expected"),
    [
        # Absolute path and invalid relative paths
        ("/etc/passwd", True),
        ("../../../../app_desc.yaml", True),
        ("../../..", True),
        # Safe relative paths within the root directory
        ("src/main.py", False),
        # Edge cases with single parent directory navigation
        ("folder/../file.txt", False),
        ("folder/subfolder/../file.txt", False),
    ],
)
def test_path_may_escape(input_path, expected):
    assert path_may_escape(input_path) == expected
