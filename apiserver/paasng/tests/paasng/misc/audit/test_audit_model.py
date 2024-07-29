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

import pytest
from django.test.utils import override_settings

from paasng.misc.audit.constants import OperationEnum, OperationTarget, ResultCode
from paasng.misc.audit.utils import add_app_audit_record

pytestmark = pytest.mark.django_db


class TestAppAuditRecord:
    @pytest.mark.parametrize(
        ("target", "operation", "attribute", "module_name", "env", "result_code", "expected"),
        [
            (
                OperationTarget.APP,
                OperationEnum.CREATE_APP,
                None,
                None,
                None,
                ResultCode.SUCCESS,
                "{username} 创建应用成功",
            ),
            (
                OperationTarget.APP,
                OperationEnum.RELEASE_TO_MARKET,
                None,
                None,
                None,
                ResultCode.SUCCESS,
                "{username} 发布到应用市场成功",
            ),
            (
                OperationTarget.MODULE,
                OperationEnum.CREATE,
                "module1",
                None,
                None,
                ResultCode.SUCCESS,
                "{username} 新建 module1 模块成功",
            ),
            (
                OperationTarget.PROCESS,
                OperationEnum.START,
                "web",
                "module1",
                "stag",
                ResultCode.SUCCESS,
                "{username} 启动 module1 模块预发布环境 web 进程成功",
            ),
            (
                OperationTarget.ACCESS_CONTROL,
                OperationEnum.ENABLE,
                None,
                "module1",
                None,
                ResultCode.SUCCESS,
                "{username} 启用 module1 模块用户限制成功",
            ),
            (
                OperationTarget.CLOUD_API,
                OperationEnum.APPLY,
                "bkdata 网关",
                None,
                None,
                ResultCode.ONGOING,
                "{username} 申请 bkdata 网关 云 API 权限",
            ),
        ],
    )
    def test_opreation_record_display(
        self, bk_app, bk_user, operation, target, attribute, module_name, env, result_code, expected
    ):
        with override_settings(ENABLE_BK_AUDIT=False):
            record = add_app_audit_record(
                app_code=bk_app.code,
                user=bk_user,
                action_id="xxxxx",
                operation=operation,
                target=target,
                attribute=attribute,
                module_name=module_name,
                env=env,
                result_code=result_code,
            )
        assert record.get_display_text() == expected.format(username=record.username)
