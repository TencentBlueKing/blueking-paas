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
from django.conf import settings

from paas_wl.platform.api import (
    create_app_ignore_duplicated,
    delete_wl_resources,
    get_metadata_by_env,
    update_metadata_by_env,
)
from paas_wl.platform.applications.constants import WlAppType
from paas_wl.platform.applications.models import WlApp

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.mark.django_db(databases=["workloads"])
def test_create_app_ignore_duplicated():
    info = create_app_ignore_duplicated(settings.FOR_TESTS_DEFAULT_REGION, 'foo-app', WlAppType.DEFAULT)
    assert info.name == 'foo-app'

    # Create again with the same name
    recreated_info = create_app_ignore_duplicated(settings.FOR_TESTS_DEFAULT_REGION, 'foo-app', WlAppType.DEFAULT)
    assert recreated_info.uuid == info.uuid


def test_metadata_funcs(bk_app, bk_stag_env, with_wl_apps):
    assert get_metadata_by_env(bk_stag_env).paas_app_code == bk_app.code
    update_metadata_by_env(bk_stag_env, {'paas_app_code': 'foo-updated'})
    assert get_metadata_by_env(bk_stag_env).paas_app_code == 'foo-updated'


def test_delete_wl_resources(bk_stag_env, with_wl_apps):
    assert WlApp.objects.filter(pk=bk_stag_env.engine_app_id).exists()
    delete_wl_resources(bk_stag_env)
    assert not WlApp.objects.filter(pk=bk_stag_env.engine_app_id).exists()
