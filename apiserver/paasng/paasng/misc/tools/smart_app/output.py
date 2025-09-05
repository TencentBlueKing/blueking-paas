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

import abc
import json
import sys
from typing import Dict, List, Optional

from blue_krill.redis_tools.messaging import StreamChannel

from paasng.core.core.storages.redisdb import get_default_redis
from paasng.misc.tools.smart_app.models import SmartBuildLog, SmartBuildRecord
from paasng.platform.engine.utils.output import MessageWriter, ModelStream, StreamType, sanitize_message


class SmartBuildStream(metaclass=abc.ABCMeta):
    """Abstraction class of s-mart build stream"""

    @abc.abstractmethod
    def write_title(self, title: str):
        raise NotImplementedError

    @abc.abstractmethod
    def write_message(self, message: str, stream: Optional[StreamType] = None):
        raise NotImplementedError

    @abc.abstractmethod
    def write_event(self, event_name: str, data: dict):
        raise NotImplementedError

    @abc.abstractmethod
    def close(self):
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def form_smart_build_id(cls, smart_build_id: str) -> "RedisChannelStream":
        raise NotImplementedError


class RedisChannelStream(SmartBuildStream):
    """Stream using redis channel"""

    def __init__(self, channel: StreamChannel):
        self.channel = channel

    def write_title(self, title: str):
        self.channel.publish(event="title", data=json.dumps({"title": title}))

    def write_message(self, message: str, stream=StreamType.STDOUT.value):
        message = sanitize_message(message)
        self.channel.publish_msg(message=json.dumps({"line": message, "stream": stream}))

    def write_event(self, event_name: str, data: Dict):
        self.channel.publish(event=event_name, data=json.dumps(data))

    def close(self):
        self.channel.close()

    @classmethod
    def form_smart_build_id(cls, smart_build_id: str) -> "RedisChannelStream":
        channel = StreamChannel(smart_build_id, redis_db=get_default_redis())
        channel.initialize()
        return cls(channel)


class ConsoleStream(SmartBuildStream):
    """Stream using console, useful for unit tests"""

    def write_title(self, title):
        print(f"[TITLE]: {title}")

    def write_message(self, message, stream=StreamType.STDOUT):
        f = sys.stderr if stream == StreamType.STDERR else sys.stdout
        print(message, file=f)

    def write_event(self, event_name: str, data: dict):
        return print(f"[{event_name}: {data}")

    def close(self):
        pass

    @classmethod
    def form_smart_build_id(cls, smart_build_id: str):
        return cls()


class NullStream(SmartBuildStream):
    def write_title(self, title: str):
        pass

    def write_message(self, message: str, stream: Optional[StreamType] = None):
        pass

    def write_event(self, event_name: str, data: dict):
        pass

    def close(self):
        pass

    @classmethod
    def form_smart_build_id(cls, smart_build_id: str):
        return cls()


class RedisWithModelStream(RedisChannelStream):
    """A modified redis channel stream which writes message to both model's output_stream
    and redis channel.

    :param model: A model which has output_stream field
    :param steam_channel: A redis channel stream
    """

    def __init__(self, model: MessageWriter, stream_channel: StreamChannel):
        self.model_stream = ModelStream(model)
        super().__init__(stream_channel)

    def write_message(self, message, stream="STDOUT"):
        self.model_stream.write_message(message, stream)
        super().write_message(message, stream)


def get_default_stream(smart_build: SmartBuildRecord) -> RedisChannelStream:
    stream_channel = StreamChannel(smart_build.uuid, redis_db=get_default_redis())
    stream_channel.initialize()
    return RedisChannelStream(stream_channel)


def make_channel_stream(
    smart_build: SmartBuildRecord, stream_channel_id: Optional[str] = None
) -> RedisWithModelStream:
    """Return the stream object which is able to write message to both the redis channel and the database.

    :param stream_channel_id: if provided, will use this value instead of `smart_build.id`
    """
    # ensure SmartBuild has a SmartBuildLog instance stored in smart_build.stream
    if not getattr(smart_build, "stream", None):
        stream_obj = SmartBuildLog.object.create()
        smart_build.stream = stream_obj
        smart_build.save(update_fields=["stream"])

    redis_channel = StreamChannel(stream_channel_id or smart_build.uuid, redis_db=get_default_redis())
    redis_channel.initialize()
    return RedisWithModelStream(smart_build.stream, redis_channel)


def get_all_logs(smart_build: SmartBuildRecord) -> str:
    """Get all logs of the given smart build, error detail are also included.

    :param smart_build: The SmartBuild object
    :return: All logs of the current smart build
    """

    if not getattr(smart_build, "stream", None):
        return "" if not smart_build.err_detail else "\n" + smart_build.err_detail

    lines = serialize_stream_logs(smart_build.stream)
    return "".join(lines) + "\n" + (smart_build.err_detail or "")


def serialize_stream_logs(output_stream: SmartBuildLog) -> List[str]:
    """Serialize all logs of the given output_stream object."""
    return [line.line for line in output_stream.lines.all().order_by("created")]
