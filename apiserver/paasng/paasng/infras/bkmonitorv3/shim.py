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

from contextlib import suppress
from typing import Tuple

from paasng.infras.bkmonitorv3.client import make_bk_monitor_space_manager
from paasng.infras.bkmonitorv3.definitions import gen_bk_monitor_space
from paasng.infras.bkmonitorv3.models import BKMonitorSpace
from paasng.infras.iam.tasks import add_monitoring_space_permission
from paasng.platform.applications.models import Application
from paasng.platform.applications.tenant import get_tenant_id_for_app


def create_bk_monitor_space(application: Application) -> BKMonitorSpace:
    """create bk monitor space associated to the given application

    :param application:
    :return: BKMonitorSpace
    """
    tenant_id = get_tenant_id_for_app(application.code)
    mgr = make_bk_monitor_space_manager(tenant_id)
    try:
        # 兼容多个 paas 环境对接同一个蓝鲸监控服务的情况, 先尝试获取同名的 space, 如果存在则不调用蓝鲸监控的创建接口
        space = mgr.get_space_detail(gen_bk_monitor_space(application))
    except Exception:
        space = mgr.create_space(gen_bk_monitor_space(application))

    add_monitoring_space_permission.delay(application.code, application.name, bk_space_id=space.iam_resource_id)
    return BKMonitorSpace.objects.update_or_create(
        application=application,
        defaults={
            "id": space.id,
            "space_type_id": space.space_type_id,
            "space_id": space.space_id,
            "space_name": space.space_name,
            "space_uid": space.space_uid,
            "extra_info": space.extra_info,
            "tenant_id": application.tenant_id,
        },
    )[0]


def get_or_create_bk_monitor_space(application: Application) -> Tuple[BKMonitorSpace, bool]:
    """get or create bk monitor space associated to the given application
    if a new bk monitor space is created, will invoke a delay task to grant iam permission to the created space.

    :param application:
    :return: Tuple[BKMonitorSpace, whether a bk monitor space was created]
    """
    with suppress(BKMonitorSpace.DoesNotExist):
        return BKMonitorSpace.objects.get(application=application), False
    return create_bk_monitor_space(application), True


def update_or_create_bk_monitor_space(application: Application) -> Tuple[BKMonitorSpace, bool]:
    """update the bk monitor space associated to the given application

    :param application:
    :return: Tuple[BKMonitorSpace, whether a bk monitor space was created]
    """
    try:
        db_space = BKMonitorSpace.objects.get(application=application)
    except BKMonitorSpace.DoesNotExist:
        return create_bk_monitor_space(application), True

    tenant_id = get_tenant_id_for_app(application.code)
    mgr = make_bk_monitor_space_manager(tenant_id)
    space = mgr.update_space(gen_bk_monitor_space(application))
    db_space.id = space.id
    db_space.space_type_id = space.space_type_id
    db_space.space_id = space.space_id
    db_space.space_name = space.space_name
    db_space.space_uid = space.space_uid
    db_space.extra_info = space.extra_info
    db_space.save()
    return db_space, False
