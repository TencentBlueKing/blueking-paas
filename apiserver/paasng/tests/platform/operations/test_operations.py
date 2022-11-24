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
import logging

import pytest

from paasng.engine.constants import JobStatus
from paasng.platform.operations.constant import OperationType
from paasng.platform.operations.models import AppDeploymentOperationObj, ApplicationLatestOp, Operation
from tests.engine.setup_utils import create_fake_deployment

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


class TestAppLatestOp:
    def test_post_save_handler(self, bk_app, bk_user):
        op_type = OperationType.MODIFY_PRODUCT_ATTRIBUTES.value
        operation = Operation.objects.create(
            application=bk_app,
            type=op_type,
            user=bk_user,
            region=bk_app.region,
            source_object_id=bk_app.id.hex,
            extra_values={},
        )
        latest_op = ApplicationLatestOp.objects.get(application=bk_app)
        assert latest_op.operation_type == op_type
        assert latest_op.operation_id == operation.pk


class TestOperationObj:
    def test_normal(self, bk_app, bk_user):
        operation = Operation.objects.create(
            application=bk_app,
            type=OperationType.MODIFY_PRODUCT_ATTRIBUTES.value,
            user=bk_user,
            region=bk_app.region,
            source_object_id=bk_app.id.hex,
            extra_values={},
        )
        assert operation.get_operate_display() == '完善应用市场配置'


class TestProcessOperationObj:
    @pytest.mark.parametrize(
        'type_,extra_values,expected_text',
        [
            (OperationType.PROCESS_START, {'process_type': 'web'}, '启动 web 进程'),
            (OperationType.PROCESS_STOP, {'process_type': 'web'}, '停止 web 进程'),
            (OperationType.PROCESS_STOP, {}, '停止 未知 进程'),
        ],
    )
    def test_normal(self, type_, extra_values, expected_text, bk_app, bk_user):
        operation = Operation.objects.create(
            application=bk_app,
            type=type_.value,
            user=bk_user,
            region=bk_app.region,
            source_object_id=bk_app.id.hex,
            extra_values=extra_values,
        )
        assert operation.get_operate_display() == expected_text


class TestAppDeploymentOperationObj:
    @pytest.mark.parametrize(
        'status,expected_text',
        [
            (JobStatus.SUCCESSFUL, '成功部署生产环境'),
            (JobStatus.FAILED, '尝试部署生产环境失败'),
            (JobStatus.INTERRUPTED, '中断了生产环境的部署过程'),
        ],
    )
    def test_failed_deployment(self, status, expected_text, bk_module):
        deployment = create_fake_deployment(bk_module)
        deployment.status = status
        deployment.save(update_fields=['status'])

        operation = AppDeploymentOperationObj.create_operation_from_deployment(deployment)
        assert operation.get_operate_display() == expected_text
