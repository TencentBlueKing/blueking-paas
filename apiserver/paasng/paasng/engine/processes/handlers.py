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
from typing import Dict, Iterable

from blue_krill.redis_tools.messaging import StreamChannel
from django.dispatch.dispatcher import receiver

from paasng.engine.processes.events import (
    ProcessBaseEvent,
    ProcessEvent,
    ProcessEventType,
    ProcInstEvent,
    ProcInstEventType,
)
from paasng.engine.processes.wait import processes_updated
from paasng.engine.utils.output import ConsoleStream, DeployStream, RedisChannelStream
from paasng.platform.core.storages.redisdb import get_default_redis

logger = logging.getLogger(__name__)


@receiver(processes_updated)
def _on_processes_updated(sender, events: Iterable[ProcessBaseEvent], extra_params: Dict, **kwargs):
    """Update stream when processes was updated"""
    deployment_id = extra_params.get('deployment_id')
    stream: DeployStream

    if deployment_id:
        channel = StreamChannel(deployment_id, get_default_redis())
        stream = RedisChannelStream(channel)
    else:
        stream = ConsoleStream()

    for event in events:
        logger.debug('Render message for process update event: %s', event)
        try:
            msg = render_event_message(event)
        except Exception:
            logger.exception(f'unable to render process event: {event}')
            return
        stream.write_message(f'> {msg}')


def render_event_message(event: ProcessBaseEvent) -> str:
    """Render event to message"""
    if isinstance(event, ProcessEvent):
        return render_process_event_message(event)
    elif isinstance(event, ProcInstEvent):
        return render_instance_event_message(event)
    raise TypeError('invalid event type')


def render_process_event_message(event: ProcessEvent) -> str:
    """Render a process event to a human readable message"""
    type_msg_map = {
        ProcessEventType.CREATED: 'New process "{proc.type}" was created [➕]',
        ProcessEventType.REMOVED: 'Process "{proc.type}" was removed [🗑️]',
        ProcessEventType.UPDATED_COMMAND: 'Process "{proc.type}"\'s command was updated to "{proc.command}" [ℹ️]',
        ProcessEventType.UPDATED_REPLICAS: 'Process "{proc.type}"\'s replicas was updated to {proc.replicas} [ℹ️]',
    }
    return type_msg_map[event.type].format(proc=event.invoker)


def render_instance_event_message(event: ProcInstEvent) -> str:
    """Render a instance event to a human readable message"""
    type_msg_map = {
        ProcInstEventType.CREATED: '{proc.type} instance "{inst.shorter_name}" was created [➕]',
        ProcInstEventType.REMOVED: '{proc.type} instance "{inst.shorter_name}" was removed [🗑️]',
        ProcInstEventType.UPDATED_BECOME_READY: '{proc.type} instance "{inst.shorter_name}" is ready [✅]',
        ProcInstEventType.UPDATED_BECOME_NOT_READY: '{proc.type} instance "{inst.shorter_name}" become not ready [⚠️]',
        ProcInstEventType.UPDATED_RESTARTED: '{proc.type} instance "{inst.shorter_name}" has been restarted [⚠️]',
    }
    return type_msg_map[event.type].format(proc=event.process, inst=event.invoker)
