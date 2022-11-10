# -*- coding: utf-8 -*-
import logging
from typing import Dict, Optional

from blue_krill.redis_tools.messaging import StreamChannel
from celery import shared_task

from paas_wl.platform.applications.models.app import EngineApp
from paas_wl.platform.applications.models.release import Release
from paas_wl.release_controller.hooks.models import Command
from paas_wl.release_controller.process.callbacks import ArchiveResultHandler, ReleaseResultHandler
from paas_wl.release_controller.process.wait import wait_for_all_stopped, wait_for_release
from paas_wl.resources.actions.archive import ArchiveOperationController
from paas_wl.resources.actions.deploy import AppDeploy
from paas_wl.resources.actions.exec import AppCommandExecutor
from paas_wl.utils.redisdb import get_stream_channel_redis
from paas_wl.utils.stream import ConsoleStream, MixedStream, Stream

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
    app = release.app
    AppDeploy(app=app, release=release, extra_envs=extra_envs).perform()

    # NOTE: 更新环境变量时触发的 release 不提供 deployment_id, 此时无需触发 wait_for_release
    if deployment_id:
        wait_for_release(
            engine_app=app,
            release_version=release.version,
            result_handler=ReleaseResultHandler,
            extra_params={"deployment_id": deployment_id},
        )


def archive_app(app: EngineApp, operation_id: str):
    """stop all processes of the app"""
    ArchiveOperationController(engine_app=app, operation_id=operation_id).start()

    wait_for_all_stopped(
        engine_app=app,
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
