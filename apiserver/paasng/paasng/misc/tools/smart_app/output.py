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
from typing import Dict, List

from blue_krill.redis_tools.messaging import StreamChannel

from paasng.core.core.storages.redisdb import get_default_redis
from paasng.misc.tools.smart_app.models import SmartBuildLog, SmartBuildRecord
from paasng.platform.engine.utils.output import MessageWriter, ModelStream, StreamType, sanitize_message


class SmartBuildStream(metaclass=abc.ABCMeta):
    """Abstraction class of s-mart build stream"""

    @abc.abstractmethod
    def write_title(self, title: str): ...

    @abc.abstractmethod
    def write_message(self, message: str, stream: StreamType | None = None): ...

    @abc.abstractmethod
    def write_event(self, event_name: str, data: Dict): ...

    @abc.abstractmethod
    def close(self): ...

    @classmethod
    @abc.abstractmethod
    def form_smart_build_id(cls, smart_build_id: str) -> "SmartBuildStream": ...


class RedisChannelStream(SmartBuildStream):
    """Stream using redis channel"""

    def __init__(self, channel: StreamChannel):
        self.channel = channel

    def write_title(self, title):
        self.channel.publish(event="title", data=json.dumps({"title": title}))

    def write_message(self, message, stream=None):
        stream = stream or StreamType.STDOUT
        self.channel.publish_msg(message=json.dumps({"line": sanitize_message(message), "stream": stream.value}))

    def write_event(self, event_name, data):
        self.channel.publish(event=event_name, data=json.dumps(data))

    def close(self):
        self.channel.close()

    @classmethod
    def form_smart_build_id(cls, smart_build_id):
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
    def form_smart_build_id(cls, smart_build_id):
        return cls()


class NullStream(SmartBuildStream):
    def write_title(self, title):
        pass

    def write_message(self, message, stream=None):
        pass

    def write_event(self, event_name, data):
        pass

    def close(self):
        pass

    @classmethod
    def form_smart_build_id(cls, smart_build_id):
        return cls()


class RedisWithModelStream(RedisChannelStream):
    """Streams that write to both the database and Redis channels

    :param model: A model which has output_stream field
    :param steam_channel: A redis channel stream
    """

    def __init__(self, model: MessageWriter, stream_channel: StreamChannel):
        self.model_stream = ModelStream(model)
        super().__init__(stream_channel)

    def write_title(self, title: str):
        self.model_stream.write_message(f"[TITLE]: {title}\n", StreamType.STDOUT.value)
        super().write_title(title)

    def write_message(self, message: str, stream: StreamType | None = None):
        stream = stream or StreamType.STDOUT
        self.model_stream.write_message(message, stream.value)
        super().write_message(message, stream)


def get_default_stream(smart_build: SmartBuildRecord):
    stream_channel = StreamChannel(smart_build.uuid, redis_db=get_default_redis())
    stream_channel.initialize()
    return RedisChannelStream(stream_channel)


def make_channel_stream(smart_build: SmartBuildRecord, stream_channel_id: str | None = None):
    """Create a stream object that writes to both the database and Redis channels

    :param smart_build: The build record instance
    :param stream_channel_id: If provided, will use this value instead of `smart_build.id`
    :return: The created stream object
    """

    if not getattr(smart_build, "stream", None):
        smart_build.stream = SmartBuildLog.objects.create()
        smart_build.save(update_fields=["stream"])

    redis_channel = StreamChannel(stream_channel_id or str(smart_build.uuid), redis_db=get_default_redis())
    redis_channel.initialize()
    return RedisWithModelStream(smart_build.stream, redis_channel)


def get_all_logs(smart_build: SmartBuildRecord):
    """Get all logs of the build, including error details"""

    if not getattr(smart_build, "stream", None):
        return "\n" + smart_build.err_detail if smart_build.err_detail else ""

    lines = serialize_stream_logs(smart_build.stream)
    return "".join(lines) + "\n" + (smart_build.err_detail or "")


def serialize_stream_logs(output_stream: SmartBuildLog) -> List[str]:
    """Serialize all logs to the output stream"""

    return [line.line for line in output_stream.lines.order_by("created")]
