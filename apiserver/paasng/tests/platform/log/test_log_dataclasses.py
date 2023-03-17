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
from typing import List, Optional, Type

import pytest
from elasticsearch_dsl.response.hit import Hit

from paasng.platform.log.dataclasses import IngressLogLine, LogLine
from paasng.platform.log.exceptions import LogLineInfoBrokenError
from tests.utils.helpers import create_app

pytestmark = pytest.mark.django_db


class TestLogLine:
    @pytest.fixture
    def make_fake_hit(self):
        """一个用于测试的日志返回结果"""

        def _make_fake_hit(force_source: dict, deleting_field: Optional[List[str]] = None):
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
                    'process_id': 'fake_process_id',
                },
                'sort': [1607412300622, 622628538],
            }
            template['_source'].update(force_source)  # type: ignore
            deleting_field = deleting_field or []
            for f in deleting_field:
                if f in template['_source']:  # type: ignore
                    del template['_source'][f]  # type: ignore

            return Hit(template)

        return _make_fake_hit

    @pytest.fixture
    def make_fake_expected_result(self):
        """一个用于测试的日志解析结果"""

        def _make_fake_expected_result(force_update: dict, log_line_cls: Type[LogLine] = LogLine):
            r = dict(
                region="fake_region",
                app_code="fake_code",
                environment="fake",
                process_id="fake_process_id",
                stream="stderr",
                message="fake_message",
                detail={'json.message': 'fake_message'},
                ts="2020-12-08 15:25:00",
            )
            r.update(force_update)

            return log_line_cls(**r)

        return _make_fake_expected_result

    @pytest.fixture
    def make_fake_ingress_hit(self, make_fake_hit):
        def _make_fake_ingress_hit(force_source: dict, deleting_fields: List[str]):
            ingress_detail = {
                "engine_app_name": "aaa",
                "method": "aaa",
                "path": "aaa",
                "status_code": "aaa",
                "response_time": "aaa",
                "client_ip": "aaa",
                "bytes_sent": "aaa",
                "user_agent": "aaa",
                "http_version": "aaa",
            }
            ingress_detail.update(force_source)

            return make_fake_hit(ingress_detail, deleting_fields)

        return _make_fake_ingress_hit

    @pytest.fixture
    def make_fake_ingress_expected_result(self, make_fake_expected_result):
        def _make_fake_ingress_expected_result(force_source: dict):
            ingress_detail = {
                "method": "aaa",
                "path": "aaa",
                "status_code": "aaa",
                "response_time": "aaa",
                "client_ip": "aaa",
                "bytes_sent": "aaa",
                "user_agent": "aaa",
                "http_version": "aaa",
            }
            result = {"detail": ingress_detail}
            result.update(force_source)
            return make_fake_expected_result(result, log_line_cls=IngressLogLine)

        return _make_fake_ingress_expected_result

    @pytest.mark.parametrize(
        "force_update,expected,deleting_fields",
        [
            ({}, {}, []),
            ({}, {}, ["process_type"]),
            ({}, {}, ["process_id"]),
        ],
    )
    def test_parse_raw_log(self, make_fake_hit, make_fake_expected_result, force_update, expected, deleting_fields):
        """正常解析"""
        hit = make_fake_hit(force_update, deleting_fields)
        assert str(LogLine.parse_from_es_log(hit)) == str(make_fake_expected_result(expected))

    @pytest.mark.parametrize(
        "deleting_field",
        [
            ["region"],
            ["stream"],
            ["app_code"],
            ["environment"],
            ["@timestamp"],
            ["process_id", "process_type"],
        ],
    )
    def test_lacking_key_info(self, make_fake_hit, make_fake_expected_result, deleting_field):
        """针对一些字段缺失，能够正确抛出异常"""
        with pytest.raises(LogLineInfoBrokenError):
            LogLine.parse_from_es_log(make_fake_hit({}, deleting_field))

    @pytest.mark.parametrize(
        "force_update,expected,deleting_fields",
        [
            (
                {"app_code": "asdfqwer"},
                {"app_code": "asdfqwer", "environment": 'stag'},
                [],
            ),
            (
                {"app_code": "qwer_asdf"},
                {"app_code": "qwer_asdf", "environment": 'stag'},
                [],
            ),
            (
                {"app_code": "qwer-asdf"},
                {"app_code": "qwer-asdf", "environment": 'stag'},
                [],
            ),
        ],
    )
    def test_parse_ingress_raw_log(
        self,
        bk_user,
        make_fake_ingress_hit,
        make_fake_ingress_expected_result,
        force_update,
        expected,
        deleting_fields,
    ):
        """正常解析 Ingress 日志"""
        app = create_app(owner_username=bk_user.pk, force_info=force_update)
        # 模拟 engine 转换 _
        force_update.update({"engine_app_name": app.get_engine_app("stag").name.replace("_", "0us0")})

        hit = make_fake_ingress_hit(force_update, deleting_fields)
        assert IngressLogLine.parse_from_es_log(hit).__dict__ == make_fake_ingress_expected_result(expected).__dict__

    @pytest.mark.parametrize(
        "deleting_field",
        [
            ["region"],
            ["stream"],
            ["@timestamp"],
            ["engine_app_name"],
            ["process_id", "process_type"],
        ],
    )
    def test_ingress_lacking_key_info(self, make_fake_ingress_hit, make_fake_expected_result, deleting_field):
        """针对一些字段缺失，能够正确抛出异常"""
        with pytest.raises(LogLineInfoBrokenError):
            IngressLogLine.parse_from_es_log(make_fake_ingress_hit({}, deleting_field))
