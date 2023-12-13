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
import json
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Union

import requests
from blue_krill.auth.jwt import ClientJWTAuth, JWTAuthConf
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from paasng.accessories.paas_analysis import serializers as slzs
from paasng.accessories.paas_analysis.constants import MetricsDimensionType, MetricsInterval, MetricSourceType
from paasng.accessories.paas_analysis.entities import Site
from paasng.accessories.paas_analysis.exceptions import PAClientException, PAResponseError
from paasng.core.core.storages.cache import region as cache_region

logger = logging.getLogger(__name__)


@contextmanager
def wrap_request_exc():
    try:
        yield
    except requests.RequestException as e:
        # Handle the potential NoneType of e.request
        request_info = e.request.url if e.request else "unknown"
        logger.exception(f"Unable to fetch response from {request_info}")

        error_msg = f"Something wrong happened when fetching {request_info}"
        raise PAClientException(error_msg) from e
    except json.decoder.JSONDecodeError as e:
        logger.exception(f"invalid json response: {e.doc}")
        raise PAClientException(f"invalid json response: {e.doc}") from e
    except PAResponseError as e:
        logger.exception(f"invalid response({e.status_code}) from {e.request_url}.Detail: {e.response_text}")
        raise


class PAClient:
    def __init__(self):
        if not settings.PAAS_ANALYSIS_JWT_CONF:
            raise ImproperlyConfigured('"PAAS_ANALYSIS_JWT_CONF" not configured')

        self.base_url = settings.PAAS_ANALYSIS_BASE_URL.rstrip("/")
        self.auth = ClientJWTAuth(JWTAuthConf(**settings.PAAS_ANALYSIS_JWT_CONF))

    @staticmethod
    def validate_resp(resp: requests.Response):
        """Validate response status code"""
        if not (resp.status_code >= 200 and resp.status_code < 300):
            request_url = resp.request.url or ""
            raise PAResponseError(
                f"stauts code is invalid: {resp.status_code}",
                status_code=resp.status_code,
                request_url=request_url,
                response_text=resp.text,
            )

    @cache_region.cache_on_arguments(namespace="paas-analysis", expiration_time=60)
    def get_or_create_app_site(self, app_code: str, module_name: str, env: str) -> Dict:
        """创建或获取site对象"""
        url = "/sites/register"
        with wrap_request_exc():
            resp = requests.post(
                self.base_url + url,
                json={
                    "site_type": "app",
                    "extra_info": {
                        "paas_app_code": app_code,
                        "module_name": module_name,
                        "environment": env,
                    },
                },
                auth=self.auth,
            )
            self.validate_resp(resp)
            return resp.json()["site"]

    @cache_region.cache_on_arguments(namespace="paas-analysis", expiration_time=60)
    def get_or_create_custom_site(self, site_name: str) -> Dict:
        """创建或获取自定义站点(Site)对象"""
        url = "/sites/register"
        with wrap_request_exc():
            resp = requests.post(
                self.base_url + url,
                json={"site_type": "custom", "extra_info": {"site_name": site_name}},
                auth=self.auth,
            )
            self.validate_resp(resp)
            return resp.json()["site"]

    ################
    # 访问量统计 API #
    ################

    def get_site_pv_config(self, site_name: str, metric_source_type: int) -> Dict:
        """获取展示 PageView 所需的基础配置"""
        url = f"/sites/{site_name}/t/{metric_source_type}/config"
        with wrap_request_exc():
            resp = requests.get(self.base_url + url, auth=self.auth)
            self.validate_resp(resp)
            return resp.json()

    def get_total_page_view_metric_about_site(
        self, site_name: str, metric_source_type: int, start_time: datetime.date, end_time: datetime.date
    ) -> Dict:
        """根据指定的时间区间, 查询该范围内的总访问量"""
        url = f"/sites/{site_name}/t/{metric_source_type}/metrics/total"
        with wrap_request_exc():
            resp = requests.get(
                self.base_url + url,
                params={"start_time": start_time.isoformat(), "end_time": end_time.isoformat()},
                auth=self.auth,
            )
            self.validate_resp(resp)
            return resp.json()

    def get_metrics_dimension(
        self,
        site_name: str,
        metric_source_type: int,
        dimension: str,
        start_time: datetime.date,
        end_time: datetime.date,
        limit: int,
        offset: int,
        ordering: str,
        interval: str = MetricsInterval.ONE_HOUR.value,
    ) -> Dict:
        """根据指定的分组维度和时间区间, 查询该时间区间内, 按照分组维度聚合的数据"""
        url = f"/sites/{site_name}/t/{metric_source_type}/metrics/dimension/{dimension}"

        params: Dict[str, Union[int, str]] = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "limit": limit,
            "offset": offset,
            "ordering": ordering,
            "interval": interval,
        }
        with wrap_request_exc():
            resp = requests.get(
                self.base_url + url,
                params=params,
                auth=self.auth,
            )
            self.validate_resp(resp)
            return resp.json()

    def get_metrics_aggregate_by_interval_about_site(
        self,
        site_name: str,
        metric_source_type: int,
        interval: str,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        fill_missing_data: bool = True,
    ) -> Dict:
        """根据指定的`时间粒度`聚合查询某时间区间内的访问量数据"""
        url = f"/sites/{site_name}/t/{metric_source_type}/metrics/aggregate_by_interval"
        params: Dict[str, Union[str, int]] = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "interval": interval,
            "fill_missing_data": 1 if fill_missing_data else 0,
        }
        resp = requests.get(
            self.base_url + url,
            params=params,
            auth=self.auth,
        )
        with wrap_request_exc():
            self.validate_resp(resp)
            return resp.json()

    ################
    # 自定义事件 API #
    ################

    def get_site_ce_config(self, site_name: str) -> Dict:
        """获取展示 CustomEvent 所需的基础配置"""
        url = f"/sites/{site_name}/event/config"
        with wrap_request_exc():
            resp = requests.get(self.base_url + url, auth=self.auth)
            self.validate_resp(resp)
            return resp.json()

    def get_total_custom_event_metric_about_site(
        self, site_name: str, start_time: datetime.date, end_time: datetime.date
    ) -> Dict:
        """根据指定的时间区间, 查询该范围内的总访问量"""
        url = f"/sites/{site_name}/event/metrics/total"
        with wrap_request_exc():
            resp = requests.get(
                self.base_url + url,
                params={"start_time": start_time.isoformat(), "end_time": end_time.isoformat()},
                auth=self.auth,
            )
            self.validate_resp(resp)
            return resp.json()

    def get_custom_event_overview(
        self,
        site_name: str,
        start_time: datetime.date,
        end_time: datetime.date,
        limit: int,
        offset: int,
        ordering: str,
        interval: str = MetricsInterval.ONE_HOUR.value,
    ):
        """根据指定的`时间粒度`聚合查询某时间区间内的自定义事件概览"""
        url = f"/sites/{site_name}/event/metrics/overview"
        params: Dict[str, Union[int, str]] = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "limit": limit,
            "offset": offset,
            "ordering": ordering,
            "interval": interval,
        }
        resp = requests.get(
            self.base_url + url,
            params=params,
            auth=self.auth,
        )
        with wrap_request_exc():
            self.validate_resp(resp)
            return resp.json()

    def get_custom_event_detail(
        self,
        site_name: str,
        category: str,
        dimension: str,
        start_time: datetime.date,
        end_time: datetime.date,
        limit: int,
        offset: int,
        ordering: str,
        interval: str = MetricsInterval.ONE_HOUR.value,
    ):
        """根据指定的`时间粒度`聚合查询某时间区间内某个类别下的自定义事件(带维度)"""
        url = f"/sites/{site_name}/event/metrics/c/{category}/d/{dimension}/detail"
        params: Dict[str, Union[int, str]] = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "limit": limit,
            "offset": offset,
            "ordering": ordering,
            "interval": interval,
        }
        resp = requests.get(
            self.base_url + url,
            params=params,
            auth=self.auth,
        )
        with wrap_request_exc():
            self.validate_resp(resp)
            return resp.json()

    def get_custom_event_trend_about_site(
        self,
        site_name: str,
        interval: str,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        fill_missing_data: bool = True,
    ) -> Dict:
        """根据指定的`时间粒度`聚合查询某时间区间内的自定义事件触发趋势"""
        url = f"/sites/{site_name}/event/metrics/aggregate_by_interval"
        params: Dict[str, Union[str, int]] = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "interval": interval,
            "fill_missing_data": 1 if fill_missing_data else 0,
        }
        resp = requests.get(
            self.base_url + url,
            params=params,
            auth=self.auth,
        )
        with wrap_request_exc():
            self.validate_resp(resp)
            return resp.json()


@dataclass
class SiteMetricsClient:
    site: Site
    metric_source_type: MetricSourceType

    def __post_init__(self):
        self.pa_client = PAClient()

    def get_site_pv_config(self):
        resp = self.pa_client.get_site_pv_config(
            site_name=self.site.name, metric_source_type=self.metric_source_type.value
        )
        slz = slzs.PageViewConfigSLZ(data=resp, context={"region": self.site.region})
        slz.is_valid(True)
        return slz.validated_data

    def get_total_page_view_metric_about_site(self, start_time: datetime.date, end_time: datetime.date):
        resp = self.pa_client.get_total_page_view_metric_about_site(
            site_name=self.site.name,
            metric_source_type=self.metric_source_type.value,
            start_time=start_time,
            end_time=end_time,
        )
        slz = slzs.PageViewTotalMetricSLZ(data=resp)
        slz.is_valid(True)
        return slz.validated_data

    def get_metrics_dimension(
        self,
        dimension: MetricsDimensionType,
        start_time: datetime.date,
        end_time: datetime.date,
        limit: int,
        offset: int,
        ordering: str,
        interval: MetricsInterval = MetricsInterval.ONE_HOUR,
    ):
        resp = self.pa_client.get_metrics_dimension(
            site_name=self.site.name,
            metric_source_type=self.metric_source_type.value,
            dimension=dimension.value,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
            ordering=ordering,
            interval=interval.value,
        )
        slz = slzs.MetricsDimensionSLZ(data=resp)
        slz.is_valid(True)
        return slz.validated_data

    def get_metrics_aggregate_by_interval_about_site(
        self,
        interval: MetricsInterval,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        fill_missing_data: bool = True,
    ):
        resp = self.pa_client.get_metrics_aggregate_by_interval_about_site(
            site_name=self.site.name,
            metric_source_type=self.metric_source_type.value,
            interval=interval.value,
            start_time=start_time,
            end_time=end_time,
            fill_missing_data=fill_missing_data,
        )
        slz = slzs.PageViewMetricTrendSLZ(data=resp)
        slz.is_valid(True)
        return slz.validated_data

    ################
    # 自定义事件 API #
    ################

    def get_site_ce_config(self):
        resp = self.pa_client.get_site_ce_config(site_name=self.site.name)
        slz = slzs.CustomEventConfigSLZ(data=resp)
        slz.is_valid(True)
        return slz.validated_data

    def get_total_custom_event_metric_about_site(
        self,
        start_time: datetime.date,
        end_time: datetime.date,
    ):
        resp = self.pa_client.get_total_custom_event_metric_about_site(
            site_name=self.site.name,
            start_time=start_time,
            end_time=end_time,
        )
        slz = slzs.CustomEventTotalMetricSLZ(data=resp)
        slz.is_valid(True)
        return slz.validated_data

    def get_custom_event_overview(
        self,
        start_time: datetime.date,
        end_time: datetime.date,
        limit: int,
        offset: int,
        ordering: str,
        interval: MetricsInterval = MetricsInterval.ONE_HOUR,
    ):
        resp = self.pa_client.get_custom_event_overview(
            site_name=self.site.name,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
            ordering=ordering,
            interval=interval.value,
        )
        slz = slzs.CustomEventOverviewTableSLZ(data=resp)
        slz.is_valid(True)
        return slz.validated_data

    def get_custom_event_detail(
        self,
        category: str,
        dimension: MetricsDimensionType,
        start_time: datetime.date,
        end_time: datetime.date,
        limit: int,
        offset: int,
        ordering: str,
        interval: MetricsInterval = MetricsInterval.ONE_HOUR,
    ):
        resp = self.pa_client.get_custom_event_detail(
            site_name=self.site.name,
            category=category,
            dimension=dimension.value,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
            ordering=ordering,
            interval=interval.value,
        )
        slz = slzs.CustomEventDetailTableSLZ(data=resp)
        slz.is_valid(True)
        return slz.validated_data

    def get_custom_event_trend_about_site(
        self,
        interval: MetricsInterval,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        fill_missing_data: bool = True,
    ) -> Dict:
        resp = self.pa_client.get_custom_event_trend_about_site(
            site_name=self.site.name,
            interval=interval.value,
            start_time=start_time,
            end_time=end_time,
            fill_missing_data=fill_missing_data,
        )
        slz = slzs.CustomEventMetricTrendSLZ(data=resp)
        slz.is_valid(True)
        return slz.validated_data
