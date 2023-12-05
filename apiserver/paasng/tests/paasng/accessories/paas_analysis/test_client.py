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
from unittest import mock

import pytest

from paas_wl.bk_app.applications.models.managers.app_metadata import WlAppMetadata
from paasng.accessories.paas_analysis.clients import SiteMetricsClient
from paasng.accessories.paas_analysis.constants import MetricsDimensionType, MetricsInterval, MetricSourceType
from paasng.accessories.paas_analysis.utils import (
    enable_ingress_tracking,
    get_ingress_tracking_status,
    get_or_create_site_by_env,
)

pytestmark = pytest.mark.django_db


@mock.patch("paasng.accessories.paas_analysis.clients.PAClient")
class TestSiteMetricsClient:
    def test_get_or_create_site_by_env(self, pa_client_class, site, site_dict, bk_module):
        pa_client_class().get_or_create_app_site.return_value = site_dict
        fake_env = mock.MagicMock()
        fake_env.module.region = bk_module.region
        site_output = get_or_create_site_by_env(fake_env)
        assert pa_client_class().get_or_create_app_site.called
        assert site_output == site

    @pytest.mark.parametrize(
        ("region", "expected_dimension_size"),
        [
            ("ieod", 2),
            # TODO: 在实现过滤用户维度后, 修复这个单元测试
            ("foo", 2),
        ],
    )
    def test_get_site_config(self, pa_client_class, site, page_view_config, region, expected_dimension_size):
        site.region = region
        pa_client_class().get_site_pv_config.return_value = page_view_config
        client = SiteMetricsClient(site, MetricSourceType.USER_TRACKER)
        site_config = client.get_site_pv_config()
        assert pa_client_class().get_site_pv_config.called
        assert site_config["site"]["name"] == site.name
        assert len(site_config["supported_dimension_type"]) == expected_dimension_size

    def test_get_total_metric_about_site(self, pa_client_class, site, total_data_metrics):
        pa_client_class().get_total_page_view_metric_about_site.return_value = total_data_metrics
        client = SiteMetricsClient(site, MetricSourceType.USER_TRACKER)
        metrics = client.get_total_page_view_metric_about_site(datetime.date.today(), datetime.date.today())
        assert pa_client_class().get_total_page_view_metric_about_site.called
        assert metrics["site"]["name"] == site.name
        assert isinstance(metrics["result"], dict)
        assert isinstance(metrics["result"]["results"], dict)

    def test_get_metrics_dimension(self, pa_client_class, site, dimension_metrics):
        pa_client_class().get_metrics_dimension.return_value = dimension_metrics

        client = SiteMetricsClient(site, MetricSourceType.USER_TRACKER)
        metrics = client.get_metrics_dimension(
            MetricsDimensionType.PATH,
            datetime.date.today(),
            datetime.date.today(),
            limit=100,
            offset=0,
            ordering="-pv",
        )

        assert pa_client_class().get_metrics_dimension.called
        assert metrics["meta"]["schemas"]["resource_type"] == dict(
            name=MetricsDimensionType.PATH.value, display_name="访问路径"
        )
        assert metrics["meta"]["schemas"]["values_type"] == [
            dict(name="pv", display_name="访问量", sortable=True),
            dict(name="uv", display_name="独立访客数", sortable=True),
        ]
        assert metrics["meta"]["pagination"]["total"] == 3
        assert metrics["meta"]["pagination"]["total"] == len(metrics["resources"])

    def test_get_metrics_aggregate_by_interval_about_site(self, pa_client_class, site, pv_agg_by_interval_metrics):
        pa_client_class().get_metrics_aggregate_by_interval_about_site.return_value = pv_agg_by_interval_metrics

        client = SiteMetricsClient(site, MetricSourceType.USER_TRACKER)
        metrics = client.get_metrics_aggregate_by_interval_about_site(
            interval=MetricsInterval.ONE_HOUR,
            start_time=datetime.datetime.now(),
            end_time=datetime.datetime.now(),
        )

        assert pa_client_class().get_metrics_aggregate_by_interval_about_site.called
        assert metrics["site"]["name"] == site.name
        assert isinstance(metrics["result"]["results"], list)
        assert len(metrics["result"]["results"]) == 2
        assert isinstance(metrics["result"]["results"][0], dict)

    ################
    # 自定义事件 API #
    ################

    def test_get_custom_event_overview(self, pa_client_class, site, custom_event_overview):
        pa_client_class().get_custom_event_overview.return_value = custom_event_overview

        client = SiteMetricsClient(site, MetricSourceType.USER_TRACKER)
        metrics = client.get_custom_event_overview(
            interval=MetricsInterval.ONE_HOUR,
            start_time=datetime.date.today(),
            end_time=datetime.date.today(),
            limit=100,
            offset=0,
            ordering="-ev",
        )

        assert pa_client_class().get_custom_event_overview.called
        assert metrics["meta"]["schemas"] == [
            dict(name="category", display_name="类别", sortable=False),
            dict(name="ev", display_name="事件总数", sortable=True),
            dict(name="ue", display_name="唯一身份事件数", sortable=True),
        ]
        assert metrics["meta"]["pagination"]["total"] == 2
        assert metrics["meta"]["pagination"]["total"] == len(metrics["resources"])

    def get_custom_event_detail(self, pa_client_class, site, custom_event_category_detail):
        pa_client_class().get_custom_event_detail.return_value = custom_event_category_detail
        client = SiteMetricsClient(site, MetricSourceType.USER_TRACKER)
        metrics = client.get_custom_event_detail(
            category="",
            dimension=MetricsDimensionType.ACTION,
            start_time=datetime.date.today(),
            end_time=datetime.date.today(),
            limit=100,
            offset=0,
            ordering="-ev",
            interval=MetricsInterval.ONE_HOUR,
        )

        assert pa_client_class().get_custom_event_detail.called
        assert metrics["meta"]["schemas"] == [
            dict(name="event_id", display_name="事件ID", sortable=False),
            dict(name="action", display_name="事件操作", sortable=False),
            dict(name="ev", display_name="事件总数", sortable=True),
            dict(name="ue", display_name="唯一身份事件数", sortable=True),
        ]
        assert metrics["meta"]["pagination"]["total"] == 2
        assert metrics["meta"]["pagination"]["total"] == len(metrics["resources"])

    def test_get_custom_event_trend_about_site(self, pa_client_class, site, ce_agg_by_interval_metrics):
        pa_client_class().get_custom_event_trend_about_site.return_value = ce_agg_by_interval_metrics

        client = SiteMetricsClient(site, MetricSourceType.USER_TRACKER)
        metrics = client.get_custom_event_trend_about_site(
            interval=MetricsInterval.ONE_HOUR,
            start_time=datetime.datetime.now(),
            end_time=datetime.datetime.now(),
        )

        assert pa_client_class().get_custom_event_trend_about_site.called
        assert metrics["site"]["name"] == site.name
        assert isinstance(metrics["result"]["results"], list)
        assert len(metrics["result"]["results"]) == 2
        assert isinstance(metrics["result"]["results"][0], dict)


class TestIngressTrackingStatus:
    @pytest.mark.parametrize(
        ("bkpa_site_id", "status"),
        [(None, False), (100, True)],
    )
    def test_get_status(self, bk_stag_env, bkpa_site_id, status: bool):
        with mock.patch("paasng.accessories.paas_analysis.utils.get_metadata_by_env") as mocked_get:
            mocked_get.return_value = WlAppMetadata(bkpa_site_id=bkpa_site_id)
            assert get_ingress_tracking_status(bk_stag_env) is status

    @pytest.mark.parametrize(
        ("bkpa_site_id", "update_called"),
        [(None, True), (100, False)],
    )
    def test_enable(self, bk_stag_env, bkpa_site_id, update_called: bool, site_dict):
        with mock.patch("paasng.accessories.paas_analysis.clients.PAClient") as pa_client_class, mock.patch(
            "paasng.accessories.paas_analysis.utils.get_metadata_by_env"
        ) as mocked_get, mock.patch(
            "paasng.accessories.paas_analysis.utils.update_metadata_by_env"
        ) as mocked_update, mock.patch("paasng.accessories.paas_analysis.utils.sync_proc_ingresses"):
            pa_client_class().get_or_create_app_site.return_value = site_dict
            mocked_get.return_value = WlAppMetadata(bkpa_site_id=bkpa_site_id)

            enable_ingress_tracking(bk_stag_env)
            assert mocked_get.called
            assert mocked_update.called is update_called
