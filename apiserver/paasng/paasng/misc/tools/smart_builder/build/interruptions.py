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

import logging

from bkpaas_auth.models import User
from django.utils import timezone
from django.utils.translation import gettext as _

from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paasng.misc.tools.smart_builder.build import SmartBuildHandler, get_default_cluster_name
from paasng.misc.tools.smart_builder.exceptions import SmartBuildInterruptionFailed
from paasng.misc.tools.smart_builder.models import SmartBuild
from paasng.misc.tools.smart_builder.utils.flow import SmartBuildCoordinator
from paasng.platform.engine.constants import JobStatus

from .builder import generate_builder_name, get_default_builder_namespace

logger = logging.getLogger(__name__)


def interrupt_smart_build(smart_build: SmartBuild, user: User):
    if smart_build.operator != user.pk:
        raise SmartBuildInterruptionFailed(_("无法中断由他人发起的构建"))
    if smart_build.status in JobStatus.get_finished_states():
        raise SmartBuildInterruptionFailed(_("无法中断，构建已处于结束状态"))

    now = timezone.now()
    smart_build.build_interrupted_at = now
    smart_build.save(update_fields=["build_interrupted_at", "updated"])

    # 如果构建进程的数据上报已经超时，则认为构建失败，主动解锁
    coordinator = SmartBuildCoordinator(f"{smart_build.operator}:{smart_build.app_code}")
    coordinator.release_if_polling_timed_out(expected_smart_build=smart_build)

    # 尝试删除 构建的 pod
    client = get_client_by_cluster_name(get_default_cluster_name())
    SmartBuildHandler(client).interrupt_builder(
        namespace=get_default_builder_namespace(),
        name=generate_builder_name(smart_build),
    )
