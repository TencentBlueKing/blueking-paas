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
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.platform.applications.models import Application
from paasng.core.core.storages.sqlalchemy import console_db
from paasng.accessories.publish.sync_market.managers import AppUseRecordManger

from .handlers import on_product_deploy_success
from .serializers import PVGroupByAppSLZ


class StatisticsPVAPIView(APIView):
    """
    应用访问量
    get: 获取应用访问量
    - [测试地址](/api/bkapps/applications/statistics/pv/top5)
    """

    def get(self, request):
        serializer = PVGroupByAppSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        form = serializer.data

        has_console_db = getattr(settings, "BK_CONSOLE_DBCONF", None)
        if not has_console_db:
            return Response({"data": []})

        application_codes = list(Application.objects.filter_by_user(request.user).values_list("code", flat=True))
        session = console_db.get_scoped_session()
        data = AppUseRecordManger(session).get_app_records(application_codes, form["days_before"], form["limit"])
        return Response({"data": data})


class TestONProductDeployAPIView(APIView):

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.MANAGE_APP_MARKET)]

    def get(self, request, code):
        application = Application.objects.get(code=code)
        on_product_deploy_success(application.get_product(), 'prod')
        return Response({"msg": 'ok!', 'data': application.code})
