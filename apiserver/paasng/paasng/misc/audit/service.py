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
from typing import Optional, Union

from attrs import asdict, define
from bk_audit.log.models import AuditContext, AuditInstance
from django.conf import settings
from iam import Action

from paasng.misc.audit.client import bk_audit_client
from paasng.misc.audit.constants import AccessType, DataType, ResultCode
from paasng.misc.audit.models import AdminOperationRecord, AppOperationRecord
from paasng.platform.applications.models import Application

logger = logging.getLogger(__name__)


@define
class AppBaseObj:
    code: str
    name: str


@define
class DataDetail:
    type: DataType = DataType.RAW_DATA
    data: Union[str, int, dict, list] | None = None


class ApplicationInstance(AuditInstance):
    def __init__(self, app_code):
        try:
            app = Application.default_objects.get(code=app_code)
        except Application.DoesNotExist:
            # 如果应用已经删除，则只记录应用 ID 即可
            self.instance = AppBaseObj(code=app_code, name=f"{app_code}__DELETE__")
        else:
            self.instance = AppBaseObj(code=app_code, name=app.name)

    @property
    def instance_id(self):
        return self.instance.code

    @property
    def instance_name(self):
        return self.instance.name


def report_event_to_bk_audit(record: AppOperationRecord):
    """将操作记录中的数据上报到审计中心"""
    # 未设置审计中心相关配置则不上报
    if not settings.ENABLE_BK_AUDIT or not record.need_to_report_bk_audit:
        logger.debug(f"skip report to bk_audit, record:{record.uuid}")
        return
    try:
        audit_context = AuditContext(
            username=record.username,
            access_type=record.access_type,
            scope_type=record.scope_type,
            scope_id=record.scope_id,
        )
        bk_audit_client.add_event(
            event_id=record.uuid.hex,
            action=Action(record.action_id),
            resource_type=record.resource_type_id,
            audit_context=audit_context,
            instance=ApplicationInstance(record.app_code),
        )
    except Exception:
        logger.exception(
            "bk_audit add application event error: username: %s, action_id: %s, scope_id: %s, scope_type: %s, app_code: %s",
            record.username,
            record.action_id,
            record.scope_id,
            record.scope_type,
            record.app_code,
        )
    logger.info(
        "bk_audit add application event: username: %s, action_id: %s, app_code: %s",
        record.username,
        record.action_id,
        record.app_code,
    )
    return


def add_app_audit_record(
    app_code: str,
    tenant_id: str,
    user: str,
    action_id: str,
    operation: str,
    target: str,
    attribute: Optional[str] = None,
    module_name: Optional[str] = None,
    environment: Optional[str] = None,
    access_type: int = AccessType.WEB,
    result_code: int = ResultCode.SUCCESS,
    data_before: Optional[DataDetail] = None,
    data_after: Optional[DataDetail] = None,
) -> AppOperationRecord:
    """
    创建应用审计记录，并根据配置决定是否上报到审计中心。
    说明：已讨论确认在操作过程结束的时候记录操作记录即可，比如部署成功、失败时，所以不需要记录 end_time, 也不需要提供更新操作记录的方法

    :param app_code: 应用 ID
    :param tenant_id: 租户 ID
    :param user: encode 后的用户名，形如 0335cce79c92
    :param action_id: 注册到权限中心的操作ID, 如：基础开发、模块管理
    :param operation: 操作类型，如：新建、部署、扩容等
    :param target: 操作对象，如：模块、进程、增强服务等
    :param attribute: 对象属性，如 【web】进程、【mysql】增强服务
    :param module_name: 模块名
    :param environment: 环境，如: stag、prod
    :param access_type: 访问方式，默认为网页访问
    :param result_code: 操作结果，默认为成功
    :param data_before: 操作前的数据，包含数据类型的对应的数据
    :param data_after: 操作后的数据，包含数据类型的对应的数据
    """
    record = AppOperationRecord.objects.create(
        app_code=app_code,
        user=user,
        action_id=action_id,
        operation=operation,
        target=target,
        attribute=attribute,
        module_name=module_name,
        environment=environment,
        access_type=access_type,
        result_code=result_code,
        data_before=asdict(data_before) if data_before else None,
        data_after=asdict(data_after) if data_after else None,
        tenant_id=tenant_id,
    )
    report_event_to_bk_audit(record)
    return record


def add_admin_audit_record(
    user: str,
    operation: str,
    target: str,
    app_code: Optional[str] = None,
    attribute: Optional[str] = None,
    module_name: Optional[str] = None,
    environment: Optional[str] = None,
    access_type: int = AccessType.WEB,
    result_code: int = ResultCode.SUCCESS,
    data_before: Optional[DataDetail] = None,
    data_after: Optional[DataDetail] = None,
) -> AdminOperationRecord:
    """
    创建 admin42 审计记录

    :param user: encode 后的用户名，形如 0335cce79c92
    :param operation: 操作类型，如：新建、部署、扩容等
    :param target: 操作对象，如：模块、进程、增强服务等
    :param app_code: 应用 ID，在 admin 中操作默认为 None
    :param attribute: 对象属性，如 【web】进程、【mysql】增强服务
    :param module_name: 模块名
    :param environment: 环境，如: stag、prod
    :param access_type: 访问方式，默认为网页访问
    :param result_code: 操作结果，默认为成功
    :param data_before: 操作前的数据，包含数据类型的对应的数据
    :param data_after: 操作后的数据，包含数据类型的对应的数据
    """
    return AdminOperationRecord.objects.create(
        user=user,
        operation=operation,
        target=target,
        app_code=app_code,
        attribute=attribute,
        module_name=module_name,
        environment=environment,
        access_type=access_type,
        result_code=result_code,
        data_before=asdict(data_before) if data_before else None,
        data_after=asdict(data_after) if data_after else None,
    )


# 平台管理推荐使用该函数名以做区分，未来可能会废弃 admin42 的
add_plat_mgt_audit_record = add_admin_audit_record
