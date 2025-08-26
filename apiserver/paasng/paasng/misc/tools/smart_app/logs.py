# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

from typing import List, Optional

from paas_wl.bk_app.applications.models.misc import OutputStream
from paasng.core.core.storages.redisdb import get_default_redis
from paasng.misc.tools.smart_app.models.smart_build import SmartBuild
from paasng.platform.engine.utils.output import RedisWithModelStream, StreamChannel


def make_channel_stream(
    smart_build: SmartBuild, stream_type: str, stream_channel_id: Optional[str] = None
) -> RedisWithModelStream:
    """Return the stream object which is able to write message to both the redis channel and the database.

    :param stream_type: choices: 'preparation_phase', 'build_phase'
    :param stream_channel_id: if provided, will use this value instead of `smart_build.id`
    """
    # {type: stream property name}
    stream_types = {
        "preparation_phase": "preparation_stream",
        "build_phase": "build_stream",
    }
    if stream_type not in stream_types:
        raise ValueError(stream_type)

    db_stream = getattr(SmartBuildLogStreams(smart_build), stream_types[stream_type])
    if not db_stream:
        raise ValueError("The output stream object does not exist")

    redis_channel = StreamChannel(stream_channel_id or smart_build.id, redis_db=get_default_redis())
    redis_channel.initialize()
    return RedisWithModelStream(db_stream, redis_channel)


class SmartBuildLogStreams:
    """Manages the log streams(in databases) for a smart build."""

    stream_uuid_fields = {"preparation_stream_id", "build_stream_id"}

    def __init__(self, smart_build: SmartBuild):
        self.smart_build = smart_build

    @property
    def preparation_stream(self) -> Optional[OutputStream]:
        return self._get_stream(self.smart_build, "preparation_stream_id")

    @property
    def preparation_stream_for_write(self) -> OutputStream:
        return self._get_stream_for_write(self.smart_build, "preparation_stream_id")

    @property
    def build_stream(self) -> Optional[OutputStream]:
        """Get the stream object for building process if exists."""
        if not self.smart_build.uuid:
            return None
        return self.smart_build.smart_build_stream

    def _get_stream_for_write(self, smart_build: SmartBuild, field_name: str) -> OutputStream:
        """Return the output stream object, will initialize the object if not exist.

        :param smart_build: The SmartBuild object that holds the stream uuids.
        :param field_name: The field name that stores the stream uuid.
        :return: The output stream object for writing logs to.
        """
        if field_name not in self.stream_uuid_fields:
            raise ValueError(field_name)

        if not getattr(smart_build, field_name, None):
            stream = OutputStream.objects.create()
            setattr(smart_build, field_name, stream.id)
            smart_build.save(update_fields=[field_name])
        return OutputStream.objects.get(pk=getattr(smart_build, field_name, None))

    def _get_stream(self, smart_build: SmartBuild, field_name: str) -> Optional[OutputStream]:
        """Return the output stream object if exists.

        :param smart_build: The SmartBuild object that holds the stream uuids.
        :param field_name: The field name that stores the stream uuid.
        :return: None if the stream object has not been initialized yet.
        """
        if field_name not in self.stream_uuid_fields:
            raise ValueError(field_name)

        try:
            return OutputStream.objects.get(pk=getattr(smart_build, field_name, None))
        except OutputStream.DoesNotExist:
            return None


def get_all_logs(smart_build: SmartBuild) -> str:
    """Get all logs of the given smart build, error detail are also included.

    :param smart_build: The SmartBuild object
    :return: All logs of the current smart build
    """
    lines = []
    log_streams = SmartBuildLogStreams(smart_build)
    streams: List[Optional[OutputStream]] = [
        log_streams.preparation_stream,
        log_streams.build_stream,
    ]
    for s in streams:
        if s:
            lines.extend(serialize_stream_logs(s))
    return "".join(lines) + "\n" + (smart_build.err_detail or "")


def serialize_stream_logs(output_stream: OutputStream) -> List[str]:
    """Serialize all logs of the given output_stream object."""
    return [line.line for line in output_stream.lines.all().order_by("created")]
