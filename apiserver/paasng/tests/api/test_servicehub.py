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
import uuid
from unittest import mock

import pytest
from django.test.utils import override_settings
from django_dynamic_fixture import G
from rest_framework import status

from paasng.accessories.servicehub.local.manager import LocalServiceObj
from paasng.accessories.servicehub.models import RemoteServiceEngineAppAttachment
from paasng.accessories.servicehub.remote.manager import RemoteServiceObj
from paasng.accessories.servicehub.services import ServiceInstanceObj
from paasng.accessories.services.models import Service, ServiceCategory
from paasng.core.tenant.user import DEFAULT_TENANT_ID

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
            uuid=service.uuid,
            credentials=credentials,
            config={},
            create_time=create_time,
            tenant_id=DEFAULT_TENANT_ID,
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


class TestUnboundServiceEngineAppAttachmentViewSet:
    def create_instance(self, create_time, should_hidden_fields, should_remove_fields, **credentials):
        return ServiceInstanceObj(
            uuid=str(uuid.uuid4()),
            credentials=credentials,
            config={},
            create_time=create_time,
            tenant_id=DEFAULT_TENANT_ID,
            should_hidden_fields=should_hidden_fields,
            should_remove_fields=should_remove_fields,
        )

    def create_mock_rel(self, service, instance):
        rel = mock.MagicMock()
        rel.get_instance.return_value = instance
        rel.get_service.return_value = service
        rel.db_obj.service_id = str(service.uuid)
        rel.db_obj.service_instance_id = instance.uuid
        return rel

    @mock.patch("paasng.accessories.servicehub.views.mixed_service_mgr.list_unbound_instance_rels")
    @mock.patch("paasng.accessories.servicehub.views.mixed_service_mgr.get_or_404")
    def test_list_by_module(self, mock_get_or_404, mock_list_unbound_instance_rels, api_client, bk_app, bk_module):
        service1 = G(
            Service, uuid=uuid.uuid4(), logo_b64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAZAAAAGQCAYAAAC"
        )
        service2 = G(
            Service, uuid=uuid.uuid4(), logo_b64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAZAAAAGQCAYAAAC"
        )
        service2_dict = vars(service2)
        service2_dict["category"] = G(ServiceCategory).id
        mock_get_or_404.side_effect = (
            lambda service_id: LocalServiceObj.from_db_object(service1)
            if service_id == str(service1.uuid)
            else RemoteServiceObj.from_data(service2_dict)
        )

        mock_rel1 = self.create_mock_rel(
            service1, self.create_instance(datetime.datetime(2020, 1, 1), [], [], a=1, b=1)
        )
        mock_rel2 = self.create_mock_rel(service1, self.create_instance(datetime.datetime(2020, 1, 1), [], [], c=1))
        mock_rel3 = self.create_mock_rel(
            service2, self.create_instance(datetime.datetime(2020, 1, 1), [], [], d=1, e=1)
        )
        mock_rel4 = self.create_mock_rel(service2, self.create_instance(datetime.datetime(2020, 1, 1), [], [], f=1))
        mock_list_unbound_instance_rels.return_value = [mock_rel1, mock_rel2, mock_rel3, mock_rel4]

        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/services/unbound_attachments/"

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert len(response_data) == 2
        assert response_data[0]["service"]["uuid"] == str(service1.uuid)
        assert response_data[0]["count"] == 4
        assert response_data[0]["unbound_instances"][0] == {
            "instance_id": mock_rel1.db_obj.service_instance_id,
            "service_instance": {
                "config": {},
                "credentials": '{"a": 1, "b": 1}',
                "sensitive_fields": [],
                "hidden_fields": {},
            },
            "environment": "prod",
            "environment_name": "生产环境",
        }
        assert response_data[1]["service"]["uuid"] == str(service2.uuid)
        assert response_data[1]["count"] == 4
        assert response_data[1]["unbound_instances"][3] == {
            "instance_id": mock_rel4.db_obj.service_instance_id,
            "service_instance": {"config": {}, "credentials": '{"f": 1}', "sensitive_fields": [], "hidden_fields": {}},
            "environment": "stag",
            "environment_name": "预发布环境",
        }

    @mock.patch("paasng.accessories.servicehub.views.mixed_service_mgr.get_unbound_instance_rel_by_instance_id")
    @mock.patch("paasng.accessories.servicehub.views.mixed_service_mgr.get_or_404")
    def test_retrieve_sensitive_field(self, mock_get_or_404, mock_get_rel, api_client, bk_app, bk_module):
        service = G(
            Service, uuid=uuid.uuid4(), logo_b64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAZAAAAGQCAYAAAC"
        )
        service_dict = vars(service)
        service_dict["category"] = G(ServiceCategory).id
        mock_get_or_404.return_value = RemoteServiceObj.from_data(service_dict)

        instance = self.create_instance(datetime.datetime(2020, 1, 1), ["c"], ["d"], a=1, b=2, c=3, d=4)
        mock_get_rel.return_value = self.create_mock_rel(service, instance)

        with override_settings(ENABLE_VERIFICATION_CODE=False):
            url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/services/{service.uuid}/unbound_attachments/retrieve_field/"
            data = {"instance_id": instance.uuid, "field_name": "d"}
            response = api_client.post(url, data=data)

        assert response.status_code == 200
        assert response.data == 4
