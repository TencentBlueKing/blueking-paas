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

from paasng.infras.accounts.constants import SiteRole
from paasng.infras.accounts.models import UserProfile
from paasng.infras.accounts.permissions.user import user_can_operate_in_region
from tests.utils.helpers import configure_regions

pytestmark = pytest.mark.django_db(databases=["default"])


@pytest.mark.parametrize(
    ("is_admin", "r1_expected", "r2_expected"),
    [
        # Regular user should not be able to create in non-default region
        (False, True, False),
        # Admin user should be able to create in all regions
        (True, True, True),
    ],
)
def test_user_can_operate_in_region(bk_user, is_admin, r1_expected, r2_expected):
    with configure_regions(["r1", "r2"]):
        user_profile = UserProfile.objects.get_profile(bk_user)
        role = SiteRole.ADMIN if is_admin else SiteRole.USER
        user_profile.role = role.value
        user_profile.save(update_fields=["role"])

        assert user_can_operate_in_region(bk_user, "r1") is r1_expected
        assert user_can_operate_in_region(bk_user, "r2") is r2_expected
