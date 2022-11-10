# -*- coding: utf-8 -*-
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
