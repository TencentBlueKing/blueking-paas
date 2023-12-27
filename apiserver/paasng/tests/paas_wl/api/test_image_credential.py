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
from django_dynamic_fixture import G

from paas_wl.workloads.images.models import AppUserCredential
from paasng.platform.modules.models.build_cfg import BuildConfig

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def build_config(bk_app, bk_module):
    """创建一个 BuildConfig 对象"""
    build_config = BuildConfig.objects.get_or_create_by_module(bk_module)
    build_config.image_credential_name = "test"
    build_config.save(update_fields=["image_credential_name"])
    return build_config


@pytest.fixture()
def image_credential(bk_app):
    """创建一个 AppUserCredential 对象"""
    return G(AppUserCredential, application_id=bk_app.id, name="test")


class TestAppUserCredentialViewSet:
    def test_destroy(self, api_client, bk_app, image_credential):
        url = "/svc_workloads/api/credentials/applications/" f"{bk_app.code}/image_credentials/{image_credential.name}"
        response = api_client.delete(url)
        assert response.status_code == 204

    def test_destroy_error(self, api_client, bk_app, bk_module, image_credential, build_config):
        """测试镜像凭证已被绑定的情况下，删除镜像凭证"""
        url = "/svc_workloads/api/credentials/applications/" f"{bk_app.code}/image_credentials/{image_credential.name}"
        response = api_client.delete(url)
        assert response.status_code == 400
