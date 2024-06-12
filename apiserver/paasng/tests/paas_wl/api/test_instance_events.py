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

from paas_wl.infras.resources.base.kres import KEvent
from paas_wl.infras.resources.utils.basic import get_client_by_app

pytestmark = [pytest.mark.django_db(databases=["default", "workloads"]), pytest.mark.auto_create_ns]


@pytest.fixture()
def client(wl_app):
    return get_client_by_app(wl_app)


class TestInstanceEventsViewSet:
    @pytest.fixture()
    def event(self, bk_app, bk_module, bk_stag_env, client):
        namespace = bk_stag_env.wl_app.namespace
        event_body = {
            "apiVersion": "v1",
            "kind": "Event",
            "metadata": {
                "name": "test-event",
                "namespace": namespace,
            },
            "involvedObject": {"kind": "Pod", "apiVersion": "v1", "name": "test-pod", "namespace": namespace},
            "reason": "ExampleReason",
            "message": "This is an example event message for the Pod",
            "source": {"component": "manual"},
            "type": "Warning",
            "count": 1,
            "firstTimestamp": "2023-01-01T12:00:00Z",
            "lastTimestamp": "2023-01-01T12:00:00Z",
        }
        event, _ = KEvent(client).create_or_update(name="test-event", namespace=namespace, body=event_body)
        return event

    def test_list(self, api_client, bk_app, bk_module, bk_stag_env, event):
        url = (
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}"
            f"/envs/{bk_stag_env.environment}/instance_events/test-pod/"
        )
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["count"] == 1
        assert response.data[0]["type"] == "Warning"
