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
from typing import TYPE_CHECKING

from django.conf import settings
from django.dispatch import receiver

from paas_wl.bk_app.applications.managers.app_build import delete_redundant_images
from paas_wl.bk_app.applications.models.build import Build
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.signals import post_appenv_deploy

if TYPE_CHECKING:
    from paasng.platform.engine.models import Deployment

logger = logging.getLogger(__name__)


@receiver(post_appenv_deploy)
def handle_post_deploy(sender, deployment: "Deployment", **kwargs):
    """部署成功后清理模块的多余镜像"""
    max_reserved_images_num = settings.MAX_RESERVED_IMAGES_PER_MODULE

    build_id = deployment.build_id
    if deployment.status != JobStatus.SUCCESSFUL.value or not build_id:
        return

    try:
        build = Build.objects.get(uuid=build_id)
    except Build.DoesNotExist:
        logger.info("Deployment<%s> Build<%s> 不存在, 跳过清理多余镜像", deployment.uuid, build_id)
        return

    module_id = build.module_id
    res = delete_redundant_images(
        module_id=module_id,
        max_reserved_num=max_reserved_images_num,
    )

    logger.info("部署后清理多余镜像完成, module_id=%s, deleted=%s, failed=%s", module_id, res.deleted, res.failed)
