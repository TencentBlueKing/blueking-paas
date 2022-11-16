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

from typing import Text

from django.http import Http404
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import UserApplicationFilter

from .phalanx import Client
from .serializer import (
    AppSummaryResultSLZ,
    EventGenreListQuerySLZ,
    EventGenreListSLZ,
    EventRecordAppSummaryQuerySLZ,
    EventRecordDetailsSLZ,
    EventRecordListQuerySLZ,
    EventRecordListSLZ,
    EventRecordMetricsQuerySLZ,
    EventRecordMetricsResultSLZ,
)


class EventRecordView(ViewSet, ApplicationCodeInPathMixin):

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_ALERT_RECORDS)]

    @swagger_auto_schema(responses={200: EventRecordListSLZ}, request_body=EventRecordListQuerySLZ, tags=["查询告警记录"])
    def query(self, request: Request, code: Text):
        request_slz = EventRecordListQuerySLZ(data=request.data, partial=True)
        request_slz.is_valid(True)

        client = Client()
        params = request_slz.validated_data
        labels = params.setdefault("labels", {})
        labels["app"] = code

        result = client.get_event_records(**params)
        if not result:
            raise Http404()

        slz = EventRecordListSLZ(result)

        return Response(slz.data)

    @swagger_auto_schema(
        responses={200: AppSummaryResultSLZ}, query_serializer=EventRecordAppSummaryQuerySLZ, tags=["个人应用告警统计"]
    )
    def app_summary(self, request: Request):
        request_slz = EventRecordAppSummaryQuerySLZ(data=request.query_params, partial=True)
        request_slz.is_valid(True)

        results = []
        applications = {i.code: i for i in UserApplicationFilter(request.user).filter(order_by=["code"])}

        # query only when applications is not empty
        if applications:
            client = Client()
            params = request_slz.validated_data
            labels = params.setdefault("labels", {})
            labels["app"] = list(applications.keys())

            records = client.get_grouped_records(groups=["app"], **params)
            if not records:
                raise Http404()

            for i in records.results:
                app = applications[i.labels["app"]]
                results.append({"summary": i, "app": app})

        slz = AppSummaryResultSLZ({"results": results})

        return Response(slz.data)


class EventRecordDetailsView(ViewSet, ApplicationCodeInPathMixin):

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_ALERT_RECORDS)]

    @swagger_auto_schema(responses={200: EventRecordDetailsSLZ}, tags=["查询告警记录详情"])
    def get(self, request: Request, code: Text, record: Text):
        client = Client()

        result = client.get_event_record_details(record, labels={"app": code})
        if not result:
            raise Http404()

        slz = EventRecordDetailsSLZ(result)

        return Response(slz.data)


class EventRecordMetricsView(ViewSet, ApplicationCodeInPathMixin):

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_ALERT_RECORDS)]

    @swagger_auto_schema(
        responses={200: EventRecordMetricsResultSLZ}, query_serializer=EventRecordMetricsQuerySLZ, tags=["查询告警记录指标趋势"]
    )
    def get(self, request: Request, code: Text, record: Text):
        request_slz = EventRecordMetricsQuerySLZ(data=request.query_params)
        request_slz.is_valid(True)

        client = Client()
        result = client.get_event_record_metrics(
            record,
            request_slz.validated_data["start"],
            request_slz.validated_data["end"],
            request_slz.validated_data["step"],
        )
        if not result:
            raise Http404()

        slz = EventRecordMetricsResultSLZ(result)

        return Response(slz.data)


class EventGenreView(ViewSet, ApplicationCodeInPathMixin):

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_ALERT_RECORDS)]

    @swagger_auto_schema(responses={200: EventGenreListSLZ}, query_serializer=EventGenreListQuerySLZ, tags=["查询告警类型"])
    def list(self, request: Request, code: Text):
        request_slz = EventGenreListQuerySLZ(data=request.query_params, partial=True)
        request_slz.is_valid(True)

        client = Client()

        result = client.get_event_genre(**request_slz.validated_data)
        if not result:
            raise Http404()

        slz = EventGenreListSLZ(result)

        return Response(slz.data)
