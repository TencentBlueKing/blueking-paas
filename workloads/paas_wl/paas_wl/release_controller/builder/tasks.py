# -*- coding: utf-8 -*-
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
