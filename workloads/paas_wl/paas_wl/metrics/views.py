# -*- coding: utf-8 -*-
import logging
import os

import prometheus_client
from prometheus_client import multiprocess
from rest_framework.renderers import StaticHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import BasicAuthentication

logger = logging.getLogger(__name__)


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
        else:
            logger.info("enable prometheus using single process mode")
            registry = prometheus_client.REGISTRY

        metrics_page = prometheus_client.generate_latest(registry)
        return Response(metrics_page, content_type=prometheus_client.CONTENT_TYPE_LATEST)
