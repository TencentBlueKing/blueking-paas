# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from unittest import mock

from paasng.platform.agent_sandbox.e2b import tasks
from paasng.platform.agent_sandbox.e2b.exceptions import E2BTemplateSyncInProgress


class TestSyncTemplateTask:
    def test_retries_while_another_sync_runs(self):
        """拿不到锁时不能跳过，否则模板会一直停在待同步"""
        with mock.patch.object(
            tasks, "sync_template", side_effect=[E2BTemplateSyncInProgress("running"), None]
        ) as sync_template:
            result = tasks.sync_e2b_template_task.apply(args=["e2b-envd"])

        assert result.successful()
        assert sync_template.call_args_list == [mock.call("e2b-envd")] * 2


class TestSyncAllTemplatesTask:
    def test_retries_while_another_sync_runs(self):
        with mock.patch.object(tasks, "sync_all", side_effect=[E2BTemplateSyncInProgress("running"), []]) as sync_all:
            result = tasks.sync_all_e2b_templates_task.apply()

        assert result.successful()
        assert sync_all.call_count == 2
