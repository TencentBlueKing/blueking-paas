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

from paas_wl.bk_app.applications.models import Release

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestReleaseManager:
    def test_any_successful_empty(self, wl_app):
        assert Release.objects.any_successful(wl_app) is False

    def test_any_successful_positive(self, wl_app, bk_user, wl_build):
        wl_app.release_set.new(bk_user.username, build=wl_build, procfile={"web": "true"})
        assert Release.objects.any_successful(wl_app) is True
