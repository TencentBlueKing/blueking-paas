# -*- coding: utf-8 -*-
import abc
import json
import logging
import sys
from typing import TYPE_CHECKING, Optional

from blue_krill.redis_tools.messaging import StreamChannel
from typing_extensions import Protocol

if TYPE_CHECKING:
    from paas_wl.platform.applications.models.misc import OutputStream


logger = logging.getLogger(__name__)


class Stream(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def write_message(self, message, stream='STDOUT'):
        raise NotImplementedError

    @abc.abstractmethod
    def write_title(self, title):
        raise NotImplementedError

    @abc.abstractmethod
    def write_event(self, event_name: str, data: dict):
        raise NotImplementedError

    @staticmethod
    def cleanup_message(message):
        # Remove bad characters output by slugbuilder
        return message.replace('\x1b[1G', '')


class MessageWriter(Protocol):
    output_stream: 'OutputStream'


class ModelStream(Stream):
    def __init__(self, model: MessageWriter):
        self.model = model

    def write_message(self, message, stream='STDOUT'):
        """Write message to output stream"""
        message = self.cleanup_message(message)
        self.model.output_stream.write(line=message, stream=stream)


class RedisChannelStream(Stream):
    def __init__(self, stream_channel: Optional[StreamChannel]):
        self.stream_channel = stream_channel

    def write_message(self, message, stream='STDOUT'):
        if self.stream_channel:
            message = self.cleanup_message(message)
            self.stream_channel.publish_msg(message=json.dumps({'line': message, 'stream': stream}))

    def write_title(self, title):
        if self.stream_channel:
            self.stream_channel.publish(event='title', data=title)

    def write_event(self, event_name: str, data: dict):
        if self.stream_channel:
            self.stream_channel.publish(event=event_name, data=data)


class MixedStream(ModelStream, RedisChannelStream):
    def __init__(self, model: MessageWriter, stream_channel: Optional[StreamChannel]):
        ModelStream.__init__(self, model)
        RedisChannelStream.__init__(self, stream_channel)

    def write_message(self, message, stream='STDOUT'):
        ModelStream.write_message(self, message, stream)
        RedisChannelStream.write_message(self, message, stream)


class ConsoleStream(Stream):
    """Print message to Console"""

    @staticmethod
    def write_message(message, stream='STDOUT'):
        """Write message to output stream"""
        stream = sys.stderr if stream == 'STDERR' else sys.stdout
        logger.info(message)
        print(message, file=stream)

    @staticmethod
    def write_title(title):
        ConsoleStream.write_message(title)

    @staticmethod
    def write_event(event_name: str, data: dict):
        return print(f'[{event_name}: {data}')
