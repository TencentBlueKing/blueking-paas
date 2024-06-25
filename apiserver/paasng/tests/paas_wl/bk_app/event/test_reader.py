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
from paas_wl.workloads.event.reader import event_kmodel

pytestmark = [pytest.mark.django_db(databases=["default", "workloads"]), pytest.mark.auto_create_ns]


@pytest.fixture()
def client(wl_app):
    return get_client_by_app(wl_app)


class TestEventReader:
    """TestCases for Event"""

    @pytest.fixture()
    def event(self, wl_app, client):
        event_body = {
            "apiVersion": "v1",
            "kind": "Event",
            "metadata": {
                "name": "test-event",
            },
            "involvedObject": {"kind": "Pod", "apiVersion": "v1", "name": "test-pod", "namespace": wl_app.namespace},
            "reason": "ExampleReason",
            "message": "This is an example event message for the Pod",
            "source": {"component": "manual"},
            "type": "Warning",
            "count": 1,
            "firstTimestamp": "2023-01-01T12:00:00Z",
            "lastTimestamp": "2023-01-01T12:00:00Z",
        }
        event, _ = KEvent(client).create_or_update(name="test-event", namespace=wl_app.namespace, body=event_body)
        return event

    @pytest.fixture()
    def event_without_count(self, wl_app, client):
        event_body_without_count = {
            "apiVersion": "v1",
            "kind": "Event",
            "metadata": {
                "name": "test-event-without-count",
            },
            "involvedObject": {"kind": "Pod", "apiVersion": "v1", "name": "test-pod", "namespace": wl_app.namespace},
            "reason": "ExampleReason",
            "message": "This is an example event message for the Pod",
            "source": {"component": "manual"},
            "type": "Warning",
            "firstTimestamp": "2023-01-01T12:00:00Z",
            "lastTimestamp": "2023-01-01T12:00:00Z",
        }
        event, _ = KEvent(client).create_or_update(
            name="test-event-without-count", namespace=wl_app.namespace, body=event_body_without_count
        )
        return event

    def test_query_events(self, wl_app, event):
        # Query events
        events = event_kmodel.list_by_app_instance_name(wl_app, "test-pod")
        assert len(events.items) == 1
        assert events.items[0].involved_object.name == "test-pod"
        assert events.items[0].message == "This is an example event message for the Pod"

    def test_query_events_without_count(self, wl_app, event_without_count):
        # Query events
        events = event_kmodel.list_by_app_instance_name(wl_app, "test-pod")
        assert len(events.items) == 1
        assert events.items[0].involved_object.name == "test-pod"
        assert events.items[0].message == "This is an example event message for the Pod"
