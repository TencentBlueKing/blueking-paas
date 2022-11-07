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

from paasng.platform.core.storages.utils import SADBManager, make_sa_conn_string


@pytest.mark.parametrize(
    "driver_type, config, expected",
    [
        (
            (
                "test",
                dict(NAME="f1", USER="f2", PASSWORD="f3", HOST="f4", PORT="f5"),
                "mysql+test://f2:f3@f4:f5/f1?charset=utf8",
            )
        )
    ],
)
def test_make_sa_conn_string(driver_type, config, expected):
    assert expected == make_sa_conn_string(config, driver_type)


class TestSADBManager:
    @pytest.mark.parametrize(
        "config, expected", [((dict(NAME="f1", USER="f2", PASSWORD="f3", HOST="f4", PORT="f5"), "f4:f5:f2:f1"))]
    )
    def test_make_uni_key(self, config, expected):
        assert SADBManager.make_uni_key(config) == expected
