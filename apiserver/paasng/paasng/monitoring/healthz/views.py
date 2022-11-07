# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from blue_krill.monitoring.probe.base import ProbeSet
from django.conf import settings
from rest_framework import serializers, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from paasng.monitoring.healthz.probes import get_default_probes


class IssueSerializer(serializers.Serializer):
    fatal = serializers.BooleanField(default=False, help_text="当前问题是否致命")
    description = serializers.CharField(help_text="当前问题的描述", default="")


class DianosisSerializer(serializers.Serializer):
    system_name = serializers.CharField(help_text="当前探测的系统名称")
    alive = serializers.BooleanField(help_text="当前探测的系统是否存活", default=True)
    issues = IssueSerializer(many=True)


class HealthViewSet(viewsets.ViewSet):
    permission_classes = [
        AllowAny,
    ]

    def healthz(self, request):
        token = request.query_params.get('token', '')
        if not settings.HEALTHZ_TOKEN:
            return Response(
                data={"errors": "Token was not configured in settings, request denied"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (token and token == settings.HEALTHZ_TOKEN):
            return Response(
                data={"errors": "Please provide valid token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        probe_set = ProbeSet(get_default_probes())
        diagnosis_list = probe_set.examination()

        if diagnosis_list.is_death:
            # if something deadly exist, we have to make response non-200 which is easier to be found
            # by monitor system and make response as a plain text
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data=diagnosis_list.get_fatal_report())

        return Response(data={'results': DianosisSerializer(diagnosis_list.items, many=True).data})

    def readyz(self, request):
        return Response()
