# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

import logging
from collections import Counter
from operator import itemgetter
from typing import Dict

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response
from rest_framework.views import APIView

from paasng.accessories.publish.market.constant import AppState
from paasng.platform.applications import serializers as slzs
from paasng.platform.applications.models import Application, ApplicationEnvironment

logger = logging.getLogger(__name__)


class ApplicationGroupByStateStatisticsView(APIView):
    def get(self, request):
        """
        应用视图接口-按应用状态分组
        - [测试地址](/api/bkapps/applications/statistics/group_by_state/)
        """
        application_queryset = Application.objects.filter_by_user(request.user)
        applications_ids = application_queryset.values_list("id", flat=True)
        queryset = ApplicationEnvironment.objects.filter(application__id__in=applications_ids)
        never_deployed = queryset.filter(deployments__isnull=True, environment="stag").values("id").distinct().count()

        # 预发布环境的应用, 需要排除同时部署过预发布环境和正式环境的应用
        prod_deployed_ids = queryset.filter(is_offlined=False, deployments__isnull=False, environment="prod").values(
            "id"
        )
        stag_deployed = (
            queryset.filter(is_offlined=False, deployments__isnull=False, environment="stag")
            .exclude(id__in=prod_deployed_ids)
            .values("id")
            .distinct()
            .count()
        )

        prod_deployed = (
            queryset.filter(is_offlined=False, deployments__isnull=False, environment="prod")
            .values("id")
            .distinct()
            .count()
        )

        onlined_market = application_queryset.filter(product__state=AppState.RELEASED.value).count()

        offlined_counts = application_queryset.filter(is_active=False).count()

        data = [
            {"name": _("开发中"), "count": never_deployed, "group": "developing"},
            {"name": _("预发布环境"), "count": stag_deployed, "group": "stag"},
            {"name": _("生产环境"), "count": prod_deployed, "group": "prod"},
            {"name": _("应用市场"), "count": onlined_market, "group": "product"},
            {"name": _("已下架"), "count": offlined_counts, "group": "offline"},
        ]
        return Response({"data": data})


class ApplicationGroupByFieldStatisticsView(APIView):
    def get(self, request):
        """
        应用概览-按某个App字段聚合分类
        - [测试地址](/api/bkapps/applications/summary/group_by_field/)
        ----
        {
            "200": {
                "description": "获取应用概览信息成功",
                "schema": {
                    "type": "object",
                    "properties": {
                        "total": {
                            "type": "integer",
                            "description": "应用总数",
                            "example": 23
                        },
                        {
                            "groups": [
                                {"count": 4, "region": "clouds"},
                                {"count": 5, "region": "tencent"},
                                {"count": 10, "region": "ieod"}],
                            "total": 19
                        }
                    }
                }
            }
        }
        """

        serializer = slzs.ApplicationGroupFieldSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        params = serializer.data
        include_inactive = params["include_inactive"]
        group_field = params["field"]

        queryset = Application.objects.filter_by_user(request.user)
        # 从用户角度来看，应用分类需要区分是否为已删除应用
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        application_group = queryset.values_list(group_field, flat=True)
        counter: Dict[str, int] = Counter(application_group)
        groups = [{group_field: group, "count": count} for group, count in list(counter.items())]
        # sort by count
        sorted_groups = sorted(groups, key=itemgetter("count"), reverse=True)
        data = {"total": queryset.count(), "groups": sorted_groups}
        return Response(data)
