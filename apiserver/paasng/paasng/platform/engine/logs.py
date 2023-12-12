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
from typing import List, Optional

from paas_wl.bk_app.applications.models.build import BuildProcess
from paas_wl.bk_app.applications.models.misc import OutputStream
from paasng.core.core.storages.redisdb import get_default_redis
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.utils.output import RedisWithModelStream, StreamChannel


def make_channel_stream(
    deployment: Deployment, stream_type: str, stream_channel_id: Optional[str] = None
) -> RedisWithModelStream:
    """Return the stream object which is able to write message to both the redis channel and the database.

    :param stream_type: choices: 'main', 'preparation', 'build_proc', 'pre_release_cmd'
    :param stream_channel_id: if provided, will use this value instead of `deployment.id`
    """
    # {type: stream property name}
    stream_types = {
        "build_proc": "build_proc_stream",
        "pre_release_cmd": "pre_release_cmd_stream",
        # Always create the stream if needed by using "...for_write"
        "main": "main_stream_for_write",
        "preparation": "preparation_stream_for_write",
    }
    if stream_type not in stream_types:
        raise ValueError(stream_type)

    db_stream = getattr(DeploymentLogStreams(deployment), stream_types[stream_type])
    if not db_stream:
        raise ValueError("The output stream object does not exist")

    redis_channel = StreamChannel(stream_channel_id or deployment.id, redis_db=get_default_redis())
    redis_channel.initialize()
    return RedisWithModelStream(db_stream, redis_channel)


class DeploymentLogStreams:
    """Manages the log streams(in databases) for a deployment."""

    stream_uuid_fields = {"preparation_stream_id", "main_stream_id"}

    def __init__(self, deployment: Deployment):
        self.deployment = deployment

    @property
    def main_stream(self) -> Optional[OutputStream]:
        return self._get_stream(self.deployment, "main_stream_id")

    @property
    def main_stream_for_write(self) -> OutputStream:
        return self._get_stream_for_write(self.deployment, "main_stream_id")

    @property
    def preparation_stream(self) -> Optional[OutputStream]:
        return self._get_stream(self.deployment, "preparation_stream_id")

    @property
    def preparation_stream_for_write(self) -> OutputStream:
        return self._get_stream_for_write(self.deployment, "preparation_stream_id")

    @property
    def build_proc_stream(self) -> Optional[OutputStream]:
        """Get the stream object for building process if exists."""
        if not self.deployment.build_process_id:
            return None
        build_proc = BuildProcess.objects.get(pk=self.deployment.build_process_id)
        return build_proc.output_stream

    @property
    def pre_release_cmd_stream(self) -> Optional[OutputStream]:
        """Get the stream object for pre-release command if exists."""
        if not self.deployment.pre_release_id:
            return None
        wl_app = self.deployment.app_environment.wl_app
        command = wl_app.command_set.get(pk=self.deployment.pre_release_id)
        return command.output_stream

    def _get_stream_for_write(self, deployment: Deployment, field_name: str) -> OutputStream:
        """Return the output stream object, will initialize the object if not exist.

        :param deployment: The deployment object that holds the stream uuids.
        :param field_name: The field name that stores the stream uuid.
        :return: The output stream object for writing logs to.
        """
        if field_name not in self.stream_uuid_fields:
            raise ValueError(field_name)

        if not getattr(deployment, field_name, None):
            s = OutputStream.objects.create()
            setattr(deployment, field_name, s.uuid)
            deployment.save(update_fields=[field_name])
        return OutputStream.objects.get(pk=getattr(deployment, field_name, None))

    def _get_stream(self, deployment: Deployment, field_name: str) -> Optional[OutputStream]:
        """Return the output stream object, will initialize the stream if not exist.

        :param deployment: The deployment object that holds the stream uuids.
        :param field_name: The field name that stores the stream uuid.
        :return: None if the stream object has not been initialized yet.
        """
        if field_name not in self.stream_uuid_fields:
            raise ValueError(field_name)

        try:
            return OutputStream.objects.get(pk=getattr(deployment, field_name, None))
        except OutputStream.DoesNotExist:
            return None


def get_all_logs(d: Deployment) -> str:
    """Get all logs of the given deployment, error detail are also included.

    :param d: The Deployment object
    :return: All logs of the current deployment
    """
    lines = []
    log_streams = DeploymentLogStreams(d)
    # TODO: 当前暂不包含“准备阶段”和“检测部署结果”这两个步骤的日志，将在未来版本添加
    streams: List[Optional[OutputStream]] = [
        log_streams.preparation_stream,
        log_streams.build_proc_stream,
        log_streams.pre_release_cmd_stream,
        log_streams.main_stream,
    ]
    for s in streams:
        if s:
            lines.extend(serialize_stream_logs(s))
    return "".join(lines) + "\n" + (d.err_detail or "")


def serialize_stream_logs(output_stream: OutputStream) -> List[str]:
    """Serialize all logs of the given output_stream object."""
    return [polish_line(line.line) for line in output_stream.lines.all().order_by("created")]


def polish_line(line: str) -> str:
    """Return the line with special characters removed"""
    return line.replace("\x1b[1G", "")
