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
import datetime
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional

from bkpaas_auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet
from django.utils import timezone

from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.models.operations import ModuleEnvironmentOperations
from paasng.utils.basic import get_username_by_bkpaas_user_id


@dataclass
class AppContactInfo:
    """Information for contacting application"""

    latest_operator: Optional[User]
    recent_deployment_operators: List[User]


def get_contact_info_by_appids(ids: List[str], days_range: int = 31) -> Dict[str, AppContactInfo]:
    """Gets the contact infos for multiple applications."""
    applications = Application.objects.prefetch_related("latest_op__operation").filter(code__in=ids)

    # 获取所有应用的最新操作用户
    latest_operators = {
        app.code: app.latest_op.operation.user if hasattr(app, "latest_op") and app.latest_op else None
        for app in applications
    }

    # 获取在这个时间之后应用所有的操作者
    earliest_date = timezone.now() - datetime.timedelta(days=days_range)

    # 获取所有应用的最近部署操作者
    module_operations = (
        ModuleEnvironmentOperations.objects.filter(application__in=applications, created__gte=earliest_date)
        .values_list("application", "operator")
        .distinct()
    )

    # 应用ID和其部署操作者列表的映射
    recent_deployments = defaultdict(list)
    for app_id, operator_id in module_operations:
        recent_deployments[app_id].append(operator_id)

    contact_info_dict = {
        app.code: AppContactInfo(
            latest_operator=latest_operators[app.code],
            recent_deployment_operators=recent_deployments[app.code],
        )
        for app in applications
    }

    return contact_info_dict


def get_contact_info(application: Application) -> AppContactInfo:
    """Retrieve app's contact info; each app performs 4 SQL operations."""
    try:
        latest_operator = application.latest_op.operation.user
    except ObjectDoesNotExist:
        latest_operator = None

    # 获取距离最近操作时间一个月内，仍然在部署应用的用户
    recent_deployment_operators = query_recent_deployment_operators(application.module_operations, days_range=31)
    return AppContactInfo(latest_operator=latest_operator, recent_deployment_operators=recent_deployment_operators)


def get_env_recent_deployment_ops(env: ModuleEnvironment) -> List[User]:
    """Get environment's recent deployment operators"""
    return query_recent_deployment_operators(env.module_operations, days_range=31)


def query_recent_deployment_operators(operations: QuerySet, days_range: int) -> List[User]:
    """Query latest deployment operators within given days

    :param days_range: the max days range until the latest deployment operation
    """
    try:
        latest_deployment_operation = operations.latest("created")
        earliest_date = latest_deployment_operation.created - datetime.timedelta(days=days_range)
        return list(operations.filter(created__gte=earliest_date).values_list("operator", flat=True).distinct())
    except ModuleEnvironmentOperations.DoesNotExist:
        return []


def get_last_operator(application: Application):
    """Query latest deployment operator"""
    # 获取最近操作人员
    last_deployment = (
        Deployment.objects.filter(app_environment__module__application__code=application.code)
        .order_by("-created")
        .first()
    )
    if not last_deployment:
        return None

    return get_username_by_bkpaas_user_id(last_deployment.operator)
