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

from paasng.accessories.publish.sync_market.managers import AppTagManger
from paasng.core.core.storages.sqlalchemy import console_db
from tests.utils.helpers import generate_random_string


@pytest.fixture()
def tag_name():
    return generate_random_string(length=6)


@pytest.fixture()
def create_default_tag(tag_name):
    with console_db.session_scope() as session:
        try:
            AppTagManger(session).create_tag(
                {
                    "code": generate_random_string(length=6),
                    "name": tag_name,
                    "is_select": 1,
                }
            )
        except TypeError:
            # 兼容企业版桌面没有 is_select 的情况
            AppTagManger(session).create_tag(
                {
                    "code": generate_random_string(length=6),
                    "name": tag_name,
                    "index": 100,
                }
            )

        # 同步应用
        AppTagManger(session).sync_tags_from_console()
    return tag_name
