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
import datetime
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from bk_audit.log.models import AuditContext, AuditInstance
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from iam import Action

from paasng.misc.audit import constants
from paasng.misc.audit.client import bk_audit_client
from paasng.misc.audit.models import AppAuditRecord
from paasng.platform.applications.models import Application

logger = logging.getLogger(__name__)


@dataclass
class AppBaseObj:
    code: str
    name: str


class ApplicationInstance(AuditInstance):
    def __init__(self, app_code):
        try:
            app = Application.default_objects.get(code=app_code)
        except ObjectDoesNotExist:
            # 如果应用已经删除，则只记录应用 ID 即可
            self.instance = AppBaseObj(code=app_code, name=app_code)
        self.instance = AppBaseObj(code=app_code, name=app.name)

    @property
    def instance_id(self):
        return self.instance.code

    @property
    def instance_name(self):
        return self.instance.name


def report_event_to_bk_audit(record: AppAuditRecord):
    """将操作记录中的数据上报到审计中心"""
    # 仅操作为终止状态时才记录到审计中心
    if (
        (not settings.ENABLE_BK_AUDIT)
        or (not record.action_id)
        or (record.result_code not in constants.ResultCode.terminated_result())
    ):
        return
    try:
        audit_context = AuditContext(
            username=record.username,
            access_type=record.access_type,
            scope_type=record.scope_type,
            scope_id=record.scope_id,
        )
        bk_audit_client.add_event(
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


def add_app_audit_record(
    app_code: str,
    user: str,
    action_id: str,
    operation: str,
    target: str,
    source_object_id: Optional[str] = None,
    attribute: Optional[str] = None,
    module_name: Optional[str] = None,
    env: Optional[str] = None,
    access_type: int = constants.AccessType.WEB,
    result_code: int = constants.ResultCode.SUCCESS,
    data_type: str = constants.DataType.NO_DATA,
    data_before: Union[str, int, Dict[str, Any], None] = None,
    data_after: Union[str, int, Dict[str, Any], None] = None,
    end_time: Optional[datetime.datetime] = None,
) -> AppAuditRecord:
    """
    创建应用审计记录，并根据配置决定是否上报到审计中心

    :param app_code: 应用 ID
    :param user: encode 后的用户名
    :param action_id: 注册到权限中心的操作ID
    :param operation: 操作类型
    :param target: 操作对象
    :param source_object_id: 事件来源对象ID
    :param attribute: 对象属性
    :param module_name: 模块名
    :param env: 环境
    :param access_type: 访问方式
    :param result_code: 操作结果
    :param data_before: 操作前的数据，可以是字符串、整数或字典
    :param data_after: 操作后的数据，可以是字符串、整数或字典
    :param data_type: 数据类型，可选，默认值为 None
    :param end_time: 操作结束时间
    """
    record = AppAuditRecord.objects.create(
        app_code=app_code,
        user=user,
        action_id=action_id,
        operation=operation,
        target=target,
        source_object_id=source_object_id,
        attribute=attribute,
        module_name=module_name,
        env=env,
        access_type=access_type,
        result_code=result_code,
        data_type=data_type,
        data_before=data_before,
        data_after=data_after,
        end_time=end_time,
    )
    report_event_to_bk_audit(record)
    return record


def update_app_audit_record(source_object_id: str, result_code: int) -> AppAuditRecord:
    """更新审计记录的结果

    :param source_object_id: 事件来源对象ID,用于定位要更新的操作记录
    """
    try:
        record = AppAuditRecord.objects.get(source_object_id=source_object_id)
    except ObjectDoesNotExist:
        logger.exception("update app audit error, record with source_object_id<%s> not exits", source_object_id)

    record.result_code = result_code
    update_fields = ["result_code"]
    # 如果是终止状态，则同时更新结束时间
    if result_code not in constants.ResultCode.terminated_result():
        record.end_time = timezone.now()
        update_fields.append("end_time")
    record.save(update_fields=update_fields)

    report_event_to_bk_audit(record)
    return record
