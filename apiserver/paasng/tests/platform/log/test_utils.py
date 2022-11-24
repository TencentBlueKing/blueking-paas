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
import datetime
from typing import Dict, List
from unittest import mock

import pytest

from paasng.platform.log.utils import detect_indexes, get_es_term


class TestUtils:
    @pytest.fixture
    def make_stats_indexes_fake_resp(self):
        def _make_stats_indexes_fake_resp(indexes: List[str]):
            def _wrapper(*args, **kwargs):
                results: Dict[str, Dict] = {}
                for index in indexes:
                    results[index] = {}

                return {"indices": results}

            return _wrapper

        return _make_stats_indexes_fake_resp

    @pytest.mark.parametrize(
        "pattern, expected, start_time, end_time, indexes",
        [
            # 正常匹配
            (
                "k8s_app_log_szp-(?P<date>.+)",
                ["k8s_app_log_szp-2021.01.01"],
                "2020-12-30 00:00:00",
                "2021-01-01 08:00:00",
                ["k8s_app_log_szp-2021.01.01", "k8s_app_log_szp-2021.01.02", "k8s_app_log_szp-2021.01.03"],
            ),
            # 时区问题, 导致无匹配
            (
                "k8s_app_log_szp-(?P<date>.+)",
                [],
                "2020-12-30 00:00:00",
                "2021-01-01 00:00:00",
                ["k8s_app_log_szp-2021.01.01", "k8s_app_log_szp-2021.01.02", "k8s_app_log_szp-2021.01.03"],
            ),
            # pattern 不匹配
            (
                "k8s_app_log_sz-(?P<date>.+)",
                [],
                "2020-12-30 00:00:00",
                "2021-01-01 00:00:00",
                ["k8s_app_log_szp-2021.01.01", "k8s_app_log_szp-2021.01.02", "k8s_app_log_szp-2021.01.03"],
            ),
            # 时间范围不匹配
            (
                "k8s_app_log_szp-(?P<date>.+)",
                [],
                "2020-12-30 00:00:00",
                "2020-12-31 00:00:00",
                ["k8s_app_log_szp-2021.01.01", "k8s_app_log_szp-2021.01.02", "k8s_app_log_szp-2021.01.03"],
            ),
            # 未填写必须部分
            (
                "k8s_app_log_szp-",
                ValueError,
                "2020-12-30 00:00:00",
                "2020-12-31 00:00:00",
                ["k8s_app_log_szp-2021.01.01", "k8s_app_log_szp-2021.01.02", "k8s_app_log_szp-2021.01.03"],
            ),
            # 未填写具体的 pattern 主体
            (
                "(?P<date>.+)",
                [],
                "2020-12-30 00:00:00",
                "2021-01-02 00:00:00",
                ["k8s_app_log_szp-2021.01.01", "k8s_app_log_szp-2021.01.02", "k8s_app_log_szp-2021.01.03"],
            ),
            # 匹配多个
            (
                "k8s_app_log_szp-(?P<date>.+)",
                ["k8s_app_log_szp-2021.01.01", "k8s_app_log_szp-2021.01.02"],
                "2020-12-30 00:00:00",
                "2021-01-02 08:00:00",
                ["k8s_app_log_szp-2021.01.01", "k8s_app_log_szp-2021.01.02", "k8s_app_log_szp-2021.01.03"],
            ),
            # 时区问题, 导致仅到匹配一个
            (
                "k8s_app_log_szp-(?P<date>.+)",
                ["k8s_app_log_szp-2021.01.01"],
                "2020-12-30 00:00:00",
                "2021-01-02 00:00:00",
                ["k8s_app_log_szp-2021.01.01", "k8s_app_log_szp-2021.01.02", "k8s_app_log_szp-2021.01.03"],
            ),
            # 包含 grokfailure 情况下匹配
            (
                "k8s_app_log_szp-(?P<date>.+)",
                ["k8s_app_log_szp-2021.01.02"],
                "2020-12-30 00:00:00",
                "2021-01-02 08:00:00",
                [
                    "k8s_app_log_szp-grokfailure-2021.01.01",
                    "k8s_app_log_szp-grokfailure-2021.01.02",
                    "k8s_app_log_szp-2021.01.02",
                    "k8s_app_log_szp-2021.01.03",
                ],
            ),
        ],
    )
    def test_detect_indexes(self, pattern, expected, start_time, end_time, indexes, make_stats_indexes_fake_resp):
        """探测 indexes"""
        with mock.patch('elasticsearch.client.Transport.perform_request') as perform_request:
            perform_request.side_effect = make_stats_indexes_fake_resp(indexes)

            if type(expected) is type and issubclass(expected, Exception):
                with pytest.raises(expected):
                    detect_indexes(
                        datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S"),
                        datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S"),
                        pattern,
                    )
            else:
                assert set(expected) == set(
                    detect_indexes(
                        datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S"),
                        datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S"),
                        pattern,
                    )
                )

    @pytest.mark.parametrize(
        "query_term,mappings,expected",
        [
            ("dd", {"dd": {"type": "text"}}, "dd.keyword"),
            ("dd", {"dd": {"type": "int"}}, "dd"),
            ("dd", {"dd": {"type": "keyword"}}, "dd"),
            ("dd", {"xxx": {"type": "keyword"}}, "dd"),
            ("json.levelname", {"json": {"properties": {"levelname": {"type": "text"}}}}, "json.levelname.keyword"),
            ("json.levelname", {"json": {"properties": {"levelname": {"type": "keyword"}}}}, "json.levelname"),
            (
                "json.levelname.no",
                {"json": {"properties": {"levelname": {"properties": {"no": {"type": "keyword"}}}}}},
                "json.levelname.no",
            ),
            (
                "json.levelname.no",
                {"json": {"properties": {"levelname": {"properties": {"no": {"type": "text"}}}}}},
                "json.levelname.no.keyword",
            ),
        ],
    )
    def test_get_es_term(self, query_term, mappings, expected):
        assert get_es_term(query_term, mappings) == expected
