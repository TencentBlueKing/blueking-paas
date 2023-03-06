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

from blue_krill.redis_tools.messaging import StreamChannel
from celery import shared_task

from paas_wl.platform.applications.models.release import Release
from paas_wl.release_controller.hooks.models import Command
from paas_wl.release_controller.process.callbacks import ArchiveResultHandler, ReleaseResultHandler
from paas_wl.release_controller.process.wait import wait_for_all_stopped, wait_for_release
from paas_wl.resources.actions.archive import ArchiveOperationController
from paas_wl.resources.actions.deploy import AppDeploy
from paas_wl.resources.actions.exec import AppCommandExecutor
from paas_wl.utils.redisdb import get_stream_channel_redis
from paas_wl.utils.stream import ConsoleStream, MixedStream, Stream
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


def release_app(
    release: Release,
    deployment_id: Optional[str],
    extra_envs: Dict,
):
    """execute Release

    :param release: the release instance
    :param deployment_id: RedisStreamChannel id
    :param extra_envs:
    """
    wl_app = release.app
    AppDeploy(app=wl_app, release=release, extra_envs=extra_envs).perform()

    # NOTE: 更新环境变量时触发的 release 不提供 deployment_id, 此时无需触发 wait_for_release
    if deployment_id:
        wait_for_release(
            wl_app=wl_app,
            release_version=release.version,
            result_handler=ReleaseResultHandler,
            extra_params={"deployment_id": deployment_id},
        )


def archive_env(env: ModuleEnvironment, operation_id: str):
    """stop all processes of the app"""
    ArchiveOperationController(env=env, operation_id=operation_id).start()

    wait_for_all_stopped(
        wl_app=env.wl_app,
        result_handler=ArchiveResultHandler,
        extra_params={"operation_id": operation_id},
    )


@shared_task
def run_command(uuid: str, stream_channel_id: Optional[str] = None, extra_envs: Optional[Dict] = None):
    """execute a command.

    :param uuid: pk of Command
    :param stream_channel_id: RedisStreamChannel id
    """
    command = Command.objects.get(pk=uuid)
    stream: Stream
    executor: AppCommandExecutor

    # Make a new channel if stream_channel_id is given
    if stream_channel_id:
        stream_channel = StreamChannel(stream_channel_id, redis_db=get_stream_channel_redis())
        stream_channel.initialize()
        stream = MixedStream(command, stream_channel)
    else:
        stream = ConsoleStream()

    executor = AppCommandExecutor(command=command, stream=stream, extra_envs=extra_envs or {})
    executor.perform()
