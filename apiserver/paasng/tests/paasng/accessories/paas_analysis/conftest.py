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

import pytest

from paasng.accessories.paas_analysis.entities import Site


@pytest.fixture()
def site_name(bk_app, bk_module):
    return f"app:{bk_app.code}:{bk_module.name}:test"


@pytest.fixture()
def site(site_name, bk_app):
    return Site(type="app", id=1, name=site_name)


@pytest.fixture()
def site_dict(site):
    return {"type": site.type, "name": site.name, "id": site.id}


@pytest.fixture()
def page_view_config(site_dict):
    return {
        "site": site_dict,
        "time_range": {"start_time": "2020-02-27T16:00:00+08:00", "end_time": "2020-02-27T17:00:00+08:00"},
        "supported_dimension_type": [{"name": "访问路径", "value": "path"}, {"name": "用户", "value": "user"}],
        "metrics": {
            "results": {"pv": 38, "uv": 19},
            "source_type": "tracked_pv_by_site",
            "display_name": "站点总访问量",
        },
    }


@pytest.fixture()
def interval_metrics(site_dict):
    return {
        "site": site_dict,
        "result": {
            "results": [
                {"pv": 0, "uv": 0, "time": "2020-02-26T00:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T01:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T02:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T03:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T04:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T05:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T06:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T07:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T08:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T09:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T10:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T11:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T12:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T13:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T14:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T15:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T16:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T17:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T18:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T19:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T20:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T21:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T22:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-26T23:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T00:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T01:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T02:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T03:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T04:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T05:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T06:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T07:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T08:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T09:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T10:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T11:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T12:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T13:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T14:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T15:00:00+08:00"},
                {"pv": 13, "uv": 13, "time": "2020-02-27T16:00:00+08:00"},
                {"pv": 25, "uv": 6, "time": "2020-02-27T17:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T18:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T19:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T20:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T21:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T22:00:00+08:00"},
                {"pv": 0, "uv": 0, "time": "2020-02-27T23:00:00+08:00"},
            ],
            "interval": "1h",
            "source_type": "tracked_pv_by_site",
            "display_name": "一小时",
        },
    }


@pytest.fixture()
def total_data_metrics(site_dict):
    return {
        "site": site_dict,
        "result": {
            "results": {"pv": 38, "uv": 19},
            "source_type": "tracked_pv_by_site",
            "display_name": "站点总访问量",
        },
    }


@pytest.fixture()
def dimension_metrics(site_dict):
    return {
        "meta": {
            "schemas": {
                "resource_type": dict(name="path", display_name="访问路径"),
                "values_type": [
                    dict(name="pv", display_name="访问量", sortable=True),
                    dict(name="uv", display_name="独立访客数", sortable=True),
                ],
            },
            "pagination": {"total": 3},
        },
        "resources": [
            {"name": "/ccc", "values": dict(pv=22, uv=3)},
            {"name": "/aaa", "values": dict(pv=3, uv=3)},
            {"name": "/bbb", "values": dict(pv=3, uv=3)},
        ],
    }


@pytest.fixture()
def pv_agg_by_interval_metrics(site_dict):
    return {
        "site": site_dict,
        "result": {
            "source_type": "--",
            "display_name": "一小时",
            "interval": "1h",
            "results": [
                {"pv": 38, "uv": 19, "time": "1970-01-01 00:00:00"},
                {"pv": 38, "uv": 19, "time": "1970-01-01 01:00:00"},
            ],
        },
    }


@pytest.fixture()
def ce_agg_by_interval_metrics(site_dict):
    return {
        "site": site_dict,
        "result": {
            "source_type": "--",
            "display_name": "一小时",
            "interval": "1h",
            "results": [
                {"ev": 38, "ue": 19, "time": "1970-01-01 00:00:00"},
                {"ev": 38, "ue": 19, "time": "1970-01-01 01:00:00"},
            ],
        },
    }


@pytest.fixture()
def custom_event_overview():
    return {
        "meta": {
            "schemas": [
                dict(name="category", display_name="类别", sortable=False),
                dict(name="ev", display_name="事件总数", sortable=True),
                dict(name="ue", display_name="唯一身份事件数", sortable=True),
            ],
            "pagination": {"total": 2},
        },
        "resources": [
            dict(category="foo", ev=1, ue=2),
            dict(category="bar", ev=1, ue=2),
        ],
    }


@pytest.fixture()
def custom_event_category_detail():
    return {
        "meta": {
            "schemas": [
                dict(name="event_id", display_name="事件ID", sortable=False),
                dict(name="action", display_name="事件操作", sortable=False),
                dict(name="ev", display_name="事件总数", sortable=True),
                dict(name="ue", display_name="唯一身份事件数", sortable=True),
            ],
            "pagination": {"total": 2},
        },
        "resources": [
            dict(event_id="foo", action="foo", ev=1, ue=2),
            dict(event_id="bar", action="bar", ev=1, ue=2),
        ],
    }
