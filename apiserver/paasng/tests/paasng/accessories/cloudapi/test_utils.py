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

import pytest
from blue_krill.web.std_error import APIError

from paasng.accessories.cloudapi import utils

pytestmark = pytest.mark.django_db


class TestUtils:
    @pytest.mark.parametrize(
        ("mocked_region_map", "region", "expected", "will_error"),
        [
            (
                {
                    "test": "region",
                },
                "test",
                "region",
                False,
            ),
            (
                {},
                "test",
                None,
                True,
            ),
        ],
    )
    def test_get_user_auth_type(self, settings, mocked_region_map, region, expected, will_error):
        settings.REGION_TO_USER_AUTH_TYPE_MAP = mocked_region_map

        if will_error:
            with pytest.raises(APIError):
                utils.get_user_auth_type(region)

            return

        result = utils.get_user_auth_type(region)
        assert result == expected
