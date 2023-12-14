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
import abc
import json
import sys
from enum import Enum
from typing import Optional, Protocol

from blue_krill.redis_tools.messaging import StreamChannel
from django.conf import settings

from paasng.core.core.storages.redisdb import get_default_redis
from paasng.platform.engine.models import Deployment
from paasng.utils import termcolors


def make_style(*args, **kwargs):
    colorful = termcolors.make_style(*args, **kwargs)

    def dynamic_style(text):
        if settings.COLORFUL_TERMINAL_OUTPUT:
            return colorful(text)
        return termcolors.no_color(text)

    return dynamic_style


class Style:
    """
    Valid colors:
        ANSI Color: 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'
        XTerm Color: [0-256]
        Hex Color: #000000 ~ #FFFFFF
    see also: https://en.wikipedia.org/wiki/X11_color_names#Clashes_between_web_and_X11_colors_in_the_CSS_color_scheme

    Valid options:
        'bold', 'underscore', 'blink', 'reverse', 'conceal', 'noreset'
    """

    Title = make_style(fg="#c4c6cc", opts=("bold",))
    Error = make_style(fg="#e82f2f", opts=("bold",))
    Warning = make_style(fg="#ff9c01", opts=("bold",))
    Comment = make_style(fg="#3a84ff", opts=("bold",))
    NoColor = termcolors.no_color

    Black = make_style(fg="black", opts=("bold",))
    Red = make_style(fg="red", opts=("bold",))
    Green = make_style(fg="green", opts=("bold",))
    Yellow = make_style(fg="yellow", opts=("bold",))
    Blue = make_style(fg="blue", opts=("bold",))
    Magenta = make_style(fg="magenta", opts=("bold",))
    Cyan = make_style(fg="cyan", opts=("bold",))
    White = make_style(fg="white", opts=("bold",))


class StreamType(str, Enum):
    STDOUT = "STDOUT"
    STDERR = "STDERR"


class DeployStream(metaclass=abc.ABCMeta):
    """Abstraction class of deployment stream"""

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
    def from_deployment_id(cls, deployment_id: str):
        raise NotImplementedError


class RedisChannelStream(DeployStream):
    """Stream using redis channel"""

    def __init__(self, channel: StreamChannel):
        self.channel = channel

    def write_title(self, title):
        return self.channel.publish(event="title", data=title)

    def write_message(self, message, stream=StreamType.STDOUT.value):
        return self.channel.publish_msg(message=json.dumps({"line": message, "stream": str(stream)}))

    def write_event(self, event_name: str, data: dict):
        return self.channel.publish(event=event_name, data=json.dumps(data))

    def close(self):
        return self.channel.close()

    @classmethod
    def from_deployment_id(cls, deployment_id: str) -> "RedisChannelStream":
        stream_channel = StreamChannel(deployment_id, redis_db=get_default_redis())
        stream_channel.initialize()
        return cls(stream_channel)


class ConsoleStream(DeployStream):
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
    def from_deployment_id(cls, deployment_id: str):
        return cls()


class MessageWriter(Protocol):
    """A protocol for types which has output_stream field"""

    def write(self, line: str, stream: Optional[str]):
        ...


class ModelStream:
    """Stream using model's output_stream field"""

    def __init__(self, model: MessageWriter):
        self.model = model

    def write_message(self, message, stream="STDOUT"):
        """Write message to output stream"""
        message = self.cleanup_message(message)
        self.model.write(line=message, stream=stream)

    @staticmethod
    def cleanup_message(message):
        # Remove bad characters output by slugbuilder
        # NOTE: Only `ModelStream` use this method to cleanup message at this moment,
        # consider to make other stream classes to use this method if needed.
        return message.replace("\x1b[1G", "")


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


def get_default_stream(deployment: Deployment) -> RedisChannelStream:
    stream_channel = StreamChannel(deployment.id, redis_db=get_default_redis())
    stream_channel.initialize()
    return RedisChannelStream(stream_channel)
