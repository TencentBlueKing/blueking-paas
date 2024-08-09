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

from typing import Dict, Optional

from django.core.management.base import BaseCommand

from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import OperationEnum, OperationTarget, ResultCode
from paasng.misc.audit.handlers import on_app_operation_created, post_save
from paasng.misc.audit.models import AppLatestOperationRecord, AppOperationRecord
from paasng.misc.operations.constant import OperationType as OpType
from paasng.misc.operations.models import Operation

OPRATION_TRANSFER_MAP: Dict[int, Dict[str, Optional[str]]] = {
    OpType.CREATE_APPLICATION.value: {
        "action_id": "",
        "target": OperationTarget.APP,
        "operation": OperationEnum.CREATE_APP,
        "attribute_name": None,
    },
    OpType.REGISTER_PRODUCT.value: {
        "action_id": AppAction.MANAGE_APP_MARKET,
        "target": OperationTarget.APP,
        "operation": OperationEnum.MODIFY_MARKET_INFO,
        "attribute_name": None,
    },
    OpType.MODIFY_PRODUCT_ATTRIBUTES.value: {
        "action_id": AppAction.MANAGE_APP_MARKET,
        "target": OperationTarget.APP,
        "operation": OperationEnum.MODIFY_MARKET_INFO,
        "attribute_name": None,
    },
    OpType.PROCESS_START.value: {
        "action_id": AppAction.BASIC_DEVELOP,
        "target": OperationTarget.PROCESS,
        "operation": OperationEnum.START,
        "attribute_name": "process_type",
    },
    OpType.PROCESS_STOP.value: {
        "action_id": AppAction.BASIC_DEVELOP,
        "target": OperationTarget.PROCESS,
        "operation": OperationEnum.STOP,
        "attribute_name": "process_type",
    },
    OpType.DELETE_APPLICATION.value: {
        "action_id": AppAction.DELETE_APPLICATION,
        "target": OperationTarget.APP,
        "operation": OperationEnum.DELETE,
        "attribute_name": None,
    },
    OpType.OFFLINE_APPLICATION_STAG_ENVIRONMENT.value: {
        "action_id": AppAction.DELETE_APPLICATION,
        "target": OperationTarget.APP,
        "operation": OperationEnum.OFFLINE,
        "attribute_name": None,
    },
    OpType.OFFLINE_APPLICATION_PROD_ENVIRONMENT.value: {
        "action_id": AppAction.DELETE_APPLICATION,
        "target": OperationTarget.APP,
        "operation": OperationEnum.OFFLINE,
        "attribute_name": None,
    },
    OpType.DEPLOY_APPLICATION.value: {
        "action_id": AppAction.BASIC_DEVELOP,
        "target": OperationTarget.APP,
        "operation": OperationEnum.DEPLOY,
        "attribute_name": None,
    },
    OpType.CREATE_MODULE.value: {
        "action_id": AppAction.MANAGE_MODULE,
        "target": OperationTarget.MODULE,
        "operation": OperationEnum.CREATE,
        "attribute_name": None,
    },
    OpType.DELETE_MODULE.value: {
        "action_id": AppAction.MANAGE_MODULE,
        "target": OperationTarget.MODULE,
        "operation": OperationEnum.DELETE,
        "attribute_name": None,
    },
    OpType.DEPLOY_CNATIVE_APP.value: {
        "action_id": AppAction.BASIC_DEVELOP,
        "target": OperationTarget.APP,
        "operation": OperationEnum.DEPLOY,
    },
    OpType.OFFLINE_MARKET.value: {
        "action_id": AppAction.MANAGE_APP_MARKET,
        "target": OperationTarget.APP,
        "operation": OperationEnum.OFFLINE_MARKET,
        "attribute_name": None,
    },
    OpType.RELEASE_TO_MARKET.value: {
        "action_id": AppAction.MANAGE_APP_MARKET,
        "target": OperationTarget.APP,
        "operation": OperationEnum.RELEASE_TO_MARKET,
        "attribute_name": None,
    },
    OpType.APPLY_PERM_FOR_CLOUD_API.value: {
        "action_id": AppAction.MANAGE_CLOUD_API,
        "target": OperationTarget.CLOUD_API,
        "operation": OperationEnum.APPLY,
        "attribute_name": "gateway_name",
    },
    OpType.RENEW_PERM_FOR_CLOUD_API.value: {
        "action_id": AppAction.MANAGE_CLOUD_API,
        "target": OperationTarget.CLOUD_API,
        "operation": OperationEnum.RENEW,
        "attribute_name": "gateway_name",
    },
    OpType.ENABLE_ACCESS_CONTROL.value: {
        "action_id": AppAction.MANAGE_ACCESS_CONTROL,
        "target": OperationTarget.ACCESS_CONTROL,
        "operation": OperationEnum.ENABLE,
        "attribute_name": None,
    },
    OpType.DISABLE_ACCESS_CONTROL.value: {
        "action_id": AppAction.MANAGE_ACCESS_CONTROL,
        "target": OperationTarget.ACCESS_CONTROL,
        "operation": OperationEnum.DISABLE,
        "attribute_name": None,
    },
}


class Command(BaseCommand):
    help = "Transfer operations from Operation table to AppOperationRecord table, only executed when bk-audit is launched for the first time"

    def handle(self, *args, **kwargs):
        # 获取所有用于展示应用最近操作的记录
        operations = Operation.objects.filter(is_hidden=False)
        self.stdout.write(f"Transferring {operations.count()} operations...")
        for op in operations.iterator():
            operation_type = OPRATION_TRANSFER_MAP.get(op.type, {}).get("operation")
            if not operation_type:
                continue

            # 申请网关权限、启停进程等操作对象的具体属性记录在 extra_values 的相应字段中
            attribute_name = OPRATION_TRANSFER_MAP.get(op.type, {}).get("attribute_name")
            if attribute_name:
                attribute = op.extra_values.get(attribute_name)
            else:
                attribute = None
            # 如果原来的操作记录中保存了操作结果，则也需要同步
            if not op.extra_values.get("has_succeeded"):
                result_code = ResultCode.FAILURE
            else:
                result_code = ResultCode.SUCCESS

            post_save.disconnect(on_app_operation_created)
            new_record = AppOperationRecord.objects.create(
                app_code=op.application.code,
                user=op.user,
                module_name=op.module_name,
                environment=op.extra_values.get("env_name"),
                action_id=OPRATION_TRANSFER_MAP.get(op.type, {}).get("action_id"),
                operation=OPRATION_TRANSFER_MAP.get(op.type, {}).get("operation"),
                target=OPRATION_TRANSFER_MAP.get(op.type, {}).get("target"),
                attribute=attribute,
                result_code=result_code,
            )

            # 时间字段都是自动添加的，只能通过 update 方法来自定义
            AppOperationRecord.objects.filter(uuid=new_record.uuid).update(
                start_time=op.created,
                created=op.created,
            )
            AppLatestOperationRecord.objects.update_or_create(
                application=new_record.application,
                defaults={
                    "operation_id": new_record.pk,
                    "latest_operated_at": op.created,
                },
            )
        self.stdout.write("Transfer complete.")
