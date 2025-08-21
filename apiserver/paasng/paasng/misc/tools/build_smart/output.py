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

import json
import uuid
from functools import lru_cache
from typing import Dict

from blue_krill.data_types.enum import StrStructuredEnum
from blue_krill.redis_tools.messaging import StreamChannel

from paasng.core.core.storages.redisdb import get_default_redis
from paasng.misc.tools.build_smart.models import SmartBuildRecord


class StreamType(StrStructuredEnum):
    STDOUT = "STDOUT"
    STDERR = "STDERR"


class StreamWriter:
    """Lightweight packaging, directly using StreamChannel"""

    def __init__(self, channel: StreamChannel):
        self.channel = channel

    def write_title(self, title: str):
        self.channel.publish(event="title", data=json.dumps({"title": title}))

    def write_message(self, message: str, stream=StreamType.STDOUT.value):
        self.channel.publish_msg(message=json.dumps({"line": message, "stream": stream}))

    def write_event(self, event_name: str, data: Dict):
        self.channel.publish(event=event_name, data=json.dumps(data))

    def close(self):
        self.channel.close()


def get_default_stream(smart_build: SmartBuildRecord) -> StreamWriter:
    return StreamWriter(_get_stream_channel(smart_build.id))


@lru_cache(maxsize=128)
def _get_stream_channel(smart_build_id: uuid.UUID) -> StreamChannel:
    stream_channel = StreamChannel(smart_build_id, redis_db=get_default_redis())
    stream_channel.initialize()
    return stream_channel
