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

from paas_wl.bk_app.cnative.specs.resource import delete_bkapp
from paasng.platform.engine.deploy.archive.base import BaseArchiveManager
from paasng.platform.engine.deploy.bg_wait.wait_deployment import wait_for_all_stopped
from paasng.platform.engine.models.offline import OfflineOperation


class BkAppArchiveManager(BaseArchiveManager):
    def perform_implement(self, offline_operation: OfflineOperation, result_handler: Type[CallbackHandler]):
        """Start the offline operation, this will start background task, and call result handler when task finished"""
        op_id = str(offline_operation.pk)
        # 清理 BkApp crd
        delete_bkapp(self.env)
        # 清理进程配置
        # Note: 由于云原生应用可由用户直接选择 plan, 因此下架应用可直接删除 ProcessSpec 数据, 无需担心后台分配的 plan 记录被清理
        self.env.wl_app.process_specs.all().delete()
        wait_for_all_stopped(env=self.env, result_handler=result_handler, extra_params={"operation_id": op_id})
