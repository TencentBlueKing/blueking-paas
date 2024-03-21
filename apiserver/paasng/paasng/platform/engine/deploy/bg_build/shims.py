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
from typing import Dict, Optional
from uuid import UUID

from blue_krill.redis_tools.messaging import StreamChannel
from celery import shared_task

from paas_wl.bk_app.applications.models.build import BuildProcess
from paas_wl.bk_app.deploy.app_res.utils import get_scheduler_client_by_app
from paasng.core.core.storages.redisdb import get_default_redis
from paasng.platform.engine.deploy.bg_build.executors import (
    DevopsPipelineBuildProcessExecutor,
    K8sBuildProcessExecutor,
)
from paasng.platform.engine.deploy.bg_build.utils import generate_builder_name
from paasng.platform.engine.exceptions import DeployInterruptionFailed
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.utils.output import ConsoleStream, DeployStream, RedisWithModelStream

logger = logging.getLogger(__name__)

# Max timeout seconds for waiting the slugbuilder pod to become ready
_WAIT_FOR_READINESS_TIMEOUT = 300
_FOLLOWING_LOGS_TIMEOUT = 300


@shared_task
def start_bg_build_process(
    deploy_id: UUID,
    bp_id: UUID,
    metadata: Dict,
    stream_channel_id: Optional[str] = None,
    use_devops_pipeline: bool = False,
):
    """Start a new build process which starts a builder to build a slug and deploy
    it to the app cluster.

    :param deploy_id: The ID of the deployment object.
    :param bp_id: The ID of the build process object.
    """
    build_process = BuildProcess.objects.get(pk=bp_id)
    # Make a new channel if stream_channel_id is given

    stream: DeployStream
    if stream_channel_id:
        stream_channel = StreamChannel(stream_channel_id, redis_db=get_default_redis())
        stream_channel.initialize()
        stream = RedisWithModelStream(build_process.output_stream, stream_channel)
    else:
        stream = ConsoleStream()

    if use_devops_pipeline:
        logger.info("deployment %s, build process %s use devops pipeline to build image", deploy_id, bp_id)
        devops_pipeline_bp_executor = DevopsPipelineBuildProcessExecutor(
            Deployment.objects.get(pk=deploy_id), build_process, stream
        )
        devops_pipeline_bp_executor.execute(metadata=metadata)
    else:
        k8s_bp_executor = K8sBuildProcessExecutor(Deployment.objects.get(pk=deploy_id), build_process, stream)
        k8s_bp_executor.execute(metadata=metadata)


def interrupt_build_proc(bp_id: UUID) -> bool:
    """Interrupt a build process

    :return: Whether the build process was successfully interrupted.
    :raises: DeployInterruptionFailed if the build process is not interruptable.
    """
    bp = BuildProcess.objects.get(pk=bp_id)
    if not bp.check_interruption_allowed():
        raise DeployInterruptionFailed()

    bp.set_int_requested_at()
    app = bp.app
    result = get_scheduler_client_by_app(app).interrupt_builder(app.namespace, name=generate_builder_name(app))
    return result
