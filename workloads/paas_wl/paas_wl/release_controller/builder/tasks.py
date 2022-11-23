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

from blue_krill.redis_tools.messaging import StreamChannel
from celery import shared_task

from paas_wl.platform.applications.models.build import BuildProcess
from paas_wl.release_controller.builder.executor import BuildProcessExecutor
from paas_wl.utils.redisdb import get_stream_channel_redis
from paas_wl.utils.stream import ConsoleStream, MixedStream, Stream

logger = logging.getLogger(__name__)


@shared_task
def start_build_process(uuid, stream_channel_id=None, metadata=None):
    """Start a new build process"""
    build_process = BuildProcess.objects.get(pk=uuid)
    # Make a new channel if stream_channel_id is given

    stream: Stream
    if stream_channel_id:
        stream_channel = StreamChannel(stream_channel_id, redis_db=get_stream_channel_redis())
        stream_channel.initialize()
        stream = MixedStream(build_process, stream_channel)
    else:
        stream = ConsoleStream()

    bp_executor = BuildProcessExecutor(build_process, stream)
    bp_executor.execute(metadata=metadata)
