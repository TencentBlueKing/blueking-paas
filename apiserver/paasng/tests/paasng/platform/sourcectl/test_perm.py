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

from unittest import mock

import pytest

from paasng.infras.accounts.constants import AccountFeatureFlag as AFF
from paasng.infras.accounts.models import AccountFeatureFlag
from paasng.platform.sourcectl.perm import UserSourceProviders, render_providers

pytestmark = pytest.mark.django_db


class TestUserSourceProviders:
    @pytest.mark.parametrize(
        ("flag", "provider_in_results"),
        [
            (True, True),
            (False, False),
        ],
    )
    def test_list_availables(self, bk_user, flag, provider_in_results):
        user_providers = UserSourceProviders(bk_user)
        AccountFeatureFlag.objects.set_feature(bk_user, AFF.ENABLE_DFT_BK_SVN, flag)  # type: ignore
        providers = user_providers.list_available()
        assert ("dft_bk_svn" in providers) == provider_in_results

    @pytest.mark.usefixtures("_init_tmpls")
    def test_list_module_availables(self, bk_user, bk_module_full):
        user_providers = UserSourceProviders(bk_user)
        source_obj = bk_module_full.get_source_obj()

        with mock.patch.object(user_providers, "list_available") as mocked_func:
            mocked_func.return_value = []
            assert user_providers.list_available() == []

            module_providers = user_providers.list_module_available(bk_module_full)
            assert module_providers != []
            assert source_obj.get_source_type() in module_providers


def test_render_providers():
    results = render_providers(["dft_bk_svn"])
    assert isinstance(results, list)
    assert len(results) > 0
