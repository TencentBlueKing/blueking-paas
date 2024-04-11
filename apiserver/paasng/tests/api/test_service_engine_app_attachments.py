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
from unittest import mock

import pytest
from django_dynamic_fixture import G

from paasng.accessories.servicehub.models import RemoteServiceEngineAppAttachment
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

    @mock.patch("paasng.accessories.servicehub.views.mixed_service_mgr.get_or_404")
    @mock.patch("paasng.accessories.servicehub.views.mixed_service_mgr.get_attachment_by_engine_app")
    def test_list(self, get_attachment_by_engine_app, get_or_404, api_client, bk_app, bk_module):
        service = G(Service)
        get_attachment_by_engine_app.side_effect = self.mock_get_attachment_by_engine_app(service.uuid)

        response = api_client.get(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/services/engine-app-attachments/{service.uuid}/"
        )
        assert response.status_code == 200
        assert response.data[0]["credentials_disabled"] is False

    @mock.patch("paasng.accessories.servicehub.views.mixed_service_mgr.get_or_404")
    @mock.patch("paasng.accessories.servicehub.views.mixed_service_mgr.get_attachment_by_engine_app")
    def test_update(self, get_attachment_by_engine_app, get_or_404, api_client, bk_app, bk_module):
        service = G(Service)
        get_attachment_by_engine_app.side_effect = self.mock_get_attachment_by_engine_app(service.uuid)

        response = api_client.put(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/services/engine-app-attachments/{service.uuid}/",
            {"credentials_disabled": True},
        )
        assert response.status_code == 200
        assert response.data[0]["credentials_disabled"] is True
        assert response.data[1]["credentials_disabled"] is True
