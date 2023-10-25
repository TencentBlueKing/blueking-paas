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

from paas_wl.bk_app.deploy.actions.exec import AppCommandExecutor
from paas_wl.workloads.release_controller.hooks.entities import CommandTemplate
from paas_wl.workloads.release_controller.hooks.models import Command
from paasng.core.core.storages.redisdb import get_default_redis
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.utils.output import ConsoleStream, DeployStream, RedisWithModelStream

logger = logging.getLogger(__name__)


def exec_command(
    env: ModuleEnvironment,
    command_template: CommandTemplate,
    operator: str,
    stream_channel_id: Optional[str] = None,
    extra_envs: Optional[Dict] = None,
) -> str:
    """run a command in a built slug."""
    wl_app = env.wl_app
    build = wl_app.build_set.get(pk=command_template.build_id)
    cmd_obj = wl_app.command_set.new(
        type_=command_template.type,
        command=command_template.command,
        build=build,
        operator=operator,
    )
    execute_bg_command.delay(cmd_obj.uuid, stream_channel_id=stream_channel_id, extra_envs=extra_envs or {})
    return str(cmd_obj.uuid)


@shared_task
def execute_bg_command(uuid: str, stream_channel_id: Optional[str] = None, extra_envs: Optional[Dict] = None):
    """execute a command.

    :param uuid: pk of Command
    :param stream_channel_id: RedisStreamChannel id
    :param extra_envs: extra env vars
    """
    command = Command.objects.get(pk=uuid)
    stream: DeployStream
    executor: AppCommandExecutor

    # Make a new channel if stream_channel_id is given
    if stream_channel_id:
        stream_channel = StreamChannel(stream_channel_id, redis_db=get_default_redis())
        stream_channel.initialize()
        stream = RedisWithModelStream(command, stream_channel)
    else:
        stream = ConsoleStream()

    executor = AppCommandExecutor(command=command, stream=stream, extra_envs=extra_envs or {})
    executor.perform()
