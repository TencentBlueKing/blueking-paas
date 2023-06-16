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
import logging
import os

import prometheus_client
from prometheus_client import multiprocess
from rest_framework.renderers import StaticHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import BasicAuthentication
from .collector import cb_metric_collector

logger = logging.getLogger(__name__)

# register cb_metric_collector to default Metric collector registry
prometheus_client.REGISTRY.register(cb_metric_collector)


class ExportToDjangoView(APIView):
    """参考 django_prometheus.exports.ExportToDjangoView, 增加了鉴权"""

    renderer_classes = [StaticHTMLRenderer]
    authentication_classes = (BasicAuthentication,)
    permission_classes = ()

    def get(self, request):
        if 'prometheus_multiproc_dir' in os.environ:
            logger.info("enable prometheus using multi processes mode")
            registry = prometheus_client.CollectorRegistry()
            multiprocess.MultiProcessCollector(registry)
            registry.register(cb_metric_collector)  # type: ignore
        else:
            logger.info("enable prometheus using single process mode")
            registry = prometheus_client.REGISTRY

        metrics_page = prometheus_client.generate_latest(registry)
        return Response(metrics_page, content_type=prometheus_client.CONTENT_TYPE_LATEST)
