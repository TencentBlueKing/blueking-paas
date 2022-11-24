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
from django.core.exceptions import ObjectDoesNotExist

from paas_wl.platform.applications.models import Release
from tests.utils.app import release_setup

pytestmark = pytest.mark.django_db


class TestAppModel:
    def test_app_get_release(self, fake_app):
        release_setup(fake_app=fake_app)
        release_setup(
            fake_app=fake_app, build_params={"procfile": {"web": "command -x -z -y"}}, release_params={"version": 3}
        )

        release = Release.objects.get_latest(fake_app)
        previous = release.get_previous()

        assert release.version == 3
        assert previous.version == 2

    def test_first_release(self, fake_app):
        with pytest.raises(ObjectDoesNotExist):
            Release.objects.get_latest(fake_app).get_previous()
