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

"""Base functions for s-mart app building steps"""

import logging
from typing import Dict, Optional, Type
from blue_krill.async_utils.poll_task import TaskPoller

from paasng.misc.tools.smart_app.models import SmartBuild
from paasng.misc.tools.smart_app.workflow import SmartBuildCoordinator

logger = logging.getLogger(__name__)

class SmartBuildPoller(TaskPoller):
    """BasePoller for querying the status of s-mart build operation, will auto refresh polling time before task start"""

    @classmethod
    def start(cls, params: Dict, callback_handler_cls: Optional[Type] = None):
        smart_build = SmartBuild.objects.get(pk=params["smart_build_id"])
        SmartBuildCoordinator(f"{smart_build.operator}:{smart_build.app_code}").update_polling_time()
        super().start(params, callback_handler_cls)
