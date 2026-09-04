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

"""celery 任务的注册入口。

`autodiscover_tasks()` 只会在每个 app 的根包下找 `tasks` 模块，而本 app 的任务都
定义在子包里。对账任务没有视图会引用它，必须在这里显式导入，否则 worker 侧不会
注册，投递会以 `Received unregistered task` 失败。
"""

from .e2b.tasks import reconcile_e2b_sandboxes_task

__all__ = ["reconcile_e2b_sandboxes_task"]
