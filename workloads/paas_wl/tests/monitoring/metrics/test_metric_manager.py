# -*- coding: utf-8 -*-
import datetime
from collections import namedtuple
from typing import List
from unittest.mock import Mock, patch

import pytest
from django.conf import settings

from paas_wl.monitoring.metrics.clients import PrometheusMetricClient
from paas_wl.monitoring.metrics.constants import MetricsResourceType, MetricsSeriesType
from paas_wl.monitoring.metrics.exceptions import RequestMetricBackendError
from paas_wl.monitoring.metrics.models import ResourceMetricManager
from paas_wl.monitoring.metrics.utils import MetricSmartTimeRange
from paas_wl.workloads.processes.managers import AppProcessManager
from tests.utils.app import random_fake_app, random_fake_instance, release_setup

pytestmark = pytest.mark.django_db


class TestResourceMetricManager:
    @pytest.fixture(autouse=True)
    def setUp(self) -> None:
        self.app = random_fake_app(force_app_info={'region': settings.FOR_TESTS_DEFAULT_REGION})
        release_setup(fake_app=self.app)
        self.web_process = AppProcessManager(app=self.app).assemble_process('web')
        self.worker_process = AppProcessManager(app=self.app).assemble_process('worker')
        self.web_process.instances = [random_fake_instance(self.app), random_fake_instance(self.app)]
        self.worker_process.instances = [random_fake_instance(self.app)]

    @pytest.fixture
    def metric_client(self):
        yield PrometheusMetricClient(basic_auth=("foo", "bar"), host="example.com")

    def test_normal_gen_series_query(self, metric_client):
        manager = ResourceMetricManager(process=self.web_process, metric_client=metric_client, bcs_cluster_id='')
        fake_metrics_value = [[1234, 1234], [1234, 1234], [1234, 1234]]
        query_range_mock = Mock(return_value=fake_metrics_value)
        with patch('paas_wl.monitoring.metrics.clients.PrometheusMetricClient.query_range', query_range_mock):
            result = list(
                manager.get_all_instances_metrics(
                    time_range=MetricSmartTimeRange(start="2013-05-11 21:23:58", end="2013-05-11 21:25:58"),
                    resource_types=[MetricsResourceType.MEM.value],
                )
            )

            assert len(result) == 2
            assert result[0].results[0].type_name == "mem"
            assert result[0].results[0].results[0].type_name == "current"
            assert result[0].results[0].results[0].results == fake_metrics_value

    def test_empty_gen_series_query(self, metric_client):
        manager = ResourceMetricManager(process=self.web_process, metric_client=metric_client, bcs_cluster_id='')
        fake_metrics_value: List = []
        query_range_mock = Mock(return_value=fake_metrics_value)
        with patch('paas_wl.monitoring.metrics.clients.PrometheusMetricClient.query_range', query_range_mock):
            result = list(
                manager.get_all_instances_metrics(
                    time_range=MetricSmartTimeRange(start="2013-05-11 21:23:58", end="2013-05-11 21:25:58"),
                    resource_types=[MetricsResourceType.MEM],
                )
            )

            assert result[0].results[0].type_name == "mem"
            assert result[0].results[0].results[0].type_name == "current"
            assert result[0].results[0].results[0].results == fake_metrics_value

    def test_exception_gen_series_query(self, metric_client):
        manager = ResourceMetricManager(process=self.web_process, metric_client=metric_client, bcs_cluster_id='')
        FakeResponse = namedtuple('FakeResponse', 'status_code')

        query_range_mock = Mock(side_effect=RequestMetricBackendError(FakeResponse(status_code=400)))
        with patch('paas_wl.monitoring.metrics.clients.PrometheusMetricClient.query_range', query_range_mock):
            result = list(
                manager.get_all_instances_metrics(
                    time_range=MetricSmartTimeRange(start="2013-05-11 21:23:58", end="2013-05-11 21:25:58"),
                    resource_types=[MetricsResourceType.MEM],
                )
            )

            assert len(result) == 2

    def test_gen_series_query(self, metric_client):
        temp_process = self.worker_process
        temp_process.instances[0].name = f"{settings.FOR_TESTS_DEFAULT_REGION}-test-test-stag-asdfasdf"
        manager = ResourceMetricManager(process=temp_process, metric_client=metric_client, bcs_cluster_id='')
        query = manager.gen_series_query(
            instance_name=temp_process.instances[0].name,
            resource_type=MetricsResourceType.MEM.value,
            series_type=MetricsSeriesType.CURRENT.value,
            time_range=MetricSmartTimeRange(start="2013-05-11 21:23:58", end="2013-05-11 21:25:58"),
        )

        assert query.type_name == "current"
        assert query.query.startswith(
            'sum by(container_name) '
            '(container_memory_working_set_bytes{'
            f'pod_name="{settings.FOR_TESTS_DEFAULT_REGION}-test-test-stag-asdfasdf", '
            'container_name!="POD", '
        )

    def test_gen_all_series_query(self, metric_client):
        manager = ResourceMetricManager(process=self.web_process, metric_client=metric_client, bcs_cluster_id='')
        queries = manager.gen_all_series_query(
            instance_name=self.web_process.instances[0].name,
            resource_type=MetricsResourceType.MEM.value,
            time_range=MetricSmartTimeRange(start="2013-05-11 21:23:58", end="2013-05-11 21:25:58"),
        )

        assert len(list(queries)) == 2


class TestTimeRange:
    def test_simple_date_string(self):
        tr = MetricSmartTimeRange(start='2013-05-11 21:23:58', end='2013-05-11 21:25:58')

        assert tr.start == '1368278638'
        assert tr.end == '1368278758'

    def test_to_now(self):
        tr = MetricSmartTimeRange(
            start='2013-05-11 21:23:58', end='2013-05-11 21:25:58', time_range_str=datetime.timedelta(hours=1)
        )

        assert not tr.start == '1368278638'
        assert not tr.end == '1368278758'

        # 精确到秒
        assert int(tr.end) - int(tr.start) == 3600
