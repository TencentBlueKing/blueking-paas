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

from paas_wl.release_controller.hooks.models import Command
from paas_wl.resources.actions.exec import AppCommandExecutor
from paas_wl.utils.redisdb import get_default_redis
from paas_wl.utils.stream import ConsoleStream, MixedStream, Stream

logger = logging.getLogger(__name__)


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
        stream_channel = StreamChannel(stream_channel_id, redis_db=get_default_redis())
        stream_channel.initialize()
        stream = MixedStream(command, stream_channel)
    else:
        stream = ConsoleStream()

    executor = AppCommandExecutor(command=command, stream=stream, extra_envs=extra_envs or {})
    executor.perform()
