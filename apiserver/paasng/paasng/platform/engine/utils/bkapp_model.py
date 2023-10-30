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
from typing import List

from paasng.platform.bkapp_model.manager import ModuleProcessSpecManager, sync_hooks
from paasng.platform.engine.models.deployment import ProcessTmpl
from paasng.platform.modules.models.deploy_config import HookList


def sync_to_bkapp_model(module, processes: List[ProcessTmpl], hooks: HookList):
    """保存应用描述文件记录的信息到 bkapp_models
    - Processes
    - Hooks
    """
    ModuleProcessSpecManager(module).sync_from_desc(processes=processes)
    sync_hooks(module, hooks)
