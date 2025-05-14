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
from django.core.exceptions import ObjectDoesNotExist

from paas_wl.bk_app.applications.models import Release
from tests.paas_wl.utils.release import create_release

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestAppModel:
    def test_app_get_release(self, wl_app, bk_user):
        create_release(wl_app, bk_user)
        create_release(wl_app, bk_user)

        release = Release.objects.get_latest(wl_app)
        previous = release.get_previous()

        assert release.version == 11
        assert previous.version == 10

    def test_first_release(self, wl_app):
        with pytest.raises(ObjectDoesNotExist):
            Release.objects.get_latest(wl_app).get_previous()
