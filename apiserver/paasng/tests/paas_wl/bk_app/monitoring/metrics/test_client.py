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
from django.test import TestCase

from paas_wl.bk_app.monitoring.metrics.clients.bkmonitor import BkPromResult
from paas_wl.bk_app.monitoring.metrics.clients.prometheus import PromResult


class TestPromResult(TestCase):
    def setUp(self) -> None:
        self.fake_range_result = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"container_name": "cl5"},
                        "values": [
                            [1590000844, "0.005465409366663229"],
                            [1590001444, "0.0046846496000010045"],
                            [1590002044, "0.004948108500001069"],
                        ],
                    },
                    {
                        "metric": {"container_name": "ieod-bkapp-career-stag"},
                        "values": [
                            [1590000844, "0.0003452615666667214"],
                            [1590001444, "0.00040326460000083365"],
                            [1590002044, "0.0003675630666667947"],
                            [1590003044, "0.0003675630666667947"],
                        ],
                    },
                ],
            },
        }

        self.fake_no_range_result = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {"metric": {"container_name": "cl5"}, "value": [1590000844, "0.005465409366663229"]},
                    {
                        "metric": {"container_name": "ieod-bkapp-career-stag"},
                        "value": [1590000844, "0.0003452615666667214"],
                    },
                ],
            },
        }

    def test_from_dict(self):
        """测试 dict 转换对象"""
        pr = PromResult.from_resp(raw_resp=self.fake_range_result)
        assert pr.results[0].metric.container_name == "cl5"
        assert len(pr.results[0].values) == 3
        assert pr.results[1].metric.container_name == "ieod-bkapp-career-stag"
        assert len(pr.results[1].values) == 4

    def test_none(self):
        """测试空值"""
        error_results = {
            "status": "success",
            "data": {"resultType": "matrix", "result": []},
            "warnings": ["No store matched for this query"],
        }
        with pytest.raises(ValueError, match=r"No store matched.*"):
            PromResult.from_resp(raw_resp=error_results)

        error_results = {
            "status": "success",
            "data": {"resultType": "matrix", "result": []},
        }
        with pytest.raises(ValueError, match=r"empty results"):
            PromResult.from_resp(raw_resp=error_results)

        error_results = {}
        with pytest.raises(ValueError, match=r"No valid results"):
            PromResult.from_resp(raw_resp=error_results)

    def test_get_by_container_name(self):
        """测试 对象转换 dict"""
        pr = PromResult.from_resp(raw_resp=self.fake_range_result)
        r1 = pr.get_raw_by_container_name("ieod-bkapp-career-stag")

        assert r1
        assert len(r1["values"]) == 4

        r2 = pr.get_raw_by_container_name("cl5")
        assert r2
        assert len(r2["values"]) == 3

        assert r1["metric"] == {"container_name": "ieod-bkapp-career-stag"}
        assert r1["values"] == [
            [1590000844, "0.0003452615666667214"],
            [1590001444, "0.00040326460000083365"],
            [1590002044, "0.0003675630666667947"],
            [1590003044, "0.0003675630666667947"],
        ]

        r3 = pr.get_raw_by_container_name("cxxxx")
        assert r3 is None

        r4 = pr.get_raw_by_container_name()
        assert r4
        assert len(r4["values"]) == 3

    def test_response_change(self):
        """测试返回值变动（只测试增）"""
        fake_range_result = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"container_name": "cl5"},
                        "something_else": {},
                        "values": [
                            [1590000844, "0.005465409366663229"],
                            [1590001444, "0.0046846496000010045"],
                            [1590002044, "0.004948108500001069"],
                        ],
                    },
                    {
                        "metric": {"container_name": "ieod-bkapp-career-stag"},
                        "something_else": {},
                        "values": [
                            [1590000844, "0.0003452615666667214"],
                            [1590001444, "0.00040326460000083365"],
                            [1590002044, "0.0003675630666667947"],
                            [1590003044, "0.0003675630666667947"],
                        ],
                    },
                ],
            },
        }
        pr = PromResult.from_resp(raw_resp=fake_range_result)
        r1 = pr.get_raw_by_container_name("ieod-bkapp-career-stag")
        assert r1
        assert len(r1["values"]) == 4


class TestBkPrometheusResult(TestCase):
    def setUp(self) -> None:
        self.fake_range_series = [
            {
                "alias": "_result0",
                "metric_field": "_result_",
                "unit": "",
                "target": 'container_name="web-proc"',
                "dimensions": {"container_name": "web-proc"},
                "datapoints": [
                    [1073741824, 1673257360000],
                    [1073741824, 1673257370000],
                    [1073741824, 1673257380000],
                ],
            },
            {
                "alias": "_result1",
                "metric_field": "_result_",
                "unit": "",
                "target": 'container_name="celery-proc"',
                "dimensions": {"container_name": "celery-proc"},
                "datapoints": [
                    [1073741824, 1673257280000],
                    [1073741824, 1673257290000],
                    [1073741824, 1673257300000],
                    [1073741824, 1673257310000],
                ],
            },
        ]

    def test_from_series(self):
        """测试根据 series 创建 BkPromResult 对象"""
        pr = BkPromResult.from_series(self.fake_range_series)
        assert pr.results[0].metric.container_name == "web-proc"
        assert len(pr.results[0].values) == 3
        assert pr.results[1].metric.container_name == "celery-proc"
        assert len(pr.results[1].values) == 4

    def test_none(self):
        """测试空值"""
        with pytest.raises(ValueError, match=r".* series is empty"):
            BkPromResult.from_series([])

    def test_get_by_container_name(self):
        """测试对象转换为 dict"""
        pr = BkPromResult.from_series(self.fake_range_series)
        r1 = pr.get_raw_by_container_name("celery-proc")

        assert r1
        assert len(r1["values"]) == 4

        r2 = pr.get_raw_by_container_name("web-proc")
        assert r2
        assert len(r2["values"]) == 3

        assert r1["metric"] == {"container_name": "celery-proc"}
        assert r1["values"] == [
            [1673257280, "1073741824"],
            [1673257290, "1073741824"],
            [1673257300, "1073741824"],
            [1673257310, "1073741824"],
        ]

        r3 = pr.get_raw_by_container_name("xxx")
        assert r3 is None

        # 不指定容器名称时，默认返回第一个
        r4 = pr.get_raw_by_container_name()
        assert r4
        assert len(r4["values"]) == 3

    def test_no_container_name(self):
        fake_series = [
            {
                "alias": "_result0",
                "metric_field": "_result_",
                "unit": "",
                "target": 'container="web-proc"',
                "dimensions": {"container": "web-proc"},
                "datapoints": [
                    [1073741824, 1673257280000],
                    [1073741824, 1673257290000],
                ],
            },
        ]
        pr = BkPromResult.from_series(fake_series)
        r1 = pr.get_raw_by_container_name("web-proc")
        assert r1
        assert r1["values"] == [
            [1673257280, "1073741824"],
            [1673257290, "1073741824"],
        ]
