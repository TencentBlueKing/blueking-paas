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

import datetime
from unittest import mock

import pytest
from django_dynamic_fixture import G

from paasng.accessories.servicehub.models import RemoteServiceEngineAppAttachment
from paasng.accessories.servicehub.services import ServiceInstanceObj
from paasng.accessories.services.models import Service

pytestmark = pytest.mark.django_db


class TestServiceEngineAppAttachmentViewSet:
    def mock_get_attachment_by_engine_app(self, service_id):
        def side_effect(*args, **kwargs):
            return G(
                RemoteServiceEngineAppAttachment,
                engine_app=args[1],
                service_id=service_id,
            )

        return side_effect

    def create_mock_rel(self, service, credentials_enabled, create_time: "datetime.datetime", **credentials):
        rel = mock.MagicMock()
        rel.get_instance.return_value = ServiceInstanceObj(
            uuid=service.uuid, credentials=credentials, config={}, create_time=create_time
        )
        rel.get_service.return_value = service
        rel.db_obj.credentials_enabled = credentials_enabled
        return rel

    @mock.patch("paasng.accessories.servicehub.views.mixed_service_mgr.get_or_404")
    @mock.patch("paasng.accessories.servicehub.views.mixed_service_mgr.get_attachment_by_engine_app")
    def test_list(self, get_attachment_by_engine_app, get_or_404, api_client, bk_app, bk_module):
        service = G(Service)
        get_attachment_by_engine_app.side_effect = self.mock_get_attachment_by_engine_app(service.uuid)

        response = api_client.get(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/services/{service.uuid}/credentials_enabled/"
        )
        assert response.status_code == 200
        assert response.data[0]["credentials_enabled"] is True

    @mock.patch("paasng.accessories.servicehub.views.mixed_service_mgr.get_or_404")
    @mock.patch("paasng.accessories.servicehub.views.mixed_service_mgr.get_attachment_by_engine_app")
    def test_update(self, get_attachment_by_engine_app, get_or_404, api_client, bk_app, bk_module):
        service = G(Service)
        get_attachment_by_engine_app.side_effect = self.mock_get_attachment_by_engine_app(service.uuid)

        response = api_client.put(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/services/{service.uuid}/credentials_enabled/",
            {"credentials_enabled": False},
        )
        assert response.status_code == 200
        assert response.data[0]["credentials_enabled"] is False
        assert response.data[1]["credentials_enabled"] is False

    @mock.patch("paasng.accessories.servicehub.manager.MixedServiceMgr.list_provisioned_rels")
    def test_config_vars(self, list_provisioned_rels, api_client, bk_app, bk_module):
        service = G(Service)
        credentials_disabled_service = G(Service)
        list_provisioned_rels.return_value = [
            self.create_mock_rel(service, True, datetime.datetime(2020, 1, 1), a=1, b=1),
            # 增强服务环境变量不写入
            self.create_mock_rel(credentials_disabled_service, False, datetime.datetime(2020, 1, 1), c=1),
        ]

        response = api_client.get(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/services/config_var_keys/",
        )
        assert response.status_code == 200
        # 返回的增强服务名称列表
        return_svc_names = list(response.data.keys())
        assert service.display_name in return_svc_names
        assert set(response.data[service.display_name]) == {"a", "b"}
        # 增强服务环境变量设置为不写入则不返回
        assert credentials_disabled_service.display_name not in return_svc_names
