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
from typing import Type

from blue_krill.async_utils.poll_task import CallbackHandler

from paas_wl.bk_app.deploy.actions.archive import ArchiveOperationController
from paasng.platform.engine.deploy.archive.base import BaseArchiveManager
from paasng.platform.engine.deploy.bg_wait.wait_deployment import wait_for_all_stopped
from paasng.platform.engine.models.offline import OfflineOperation
from paasng.platform.engine.task import archive_related_resources


class ApplicationArchiveManager(BaseArchiveManager):
    def perform_implement(self, offline_operation: OfflineOperation, result_handler: Type[CallbackHandler]):
        """Start the offline operation, this will start background task, and call result handler when task finished"""
        op_id = str(offline_operation.pk)
        ArchiveOperationController(env=self.env).start()
        wait_for_all_stopped(env=self.env, result_handler=result_handler, extra_params={"operation_id": op_id})
        # 成功下架后，回收 service 和 pre-release-hook 相关资源
        # 该部分资源用户不可见，因此不论成功失败都不该阻塞下架操作
        archive_related_resources.delay(env=self.env)
