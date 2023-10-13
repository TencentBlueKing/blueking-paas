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
from dataclasses import dataclass
from typing import List, Optional

from bkpaas_auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet

from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.engine.models.operations import ModuleEnvironmentOperations


@dataclass
class AppContactInfo:
    """Information for contacting application"""

    latest_operator: Optional[User]
    recent_deployment_operators: List[User]


def get_contact_info(application: Application) -> AppContactInfo:
    """Get application's contact info"""
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
