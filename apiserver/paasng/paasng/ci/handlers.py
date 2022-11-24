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
from typing import TYPE_CHECKING

from django.dispatch import receiver

from paasng.ci.base import BkUserOAuth
from paasng.ci.constants import CIBackend
from paasng.ci.exceptions import NotSupportedRepoType
from paasng.ci.managers import get_ci_manager_cls_by_backend
from paasng.ci.models import CIAtomJob
from paasng.engine.constants import JobStatus
from paasng.engine.signals import post_appenv_deploy
from paasng.platform.applications.models import ApplicationEnvironment

if TYPE_CHECKING:
    from paasng.engine.models.deployment import Deployment

logger = logging.getLogger(__name__)


@receiver(post_appenv_deploy)
def start_ci_job(sender: 'ApplicationEnvironment', deployment: 'Deployment', **kwargs):
    """开始 CI 任务"""
    if not deployment.status == JobStatus.SUCCESSFUL.value:
        logger.info("AppEnv<%s> deploy failed, skipping", sender)
        return

    if CIAtomJob.objects.filter(deployment=deployment, backend=CIBackend.CODECC).exists():
        logger.info("Already exists a job for deployment<%s> of AppEnv<%s>, skipping", deployment.pk, sender.pk)
        return

    if CIAtomJob.objects.filter(
        env=deployment.app_environment,
        deployment__source_revision=deployment.source_revision,
        status=JobStatus.SUCCESSFUL,
    ).exists():
        logger.info(
            "the ci job of source<%s> revision<%s> has been executed before",
            deployment.source_location,
            deployment.source_revision,
        )
        return

    try:
        mgr = get_ci_manager_cls_by_backend(CIBackend.CODECC)(
            deployment=deployment, user_oauth=BkUserOAuth.from_user_profile(deployment.operator)
        )
        mgr.start()
    except NotSupportedRepoType as e:
        logger.info("source type<%s> is not support, ci skipping", e.source_type)
        return
    except Exception:
        logger.exception("failed to execute ci job")
        return
