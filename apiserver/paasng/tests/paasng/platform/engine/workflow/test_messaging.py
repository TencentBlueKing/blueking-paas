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

from paasng.platform.engine.workflow.messaging import ServerSendEvent

pytestmark = pytest.mark.django_db


class TestServerSendEvent:
    @pytest.mark.parametrize("eid, event, data_dict", [("1", "xxxx", {"aaa": "bbb"}), (333, "xxxx", {})])
    def test_from_raw_normal(self, eid, event, data_dict):
        """测试正常加载 raw event"""

        e = ServerSendEvent.from_raw(dict(id=eid, event=event, data=data_dict))

        assert e.id == eid
        assert e.event == event
        assert e.data == data_dict
        assert not e.is_internal

    @pytest.mark.parametrize("eid, event, data_dict", [("1", "message", {"aaa": "bbb"}), ("1", "msg", {"aaa": "bbb"})])
    def test_from_raw_message(self, eid, event, data_dict):
        """测试正常加载 raw event"""

        e = ServerSendEvent.from_raw(dict(id=eid, event=event, data=data_dict))

        assert e.id == eid
        assert e.event == "message"
        assert e.data == data_dict
        assert not e.is_internal

    @pytest.mark.parametrize(
        "eid, event, data_dict", [("1", "internal", {"aaa": "bbb"}), ("1", "internal", {"aaa": "bbb"})]
    )
    def test_from_raw_internal(self, eid, event, data_dict):
        """测试正常加载 raw event"""
        e = ServerSendEvent.from_raw(dict(id=eid, event=event, data=data_dict))
        assert e.is_internal

    @pytest.mark.parametrize("eid, event, data_dict", [("1", "internal", {"aaa": "bbb"})])
    def test_to_yield_str_list(self, eid, event, data_dict):
        e = ServerSendEvent.from_raw(dict(id=eid, event=event, data=data_dict))
        assert e.to_yield_str_list() == ["id: %s\n" % e.id, "event: %s\n" % e.event, "data: %s\n\n" % e.data]
