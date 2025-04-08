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
from django.core.management import call_command
from django.core.management.base import SystemCheckError

from paasng.infras.perm_insure.views_perm import INSURE_CHECKING_EXCLUDED_VIEWS


class TestPermConfigured:
    def test_drf_view_not_configured(self):
        new_excluded = INSURE_CHECKING_EXCLUDED_VIEWS.copy()
        # `ApplicationCreateViewSet` is a view that configures no extra permissions, when it
        # is in the excluded list, a SystemCheckError should be raised.
        new_excluded.remove("ApplicationCreateViewSet")

        with (
            mock.patch("paasng.infras.perm_insure.views_perm.INSURE_CHECKING_EXCLUDED_VIEWS", new=new_excluded),
            pytest.raises(SystemCheckError, match=r".*ApplicationCreateViewSet.*no extra permission_classes"),
        ):
            call_command("check")
