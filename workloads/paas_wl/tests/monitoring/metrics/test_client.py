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

from paas_wl.monitoring.metrics.clients.promethues import PromeResult


class TestPrometheusResult(TestCase):
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
        pr = PromeResult.from_resp(raw_resp=self.fake_range_result)
        assert pr.results[0].metric.container_name == "cl5"
        assert len(pr.results[0].values) == 3
        assert pr.results[0].value is None
        assert pr.results[1].metric.container_name == "ieod-bkapp-career-stag"
        assert len(pr.results[1].values) == 4
        assert pr.results[1].value is None

        pr = PromeResult.from_resp(raw_resp=self.fake_no_range_result, is_range=False)
        assert pr.results[0].metric.container_name == "cl5"
        assert pr.results[0].value and pr.results[0].value.to_raw() == [1590000844, "0.005465409366663229"]
        assert pr.results[0].values == []
        assert pr.results[1].metric.container_name == "ieod-bkapp-career-stag"
        assert pr.results[1].value and pr.results[1].value.to_raw() == [1590000844, "0.0003452615666667214"]
        assert pr.results[0].values == []

    def test_none(self):
        """测试空值"""
        error_results = {
            "status": "success",
            "data": {"resultType": "matrix", "result": []},
            "warnings": ["No store matched for this query"],
        }
        with pytest.raises(ValueError):
            PromeResult.from_resp(raw_resp=error_results)

        error_results = {
            "status": "success",
            "data": {"resultType": "matrix", "result": []},
        }
        with pytest.raises(ValueError):
            PromeResult.from_resp(raw_resp=error_results)

        error_results = {}
        with pytest.raises(ValueError):
            PromeResult.from_resp(raw_resp=error_results)

    def test_get_by_container_name(self):
        """测试 对象转换 dict"""
        pr = PromeResult.from_resp(raw_resp=self.fake_range_result)
        r1 = pr.get_raw_by_container_name("ieod-bkapp-career-stag")

        assert r1 and len(r1['values']) == 4

        r2 = pr.get_raw_by_container_name("cl5")
        assert r2 and len(r2['values']) == 3

        assert r1['metric'] == {"container_name": "ieod-bkapp-career-stag"}
        assert r1['values'] == [
            [1590000844, "0.0003452615666667214"],
            [1590001444, "0.00040326460000083365"],
            [1590002044, "0.0003675630666667947"],
            [1590003044, "0.0003675630666667947"],
        ]

        r3 = pr.get_raw_by_container_name("cxxxx")
        assert r3 is None

        r4 = pr.get_raw_by_container_name()
        assert r4 and len(r4['values']) == 3

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
        pr = PromeResult.from_resp(raw_resp=fake_range_result)
        r1 = pr.get_raw_by_container_name("ieod-bkapp-career-stag")
        assert r1 and len(r1['values']) == 4

    def test_no_range(self):
        fake_results = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"container_name": "cl5"},
                        "value": [1590000844, "0.005465409366663229"],
                    },
                    {
                        "metric": {"container_name": "ieod-bkapp-career-stag"},
                        "value": [1590000844, "0.0003452615666667214"],
                    },
                ],
            },
        }
        pr = PromeResult.from_resp(raw_resp=fake_results, is_range=False)
        r1 = pr.get_raw_by_container_name("cl5")
        assert r1 and r1['value'] == [1590000844, "0.005465409366663229"]

    def test_no_container_name(self):
        fake_results = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [
                    {
                        "metric": {
                            "__name__": "kube_pod_container_resource_limits_cpu_cores",
                            "cluster_id": "x-x-x-x",
                            "container": "bkapp-vision-m-dd-ww-stag",
                            "endpoint": "http",
                            "instance": "x.x.x.x:8080",
                            "job": "kube-state-metrics",
                            "namespace": "bkapp-vision-m-dd-ww-stag",
                            "node": "ip-x-x-x-x--m",
                            "pod": "bkapp-vision-m-dd-ww-stag-web-gunicorn-deployment-6ddfv2dn",
                            "prometheus": "thanos/po-prometheus-operator-prometheus",
                            "service": "po-kube-state-metrics",
                        },
                        "value": [1590639090.03, "0.25"],
                    }
                ],
            },
        }
        pr = PromeResult.from_resp(raw_resp=fake_results, is_range=False)
        r1 = pr.get_raw_by_container_name("bkapp-vision-m-dd-ww-stag")
        assert r1 and r1['value'] == [1590639090.03, "0.25"]

        fake_results = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [
                    {
                        "metric": {
                            "__name__": "kube_pod_container_resource_limits_cpu_cores",
                            "cluster_id": "x-x-x-x",
                            "container": "bkapp-vision-m-dd-ww-stag",
                            "endpoint": "http",
                            "instance": "x.x.x.x:8080",
                            "job": "kube-state-metrics",
                            "namespace": "bkapp-vision-m-dd-ww-stag",
                            "node": "ip-x-x-x-x--m",
                            "pod": "bkapp-vision-m-dd-ww-stag-web-gunicorn-deployment-6ddfv2dn",
                            "prometheus": "thanos/po-prometheus-operator-prometheus",
                            "service": "po-kube-state-metrics",
                        },
                        "values": [[1590639090.03, "0.25"], [1590639095.03, "0.25"]],
                    }
                ],
            },
        }
        pr = PromeResult.from_resp(raw_resp=fake_results)
        r1 = pr.get_raw_by_container_name("bkapp-vision-m-dd-ww-stag")
        assert r1 and len(r1['values']) == 2
