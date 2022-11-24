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
import json
from typing import List, Type

from blue_krill.monitoring.probe.base import ProbeSet
from django.conf import settings
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import serializers, status, views
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .probe import DBProbe, StreamChannelRedisProbe


class IssueSerializer(serializers.Serializer):
    deadly = serializers.BooleanField()
    description = serializers.CharField()


class DiagnosisReportSerializer(serializers.Serializer):
    system_name = serializers.CharField()
    alive = serializers.BooleanField()
    issues = IssueSerializer(many=True)


class HealthView(views.APIView):
    authentication_classes: List[Type] = []
    permission_classes = [AllowAny]

    def get(self, request):
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

        diagnosis_list = ProbeSet([DBProbe, StreamChannelRedisProbe]).examination()
        if diagnosis_list.is_death:
            return Response(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                data={
                    "result": False,
                    "data": DiagnosisReportSerializer(diagnosis_list.items, many=True).data,
                    "message": json.dumps(diagnosis_list.get_fatal_report()),
                },
            )
        return Response(
            data={
                "result": True,
                "message": json.dumps(diagnosis_list.get_fatal_report() if diagnosis_list.is_death else "ok"),
                "data": DiagnosisReportSerializer(diagnosis_list.items, many=True).data,
            }
        )


class ReadyzView(views.APIView):
    authentication_classes: List[Type] = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response()


schema_view = get_schema_view(
    openapi.Info(
        title="PaaS3.0 API[workflows]",
        default_version='vx',
        description="PaaS3.0 API Document",
        terms_of_service="https://bk.tencent.com/",
        contact=openapi.Contact(email="blueking@tencent.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(AllowAny,),
)
