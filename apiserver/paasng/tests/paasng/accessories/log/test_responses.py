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
from typing import List, Optional

import cattr
import pytest
from elasticsearch_dsl.response.hit import Hit

from paasng.accessories.log.exceptions import LogLineInfoBrokenError
from paasng.accessories.log.models import ElasticSearchParams
from paasng.accessories.log.responses import IngressLogLine, StructureLogLine
from paasng.accessories.log.utils import clean_logs

pytestmark = pytest.mark.django_db


@pytest.fixture
def search_params():
    return ElasticSearchParams(indexPattern="foo-*", termTemplate={}, timeFormat="datetime")


@pytest.fixture
def make_fake_hit():
    """一个用于测试的日志返回结果"""

    def _make_fake_hit(force_source: Optional[dict] = None, deleting_field: Optional[List[str]] = None):
        template = {
            '_index': 'fake_index',
            '_type': 'doc',
            '_id': 'AXZBV87o_J-Z3_Obv',
            '_score': None,
            '_source': {
                'json': {'message': 'fake_message'},
                'source': 'fake_source',
                'pod_name': 'useless_pod_name',
                'container_name': 'useless_container_name',
                'module_name': 'backend',
                'offset': 346441043,
                '@version': '1',
                'region': 'fake_region',
                'host': {'name': 'useless_host'},
                '@timestamp': '2020-12-08T07:25:00.622Z',
                'environment': 'fake',
                'namespace': 'useless_container_name',
                'tags': ['stdout'],
                'stream': 'stderr',
                'ns': 622628538,
                'app_code': 'fake_code',
                'process_type': 'fake_process_id',
            },
            'sort': [1607412300622, 622628538],
        }
        if force_source:
            template['_source'].update(force_source)  # type: ignore
        deleting_field = deleting_field or []
        for f in deleting_field:
            if f in template['_source']:  # type: ignore
                del template['_source'][f]  # type: ignore

        return Hit(template)

    return _make_fake_hit


class TestStructureLogLine:
    def test_parse_raw_log(self, search_params, make_fake_hit):
        """正常解析"""
        hit = make_fake_hit()
        parsed = cattr.structure(clean_logs([hit], search_params)[0], StructureLogLine)
        expected = cattr.structure(
            dict(
                message="fake_message",
                # "2020-12-08T07:25:00.622Z"
                timestamp=1607412300,
                raw={
                    'json.message': 'fake_message',
                    'source': 'fake_source',
                    'pod_name': 'useless_pod_name',
                    'container_name': 'useless_container_name',
                    'module_name': 'backend',
                    'offset': 346441043,
                    '@version': '1',
                    'region': 'fake_region',
                    'host.name': 'useless_host',
                    '@timestamp': '2020-12-08T07:25:00.622Z',
                    'environment': 'fake',
                    'namespace': 'useless_container_name',
                    'tags': ['stdout'],
                    'stream': 'stderr',
                    'ns': 622628538,
                    'app_code': 'fake_code',
                    'process_type': 'fake_process_id',
                    # 源数据的 process_type 被复制成 process_id
                    'process_id': 'fake_process_id',
                },
            ),
            StructureLogLine,
        )
        assert parsed == expected

    @pytest.mark.parametrize(
        "deleting_field",
        [
            ["region"],
            ["app_code"],
            ["environment"],
            ["@timestamp"],
            ["process_id", "process_type"],
        ],
    )
    def test_lacking_key_info(self, search_params, make_fake_hit, deleting_field):
        """针对一些字段缺失，能够正确抛出异常"""
        with pytest.raises(LogLineInfoBrokenError):
            hit = make_fake_hit(deleting_field=deleting_field)
            cattr.structure(clean_logs([hit], search_params)[0], StructureLogLine)


class TestIngressLogLine:
    @pytest.fixture
    def make_fake_hit(self, make_fake_hit):
        def _make_fake_hit(force_source: dict, deleting_fields: List[str]):
            ingress_detail = {
                "engine_app_name": "aaa",
                "method": "aaa",
                "path": "aaa",
                "status_code": "404",
                "response_time": "1",
                "client_ip": "aaa",
                "bytes_sent": "1",
                "user_agent": "aaa",
                "http_version": "aaa",
            }
            ingress_detail.update(force_source)
            return make_fake_hit(ingress_detail, deleting_fields)

        return _make_fake_hit

    @pytest.mark.parametrize(
        "force_update, expected",
        [
            (
                {"engine_app_name": "normal"},
                {"engine_app_name": "normal"},
            ),
            (
                {"engine_app_name": "under0us0line"},
                {"engine_app_name": "under_line"},
            ),
            (
                {"engine_app_name": "strike-through"},
                {"engine_app_name": "strike-through"},
            ),
        ],
    )
    def test_parse_ingress_raw_log(
        self,
        search_params,
        bk_user,
        make_fake_hit,
        force_update,
        expected,
    ):
        """正常解析 Ingress 日志"""
        hit = make_fake_hit(force_update, [])
        parsed = cattr.structure(clean_logs([hit], search_params)[0], IngressLogLine)

        expected = cattr.structure(
            {
                "message": "fake_message",
                "timestamp": 1607412300,
                "raw": {
                    'json.message': 'fake_message',
                    'source': 'fake_source',
                    'pod_name': 'useless_pod_name',
                    'container_name': 'useless_container_name',
                    'module_name': 'backend',
                    'offset': 346441043,
                    '@version': '1',
                    'region': 'fake_region',
                    'host.name': 'useless_host',
                    '@timestamp': '2020-12-08T07:25:00.622Z',
                    'environment': 'fake',
                    'namespace': 'useless_container_name',
                    'tags': ['stdout'],
                    'stream': 'stderr',
                    'ns': 622628538,
                    'app_code': 'fake_code',
                    'process_type': 'fake_process_id',
                    # 源数据的 process_type 被复制成 process_id
                    'process_id': 'fake_process_id',
                    # ingress 日志字段
                    "engine_app_name": "aaa",
                    "method": "aaa",
                    "path": "aaa",
                    "status_code": "404",
                    "response_time": "1",
                    "client_ip": "aaa",
                    "bytes_sent": "1",
                    "user_agent": "aaa",
                    "http_version": "aaa",
                    **expected,
                },
            },
            IngressLogLine,
        )
        # IngressLogLine 会修改 engine_app_name 的格式, 对比 raw 无意义
        parsed.raw.pop("engine_app_name")
        expected.raw.pop("engine_app_name")
        assert parsed == expected

    @pytest.mark.parametrize(
        "deleting_field",
        [
            ["@timestamp"],
            ["engine_app_name"],
        ],
    )
    def test_ingress_lacking_key_info(self, search_params, make_fake_hit, deleting_field):
        """针对一些字段缺失，能够正确抛出异常"""
        with pytest.raises(LogLineInfoBrokenError):
            hit = make_fake_hit({}, deleting_field)
            cattr.structure(clean_logs([hit], search_params), List[IngressLogLine])
